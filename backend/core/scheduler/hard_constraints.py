# core/scheduler/hard_constraints.py
"""
ALL hard constraints. If any cannot be satisfied, solver returns INFEASIBLE.
AddAtMostOne() is preferred over AddLinearConstraint for binary variables — faster.

HC1:  No faculty double-booking (one room per faculty per slot)
HC2:  No room double-booking (one class per room per slot)
HC3:  Block pre-taken slots (now handled at variable-creation time — zero-cost)
HC4:  Faculty weekly load cap
HC5:  Room capacity must fit subject batch size  (pre-filtered in variables.py)
HC6:  Lab subjects only in lab rooms              (pre-filtered in variables.py)
HC7:  Each subject must be assigned exactly weekly_periods times
HC8:  No same batch in two subjects simultaneously
HC9:  No more than 3 consecutive periods for same faculty
HC10: 3-credit subjects must span minimum 2 days

PERFORMANCE: All loops use INDEXED LOOKUPS from variables dict —
  O(relevant_vars) instead of scanning all variables.
"""
from ortools.sat.python import cp_model
import structlog

log = structlog.get_logger()


def apply_hard_constraints(model: cp_model.CpModel, variables: dict, data: dict):
    assignments = variables["assignments"]
    by_faculty_slot = variables["by_faculty_slot"]
    by_room_slot = variables["by_room_slot"]
    by_faculty = variables["by_faculty"]
    by_subject_faculty = variables["by_subject_faculty"]
    by_subject_faculty_day = variables["by_subject_faculty_day"]
    by_batch_slot = variables["by_batch_slot"]
    by_faculty_day = variables["by_faculty_day"]

    days = data["days"]
    periods = data["periods"]
    faculty_subject_map = data.get("faculty_subject_map", {})

    constraint_count = 0

    log.info("applying_hard_constraints", constraint_count=10)

    # ── HC1: No faculty double-booking (one room per faculty per slot) ────────
    for (fid, day, period), slot_vars in by_faculty_slot.items():
        if len(slot_vars) > 1:
            model.AddAtMostOne(slot_vars)
            constraint_count += 1

    # ── HC2: No room double-booking (one class per room per slot) ─────────────
    for (rid, day, period), slot_vars in by_room_slot.items():
        if len(slot_vars) > 1:
            model.AddAtMostOne(slot_vars)
            constraint_count += 1

    # ── HC3: Block pre-taken slots ────────────────────────────────────────────
    # NOW HANDLED at variable-creation time (variables.py skips blocked slots).
    # Zero constraint objects needed — smaller model, faster solve.

    # ── HC4: Faculty weekly load cap ──────────────────────────────────────────
    for faculty in data["faculty"]:
        fid = faculty.faculty_id
        faculty_entries = by_faculty.get(fid, [])
        if faculty_entries:
            faculty_vars = [var for _key, var in faculty_entries]
            model.Add(sum(faculty_vars) <= faculty.max_weekly_load)
            constraint_count += 1

    # ── HC5 & HC6 are pre-filtered in variables.py ────────────────────────────
    # Room capacity and lab-room matching are enforced by not creating vars
    # for invalid combos. Zero extra constraints needed.

    # ── HC7: Each subject must be assigned exactly weekly_periods times ────────
    subject_by_id = {s.subject_id: s for s in data["subjects"]}
    for subject in data["subjects"]:
        assigned_faculty_ids = faculty_subject_map.get(subject.subject_id, [])
        for faculty_id in assigned_faculty_ids:
            entries = by_subject_faculty.get((subject.subject_id, faculty_id), [])
            if entries:
                subject_vars = [var for _key, var in entries]
                model.Add(sum(subject_vars) == subject.weekly_periods)
                constraint_count += 1

    # ── HC8: No same batch in two subjects simultaneously ─────────────────────
    for (batch, day, period), batch_vars in by_batch_slot.items():
        if len(batch_vars) > 1:
            model.AddAtMostOne(batch_vars)
            constraint_count += 1

    # ── HC9: No more than 3 consecutive periods for same faculty ──────────────
    sorted_periods = sorted(periods)
    for faculty in data["faculty"]:
        fid = faculty.faculty_id
        for day in days:
            day_entries = by_faculty_day.get((fid, day), [])
            if not day_entries:
                continue
            # Build a period→vars lookup for this faculty-day
            period_vars: dict[int, list] = {}
            for p, var in day_entries:
                period_vars.setdefault(p, []).append(var)

            for i in range(len(sorted_periods) - 3):
                window = sorted_periods[i:i + 4]
                window_vars = []
                for p in window:
                    window_vars.extend(period_vars.get(p, []))
                if len(window_vars) > 3:
                    # At most 3 of 4 consecutive slots can be occupied
                    model.Add(sum(window_vars) <= 3)
                    constraint_count += 1

    # ── HC10: 3-credit subjects must span minimum 2 days ──────────────────────
    for subject in data["subjects"]:
        if subject.credits >= 3:
            assigned_faculty_ids = faculty_subject_map.get(subject.subject_id, [])
            for faculty_id in assigned_faculty_ids:
                day_indicators: dict[str, cp_model.IntVar] = {}
                for day in days:
                    day_slots = by_subject_faculty_day.get(
                        (subject.subject_id, faculty_id, day), []
                    )
                    if day_slots:
                        day_var = model.NewBoolVar(
                            f"day_{faculty_id[:8]}_{subject.subject_id[:8]}_{day[:3]}"
                        )
                        model.AddMaxEquality(day_var, day_slots)
                        day_indicators[day] = day_var
                    else:
                        day_indicators[day] = model.NewConstant(0)

                if day_indicators:
                    model.Add(sum(day_indicators.values()) >= 2)
                    constraint_count += 1

    log.info("hard_constraints_applied", constraints_added=constraint_count)
