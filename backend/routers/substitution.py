# routers/substitution.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from dependencies import get_db, require_any_admin, get_current_user
from models.user import User
from models.substitution import Substitution, SubstitutionRequest, SubstitutionStatus
from models.timetable import Timetable, TimetableEntry, EntryType
from models.global_booking import GlobalBooking
from models.faculty import Faculty
from models.subject import Subject
from models.room import Room
from schemas.substitution import (
    ReportAbsenceRequest,
    SubstitutionResponse,
    SubstitutionCandidateResponse,
    SubstitutionDetailResponse,
    SubstitutionRequestResponse,
)
from core.notifications.dispatcher import dispatch_event
from core.substitution.finder import find_substitute_candidates
from core.substitution.escalator import check_and_escalate, send_to_next_candidate
from config import settings
from sqlalchemy.exc import IntegrityError
import uuid
from datetime import datetime, timezone, date
import structlog

log = structlog.get_logger()

router = APIRouter(prefix="/substitution", tags=["Substitution"])


@router.post("/report-absence")
async def report_absence(
    request: ReportAbsenceRequest,
    current_user: User = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Report a faculty absence and trigger automatic substitute finding.
    Creates the substitution, finds candidates, sends first request.
    Returns <100ms (candidate finding is lightweight).
    """
    # Validate timetable entry exists
    entry = await db.get(TimetableEntry, request.entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Timetable entry not found")

    # Get timetable to verify dept ownership and get college_id
    tt = await db.get(Timetable, entry.timetable_id)
    if not tt or tt.dept_id != current_user.dept_id:
        raise HTTPException(status_code=403, detail="Entry does not belong to your department")

    # Create substitution record
    substitution = Substitution(
        substitution_id=str(uuid.uuid4()),
        original_entry_id=request.entry_id,
        original_faculty_id=entry.faculty_id,
        absence_date=request.absence_date,
        reason=request.reason,
        status=SubstitutionStatus.PENDING,
    )
    db.add(substitution)
    await db.commit()

    # Find candidates
    candidates = await find_substitute_candidates(
        original_faculty_id=entry.faculty_id,
        subject_id=entry.subject_id,
        day=entry.day,
        period=entry.period,
        college_id=current_user.college_id,
        dept_id=current_user.dept_id,
        db=db,
    )

    if not candidates:
        substitution.status = SubstitutionStatus.CANCELLED
        substitution.resolved_at = datetime.now(timezone.utc)
        db.add(substitution)
        await db.commit()
        return {
            "substitution_id": substitution.substitution_id,
            "status": "CANCELLED",
            "message": "No eligible substitute candidates found.",
            "candidates": [],
        }

    # Send to first candidate (escalation level 1)
    sub_request = await send_to_next_candidate(
        substitution_id=substitution.substitution_id,
        candidates=candidates,
        escalation_level=1,
        db=db,
    )

    return {
        "substitution_id": substitution.substitution_id,
        "status": "PENDING",
        "message": f"Request sent to {candidates[0]['name']} (score: {candidates[0]['score']})",
        "candidates": candidates,
        "current_request_id": sub_request.request_id if sub_request else None,
    }


@router.get("/candidates/{entry_id}", response_model=list[SubstitutionCandidateResponse])
async def get_candidates(
    entry_id: str,
    current_user: User = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Preview substitute candidates for a timetable entry WITHOUT creating a substitution.
    Useful for "what-if" analysis before reporting absence.
    """
    entry = await db.get(TimetableEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Timetable entry not found")

    candidates = await find_substitute_candidates(
        original_faculty_id=entry.faculty_id,
        subject_id=entry.subject_id,
        day=entry.day,
        period=entry.period,
        college_id=current_user.college_id,
        dept_id=current_user.dept_id,
        db=db,
    )

    return [SubstitutionCandidateResponse(**c) for c in candidates]


@router.post("/accept/{request_id}")
async def accept_substitution(
    request_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Accept a substitution request.
    Updates the substitution, creates a new timetable entry (type=SUBSTITUTION),
    updates global_bookings, and notifies all parties.
    """
    # Find the request
    sub_req = await db.get(SubstitutionRequest, request_id)
    if not sub_req:
        raise HTTPException(status_code=404, detail="Substitution request not found")

    if sub_req.status != SubstitutionStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Request already {sub_req.status.value}",
        )

    # Get the parent substitution
    substitution = await db.get(Substitution, sub_req.substitution_id)
    if not substitution:
        raise HTTPException(status_code=404, detail="Substitution record not found")

    # Get the original timetable entry
    original_entry = await db.get(TimetableEntry, substitution.original_entry_id)
    if not original_entry:
        raise HTTPException(status_code=404, detail="Original timetable entry not found")

    # Mark request as accepted
    sub_req.status = SubstitutionStatus.ACCEPTED
    sub_req.response_at = datetime.now(timezone.utc)
    db.add(sub_req)

    # Mark substitution as accepted
    substitution.status = SubstitutionStatus.ACCEPTED
    substitution.substitute_faculty_id = sub_req.candidate_faculty_id
    substitution.resolved_at = datetime.now(timezone.utc)
    db.add(substitution)

    # Cancel any other pending requests for this substitution
    other_pending = await db.execute(
        select(SubstitutionRequest).where(
            and_(
                SubstitutionRequest.substitution_id == sub_req.substitution_id,
                SubstitutionRequest.request_id != request_id,
                SubstitutionRequest.status == SubstitutionStatus.PENDING,
            )
        )
    )
    for other_req in other_pending.scalars().all():
        other_req.status = SubstitutionStatus.CANCELLED
        other_req.response_at = datetime.now(timezone.utc)
        db.add(other_req)

    # Create substitution timetable entry
    sub_entry = TimetableEntry(
        entry_id=str(uuid.uuid4()),
        timetable_id=original_entry.timetable_id,
        day=original_entry.day,
        period=original_entry.period,
        subject_id=original_entry.subject_id,
        faculty_id=sub_req.candidate_faculty_id,
        room_id=original_entry.room_id,
        entry_type=EntryType.SUBSTITUTION,
        batch=original_entry.batch,
    )
    db.add(sub_entry)

    # Release original faculty's global booking and create substitute's booking
    tt = await db.get(Timetable, original_entry.timetable_id)
    college_id = ""
    if tt:
        from models.college import Department
        dept = await db.get(Department, tt.dept_id)
        college_id = dept.college_id if dept else ""

    # Remove original faculty's booking for this slot
    original_booking_result = await db.execute(
        select(GlobalBooking).where(
            and_(
                GlobalBooking.college_id == college_id,
                GlobalBooking.day == original_entry.day,
                GlobalBooking.period == original_entry.period,
                GlobalBooking.faculty_id == substitution.original_faculty_id,
            )
        )
    )
    original_booking = original_booking_result.scalar_one_or_none()
    if original_booking:
        await db.delete(original_booking)

    # Create new booking for the substitute
    booking = GlobalBooking(
        booking_id=str(uuid.uuid4()),
        college_id=college_id,
        dept_id=tt.dept_id if tt else "",
        timetable_entry_id=sub_entry.entry_id,
        day=original_entry.day,
        period=original_entry.period,
        faculty_id=sub_req.candidate_faculty_id,
        room_id=original_entry.room_id,
        booking_type="timetable",
    )
    db.add(booking)

    # Update substitute faculty's substitution tracking
    faculty = await db.get(Faculty, sub_req.candidate_faculty_id)
    if faculty:
        faculty.substitution_count = (faculty.substitution_count or 0) + 1
        faculty.last_substitution_date = date.today()
        db.add(faculty)

    # Mark original entry as cancelled
    original_entry.entry_type = EntryType.CANCELLED
    db.add(original_entry)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Substitute faculty or room is no longer available for this slot (concurrent booking conflict).",
        )

    # Dispatch confirmation notifications
    dispatch_event("SUBSTITUTION_ACCEPTED", {
        "substitution_id": substitution.substitution_id,
        "substitute_faculty_id": sub_req.candidate_faculty_id,
        "original_faculty_id": substitution.original_faculty_id,
    })

    log.info(
        "substitution_accepted",
        substitution_id=substitution.substitution_id,
        substitute=sub_req.candidate_faculty_id,
    )

    return {
        "message": "Substitution accepted",
        "substitution_id": substitution.substitution_id,
        "substitute_faculty_id": sub_req.candidate_faculty_id,
    }


@router.post("/reject/{request_id}")
async def reject_substitution(
    request_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Reject a substitution request.
    Automatically escalates to next candidate or flags for manual intervention.
    """
    sub_req = await db.get(SubstitutionRequest, request_id)
    if not sub_req:
        raise HTTPException(status_code=404, detail="Substitution request not found")

    if sub_req.status != SubstitutionStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Request already {sub_req.status.value}",
        )

    # Mark as rejected
    sub_req.status = SubstitutionStatus.REJECTED
    sub_req.response_at = datetime.now(timezone.utc)
    db.add(sub_req)
    await db.commit()

    # Get substitution details
    substitution = await db.get(Substitution, sub_req.substitution_id)
    if not substitution:
        raise HTTPException(status_code=404, detail="Substitution record not found")

    original_entry = await db.get(TimetableEntry, substitution.original_entry_id)
    if not original_entry:
        return {"message": "Rejected, but original entry not found for escalation"}

    # Find remaining candidates and escalate
    candidates = await find_substitute_candidates(
        original_faculty_id=substitution.original_faculty_id,
        subject_id=original_entry.subject_id,
        day=original_entry.day,
        period=original_entry.period,
        college_id=current_user.college_id,
        dept_id=current_user.dept_id,
        db=db,
    )

    next_level = sub_req.escalation_level + 1

    if next_level > len(candidates) or next_level > settings.SUBSTITUTION_MAX_ESCALATIONS:
        # No more candidates or max reached
        substitution.status = SubstitutionStatus.CANCELLED
        substitution.resolved_at = datetime.now(timezone.utc)
        db.add(substitution)
        await db.commit()

        dispatch_event("SUBSTITUTION_EXHAUSTED", {
            "substitution_id": substitution.substitution_id,
        })

        return {
            "message": "Rejected. All candidates exhausted — manual intervention required.",
            "substitution_id": substitution.substitution_id,
            "status": "CANCELLED",
        }

    # Send to next candidate
    next_request = await send_to_next_candidate(
        substitution_id=substitution.substitution_id,
        candidates=candidates,
        escalation_level=next_level,
        db=db,
    )

    return {
        "message": f"Rejected. Escalated to level {next_level}: {candidates[next_level - 1]['name']}",
        "substitution_id": substitution.substitution_id,
        "next_request_id": next_request.request_id if next_request else None,
        "escalation_level": next_level,
    }


@router.get("/history")
async def substitution_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get substitution history for the department with full details (dept-scoped)."""
    # RULE 4 — DEPARTMENT ISOLATION: scope by dept
    result = await db.execute(
        select(Substitution)
        .join(TimetableEntry, Substitution.original_entry_id == TimetableEntry.entry_id)
        .join(Timetable, TimetableEntry.timetable_id == Timetable.timetable_id)
        .where(Timetable.dept_id == current_user.dept_id)
        .order_by(Substitution.created_at.desc())
        .limit(50)
    )
    substitutions = result.scalars().all()

    history = []
    for s in substitutions:
        # Get original entry details
        entry = await db.get(TimetableEntry, s.original_entry_id)
        original_faculty = await db.get(Faculty, s.original_faculty_id)
        substitute_faculty = await db.get(Faculty, s.substitute_faculty_id) if s.substitute_faculty_id else None

        subject_name = ""
        if entry:
            subject = await db.get(Subject, entry.subject_id)
            subject_name = subject.name if subject else ""

        history.append(SubstitutionDetailResponse(
            substitution_id=s.substitution_id,
            original_faculty_name=original_faculty.name if original_faculty else "Unknown",
            substitute_faculty_name=substitute_faculty.name if substitute_faculty else None,
            subject_name=subject_name,
            day=entry.day if entry else "",
            period=entry.period if entry else 0,
            absence_date=s.absence_date,
            reason=s.reason,
            status=s.status.value,
            created_at=s.created_at if s.created_at else datetime.now(timezone.utc),
            resolved_at=s.resolved_at,
        ))

    return history


@router.get("/{substitution_id}")
async def get_substitution(
    substitution_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed status of a specific substitution, including all request attempts."""
    substitution = await db.get(Substitution, substitution_id)
    if not substitution:
        raise HTTPException(status_code=404, detail="Substitution not found")

    # Get all requests for this substitution
    requests_result = await db.execute(
        select(SubstitutionRequest)
        .where(SubstitutionRequest.substitution_id == substitution_id)
        .order_by(SubstitutionRequest.escalation_level)
    )
    requests = requests_result.scalars().all()

    entry = await db.get(TimetableEntry, substitution.original_entry_id)
    original_faculty = await db.get(Faculty, substitution.original_faculty_id)

    request_details = []
    for req in requests:
        candidate = await db.get(Faculty, req.candidate_faculty_id)
        request_details.append(SubstitutionRequestResponse(
            request_id=req.request_id,
            candidate_faculty_id=req.candidate_faculty_id,
            candidate_name=candidate.name if candidate else "Unknown",
            escalation_level=req.escalation_level,
            ranking_score=req.ranking_score,
            status=req.status.value,
            notification_sent_at=req.notification_sent_at,
            response_at=req.response_at,
        ))

    subject_name = ""
    if entry:
        subject = await db.get(Subject, entry.subject_id)
        subject_name = subject.name if subject else ""

    return {
        "substitution_id": substitution.substitution_id,
        "original_faculty": original_faculty.name if original_faculty else "Unknown",
        "subject_name": subject_name,
        "day": entry.day if entry else "",
        "period": entry.period if entry else 0,
        "absence_date": substitution.absence_date,
        "reason": substitution.reason,
        "status": substitution.status.value,
        "substitute_faculty_id": substitution.substitute_faculty_id,
        "created_at": substitution.created_at.isoformat() if substitution.created_at else None,
        "resolved_at": substitution.resolved_at.isoformat() if substitution.resolved_at else None,
        "requests": request_details,
    }
