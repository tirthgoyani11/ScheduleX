# routers/timetable.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from dependencies import get_db, require_any_admin, get_current_user
from models.timetable import Timetable, TimetableEntry, TimetableStatus
from models.global_booking import GlobalBooking
from models.user import User
from schemas.timetable import (
    TimetableCreateRequest, TimetableResponse,
    TimetablePublishResponse, TimetableEntryResponse,
)
from schemas.common import JobResponse
from core.notifications.dispatcher import dispatch_event
import uuid
from datetime import datetime, timezone

router = APIRouter(prefix="/timetable", tags=["Timetable"])


@router.get("/auto-assign")
async def auto_assign_faculty(
    semester: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Auto-assign faculty to subjects for a given semester using expertise matching.

    Matching strategy:
    1. Abbreviation match: faculty expertise abbreviation maps to subject name (e.g. "CN" -> "Computer Networks")
    2. Keyword match: expertise keyword appears in subject name (e.g. "networks" in "Computer Networks")
    3. Reverse keyword: subject name keyword appears in expertise

    Returns: { subject_id: faculty_id } for each subject that could be matched.
    Faculty load balancing is applied: prefer faculty with fewer assignments.
    """
    from models.faculty import Faculty
    from models.subject import Subject
    from models.batch import Batch

    fac_result = await db.execute(
        select(Faculty).where(Faculty.dept_id == current_user.dept_id)
    )
    faculty_list = fac_result.scalars().all()

    sub_result = await db.execute(
        select(Subject).where(
            Subject.dept_id == current_user.dept_id,
            Subject.semester == semester,
        )
    )
    subject_list = sub_result.scalars().all()

    # Count batches to weight lab load
    batch_result = await db.execute(
        select(Batch).where(
            Batch.dept_id == current_user.dept_id,
            Batch.semester == semester,
        )
    )
    num_batches = len(batch_result.scalars().all()) or 1

    # Build name-keyword mapping for subjects
    # e.g. "Computer Networks" -> ["computer", "networks"]
    subject_keywords: dict[str, list[str]] = {}
    for sub in subject_list:
        subject_keywords[sub.subject_id] = [
            w.lower() for w in sub.name.split() if len(w) > 2
        ]

    # Common abbreviation mapping for expertise matching
    abbreviation_map = {
        "cn": ["computer networks", "computer network"],
        "os": ["operating systems", "operating system"],
        "dbms": ["database management", "database"],
        "se": ["software engineering"],
        "daa": ["design & analysis of algorithms", "design and analysis", "algorithms"],
        "toc": ["theory of computation"],
        "wp": ["web programming", "web development"],
        "ds": ["data structures", "data structure"],
        "ai": ["artificial intelligence"],
        "ml": ["machine learning"],
        "cd": ["compiler design"],
        "coa": ["computer organization", "computer architecture"],
    }

    # Track load per faculty for balancing
    faculty_load: dict[str, int] = {f.faculty_id: 0 for f in faculty_list}
    assignments: dict[str, str] = {}  # subject_id -> faculty_id

    def match_score(faculty: Faculty, subject: Subject) -> int:
        """Score how well a faculty matches a subject. Higher = better. 0 = no match."""
        expertise = [e.lower().strip() for e in (faculty.expertise or [])]
        name_lower = subject.name.lower()
        score = 0

        for exp in expertise:
            # Abbreviation match (highest priority)
            if exp in abbreviation_map:
                for phrase in abbreviation_map[exp]:
                    if phrase in name_lower:
                        score = max(score, 100)
                        break
            # Keyword in subject name
            elif exp in name_lower:
                score = max(score, 80)
            # Check if any subject name keyword matches expertise
            elif any(kw in exp for kw in subject_keywords.get(subject.subject_id, [])):
                score = max(score, 60)

        return score

    # Sort subjects by total load descending (assign heaviest first)
    def _subject_load(s):
        lh = s.lecture_hours if s.lecture_hours else s.weekly_periods
        return lh + s.lab_hours * num_batches

    sorted_subjects = sorted(subject_list, key=_subject_load, reverse=True)

    for subject in sorted_subjects:
        candidates = []
        for faculty in faculty_list:
            score = match_score(faculty, subject)
            if score > 0:
                # Penalize overloaded faculty
                load_penalty = faculty_load[faculty.faculty_id] * 5
                candidates.append((score - load_penalty, faculty))

        if candidates:
            # Best scoring, then least loaded
            candidates.sort(key=lambda x: (-x[0], faculty_load[x[1].faculty_id]))
            best_faculty = candidates[0][1]
            assignments[subject.subject_id] = best_faculty.faculty_id
            faculty_load[best_faculty.faculty_id] += _subject_load(subject)
        else:
            # No match found — assign least loaded faculty as fallback
            if faculty_list:
                least_loaded = min(faculty_list, key=lambda f: faculty_load[f.faculty_id])
                assignments[subject.subject_id] = least_loaded.faculty_id
                faculty_load[least_loaded.faculty_id] += _subject_load(subject)

    # Convert to {faculty_id: [subject_ids]} for frontend
    result: dict[str, list[str]] = {}
    for sid, fid in assignments.items():
        result.setdefault(fid, []).append(sid)

    return result


@router.get("", response_model=list[TimetableResponse])
async def list_timetables(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all timetables for the current user's department."""
    from models.subject import Subject as SubjectModel
    from models.faculty import Faculty as FacultyModel
    from models.room import Room as RoomModel

    result = await db.execute(
        select(Timetable)
        .where(
            Timetable.dept_id == current_user.dept_id,
            Timetable.status != TimetableStatus.DELETED,
        )
        .order_by(Timetable.created_at.desc())
    )
    timetables = result.scalars().all()
    responses = []
    for tt in timetables:
        entry_result = await db.execute(
            select(TimetableEntry).where(TimetableEntry.timetable_id == tt.timetable_id)
        )
        entries = entry_result.scalars().all()
        entry_responses = []
        for entry in entries:
            subject = await db.get(SubjectModel, entry.subject_id)
            faculty = await db.get(FacultyModel, entry.faculty_id)
            room = await db.get(RoomModel, entry.room_id)
            entry_responses.append(TimetableEntryResponse(
                entry_id=entry.entry_id,
                day=entry.day,
                period=entry.period,
                subject_name=subject.name if subject else "Unknown",
                faculty_name=faculty.name if faculty else "Unknown",
                room_name=room.name if room else "Unknown",
                entry_type=entry.entry_type.value,
                batch=entry.batch,
            ))
        responses.append(TimetableResponse(
            timetable_id=tt.timetable_id,
            semester=tt.semester,
            academic_year=tt.academic_year,
            status=tt.status.value,
            optimization_score=tt.optimization_score,
            entries=entry_responses,
            created_at=tt.created_at.isoformat() if tt.created_at else "",
            published_at=tt.published_at.isoformat() if tt.published_at else None,
        ))
    return responses


@router.post("/generate", response_model=JobResponse)
async def generate_timetable(
    request: TimetableCreateRequest,
    current_user: User = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Triggers timetable generation as a background RQ job.
    Returns job_id immediately (<100ms).
    """
    # Clean up old draft/deleted timetables for same dept+semester to free global bookings
    old_tts = await db.execute(
        select(Timetable).where(
            Timetable.dept_id == current_user.dept_id,
            Timetable.semester == request.semester,
            Timetable.status.in_([TimetableStatus.DRAFT, TimetableStatus.DELETED]),
        )
    )
    for old_tt in old_tts.scalars().all():
        # Delete global bookings tied to this timetable's entries
        await db.execute(
            GlobalBooking.__table__.delete().where(
                GlobalBooking.timetable_entry_id.in_(
                    select(TimetableEntry.entry_id).where(
                        TimetableEntry.timetable_id == old_tt.timetable_id
                    )
                )
            )
        )
        # Delete entries
        await db.execute(
            TimetableEntry.__table__.delete().where(
                TimetableEntry.timetable_id == old_tt.timetable_id
            )
        )
        # Delete the timetable itself
        await db.delete(old_tt)
    await db.flush()

    timetable = Timetable(
        timetable_id=str(uuid.uuid4()),
        dept_id=current_user.dept_id,
        semester=request.semester,
        academic_year=request.academic_year,
        status=TimetableStatus.DRAFT,
    )
    db.add(timetable)
    await db.commit()

    # Enqueue background job (or run inline on Windows)
    try:
        from workers.scheduler_worker import enqueue_timetable_generation, RQ_AVAILABLE
        if RQ_AVAILABLE:
            job_id = enqueue_timetable_generation(
                timetable_id=timetable.timetable_id,
                faculty_subject_map=request.faculty_subject_map,
                time_limit_seconds=request.time_limit_seconds or 120,
                working_days=request.working_days,
            )
            return JobResponse(
                job_id=job_id,
                timetable_id=timetable.timetable_id,
                status="QUEUED",
            )
    except (ImportError, ValueError, OSError):
        pass

    # Fallback: run solver inline (Windows dev / no Redis)
    from core.scheduler.engine import generate_timetable as run_solver
    result = await run_solver(
        timetable_id=timetable.timetable_id,
        db=db,
        config={
            "faculty_subject_map": request.faculty_subject_map,
            "time_limit_seconds": request.time_limit_seconds or 120,
            "working_days": request.working_days,
        },
    )

    return JobResponse(
        job_id=timetable.timetable_id,
        timetable_id=timetable.timetable_id,
        status=result.get("status", "UNKNOWN"),
    )


@router.get("/{timetable_id}", response_model=TimetableResponse)
async def get_timetable(
    timetable_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a full timetable with all entries."""
    result = await db.execute(
        select(Timetable).where(
            Timetable.timetable_id == timetable_id,
            Timetable.dept_id == current_user.dept_id,
        )
    )
    timetable = result.scalar_one_or_none()
    if not timetable:
        raise HTTPException(status_code=404, detail="Timetable not found")

    entry_result = await db.execute(
        select(TimetableEntry).where(TimetableEntry.timetable_id == timetable_id)
    )
    entries = entry_result.scalars().all()

    entry_responses = []
    for entry in entries:
        # Eager load names
        from models.subject import Subject
        from models.faculty import Faculty
        from models.room import Room

        subject = await db.get(Subject, entry.subject_id)
        faculty = await db.get(Faculty, entry.faculty_id)
        room = await db.get(Room, entry.room_id)

        entry_responses.append(TimetableEntryResponse(
            entry_id=entry.entry_id,
            day=entry.day,
            period=entry.period,
            subject_name=subject.name if subject else "Unknown",
            faculty_name=faculty.name if faculty else "Unknown",
            room_name=room.name if room else "Unknown",
            entry_type=entry.entry_type.value,
            batch=entry.batch,
        ))

    return TimetableResponse(
        timetable_id=timetable.timetable_id,
        semester=timetable.semester,
        academic_year=timetable.academic_year,
        status=timetable.status.value,
        optimization_score=timetable.optimization_score,
        entries=entry_responses,
        created_at=timetable.created_at.isoformat() if timetable.created_at else "",
        published_at=timetable.published_at.isoformat() if timetable.published_at else None,
    )


@router.post("/{timetable_id}/publish", response_model=TimetablePublishResponse)
async def publish_timetable(
    timetable_id: str,
    current_user: User = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Publishes a DRAFT timetable. Idempotent.
    Triggers faculty notification via WhatsApp + Email.
    """
    result = await db.execute(
        select(Timetable).where(
            Timetable.timetable_id == timetable_id,
            Timetable.dept_id == current_user.dept_id,
        )
    )
    timetable = result.scalar_one_or_none()
    if not timetable:
        raise HTTPException(status_code=404, detail="Timetable not found")

    if timetable.status == TimetableStatus.PUBLISHED:
        return TimetablePublishResponse(
            message="Already published", timetable_id=timetable_id
        )

    if timetable.status != TimetableStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot publish a timetable with status: {timetable.status.value}",
        )

    timetable.status = TimetableStatus.PUBLISHED
    timetable.published_at = datetime.now(timezone.utc)
    db.add(timetable)
    await db.commit()

    # Dispatch notification event (non-blocking)
    dispatch_event("TIMETABLE_PUBLISHED", {
        "timetable_id": timetable_id,
        "dept_id": current_user.dept_id,
        "college_id": current_user.college_id,
    })

    return TimetablePublishResponse(
        message="Published successfully", timetable_id=timetable_id
    )


@router.delete("/{timetable_id}")
async def delete_timetable(
    timetable_id: str,
    current_user: User = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a timetable and release all its global_bookings slots."""
    result = await db.execute(
        select(Timetable).where(
            Timetable.timetable_id == timetable_id,
            Timetable.dept_id == current_user.dept_id,
        )
    )
    timetable = result.scalar_one_or_none()
    if not timetable:
        raise HTTPException(status_code=404, detail="Timetable not found")

    # Release global bookings linked to this timetable's entries
    entry_ids_query = select(TimetableEntry.entry_id).where(
        TimetableEntry.timetable_id == timetable_id
    )
    await db.execute(
        GlobalBooking.__table__.delete().where(
            GlobalBooking.timetable_entry_id.in_(entry_ids_query)
        )
    )

    timetable.status = TimetableStatus.DELETED
    db.add(timetable)
    await db.commit()

    dispatch_event("TIMETABLE_DELETED", {
        "timetable_id": timetable_id,
        "dept_id": current_user.dept_id,
    })
    return {"message": "Timetable deleted and slots released"}
