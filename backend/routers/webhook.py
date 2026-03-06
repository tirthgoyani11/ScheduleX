# routers/webhook.py
"""
WhatsApp Webhook Router.
Handles Meta's webhook verification (GET) and incoming messages (POST).
Parses interactive button replies (ACCEPT_xxx / REJECT_xxx) to drive
the substitution chain without requiring the user to log into the portal.
"""
from fastapi import APIRouter, Request, HTTPException, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from dependencies import get_db
from config import settings
from models.substitution import SubstitutionRequest, SubstitutionStatus, Substitution
from models.timetable import TimetableEntry
from core.substitution.finder import find_substitute_candidates
from core.substitution.escalator import send_to_next_candidate
from core.notifications.dispatcher import dispatch_event
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone
import structlog

log = structlog.get_logger()

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


# ── WhatsApp Webhook Verification (GET) ─────────────────────
@router.get("/whatsapp")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """
    Meta sends a GET request with hub.mode, hub.verify_token, hub.challenge.
    We must respond with hub.challenge if the verify token is correct.
    """
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN:
        log.info("whatsapp_webhook_verified")
        return int(hub_challenge) if hub_challenge else ""
    raise HTTPException(status_code=403, detail="Verification failed")


# ── WhatsApp Incoming Messages (POST) ───────────────────────
@router.post("/whatsapp")
async def receive_whatsapp(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Processes incoming WhatsApp messages.
    We look for interactive button replies with IDs of the format:
      ACCEPT_{request_id}  or  REJECT_{request_id}
    """
    body = await request.json()

    # Extract messages from the Meta webhook payload
    messages = _extract_messages(body)
    if not messages:
        return {"status": "ok"}

    for msg in messages:
        action, request_id = _parse_button_reply(msg)
        if not action or not request_id:
            continue

        try:
            if action == "ACCEPT":
                await _handle_accept(request_id, db)
            elif action == "REJECT":
                await _handle_reject(request_id, db)
        except Exception as e:
            log.error("webhook_processing_error", error=str(e), request_id=request_id)

    return {"status": "ok"}


# ── Internal helpers ────────────────────────────────────────

def _extract_messages(body: dict) -> list[dict]:
    """Extract message objects from Meta's webhook payload structure."""
    messages = []
    try:
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for msg in value.get("messages", []):
                    messages.append(msg)
    except (KeyError, TypeError):
        pass
    return messages


def _parse_button_reply(msg: dict) -> tuple[str | None, str | None]:
    """
    Parse an interactive button reply.
    Expected button ID format: ACCEPT_<request_id> or REJECT_<request_id>
    """
    interactive = msg.get("interactive", {})
    button_reply = interactive.get("button_reply", {})
    button_id = button_reply.get("id", "")

    if button_id.startswith("ACCEPT_"):
        return "ACCEPT", button_id[7:]
    elif button_id.startswith("REJECT_"):
        return "REJECT", button_id[7:]
    return None, None


async def _handle_accept(request_id: str, db: AsyncSession):
    """Process an ACCEPT via webhook — mirrors the accept endpoint logic."""
    from models.faculty import Faculty
    from models.global_booking import GlobalBooking
    from models.timetable import TimetableEntry, EntryType
    from datetime import date
    import uuid

    sub_req = await db.get(SubstitutionRequest, request_id)
    if not sub_req or sub_req.status != SubstitutionStatus.PENDING:
        log.warning("webhook_accept_skip", request_id=request_id, reason="not pending")
        return

    substitution = await db.get(Substitution, sub_req.substitution_id)
    if not substitution:
        return

    original_entry = await db.get(TimetableEntry, substitution.original_entry_id)
    if not original_entry:
        return

    # Mark ACCEPTED
    sub_req.status = SubstitutionStatus.ACCEPTED
    sub_req.response_at = datetime.now(timezone.utc)
    db.add(sub_req)

    substitution.status = SubstitutionStatus.ACCEPTED
    substitution.substitute_faculty_id = sub_req.candidate_faculty_id
    substitution.resolved_at = datetime.now(timezone.utc)
    db.add(substitution)

    # Cancel other pending requests
    other_pending = await db.execute(
        select(SubstitutionRequest).where(
            and_(
                SubstitutionRequest.substitution_id == sub_req.substitution_id,
                SubstitutionRequest.request_id != request_id,
                SubstitutionRequest.status == SubstitutionStatus.PENDING,
            )
        )
    )
    for other in other_pending.scalars().all():
        other.status = SubstitutionStatus.CANCELLED
        other.response_at = datetime.now(timezone.utc)
        db.add(other)

    # Create substitution entry
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

    # Mark original as cancelled
    original_entry.entry_type = EntryType.CANCELLED
    db.add(original_entry)

    # Release original faculty's global booking and create substitute's
    from models.timetable import Timetable
    from models.college import Department
    tt = await db.get(Timetable, original_entry.timetable_id)
    dept = await db.get(Department, tt.dept_id) if tt else None
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

    # Update faculty tracking
    faculty = await db.get(Faculty, sub_req.candidate_faculty_id)
    if faculty:
        faculty.substitution_count = (faculty.substitution_count or 0) + 1
        faculty.last_substitution_date = date.today()
        db.add(faculty)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        log.error("webhook_accept_conflict", request_id=request_id,
                  reason="concurrent booking conflict")
        return

    dispatch_event("SUBSTITUTION_ACCEPTED", {
        "substitution_id": substitution.substitution_id,
        "substitute_faculty_id": sub_req.candidate_faculty_id,
        "original_faculty_id": substitution.original_faculty_id,
        "via": "whatsapp_webhook",
    })

    log.info("webhook_substitution_accepted", substitution_id=substitution.substitution_id)


async def _handle_reject(request_id: str, db: AsyncSession):
    """Process a REJECT via webhook — mirrors the reject endpoint logic."""
    sub_req = await db.get(SubstitutionRequest, request_id)
    if not sub_req or sub_req.status != SubstitutionStatus.PENDING:
        log.warning("webhook_reject_skip", request_id=request_id, reason="not pending")
        return

    sub_req.status = SubstitutionStatus.REJECTED
    sub_req.response_at = datetime.now(timezone.utc)
    db.add(sub_req)
    await db.commit()

    substitution = await db.get(Substitution, sub_req.substitution_id)
    if not substitution:
        return

    # Escalation
    next_level = sub_req.escalation_level + 1
    if next_level > settings.SUBSTITUTION_MAX_ESCALATIONS:
        substitution.status = SubstitutionStatus.CANCELLED
        substitution.resolved_at = datetime.now(timezone.utc)
        db.add(substitution)
        await db.commit()
        dispatch_event("SUBSTITUTION_EXHAUSTED", {
            "substitution_id": substitution.substitution_id,
            "via": "whatsapp_webhook",
        })
        log.warning("webhook_substitution_exhausted", substitution_id=substitution.substitution_id)
        return

    # Find next candidate (we re-run the finder to get fresh data)
    original_entry = await db.get(TimetableEntry, substitution.original_entry_id)
    if not original_entry:
        return

    # We need college_id — get it from timetable → department
    from models.timetable import Timetable
    from models.college import Department
    tt = await db.get(Timetable, original_entry.timetable_id)
    dept = await db.get(Department, tt.dept_id) if tt else None
    college_id = dept.college_id if dept else ""
    dept_id = tt.dept_id if tt else ""

    candidates = await find_substitute_candidates(
        original_faculty_id=substitution.original_faculty_id,
        subject_id=original_entry.subject_id,
        day=original_entry.day,
        period=original_entry.period,
        college_id=college_id,
        dept_id=dept_id,
        db=db,
    )

    if next_level > len(candidates):
        substitution.status = SubstitutionStatus.CANCELLED
        substitution.resolved_at = datetime.now(timezone.utc)
        db.add(substitution)
        await db.commit()
        dispatch_event("SUBSTITUTION_EXHAUSTED", {
            "substitution_id": substitution.substitution_id,
        })
        return

    await send_to_next_candidate(
        substitution_id=substitution.substitution_id,
        candidates=candidates,
        escalation_level=next_level,
        db=db,
    )

    log.info(
        "webhook_substitution_escalated",
        substitution_id=substitution.substitution_id,
        level=next_level,
    )
