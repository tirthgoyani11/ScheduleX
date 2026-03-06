# core/substitution/finder.py
"""
Finds and ranks substitute faculty candidates using a weighted formula:
  Score = (expertise_match × 0.40) + (load_headroom_pct × 0.30)
        + (days_since_last_sub_normalized × 0.20) + (preference_similarity × 0.10)

Only candidates with expertise_match > 0 are considered.
Ties broken by faculty_id (deterministic).
"""
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from models.faculty import Faculty
from models.college import Department
from models.global_booking import GlobalBooking
from models.timetable import TimetableEntry, Timetable
from core.embeddings.faculty_embeddings import FacultyEmbeddingStore
import structlog

log = structlog.get_logger()

embedding_store = FacultyEmbeddingStore()


async def find_substitute_candidates(
    original_faculty_id: str,
    subject_id: str,
    day: str,
    period: int,
    college_id: str,
    dept_id: str,
    db: AsyncSession,
) -> list[dict]:
    """
    Returns ranked list of candidate faculty with scores.
    Max 5 candidates returned.
    """
    from models.subject import Subject

    subject = await db.get(Subject, subject_id)
    if not subject:
        return []

    # Step 1: Get all faculty in the college (cross-department eligible)
    dept_ids_result = await db.execute(
        select(Department.dept_id).where(Department.college_id == college_id)
    )
    college_dept_ids = [row[0] for row in dept_ids_result.fetchall()]

    all_faculty_result = await db.execute(
        select(Faculty).where(Faculty.dept_id.in_(college_dept_ids))
    )
    all_faculty = all_faculty_result.scalars().all()

    # Step 2: Get faculty already booked at the target slot
    booked_result = await db.execute(
        select(GlobalBooking.faculty_id).where(
            and_(
                GlobalBooking.college_id == college_id,
                GlobalBooking.day == day,
                GlobalBooking.period == period,
            )
        )
    )
    booked_faculty_ids = {row[0] for row in booked_result.fetchall()}
    booked_faculty_ids.add(original_faculty_id)  # Exclude absent faculty

    # Step 3: Get weekly load for each faculty
    weekly_loads = await _get_weekly_loads(all_faculty, db)

    # Step 4: Get original faculty embedding for preference matching
    original_embedding = await embedding_store.get_faculty_embedding(original_faculty_id)

    candidates = []
    for faculty in all_faculty:
        # Must not be booked in this slot
        if faculty.faculty_id in booked_faculty_ids:
            continue

        # Calculate expertise match
        expertise_match = _expertise_match(subject, faculty)
        if expertise_match == 0:
            continue  # Must have some expertise match

        # Calculate load headroom
        current_load = weekly_loads.get(faculty.faculty_id, 0)
        if faculty.max_weekly_load <= 0:
            load_headroom = 0.0
        else:
            load_headroom = max(0, (faculty.max_weekly_load - current_load) / faculty.max_weekly_load)

        # Calculate days since last substitution (fairness)
        if not faculty.last_substitution_date:
            days_since_sub = 30
        else:
            days_since_sub = (date.today() - faculty.last_substitution_date).days
        days_normalized = min(days_since_sub / 30, 1.0)

        # Calculate preference similarity via ChromaDB
        candidate_embedding = await embedding_store.get_faculty_embedding(faculty.faculty_id)
        pref_similarity = _cosine_similarity(original_embedding, candidate_embedding) if (
            original_embedding and candidate_embedding
        ) else 0.5

        # Weighted score
        score = (
            expertise_match * 0.40
            + load_headroom * 0.30
            + days_normalized * 0.20
            + pref_similarity * 0.10
        )

        candidates.append({
            "faculty_id": faculty.faculty_id,
            "name": faculty.name,
            "score": round(score, 4),
            "expertise_match": expertise_match,
            "load_headroom_pct": round(load_headroom * 100, 1),
            "days_since_last_sub": days_since_sub,
            "preferred_time": faculty.preferred_time,
        })

    # Sort by score descending, break ties by faculty_id (deterministic)
    candidates.sort(key=lambda c: (-c["score"], c["faculty_id"]))

    log.info(
        "substitute_candidates_found",
        original_faculty=original_faculty_id,
        subject=subject_id,
        slot=f"{day} P{period}",
        candidate_count=len(candidates),
    )
    return candidates[:5]


def _expertise_match(subject, faculty) -> float:
    """1.0 = exact match, 0.5 = related area, 0.0 = no match."""
    if not faculty.expertise:
        return 0.0

    # Check subject code match
    if subject.subject_code in faculty.expertise:
        return 1.0

    # Check subject name match (case insensitive)
    subject_name_lower = subject.name.lower()
    for exp in faculty.expertise:
        if exp.lower() in subject_name_lower or subject_name_lower in exp.lower():
            return 1.0

    # Simple related-area heuristic: share first 2 chars of code
    for exp in faculty.expertise:
        if len(exp) >= 2 and len(subject.subject_code) >= 2:
            if exp[:2].upper() == subject.subject_code[:2].upper():
                return 0.5

    return 0.0


def _cosine_similarity(v1: list | None, v2: list | None) -> float:
    """Cosine similarity between two vectors. Returns 0.5 as default."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.5
    dot = sum(a * b for a, b in zip(v1, v2))
    mag1 = sum(a ** 2 for a in v1) ** 0.5
    mag2 = sum(b ** 2 for b in v2) ** 0.5
    return dot / (mag1 * mag2) if mag1 and mag2 else 0.5


async def _get_weekly_loads(faculty_list: list, db: AsyncSession) -> dict[str, int]:
    """Returns {faculty_id: current_weekly_assigned_periods}."""
    faculty_ids = [f.faculty_id for f in faculty_list]
    if not faculty_ids:
        return {}

    result = await db.execute(
        select(
            TimetableEntry.faculty_id,
            func.count(TimetableEntry.entry_id).label("load"),
        )
        .join(Timetable, TimetableEntry.timetable_id == Timetable.timetable_id)
        .where(
            Timetable.status == "published",
            TimetableEntry.faculty_id.in_(faculty_ids),
        )
        .group_by(TimetableEntry.faculty_id)
    )
    return {row.faculty_id: row.load for row in result.fetchall()}
