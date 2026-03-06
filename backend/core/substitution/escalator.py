# core/substitution/escalator.py
"""
Handles the 10-minute escalation timer for unanswered substitution requests.
Called when a SubstitutionRequest goes unanswered.

Flow:
  1. Mark current pending request as TIMED_OUT
  2. If max escalations reached → flag for manual intervention (CANCELLED)
  3. Otherwise → next candidate is sent by the caller
"""
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from models.substitution import Substitution, SubstitutionRequest, SubstitutionStatus
from config import settings
from core.notifications.dispatcher import dispatch_event
import structlog

log = structlog.get_logger()


async def check_and_escalate(substitution_id: str, db: AsyncSession) -> dict:
    """
    Called after the timeout period for a pending request.

    Returns:
        {
            "action": "escalated" | "exhausted" | "already_resolved",
            "current_level": int,
            "max_level": int,
        }
    """
    # Get pending requests for this substitution, ordered by escalation level
    result = await db.execute(
        select(SubstitutionRequest).where(
            and_(
                SubstitutionRequest.substitution_id == substitution_id,
                SubstitutionRequest.status == SubstitutionStatus.PENDING,
            )
        ).order_by(SubstitutionRequest.escalation_level)
    )
    pending_request = result.scalar_one_or_none()

    if not pending_request:
        log.info("escalation_skip_resolved", substitution_id=substitution_id)
        return {"action": "already_resolved", "current_level": 0, "max_level": settings.SUBSTITUTION_MAX_ESCALATIONS}

    # Mark as timed out
    pending_request.status = SubstitutionStatus.TIMED_OUT
    pending_request.response_at = datetime.now(timezone.utc)
    db.add(pending_request)

    current_level = pending_request.escalation_level

    # Check if max escalations reached
    if current_level >= settings.SUBSTITUTION_MAX_ESCALATIONS:
        # Flag substitution for manual intervention
        sub_result = await db.execute(
            select(Substitution).where(Substitution.substitution_id == substitution_id)
        )
        substitution = sub_result.scalar_one()
        substitution.status = SubstitutionStatus.CANCELLED
        substitution.resolved_at = datetime.now(timezone.utc)
        db.add(substitution)
        await db.commit()

        # Notify admin
        dispatch_event("SUBSTITUTION_EXHAUSTED", {
            "substitution_id": substitution_id,
            "message": "All candidates exhausted. Manual intervention required.",
        })

        log.warning(
            "substitution_exhausted",
            substitution_id=substitution_id,
            level=current_level,
        )
        return {
            "action": "exhausted",
            "current_level": current_level,
            "max_level": settings.SUBSTITUTION_MAX_ESCALATIONS,
        }

    await db.commit()

    log.info(
        "substitution_escalated",
        substitution_id=substitution_id,
        from_level=current_level,
        to_level=current_level + 1,
    )
    return {
        "action": "escalated",
        "current_level": current_level,
        "max_level": settings.SUBSTITUTION_MAX_ESCALATIONS,
    }


async def send_to_next_candidate(
    substitution_id: str,
    candidates: list[dict],
    escalation_level: int,
    db: AsyncSession,
) -> SubstitutionRequest | None:
    """
    Create a SubstitutionRequest for the next candidate in the ranked list.
    Returns the created request or None if no candidates remain.
    """
    # candidates are 0-indexed, escalation levels are 1-indexed
    candidate_idx = escalation_level - 1
    if candidate_idx >= len(candidates):
        log.info("no_more_candidates", substitution_id=substitution_id, level=escalation_level)
        return None

    candidate = candidates[candidate_idx]

    sub_request = SubstitutionRequest(
        substitution_id=substitution_id,
        candidate_faculty_id=candidate["faculty_id"],
        escalation_level=escalation_level,
        ranking_score=candidate["score"],
        notification_sent_at=datetime.now(timezone.utc),
        status=SubstitutionStatus.PENDING,
    )
    db.add(sub_request)
    await db.commit()
    await db.refresh(sub_request)

    # Dispatch notification to the candidate
    dispatch_event("SUBSTITUTION_REQUEST", {
        "substitution_id": substitution_id,
        "request_id": sub_request.request_id,
        "candidate_faculty_id": candidate["faculty_id"],
        "candidate_name": candidate["name"],
        "escalation_level": escalation_level,
    })

    log.info(
        "substitution_request_sent",
        substitution_id=substitution_id,
        candidate=candidate["name"],
        level=escalation_level,
        score=candidate["score"],
    )
    return sub_request
