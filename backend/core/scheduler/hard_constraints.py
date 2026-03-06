# core/scheduler/hard_constraints.py
"""
Hard constraints for theory + multi-batch lab scheduling.

Combined (theory + lab):
  HC1:  No faculty double-booking at any (day, period)
  HC2:  No room double-booking at any (day, period)
  HC4:  Faculty weekly load cap
  HC9:  No more than 3 consecutive periods for same faculty

Theory-specific:
  HC7t:  Each subject-faculty gets exactly lecture_hours theory slots
  HC8t:  At most 1 theory class at any (day, lecture_period) — whole division attends
  HC10:  3-credit subjects with ≥2 lecture_hours must span ≥2 days

Lab-specific:
  HC7l:    Each (subject, faculty, batch) gets exactly lab_hours lab slots
  HC8l:    Each batch has at most 1 lab at any (day, lab_period)
  HCsync:  All batches must have labs at the SAME (day, period) — synchronisation
  HCrot:   At most 1 batch per subject at any (day, lab_period) — rotation
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

    # ── HC4: Faculty weekly load cap ──────────────────────────────────────────
    for faculty in data["faculty"]:
        fid = faculty.faculty_id
        entries = by_faculty.get(fid, [])
        if entries:
            model.Add(sum(v for _, v in entries) <= faculty.max_weekly_load)
            constraint_count += 1

    # ── HC7t: Theory — each (subject, faculty) assigned exactly lecture_hours ─
    for subject in data["subjects"]:
        lh = subject.lecture_hours if subject.lecture_hours else subject.weekly_periods
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

    # ── HC7l: Lab — each (subject, faculty, batch) gets exactly lab_hours ─────
    for subject in data["subjects"]:
        if subject.lab_hours <= 0:
            continue
        for fid in faculty_subject_map.get(subject.subject_id, []):
            for batch in batches:
                entries = by_lab_subject_faculty_batch.get(
                    (subject.subject_id, fid, batch.batch_id), []
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

    # ── HCrot: Different subjects per batch at each lab slot ──────────────────
    for (sid, day, period), svars in by_lab_subject_slot.items():
        if len(svars) > 1:
            model.AddAtMostOne(svars)
            constraint_count += 1

    # ── HC_contig: Lab sessions must be consecutive periods on the same day ──
    # For each (subject, faculty, batch) with lab_hours >= 2, exactly one
    # "block start" must be chosen.  A block start at (day, p) means the lab
    # occupies consecutive slot_orders p, p+1, …, p+lab_hours-1 (no break gap).
    slot_lookup = data.get("slot_lookup", {})
    sorted_lab = sorted(lab_periods)
    for subject in data["subjects"]:
        lh = subject.lab_hours
        if lh < 2:
            continue
        for fid in faculty_subject_map.get(subject.subject_id, []):
            for batch in batches:
                sid = subject.subject_id
                bid = batch.batch_id
                entries = by_lab_subject_faculty_batch.get((sid, fid, bid), [])
                if not entries:
                    continue

                start_vars = []
                for day in days:
                    for i in range(len(sorted_lab)):
                        # Build a block of lh consecutive slot_orders
                        block = []
                        valid = True
                        for offset in range(lh):
                            idx = i + offset
                            if idx >= len(sorted_lab):
                                valid = False
                                break
                            p = sorted_lab[idx]
                            # Consecutive means slot_order differs by exactly 1
                            if offset > 0 and p != sorted_lab[idx - 1] + 1:
                                valid = False
                                break
                            block.append(p)
                        if not valid:
                            continue

                        # Every period in block must have vars for this (sid,fid,bid,day)
                        block_period_vars = []
                        all_have_vars = True
                        for p in block:
                            pvars = by_lab_sfb_day_period.get((sid, fid, bid, day, p), [])
                            if not pvars:
                                all_have_vars = False
                                break
                            block_period_vars.append(pvars)
                        if not all_have_vars:
                            continue

                        sv = model.NewBoolVar(
                            f"lbs_{sid[:6]}_{fid[:6]}_{bid[:6]}_{day[:3]}_{block[0]}"
                        )
                        start_vars.append(sv)

                        # If this block is chosen, exactly 1 var active at each period
                        for pvars in block_period_vars:
                            model.Add(sum(pvars) == 1).OnlyEnforceIf(sv)
                        constraint_count += len(block_period_vars)

                if start_vars:
                    model.AddExactlyOne(start_vars)
                    constraint_count += 1

    # ── HC9: No more than 3 consecutive periods (theory + lab) ────────────────
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
            for i in range(len(sorted_periods) - 3):
                window = sorted_periods[i : i + 4]
                wvars = []
                for p in window:
                    wvars.extend(period_vars.get(p, []))
                if len(wvars) > 3:
                    model.Add(sum(wvars) <= 3)
                    constraint_count += 1

    # ── HC10: 3-credit theory subjects must span ≥2 days ──────────────────────
    for subject in data["subjects"]:
        lh = subject.lecture_hours if subject.lecture_hours else subject.weekly_periods
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

    log.info("hard_constraints_applied", constraints_added=constraint_count)
