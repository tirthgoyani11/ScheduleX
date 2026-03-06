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
           Any department faculty can teach labs (not limited to theory teacher).

Indexed lookups are built for O(1) constraint access.
"""
from ortools.sat.python import cp_model
from collections import defaultdict
import structlog
from models.timeslot import SlotType

log = structlog.get_logger()


def _infer_lab_category(room_name: str) -> str:
    """Infer lab category from room name for subject-lab matching."""
    n = room_name.lower()
    if "networking lab" in n:
        return "networking"
    if any(k in n for k in ["computer lab", "ai/ml lab"]):
        return "computer"
    if "electronics lab" in n:
        return "electronics"
    if any(k in n for k in ["electrical", "power systems lab", "power system lab"]):
        return "electrical"
    if any(k in n for k in ["workshop", "mechanical"]):
        return "mechanical"
    if any(k in n for k in ["chemical", "petroleum"]):
        return "chemistry_eng"
    if "physics lab" in n:
        return "physics"
    if "chemistry lab" in n:
        return "chemistry"
    if any(k in n for k in ["design studio", "simulation", "3d printing"]):
        return "design"
    if "robotics" in n:
        return "robotics"
    if "iot lab" in n:
        return "iot"
    return "general"


def _infer_subject_lab_needs(subject_name: str) -> set[str]:
    """Return set of compatible lab categories for a subject with lab component."""
    n = subject_name.lower()

    # Physical science labs
    if "physics" in n:
        return {"physics"}
    if n.startswith("chemistry") and "chemical" not in n:
        return {"chemistry"}

    # Chemical engineering labs
    if any(k in n for k in ["chemical", "petroleum", "polymer"]):
        return {"chemistry_eng"}

    # Mechanical workshops
    if any(k in n for k in ["workshop", "smithy", "fitting", "welding"]):
        return {"mechanical"}
    if "basic mechanical" in n:
        return {"mechanical"}

    # Electrical labs
    if any(k in n for k in ["basic electrical", "electrical machine", "electrical measurement", "power system"]):
        return {"electrical"}

    # Engineering graphics / CAD
    if any(k in n for k in ["engineering graphics", "drafting"]):
        return {"design", "computer"}

    # Electronics-only subjects
    if any(k in n for k in [
        "electronic device", "electronic circuit", "digital electronics",
        "analog communication", "digital communication",
        "vlsi", "linear integrated", "control system",
        "wireless communication", "digital signal",
        "antenna", "network analysis", "basic electronics",
    ]):
        return {"electronics"}

    # Subjects that could use electronics OR computer labs
    if any(k in n for k in ["digital logic", "digital system", "microprocessor", "microcontroller", "embedded"]):
        return {"electronics", "computer"}

    # Robotics
    if "robotics" in n:
        return {"robotics", "computer"}

    # Networking subjects
    if any(k in n for k in ["computer network", "networking"]):
        return {"computer", "networking"}

    # IoT
    if "iot" in n or "internet of things" in n:
        return {"computer", "iot"}

    # Default: computer lab (programming, DS, algorithms, web, DB, AI, ML, etc.)
    return {"computer"}


def build_variables(model: cp_model.CpModel, data: dict) -> dict:
    faculty_subject_map: dict[str, list[str]] = data.get("faculty_subject_map", {})
    days = data["days"]
    periods = data["periods"]
    rooms = data["rooms"]
    subjects = data["subjects"]
    batches = data.get("batches", [])
    slot_lookup = data.get("slot_lookup", {})

    # ── Classify periods — all non-break periods available for both theory & lab
    usable_periods = []
    for p in periods:
        slot = slot_lookup.get(p)
        if slot and slot.slot_type == SlotType.BREAK:
            continue
        usable_periods.append(p)
    # Keep lecture_periods & lab_periods as aliases (both = all usable)
    lecture_periods = list(usable_periods)
    lab_periods = list(usable_periods)

    # ── Classify rooms ────────────────────────────────────────────────────────
    # Theory: only CLASSROOM rooms (exclude seminar halls & auditorium)
    classrooms = [r for r in rooms if r.room_type.value == "classroom"]
    lab_rooms = [r for r in rooms if r.room_type.value == "lab"]

    # Pre-compute lab categories for subject-lab matching
    lab_room_categories = {r.room_id: _infer_lab_category(r.name) for r in lab_rooms}

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
    by_lab_subject_batch: dict[tuple, list] = defaultdict(list)  # (sid,bid) → [(key,var)]
    by_lab_batch_slot: dict[tuple, list] = defaultdict(list)
    by_lab_subject_slot: dict[tuple, list] = defaultdict(list)
    by_lab_slot: dict[tuple, list] = defaultdict(list)
    by_lab_sfb_day_period: dict[tuple, list] = defaultdict(list)  # (sid,fid,bid,day,period) → [var]
    by_lab_sfb_day_period_room: dict[tuple, cp_model.IntVar] = {}  # (sid,fid,bid,day,period,rid) → var

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
            lh = subject.lecture_hours if subject.lecture_hours is not None else subject.weekly_periods
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

    log.info(
        "theory_vars_built", theory_vars=theory_count, skipped=skipped,
    )

    # ── Lab variables (any dept faculty can teach labs) ────────────────────────
    # Decoupled from theory: iterate ALL faculty × ALL lab subjects so the
    # solver can pick the best faculty for each batch's lab independently.
    lab_subjects = [s for s in subjects if s.lab_hours > 0]
    if batches and lab_periods and lab_subjects:
        for subject in lab_subjects:
            sid = subject.subject_id
            subject_lab_needs = _infer_subject_lab_needs(subject.name)
            for faculty in data["faculty"]:
                fid = faculty.faculty_id
                for batch in batches:
                    bid = batch.batch_id
                    for room in lab_rooms:
                        if lab_room_categories[room.room_id] not in subject_lab_needs:
                            continue
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
                                by_lab_subject_batch[(sid, bid)].append((key, var))
                                by_lab_batch_slot[(bid, day, period)].append(var)
                                by_lab_subject_slot[(sid, day, period)].append(var)
                                by_lab_slot[(day, period)].append(var)
                                by_lab_sfb_day_period[(sid, fid, bid, day, period)].append(var)
                                by_lab_sfb_day_period_room[(sid, fid, bid, day, period, rid)] = var

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
        "by_lab_subject_batch": dict(by_lab_subject_batch),
        "by_lab_batch_slot": dict(by_lab_batch_slot),
        "by_lab_subject_slot": dict(by_lab_subject_slot),
        "by_lab_slot": dict(by_lab_slot),
        "by_lab_sfb_day_period": dict(by_lab_sfb_day_period),
        "by_lab_sfb_day_period_room": by_lab_sfb_day_period_room,
        # meta
        "lecture_periods": lecture_periods,
        "lab_periods": lab_periods,
    }
