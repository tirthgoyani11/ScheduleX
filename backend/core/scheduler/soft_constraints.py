# core/scheduler/soft_constraints.py
"""
Soft constraints implemented as penalty terms.
The solver minimizes the sum of all penalties.
Optimization Score (0–100%) = 1 - (actual_penalty / max_possible_penalty)

SC1: Guarantee lunch break                   (weight: 100)
SC2: Avoid large gaps between batch classes   (weight: 80)
SC3: Faculty time preference                  (weight: 50)
SC4: Avoid scheduling period 1               (weight: 30)

PERFORMANCE: Uses indexed lookups from variables dict.
"""
from ortools.sat.python import cp_model
import structlog

log = structlog.get_logger()

PENALTY_WEIGHTS = {
    "lunch_break":          100,
    "student_gap":          80,
    "faculty_preference":   50,
    "room_utilization":     40,
    "lab_anchoring":        35,
    "avoid_early_morning":  30,
    "isolated_day":         25,
    "consistent_pattern":   20,
}


def _detect_break_neighbours(data: dict) -> list[int]:
    """Return periods immediately before and after a break slot (for lunch penalty)."""
    slot_lookup = data.get("slot_lookup", {})
    if not slot_lookup:
        return [4, 5]  # legacy fallback
    break_orders = sorted(
        order for order, s in slot_lookup.items()
        if s.slot_type.value == "break"
    )
    if not break_orders:
        return [4, 5]
    # Periods adjacent to break(s): the schedulable period just before and just after
    neighbours = set()
    for b in break_orders:
        neighbours.add(b - 1)
        neighbours.add(b + 1)
    # Keep only orders that are actual schedulable periods
    valid_periods = set(data.get("periods", []))
    return sorted(neighbours & valid_periods)


def _morning_afternoon_split(data: dict) -> tuple[set[int], set[int]]:
    """Split periods into morning/afternoon based on slot start_time."""
    slot_lookup = data.get("slot_lookup", {})
    periods = data.get("periods", list(range(1, 9)))
    if not slot_lookup:
        mid = len(periods) // 2
        return set(periods[:mid]), set(periods[mid:])
    morning = set()
    afternoon = set()
    for p in periods:
        slot = slot_lookup.get(p)
        if slot and slot.start_time < "12:00":
            morning.add(p)
        else:
            afternoon.add(p)
    return morning, afternoon


def apply_soft_constraints(
    model: cp_model.CpModel, variables: dict, data: dict
) -> list:
    """
    Returns a list of penalty IntVar terms to be summed in the objective.
    Each penalty is a BoolVar * weight (or IntVar for linear penalties).
    """
    assignments = variables["assignments"]
    by_faculty_slot = variables["by_faculty_slot"]
    by_batch_slot = variables["by_batch_slot"]
    by_faculty = variables["by_faculty"]
    by_faculty_day = variables["by_faculty_day"]

    penalties: list = []
    days = data["days"]
    periods = data["periods"]

    log.info("applying_soft_constraints")

    # Derive break/morning/afternoon from configured slots
    lunch_periods = _detect_break_neighbours(data)
    morning_periods, afternoon_periods = _morning_afternoon_split(data)

    # ── SC1: Guarantee lunch break (weight: 100) ─────────────────────────────
    # Penalize if BOTH lunch-adjacent periods are occupied for a faculty on a day
    for faculty in data["faculty"]:
        fid = faculty.faculty_id
        for day in days:
            lunch_vars = []
            for lp in lunch_periods:
                lunch_vars.extend(by_faculty_slot.get((fid, day, lp), []))
            if len(lunch_vars) >= 2:
                lunch_penalty = model.NewBoolVar(f"lp_{fid[:8]}_{day[:3]}")
                model.Add(
                    sum(lunch_vars) >= len(lunch_periods)
                ).OnlyEnforceIf(lunch_penalty)
                model.Add(
                    sum(lunch_vars) < len(lunch_periods)
                ).OnlyEnforceIf(lunch_penalty.Not())
                penalties.append(lunch_penalty * PENALTY_WEIGHTS["lunch_break"])

    # ── SC2: Avoid large gaps between classes for batches (weight: 80) ────────
    all_batches = list(set(
        s.batch for s in data["subjects"] if hasattr(s, "batch") and s.batch
    ))
    for batch in all_batches:
        for day in days:
            for p1 in range(1, max(periods) - 1):
                p2 = p1 + 2
                if p2 > max(periods):
                    continue
                p_mid = p1 + 1

                before_vars = by_batch_slot.get((batch, day, p1), [])
                after_vars = by_batch_slot.get((batch, day, p2), [])
                gap_vars = by_batch_slot.get((batch, day, p_mid), [])

                if before_vars and after_vars and gap_vars:
                    has_before = model.NewBoolVar(f"gap_b_{batch[:6]}_{day[:3]}_{p1}")
                    has_after = model.NewBoolVar(f"gap_a_{batch[:6]}_{day[:3]}_{p1}")
                    no_middle = model.NewBoolVar(f"gap_m_{batch[:6]}_{day[:3]}_{p1}")
                    gap_penalty = model.NewBoolVar(f"gap_p_{batch[:6]}_{day[:3]}_{p1}")

                    model.Add(sum(before_vars) >= 1).OnlyEnforceIf(has_before)
                    model.Add(sum(before_vars) == 0).OnlyEnforceIf(has_before.Not())

                    model.Add(sum(after_vars) >= 1).OnlyEnforceIf(has_after)
                    model.Add(sum(after_vars) == 0).OnlyEnforceIf(has_after.Not())

                    model.Add(sum(gap_vars) == 0).OnlyEnforceIf(no_middle)
                    model.Add(sum(gap_vars) >= 1).OnlyEnforceIf(no_middle.Not())

                    model.AddBoolAnd([has_before, has_after, no_middle]).OnlyEnforceIf(gap_penalty)
                    model.AddBoolOr([
                        has_before.Not(), has_after.Not(), no_middle.Not()
                    ]).OnlyEnforceIf(gap_penalty.Not())

                    penalties.append(gap_penalty * PENALTY_WEIGHTS["student_gap"])

    # ── SC3: Faculty time preference (weight: 50) ────────────────────────────
    for faculty in data["faculty"]:
        if faculty.preferred_time in ("morning", "afternoon"):
            fid = faculty.faculty_id
            wrong_periods = (
                afternoon_periods if faculty.preferred_time == "morning"
                else morning_periods
            )
            faculty_entries = by_faculty.get(fid, [])
            for (f, s, r, d, p), var in faculty_entries:
                if p in wrong_periods:
                    penalties.append(var * PENALTY_WEIGHTS["faculty_preference"])

    # ── SC4: Avoid scheduling period 1 (early morning) (weight: 30) ──────────
    for day in days:
        for (key, var) in variables.get("by_day_period", {}).get((day, 1), []):
            penalties.append(var * PENALTY_WEIGHTS["avoid_early_morning"])

    log.info("soft_constraints_applied", penalty_terms=len(penalties))
    return penalties


def build_objective(model: cp_model.CpModel, penalties: list):
    """Set the model objective to minimize total penalty."""
    if penalties:
        model.Minimize(sum(penalties))
