# core/scheduler/variables.py
"""
OR-Tools CP-SAT variable builder.

Creates one Boolean variable for each valid (faculty, subject, room, day, period) combination.
Pre-filters invalid combos to reduce solver search space:
  - Labs only get lab rooms
  - Subject batch_size must fit room capacity
  - Faculty can only teach subjects they're assigned to
  - Slots already blocked by global bookings are excluded

Also builds INDEXED LOOKUPS so constraint functions use O(1) dict access
instead of scanning ALL variables — critical for scaling to 50+ rooms / 60+ faculty.
"""
from ortools.sat.python import cp_model
from collections import defaultdict
import structlog

log = structlog.get_logger()


def build_variables(model: cp_model.CpModel, data: dict) -> dict:
    """
    Build decision variables for the CP-SAT model.

    Each variable X[f, s, r, d, p] is a BoolVar meaning:
      "Faculty f teaches Subject s in Room r on Day d, Period p"

    Returns dict with:
        assignments:             {(fid, sid, rid, day, period): BoolVar}
        by_faculty_slot:         {(fid, day, period): [BoolVar]}
        by_room_slot:            {(rid, day, period): [BoolVar]}
        by_faculty:              {fid: [(key, BoolVar)]}
        by_subject_faculty:      {(sid, fid): [(key, BoolVar)]}
        by_subject_faculty_day:  {(sid, fid, day): [BoolVar]}
        by_batch_slot:           {(batch, day, period): [BoolVar]}
        by_day_period:           {(day, period): [(key, BoolVar)]}
        by_faculty_day:          {(fid, day): [(period, BoolVar)]}
    """
    assignments: dict[tuple, cp_model.IntVar] = {}

    # ── Index dictionaries ────────────────────────────────────────────────────
    by_faculty_slot: dict[tuple, list] = defaultdict(list)
    by_room_slot: dict[tuple, list] = defaultdict(list)
    by_faculty: dict[str, list] = defaultdict(list)
    by_subject_faculty: dict[tuple, list] = defaultdict(list)
    by_subject_faculty_day: dict[tuple, list] = defaultdict(list)
    by_batch_slot: dict[tuple, list] = defaultdict(list)
    by_day_period: dict[tuple, list] = defaultdict(list)
    by_faculty_day: dict[tuple, list] = defaultdict(list)

    faculty_subject_map: dict[str, list[str]] = data.get("faculty_subject_map", {})
    days = data["days"]
    periods = data["periods"]
    rooms = data["rooms"]
    subjects = data["subjects"]

    # Build a reverse map: faculty_id -> [subject_ids]
    # faculty_subject_map is {subject_id: [faculty_ids]}
    faculty_to_subjects: dict[str, list[str]] = {}
    for subject_id, faculty_ids in faculty_subject_map.items():
        for fid in faculty_ids:
            faculty_to_subjects.setdefault(fid, []).append(subject_id)

    # Build subject lookup
    subject_by_id = {s.subject_id: s for s in subjects}

    # Pre-compute blocked slots from existing bookings + general blocks
    blocked_faculty_slots: set[tuple[str, str, int]] = set()
    blocked_room_slots: set[tuple[str, str, int]] = set()
    for booking in data.get("existing_bookings", []):
        blocked_faculty_slots.add((booking.faculty_id, booking.day, booking.period))
        blocked_room_slots.add((booking.room_id, booking.day, booking.period))
    for block in data.get("general_blocks", []):
        blocked_faculty_slots.add((block.faculty_id, block.day, block.period))

    # Pre-compute eligible rooms per subject (filter once, reuse)
    eligible_rooms: dict[str, list] = {}
    for subject in subjects:
        good_rooms = []
        for room in rooms:
            if subject.needs_lab and room.room_type.value != "lab":
                continue
            if room.capacity < subject.batch_size:
                continue
            good_rooms.append(room)
        eligible_rooms[subject.subject_id] = good_rooms

    var_count = 0
    skipped_rooms = 0
    skipped_blocked = 0

    for faculty in data["faculty"]:
        fid = faculty.faculty_id
        assigned_subject_ids = faculty_to_subjects.get(fid, [])
        if not assigned_subject_ids:
            continue

        for sid in assigned_subject_ids:
            subject = subject_by_id.get(sid)
            if subject is None:
                continue

            rooms_for_subject = eligible_rooms.get(sid, [])
            skipped_rooms += len(rooms) - len(rooms_for_subject)

            for room in rooms_for_subject:
                rid = room.room_id
                for day in days:
                    for period in periods:
                        # Pre-filter: skip globally blocked slots
                        if (fid, day, period) in blocked_faculty_slots:
                            skipped_blocked += 1
                            continue
                        if (rid, day, period) in blocked_room_slots:
                            skipped_blocked += 1
                            continue

                        var_name = f"X_{fid[:8]}_{sid[:8]}_{rid[:8]}_{day[:3]}_{period}"
                        var = model.NewBoolVar(var_name)
                        key = (fid, sid, rid, day, period)
                        assignments[key] = var

                        # Populate indexes
                        by_faculty_slot[(fid, day, period)].append(var)
                        by_room_slot[(rid, day, period)].append(var)
                        by_faculty[fid].append((key, var))
                        by_subject_faculty[(sid, fid)].append((key, var))
                        by_subject_faculty_day[(sid, fid, day)].append(var)
                        by_day_period[(day, period)].append((key, var))
                        by_faculty_day[(fid, day)].append((period, var))

                        # Batch index
                        batch = subject.batch
                        if batch:
                            by_batch_slot[(batch, day, period)].append(var)

                        var_count += 1

    log.info(
        "variables_built",
        total_vars=var_count,
        skipped_room_filter=skipped_rooms,
        skipped_blocked_slots=skipped_blocked,
        faculty_count=len(data["faculty"]),
        subject_count=len(subjects),
        room_count=len(rooms),
    )

    return {
        "assignments": assignments,
        "by_faculty_slot": dict(by_faculty_slot),
        "by_room_slot": dict(by_room_slot),
        "by_faculty": dict(by_faculty),
        "by_subject_faculty": dict(by_subject_faculty),
        "by_subject_faculty_day": dict(by_subject_faculty_day),
        "by_batch_slot": dict(by_batch_slot),
        "by_day_period": dict(by_day_period),
        "by_faculty_day": dict(by_faculty_day),
    }
