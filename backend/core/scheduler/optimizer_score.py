# core/scheduler/optimizer_score.py
"""
Calculate a 0–100% optimization score for a solved timetable.

Score = 100 × (1 - actual_penalty / max_possible_penalty)

Where max_possible_penalty is the worst-case scenario where every
soft constraint is violated.
"""
from ortools.sat.python import cp_model
import structlog

log = structlog.get_logger()


async def calculate_score(
    solver: cp_model.CpSolver,
    penalties: list,
    data: dict,
) -> float:
    """
    Compute the optimization score as a percentage (0–100).

    Args:
        solver: The solved CP-SAT solver instance
        penalties: The list of penalty terms from soft_constraints
        data: The scheduling data dict

    Returns:
        Float score between 0.0 and 100.0
    """
    if not penalties:
        return 100.0

    # Actual penalty from the solution
    actual_penalty = solver.ObjectiveValue()

    # Estimate max possible penalty
    max_possible_penalty = _estimate_max_penalty(data)

    if max_possible_penalty <= 0:
        return 100.0

    # Clamp to 0–100 range
    score = max(0.0, min(100.0, 100.0 * (1.0 - actual_penalty / max_possible_penalty)))

    log.info(
        "optimization_score",
        actual_penalty=actual_penalty,
        max_penalty=max_possible_penalty,
        score=round(score, 2),
    )

    return round(score, 2)


def _estimate_max_penalty(data: dict) -> float:
    """
    Estimate the maximum possible penalty (worst-case scenario).
    This gives us a denominator for the percentage calculation.
    """
    from core.scheduler.soft_constraints import PENALTY_WEIGHTS

    faculty_count = len(data["faculty"])
    day_count = len(data["days"])
    period_count = len(data["periods"])
    total_slots = day_count * period_count

    max_penalty = 0.0

    # SC1: Lunch break — worst case: every faculty loses lunch every day
    max_penalty += faculty_count * day_count * PENALTY_WEIGHTS["lunch_break"]

    # SC2: Student gaps — estimate: one gap per batch per day
    batches = set(
        s.batch for s in data["subjects"]
        if hasattr(s, "batch") and s.batch
    )
    max_penalty += len(batches) * day_count * PENALTY_WEIGHTS["student_gap"]

    # SC3: Faculty preference — worst case: all periods in wrong half
    pref_faculty = [
        f for f in data["faculty"]
        if f.preferred_time in ("morning", "afternoon")
    ]
    max_penalty += len(pref_faculty) * total_slots * PENALTY_WEIGHTS["faculty_preference"]

    # SC4: Early morning — worst case: every faculty has period 1 every day
    max_penalty += faculty_count * day_count * PENALTY_WEIGHTS["avoid_early_morning"]

    return max_penalty if max_penalty > 0 else 1.0
