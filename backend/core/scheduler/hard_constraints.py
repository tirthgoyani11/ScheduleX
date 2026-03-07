# core/scheduler/hard_constraints.py
"""
Hard constraints for theory + multi-batch lab scheduling.

Combined (theory + lab):
  HC1:  No faculty double-booking at any (day, period)
  HC2:  No room double-booking at any (day, period)
  HC4:  Faculty weekly load cap
  HC9:  No more than 4 consecutive periods for same faculty
  HC_theory_lab: Theory and labs cannot share the same (day, period)

Theory-specific:
  HC7t:  Each subject-faculty gets exactly lecture_hours theory slots
  HC8t:  At most 1 theory class at any (day, lecture_period) — whole division attends
  HC10:  3-credit subjects with ≥2 lecture_hours must span ≥2 days
  HC11:  At most 1 theory class per subject per day

Lab-specific:
  HC7l:    Each (subject, batch) gets exactly lab_hours lab slots (any faculty)
  HC8l:    Each batch has at most 1 lab at any (day, lab_period)
  HCsync:  All batches must have labs at the SAME (day, period) — synchronisation
"""
from ortools.sat.python import cp_model
import structlog

log = structlog.get_logger()


def apply_hard_constraints(model: cp_model.CpModel, variables: dict, data: dict):
    by_faculty_slot = variables["by_faculty_slot"]
    by_room_slot = variables["by_room_slot"]
    by_faculty = variables["by_faculty"]
    by_faculty_day = variables["by_faculty_day"]

    by_theory_subject_faculty = variables["by_theory_subject_faculty"]
    by_theory_slot = variables["by_theory_slot"]
    by_theory_subject_faculty_day = variables["by_theory_subject_faculty_day"]

    by_lab_subject_faculty_batch = variables["by_lab_subject_faculty_batch"]
    by_lab_batch_slot = variables["by_lab_batch_slot"]
    by_lab_subject_slot = variables["by_lab_subject_slot"]
    by_lab_sfb_day_period = variables.get("by_lab_sfb_day_period", {})
    by_lab_sfb_day_period_room = variables.get("by_lab_sfb_day_period_room", {})

    lecture_periods = variables["lecture_periods"]
    lab_periods = variables["lab_periods"]

    days = data["days"]
    periods = data["periods"]
    batches = data.get("batches", [])
    faculty_subject_map = data.get("faculty_subject_map", {})

    constraint_count = 0

    # ── HC1: No faculty double-booking (across theory + lab) ──────────────────
    for (fid, day, period), slot_vars in by_faculty_slot.items():
        if len(slot_vars) > 1:
            model.AddAtMostOne(slot_vars)
            constraint_count += 1

    # ── HC2: No room double-booking (across theory + lab) ─────────────────────
    for (rid, day, period), slot_vars in by_room_slot.items():
        if len(slot_vars) > 1:
            model.AddAtMostOne(slot_vars)
            constraint_count += 1

    # ── HC4: Faculty weekly load cap (subtract existing cross-semester bookings) ─
    existing_bookings = data.get("existing_bookings", [])
    for faculty in data["faculty"]:
        fid = faculty.faculty_id
        entries = by_faculty.get(fid, [])
        if entries:
            already_booked = sum(1 for b in existing_bookings if b.faculty_id == fid)
            remaining = faculty.max_weekly_load - already_booked
            if remaining < 0:
                remaining = 0
            model.Add(sum(v for _, v in entries) <= remaining)
            constraint_count += 1

    # ── HC7t: Theory — each (subject, faculty) assigned exactly lecture_hours ─
    for subject in data["subjects"]:
        lh = subject.lecture_hours if subject.lecture_hours is not None else subject.weekly_periods
        if lh <= 0:
            continue
        for fid in faculty_subject_map.get(subject.subject_id, []):
            entries = by_theory_subject_faculty.get(
                (subject.subject_id, fid), []
            )
            if entries:
                model.Add(sum(v for _, v in entries) == lh)
                constraint_count += 1

    # ── HC8t: Theory non-overlap — at most 1 theory class per (day, period) ──
    for (day, period), slot_entries in by_theory_slot.items():
        if len(slot_entries) > 1:
            model.AddAtMostOne([v for _, v in slot_entries])
            constraint_count += 1

    # ── HC7l: Lab — each (subject, batch) gets exactly lab_hours ──────────────
    # Any department faculty can teach labs (decoupled from theory teacher).
    by_lab_subject_batch = variables.get("by_lab_subject_batch", {})
    for subject in data["subjects"]:
        if subject.lab_hours <= 0:
            continue
        for batch in batches:
            entries = by_lab_subject_batch.get(
                (subject.subject_id, batch.batch_id), []
            )
            if entries:
                model.Add(
                    sum(v for _, v in entries) == subject.lab_hours
                )
                constraint_count += 1

    # ── HC8l: Each batch at most 1 lab per (day, period) ──────────────────────
    for (bid, day, period), bvars in by_lab_batch_slot.items():
        if len(bvars) > 1:
            model.AddAtMostOne(bvars)
            constraint_count += 1

    # ── HCsync: All batches do labs at same (day, period) ─────────────────────
    if batches and lab_periods:
        for day in days:
            for period in lab_periods:
                use_lab = model.NewBoolVar(f"use_lab_{day[:3]}_{period}")
                can_use = True
                for batch in batches:
                    bvars = by_lab_batch_slot.get(
                        (batch.batch_id, day, period), []
                    )
                    if bvars:
                        model.Add(sum(bvars) == 1).OnlyEnforceIf(use_lab)
                        model.Add(sum(bvars) == 0).OnlyEnforceIf(
                            use_lab.Not()
                        )
                    else:
                        # This batch has no vars here — slot unusable
                        can_use = False
                    constraint_count += 1
                if not can_use:
                    model.Add(use_lab == 0)
                    constraint_count += 1

    # ── HC_contig: Lab sessions must be consecutive periods, SAME room ──────
    # For each (subject, faculty, batch) with lab_hours >= 2, exactly one
    # "block" is chosen: a (day, starting_period, room) tuple.  The block
    # occupies adjacent schedulable periods in the SAME lab room.
    # "Adjacent" means consecutive in the sorted schedulable period list,
    # with no lunch/long break in between.
    slot_lookup = data.get("slot_lookup", {})
    sorted_lab = sorted(lab_periods)

    # Detect break slot_orders to prevent blocks spanning across lunch
    break_orders = set()
    for order, slot in slot_lookup.items():
        if slot.slot_type.value == "break":
            break_orders.add(order)

    def _periods_adjacent(p1: int, p2: int) -> bool:
        """Check two schedulable periods are truly adjacent (no break between)."""
        lo, hi = min(p1, p2), max(p1, p2)
        for b in break_orders:
            if lo < b < hi:
                return False
        return True

    lab_room_list = [r for r in data["rooms"] if r.room_type.value == "lab"]
    all_faculty = data["faculty"]
    for subject in data["subjects"]:
        lh = subject.lab_hours
        if lh < 2:
            continue
        for batch in batches:
            sid = subject.subject_id
            bid = batch.batch_id
            # Check this (subject, batch) has any lab vars at all
            sb_entries = by_lab_subject_batch.get((sid, bid), [])
            if not sb_entries:
                continue

            # Build start_vars across ALL faculty — solver picks best one
            start_vars = []
            for faculty in all_faculty:
                fid = faculty.faculty_id
                # Skip this faculty if they have no lab vars for this subject+batch
                if not by_lab_subject_faculty_batch.get((sid, fid, bid)):
                    continue
                for day in days:
                    for i in range(len(sorted_lab)):
                        # Build a block of lh adjacent schedulable periods
                        block = []
                        valid = True
                        for offset in range(lh):
                            idx = i + offset
                            if idx >= len(sorted_lab):
                                valid = False
                                break
                            p = sorted_lab[idx]
                            if offset > 0 and not _periods_adjacent(sorted_lab[idx - 1], p):
                                valid = False
                                break
                            block.append(p)
                        if not valid:
                            continue

                        # For each lab room, create a block variable
                        for room in lab_room_list:
                            rid = room.room_id
                            # Check all periods in block have a var for this room
                            room_vars = []
                            all_ok = True
                            for p in block:
                                v = by_lab_sfb_day_period_room.get(
                                    (sid, fid, bid, day, p, rid)
                                )
                                if v is None:
                                    all_ok = False
                                    break
                                room_vars.append(v)
                            if not all_ok:
                                continue

                            sv = model.NewBoolVar(
                                f"lbs_{sid[:6]}_{fid[:6]}_{bid[:6]}_{rid[:6]}_{day[:3]}_{block[0]}"
                            )
                            start_vars.append(sv)

                            # If this block+room is chosen, activate
                            # the var for this room at each period
                            for rv in room_vars:
                                model.Add(rv == 1).OnlyEnforceIf(sv)
                            constraint_count += len(room_vars)

            if start_vars:
                model.AddExactlyOne(start_vars)
                constraint_count += 1

    # ── HC_theory_lab: Theory & labs cannot share the same (day, period) ──────
    # Theory is attended by ALL students; if a lab is running for ANY batch,
    # no theory can happen at that slot (students can't be in two places).
    by_lab_slot = variables.get("by_lab_slot", {})
    for day in days:
        for period in periods:
            theory_at_slot = by_theory_slot.get((day, period), [])
            lab_at_slot = by_lab_slot.get((day, period), [])
            if theory_at_slot and lab_at_slot:
                has_theory = model.NewBoolVar(f"ht_{day[:3]}_{period}")
                model.AddMaxEquality(
                    has_theory, [v for _, v in theory_at_slot]
                )
                model.Add(sum(lab_at_slot) == 0).OnlyEnforceIf(has_theory)
                constraint_count += 1

    # ── HC9: No more than 4 consecutive periods (theory + lab) ────────────────
    # Allows 4-period lab blocks (e.g. Project-I) while preventing 5+ straight.
    sorted_periods = sorted(periods)
    for faculty in data["faculty"]:
        fid = faculty.faculty_id
        for day in days:
            day_entries = by_faculty_day.get((fid, day), [])
            if not day_entries:
                continue
            period_vars: dict[int, list] = {}
            for p, var in day_entries:
                period_vars.setdefault(p, []).append(var)
            for i in range(len(sorted_periods) - 4):
                window = sorted_periods[i : i + 5]
                wvars = []
                for p in window:
                    wvars.extend(period_vars.get(p, []))
                if len(wvars) > 4:
                    model.Add(sum(wvars) <= 4)
                    constraint_count += 1

    # ── HC10: 3-credit theory subjects must span ≥2 days ──────────────────────
    for subject in data["subjects"]:
        lh = subject.lecture_hours if subject.lecture_hours is not None else subject.weekly_periods
        if subject.credits >= 3 and lh >= 2:
            for fid in faculty_subject_map.get(subject.subject_id, []):
                day_indicators: dict[str, cp_model.IntVar] = {}
                for day in days:
                    day_slots = by_theory_subject_faculty_day.get(
                        (subject.subject_id, fid, day), []
                    )
                    if day_slots:
                        day_var = model.NewBoolVar(
                            f"day_{fid[:6]}_{subject.subject_id[:6]}_{day[:3]}"
                        )
                        model.AddMaxEquality(day_var, day_slots)
                        day_indicators[day] = day_var
                    else:
                        day_indicators[day] = model.NewConstant(0)
                if day_indicators:
                    model.Add(sum(day_indicators.values()) >= 2)
                    constraint_count += 1

    # ── HC11: At most 1 theory class per subject per day ──────────────────────
    # Prevents the same subject from being scheduled multiple times on one day.
    for subject in data["subjects"]:
        lh = subject.lecture_hours if subject.lecture_hours is not None else subject.weekly_periods
        if lh <= 0:
            continue
        for fid in faculty_subject_map.get(subject.subject_id, []):
            for day in days:
                day_slots = by_theory_subject_faculty_day.get(
                    (subject.subject_id, fid, day), []
                )
                if len(day_slots) > 1:
                    model.Add(sum(day_slots) <= 1)
                    constraint_count += 1

    log.info("hard_constraints_applied", constraints_added=constraint_count)
