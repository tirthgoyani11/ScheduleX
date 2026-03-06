# core/scheduler/variables.py
"""
OR-Tools CP-SAT variable builder — Theory + Lab split.

Two variable sets:
  Theory:  X_t[faculty, subject, room, day, period]
           Only for LECTURE-type periods and CLASSROOM/SEMINAR rooms.
           Applied to whole division (no batch dimension).

  Lab:     X_l[faculty, subject, batch, room, day, period]
           Only for LAB-type periods and LAB rooms.
           Per-batch scheduling with synchronisation constraints.

Indexed lookups are built for O(1) constraint access.
"""
from ortools.sat.python import cp_model
from collections import defaultdict
import structlog
from models.timeslot import SlotType

log = structlog.get_logger()


def build_variables(model: cp_model.CpModel, data: dict) -> dict:
    faculty_subject_map: dict[str, list[str]] = data.get("faculty_subject_map", {})
    days = data["days"]
    periods = data["periods"]
    rooms = data["rooms"]
    subjects = data["subjects"]
    batches = data.get("batches", [])
    slot_lookup = data.get("slot_lookup", {})

    # ── Classify periods by type ──────────────────────────────────────────────
    lecture_periods = []
    lab_periods = []
    for p in periods:
        slot = slot_lookup.get(p)
        if slot and slot.slot_type == SlotType.LAB:
            lab_periods.append(p)
        else:
            lecture_periods.append(p)

    # ── Classify rooms ────────────────────────────────────────────────────────
    classrooms = [r for r in rooms if r.room_type.value != "lab"]
    lab_rooms = [r for r in rooms if r.room_type.value == "lab"]

    # ── Build reverse map: faculty_id → [subject_ids] ─────────────────────────
    faculty_to_subjects: dict[str, list[str]] = {}
    for sid, fids in faculty_subject_map.items():
        for fid in fids:
            faculty_to_subjects.setdefault(fid, []).append(sid)

    subject_by_id = {s.subject_id: s for s in subjects}

    # ── Pre-compute blocked slots ─────────────────────────────────────────────
    blocked_faculty_slots: set[tuple[str, str, int]] = set()
    blocked_room_slots: set[tuple[str, str, int]] = set()
    for booking in data.get("existing_bookings", []):
        blocked_faculty_slots.add((booking.faculty_id, booking.day, booking.period))
        blocked_room_slots.add((booking.room_id, booking.day, booking.period))
    for block in data.get("general_blocks", []):
        blocked_faculty_slots.add((block.faculty_id, block.day, block.period))

    # ── Variable dicts ────────────────────────────────────────────────────────
    theory: dict[tuple, cp_model.IntVar] = {}
    lab: dict[tuple, cp_model.IntVar] = {}

    # ── Combined indexes (theory + lab) ───────────────────────────────────────
    by_faculty_slot: dict[tuple, list] = defaultdict(list)
    by_room_slot: dict[tuple, list] = defaultdict(list)
    by_faculty: dict[str, list] = defaultdict(list)
    by_faculty_day: dict[tuple, list] = defaultdict(list)

    # ── Theory-specific indexes ───────────────────────────────────────────────
    by_theory_subject_faculty: dict[tuple, list] = defaultdict(list)
    by_theory_slot: dict[tuple, list] = defaultdict(list)
    by_theory_subject_faculty_day: dict[tuple, list] = defaultdict(list)

    # ── Lab-specific indexes ──────────────────────────────────────────────────
    by_lab_subject_faculty_batch: dict[tuple, list] = defaultdict(list)
    by_lab_batch_slot: dict[tuple, list] = defaultdict(list)
    by_lab_subject_slot: dict[tuple, list] = defaultdict(list)
    by_lab_slot: dict[tuple, list] = defaultdict(list)

    theory_count = 0
    lab_count = 0
    skipped = 0

    for faculty in data["faculty"]:
        fid = faculty.faculty_id
        assigned_sids = faculty_to_subjects.get(fid, [])
        if not assigned_sids:
            continue

        for sid in assigned_sids:
            subject = subject_by_id.get(sid)
            if subject is None:
                continue

            # ── Theory variables ──────────────────────────────────────────────
            lh = subject.lecture_hours if subject.lecture_hours else subject.weekly_periods
            if lh > 0:
                for room in classrooms:
                    if room.capacity < subject.batch_size:
                        continue
                    rid = room.room_id
                    for day in days:
                        for period in lecture_periods:
                            if (fid, day, period) in blocked_faculty_slots:
                                skipped += 1
                                continue
                            if (rid, day, period) in blocked_room_slots:
                                skipped += 1
                                continue

                            var = model.NewBoolVar(
                                f"T_{fid[:6]}_{sid[:6]}_{rid[:6]}_{day[:3]}_{period}"
                            )
                            key = (fid, sid, rid, day, period)
                            theory[key] = var

                            by_faculty_slot[(fid, day, period)].append(var)
                            by_room_slot[(rid, day, period)].append(var)
                            by_faculty[fid].append((key, var))
                            by_faculty_day[(fid, day)].append((period, var))
                            by_theory_subject_faculty[(sid, fid)].append((key, var))
                            by_theory_slot[(day, period)].append((key, var))
                            by_theory_subject_faculty_day[(sid, fid, day)].append(var)

                            theory_count += 1

            # ── Lab variables ─────────────────────────────────────────────────
            if subject.lab_hours > 0 and batches and lab_periods:
                for batch in batches:
                    bid = batch.batch_id
                    for room in lab_rooms:
                        if room.capacity < batch.size:
                            continue
                        rid = room.room_id
                        for day in days:
                            for period in lab_periods:
                                if (fid, day, period) in blocked_faculty_slots:
                                    skipped += 1
                                    continue
                                if (rid, day, period) in blocked_room_slots:
                                    skipped += 1
                                    continue

                                var = model.NewBoolVar(
                                    f"L_{fid[:6]}_{sid[:6]}_{bid[:6]}_{rid[:6]}_{day[:3]}_{period}"
                                )
                                key = (fid, sid, bid, rid, day, period)
                                lab[key] = var

                                by_faculty_slot[(fid, day, period)].append(var)
                                by_room_slot[(rid, day, period)].append(var)
                                by_faculty[fid].append((key, var))
                                by_faculty_day[(fid, day)].append((period, var))
                                by_lab_subject_faculty_batch[(sid, fid, bid)].append(
                                    (key, var)
                                )
                                by_lab_batch_slot[(bid, day, period)].append(var)
                                by_lab_subject_slot[(sid, day, period)].append(var)
                                by_lab_slot[(day, period)].append(var)

                                lab_count += 1

    log.info(
        "variables_built",
        theory_vars=theory_count,
        lab_vars=lab_count,
        total_vars=theory_count + lab_count,
        skipped_blocked_slots=skipped,
        batch_count=len(batches),
        lecture_periods=lecture_periods,
        lab_periods=lab_periods,
    )

    return {
        "theory": theory,
        "lab": lab,
        # combined
        "by_faculty_slot": dict(by_faculty_slot),
        "by_room_slot": dict(by_room_slot),
        "by_faculty": dict(by_faculty),
        "by_faculty_day": dict(by_faculty_day),
        # theory-specific
        "by_theory_subject_faculty": dict(by_theory_subject_faculty),
        "by_theory_slot": dict(by_theory_slot),
        "by_theory_subject_faculty_day": dict(by_theory_subject_faculty_day),
        # lab-specific
        "by_lab_subject_faculty_batch": dict(by_lab_subject_faculty_batch),
        "by_lab_batch_slot": dict(by_lab_batch_slot),
        "by_lab_subject_slot": dict(by_lab_subject_slot),
        "by_lab_slot": dict(by_lab_slot),
        # meta
        "lecture_periods": lecture_periods,
        "lab_periods": lab_periods,
    }
