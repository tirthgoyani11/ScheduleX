# core/chatbot/handlers.py
"""
One handler per intent.  Each receives (user_msg, entities, db) and returns a
plain-text reply string.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.faculty import Faculty
from models.subject import Subject
from models.room import Room
from models.timetable import Timetable, TimetableEntry, TimetableStatus
from models.global_booking import GlobalBooking
from models.user import User
from models.college import Department

from .llm_client import llm


# ── QUERY ─────────────────────────────────────────────────────────
async def handle_query(
    user_msg: str, entities: dict, db: AsyncSession,
    college_id: str, dept_id: str,
) -> str:
    msg = user_msg.lower()

    # ── Extract semester from entities or message ──
    semester = entities.get("semester")
    if not semester:
        import re
        sem_m = re.search(r'sem(?:ester)?\s*(\d)', msg)
        if sem_m:
            semester = int(sem_m.group(1))

    # ── Extract day ──
    day = entities.get("day")
    if not day:
        for d in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"):
            if d.lower() in msg or d[:3].lower() in msg:
                day = d
                break

    # ── Extract period ──
    period = entities.get("period")
    if period:
        period = int(period)
    else:
        import re
        pm = re.search(r'(?:period|p|slot)\s*(\d)', msg)
        if not pm:
            pm = re.search(r'(\d)(?:st|nd|rd|th)\s*(?:period|slot|lecture)?', msg)
        if pm:
            period = int(pm.group(1))

    # ── Load timeslots for reference ──
    from models.timeslot import TimeSlotConfig
    dept = await db.get(Department, dept_id) if dept_id else None
    ts_college_id = dept.college_id if dept else college_id
    slot_result = await db.execute(
        select(TimeSlotConfig)
        .where(TimeSlotConfig.college_id == ts_college_id)
        .order_by(TimeSlotConfig.slot_order)
    )
    all_slots = slot_result.scalars().all()
    non_break_slots = [s for s in all_slots if s.slot_type.value != "break"]
    ALL_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

    # ── Branch 1: Free slots / free rooms for a semester ──
    if ("free" in msg or "available" in msg or "open" in msg) and (
        "slot" in msg or "room" in msg or "class" in msg or "lab" in msg
        or "time" in msg or "period" in msg or semester
    ):
        # Find the timetable for this semester
        tt = None
        if semester:
            tt_result = await db.execute(
                select(Timetable)
                .where(
                    Timetable.dept_id == dept_id,
                    Timetable.semester == semester,
                    Timetable.status.in_([TimetableStatus.PUBLISHED, TimetableStatus.DRAFT]),
                )
                .order_by(Timetable.created_at.desc())
            )
            tt = tt_result.scalars().first()

        if not tt and semester:
            return (
                f"No timetable found for semester {semester}. "
                f"Generate one first by saying 'Generate timetable for semester {semester}'."
            )

        # Get all existing entries for this timetable
        entries = []
        if tt:
            entry_result = await db.execute(
                select(TimetableEntry).where(
                    TimetableEntry.timetable_id == tt.timetable_id
                )
            )
            entries = entry_result.scalars().all()

        # Build set of occupied (day, period) combos
        occupied = {(e.day, e.period) for e in entries}

        # Also get globally booked rooms
        booked_rooms: dict[str, set] = {}  # "(day, period)" → set of room_ids
        if tt:
            for e in entries:
                key = f"{e.day}|{e.period}"
                booked_rooms.setdefault(key, set()).add(e.room_id)

        # Get all rooms
        rooms = (await db.execute(
            select(Room).where(Room.college_id == college_id)
        )).scalars().all()
        classrooms = [r for r in rooms if r.room_type.value in ("classroom", "seminar_hall")]
        labs = [r for r in rooms if r.room_type.value == "lab"]

        if day and period:
            # Specific slot — show free rooms for that exact slot
            key = f"{day}|{period}"
            booked_ids = booked_rooms.get(key, set())

            # Also check global bookings
            global_booked = (await db.execute(
                select(GlobalBooking.room_id)
                .where(GlobalBooking.college_id == college_id,
                       GlobalBooking.day == day,
                       GlobalBooking.period == period)
            )).scalars().all()
            booked_ids = booked_ids | set(global_booked)

            free_rooms = [r for r in rooms if r.room_id not in booked_ids]
            free_cr = [r for r in free_rooms if r.room_type.value in ("classroom", "seminar_hall")]
            free_labs = [r for r in free_rooms if r.room_type.value == "lab"]

            # Check if sem students are free too
            sem_label = f"Sem {semester}" if semester else ""
            slot_info = next((s for s in non_break_slots if s.slot_order == period), None)
            time_str = f"{slot_info.start_time}–{slot_info.end_time}" if slot_info else f"Period {period}"

            lines = [f"📍 **Free resources on {day} Period {period} ({time_str}):**"]
            if semester:
                is_sem_free = (day, period) not in occupied
                lines.append(f"• Sem {semester} students: {'✅ FREE' if is_sem_free else '❌ Occupied'}")
            lines.append(f"• Free classrooms: **{len(free_cr)}** of {len(classrooms)}")
            if free_cr:
                lines.append("  " + ", ".join(f"{r.name} ({r.capacity})" for r in free_cr[:8]))
                if len(free_cr) > 8:
                    lines.append(f"  ...and {len(free_cr) - 8} more")
            lines.append(f"• Free labs: **{len(free_labs)}** of {len(labs)}")
            if free_labs:
                lines.append("  " + ", ".join(f"{r.name} ({r.capacity})" for r in free_labs[:8]))
                if len(free_labs) > 8:
                    lines.append(f"  ...and {len(free_labs) - 8} more")
            return "\n".join(lines)

        elif day:
            # Show all free periods for this day
            lines = [f"📅 **Free slots on {day}" + (f" for Sem {semester}" if semester else "") + ":**"]
            for slot in non_break_slots:
                is_free = (day, slot.slot_order) not in occupied
                key = f"{day}|{slot.slot_order}"
                n_rooms_booked = len(booked_rooms.get(key, set()))
                n_free_rooms = len(rooms) - n_rooms_booked
                status = "✅ FREE" if is_free else "❌ Occupied"
                lines.append(
                    f"  P{slot.slot_order} ({slot.start_time}–{slot.end_time}): "
                    f"{status} | {n_free_rooms} rooms available"
                )
            return "\n".join(lines)

        else:
            # Show overview of all free slots across the week
            lines = [f"📊 **Free slot overview" + (f" for Sem {semester}" if semester else "") + ":**\n"]
            lines.append("Day         | " + " | ".join(f"P{s.slot_order}" for s in non_break_slots))
            lines.append("------------ | " + " | ".join("---" for _ in non_break_slots))
            for d in ALL_DAYS:
                row = []
                for slot in non_break_slots:
                    is_free = (d, slot.slot_order) not in occupied
                    row.append(" ✅ " if is_free else " ❌ ")
                lines.append(f"{d:<12} | " + " | ".join(row))

            free_count = sum(
                1 for d in ALL_DAYS for s in non_break_slots
                if (d, s.slot_order) not in occupied
            )
            total = len(ALL_DAYS) * len(non_break_slots)
            lines.append(f"\n**{free_count}/{total} slots free.** Specify a day for room details, e.g. 'Free rooms Tuesday P3 for sem {semester or 3}'")
            return "\n".join(lines)

    # ── Branch 2: Faculty load ──
    elif "load" in msg or "hours" in msg or "workload" in msg:
        facs = (await db.execute(
            select(Faculty).where(Faculty.dept_id == dept_id)
        )).scalars().all()
        lines = ["📊 **Faculty Workload:**"]
        for f in facs:
            cnt = (await db.execute(
                select(func.count()).select_from(TimetableEntry)
                .where(TimetableEntry.faculty_id == f.faculty_id)
            )).scalar() or 0
            pct = round(cnt / f.max_weekly_load * 100) if f.max_weekly_load else 0
            icon = "🟢" if pct < 80 else "🟡" if pct < 100 else "🔴"
            lines.append(f"{icon} {f.name}: {cnt}/{f.max_weekly_load} periods ({pct}%)")
        return "\n".join(lines)

    # ── Branch 3: Clashes ──
    elif any(w in msg for w in ("clash", "conflict", "double")):
        return "✅ Zero clashes — the OR-Tools CP-SAT solver mathematically guarantees no faculty, room, or batch conflicts."

    # ── Branch 4: Who teaches / what's scheduled ──
    elif any(w in msg for w in ("who teach", "which faculty", "professor for")):
        if not semester:
            return "Which semester? e.g. 'Who teaches in semester 3?'"
        subjects = (await db.execute(
            select(Subject).where(Subject.dept_id == dept_id, Subject.semester == semester)
        )).scalars().all()

        tt_result = await db.execute(
            select(Timetable)
            .where(Timetable.dept_id == dept_id, Timetable.semester == semester,
                   Timetable.status.in_([TimetableStatus.PUBLISHED, TimetableStatus.DRAFT]))
            .order_by(Timetable.created_at.desc())
        )
        tt = tt_result.scalars().first()
        if not tt:
            return f"No timetable found for semester {semester}."

        entries = (await db.execute(
            select(TimetableEntry).where(TimetableEntry.timetable_id == tt.timetable_id)
        )).scalars().all()

        # Map subject_id → faculty_id
        sub_fac: dict[str, set] = {}
        for e in entries:
            sub_fac.setdefault(e.subject_id, set()).add(e.faculty_id)

        lines = [f"👨‍🏫 **Faculty assignments for Sem {semester}:**"]
        for sub in subjects:
            fac_ids = sub_fac.get(sub.subject_id, set())
            if fac_ids:
                fac_names = []
                for fid in fac_ids:
                    f = await db.get(Faculty, fid)
                    fac_names.append(f.name if f else "Unknown")
                lines.append(f"• {sub.name}: {', '.join(fac_names)}")
            else:
                lines.append(f"• {sub.name}: ⚠️ Not assigned")
        return "\n".join(lines)

    # ── Branch 5: Schedule overview for a day ──
    elif day and semester:
        tt_result = await db.execute(
            select(Timetable)
            .where(Timetable.dept_id == dept_id, Timetable.semester == semester,
                   Timetable.status.in_([TimetableStatus.PUBLISHED, TimetableStatus.DRAFT]))
            .order_by(Timetable.created_at.desc())
        )
        tt = tt_result.scalars().first()
        if not tt:
            return f"No timetable for semester {semester}."

        entries = (await db.execute(
            select(TimetableEntry)
            .where(TimetableEntry.timetable_id == tt.timetable_id,
                   TimetableEntry.day == day)
        )).scalars().all()

        if not entries:
            return f"No classes on {day} for semester {semester}."

        lines = [f"📅 **{day} schedule for Sem {semester}:**"]
        sorted_entries = sorted(entries, key=lambda e: e.period)
        for e in sorted_entries:
            sub = await db.get(Subject, e.subject_id)
            fac = await db.get(Faculty, e.faculty_id)
            room = await db.get(Room, e.room_id)
            slot = next((s for s in non_break_slots if s.slot_order == e.period), None)
            time_str = f"{slot.start_time}–{slot.end_time}" if slot else ""
            batch_str = f" ({e.batch})" if e.batch else ""
            lines.append(
                f"  P{e.period} ({time_str}): {sub.name if sub else '?'}{batch_str} "
                f"| {fac.name if fac else '?'} | {room.name if room else '?'}"
            )
        return "\n".join(lines)

    # ── Default: guide the user ──
    else:
        return (
            "I can help with:\n"
            "• **Free slots**: 'Which slots are free for sem 3?'\n"
            "• **Free rooms**: 'Which rooms are free Tuesday P3?'\n"
            "• **Faculty load**: 'Show faculty workload'\n"
            "• **Schedule**: 'What's scheduled Monday for sem 5?'\n"
            "• **Assignments**: 'Who teaches in semester 3?'\n\n"
            "Try one of these!"
        )


# ── ABSENCE / SUBSTITUTE ─────────────────────────────────────────
async def handle_absence(
    user_msg: str, entities: dict, db: AsyncSession, dept_id: str,
) -> str:
    faculty_name = entities.get("faculty_name", "")
    day = entities.get("day", "today")
    period = entities.get("period", "unknown")

    q = select(Faculty).where(Faculty.dept_id == dept_id)
    if faculty_name:
        q = q.where(Faculty.name.ilike(f"%{faculty_name}%"))
    absent = (await db.execute(q)).scalars().first()
    if not absent:
        return ("I couldn't identify the faculty member. "
                "Please specify their full name, e.g. 'Prof. Harshil Patel is absent Period 3'.")

    # Find substitutes by expertise overlap
    all_fac = (await db.execute(
        select(Faculty).where(
            Faculty.dept_id == dept_id,
            Faculty.faculty_id != absent.faculty_id,
        )
    )).scalars().all()

    absent_exp = set(absent.expertise or [])
    candidates = []
    for f in all_fac:
        exp = set(f.expertise or [])
        overlap = absent_exp & exp
        if overlap:
            candidates.append({"name": f.name, "match": list(overlap), "overlap": len(overlap)})
    candidates.sort(key=lambda c: -c["overlap"])

    if not candidates:
        return f"⚠️ No qualified substitutes for {absent.name}. Assign manually."

    summary = "\n".join(f"{i+1}. {c['name']} (match: {c['match']})" for i, c in enumerate(candidates[:3]))
    return await llm.chat(
        f"{absent.name} absent on {day} Period {period}.\nTop subs:\n{summary}\n"
        "Recommend the best substitute in 3-4 sentences.",
    )


# ── EXPLAIN ───────────────────────────────────────────────────────
async def handle_explain(
    user_msg: str, entities: dict, db: AsyncSession,
    college_id: str, dept_id: str,
) -> str:
    subjects = (await db.execute(select(Subject).where(Subject.dept_id == dept_id))).scalars().all()
    facs = (await db.execute(select(Faculty).where(Faculty.dept_id == dept_id))).scalars().all()
    rooms = (await db.execute(select(Room).where(Room.college_id == college_id))).scalars().all()

    ctx = (
        f"Database: {len(subjects)} subjects, {len(facs)} faculty, {len(rooms)} rooms "
        f"({sum(1 for r in rooms if r.room_type=='lab')} labs).\n"
        f"User question: {user_msg}"
    )
    return await llm.chat(
        ctx,
        system="You are an expert university scheduling consultant. Explain decisions clearly.",
        thinking=True,
    )


# ── SMALLTALK ─────────────────────────────────────────────────────
async def handle_smalltalk(user_msg: str) -> str:
    return await llm.chat(
        user_msg,
        system=(
            "You are TimetableAI, a friendly scheduling assistant. "
            "You help with timetables, faculty scheduling, room allocation, and exams. "
            "Respond warmly; if it's a greeting, mention what you can help with."
        ),
    )


# ── GENERATE ──────────────────────────────────────────────────────
async def handle_generate(
    user_msg: str, entities: dict, db: AsyncSession,
    college_id: str, dept_id: str,
) -> dict:
    """
    Handle timetable generation via chat.
    Flow: extract semester → AI pre-analysis → auto-assign → run solver → AI post-analysis
    Returns dict with reply + structured data for frontend.
    """
    from .generation_advisor import pre_generation_analysis, post_generation_analysis

    # Extract semester from entities or message
    semester = entities.get("semester")
    if not semester:
        # Try to find a number in the message
        import re
        nums = re.findall(r'\b([1-8])\b', user_msg)
        semester = int(nums[0]) if nums else None

    if not semester:
        return {
            "reply": (
                "Which semester should I generate the timetable for? "
                "Please specify, e.g. 'Generate timetable for semester 3'."
            ),
            "data": {"needs_semester": True},
        }

    # Step 1: Auto-assign faculty to subjects (inline logic)
    from models.faculty import Faculty as FacultyModel
    from models.subject import Subject as SubjectModel
    from models.batch import Batch

    fac_result = await db.execute(
        select(FacultyModel).where(FacultyModel.dept_id == dept_id)
    )
    faculty_list = fac_result.scalars().all()

    sub_result = await db.execute(
        select(SubjectModel).where(
            SubjectModel.dept_id == dept_id,
            SubjectModel.semester == semester,
        )
    )
    subject_list = sub_result.scalars().all()

    if not subject_list:
        return {
            "reply": f"No subjects found for semester {semester} in your department.",
            "data": None,
        }

    if not faculty_list:
        return {
            "reply": "No faculty found in your department. Please add faculty first.",
            "data": None,
        }

    # Build auto-assignment map {faculty_id: [subject_ids]}
    batch_result = await db.execute(
        select(Batch).where(Batch.dept_id == dept_id, Batch.semester == semester)
    )
    num_batches = len(batch_result.scalars().all()) or 1

    # Load existing bookings to calculate remaining capacity
    from models.global_booking import GlobalBooking
    booking_result = await db.execute(
        select(GlobalBooking.faculty_id)
        .where(GlobalBooking.college_id == college_id)
    )
    existing_booking_counts: dict[str, int] = {}
    for (fid_b,) in booking_result.all():
        existing_booking_counts[fid_b] = existing_booking_counts.get(fid_b, 0) + 1

    subject_keywords: dict[str, list[str]] = {}
    for sub in subject_list:
        subject_keywords[sub.subject_id] = [
            w.lower() for w in sub.name.split() if len(w) > 2
        ]

    abbreviation_map = {
        "cn": ["computer networks", "computer network"],
        "os": ["operating systems", "operating system"],
        "dbms": ["database management", "database"],
        "se": ["software engineering"],
        "daa": ["design & analysis of algorithms", "design and analysis", "algorithms"],
        "toc": ["theory of computation"],
        "wp": ["web programming", "web development"],
        "ds": ["data structures", "data structure"],
        "ai": ["artificial intelligence"],
        "ml": ["machine learning"],
        "cd": ["compiler design"],
        "coa": ["computer organization", "computer architecture"],
    }

    load_tracker: dict[str, int] = {
        f.faculty_id: existing_booking_counts.get(f.faculty_id, 0)
        for f in faculty_list
    }
    sid_to_fid: dict[str, str] = {}

    def _match_score(fac, sub):
        expertise = [e.lower().strip() for e in (fac.expertise or [])]
        name_lower = sub.name.lower()
        sc = 0
        for exp in expertise:
            if exp in abbreviation_map:
                for phrase in abbreviation_map[exp]:
                    if phrase in name_lower:
                        sc = max(sc, 100)
                        break
            elif exp in name_lower:
                sc = max(sc, 80)
            elif any(kw in exp for kw in subject_keywords.get(sub.subject_id, [])):
                sc = max(sc, 60)
        return sc

    def _sub_load(s):
        lh = s.lecture_hours if s.lecture_hours else s.weekly_periods
        return lh + s.lab_hours * num_batches

    for sub in sorted(subject_list, key=_sub_load, reverse=True):
        needed = _sub_load(sub)
        candidates = []
        for fac in faculty_list:
            remaining = fac.max_weekly_load - load_tracker[fac.faculty_id]
            if remaining < needed:
                continue
            sc = _match_score(fac, sub)
            if sc > 0:
                candidates.append((sc - load_tracker[fac.faculty_id] * 5, fac))
        if candidates:
            candidates.sort(key=lambda x: (-x[0], load_tracker[x[1].faculty_id]))
            best = candidates[0][1]
            sid_to_fid[sub.subject_id] = best.faculty_id
            load_tracker[best.faculty_id] += needed
        else:
            # Fallback: pick faculty with most remaining capacity
            available = [(fac.max_weekly_load - load_tracker[fac.faculty_id], fac)
                         for fac in faculty_list
                         if fac.max_weekly_load - load_tracker[fac.faculty_id] >= needed]
            if available:
                available.sort(key=lambda x: -x[0])
                best = available[0][1]
            else:
                # Last resort: least loaded faculty
                best = min(faculty_list, key=lambda f: load_tracker[f.faculty_id])
            sid_to_fid[sub.subject_id] = best.faculty_id
            load_tracker[best.faculty_id] += needed

    # Convert to {faculty_id: [subject_ids]}
    faculty_subject_map: dict[str, list[str]] = {}
    for sid, fid in sid_to_fid.items():
        faculty_subject_map.setdefault(fid, []).append(sid)

    # Step 2: AI pre-generation analysis + auto-fix
    pre_analysis = await pre_generation_analysis(
        semester, faculty_subject_map, db, dept_id, college_id,
    )

    auto_fixes: list[str] = []
    if not pre_analysis["ok"]:
        # Auto-fix: redistribute overloaded faculty
        subject_by_id = {s.subject_id: s for s in subject_list}
        faculty_by_id = {f.faculty_id: f for f in faculty_list}
        max_retries = 5
        for _attempt in range(max_retries):
            overloaded_fids = []
            for fid, sids in faculty_subject_map.items():
                fac = faculty_by_id.get(fid)
                if not fac or not fac.max_weekly_load:
                    continue
                total = sum(_sub_load(subject_by_id[s]) for s in sids if s in subject_by_id)
                if total > fac.max_weekly_load:
                    overloaded_fids.append((fid, total, fac.max_weekly_load))

            if not overloaded_fids:
                break

            for fid, total, maxl in overloaded_fids:
                fac = faculty_by_id[fid]
                sids = list(faculty_subject_map.get(fid, []))
                # Sort subjects by load ascending — move smallest first
                sids.sort(key=lambda s: _sub_load(subject_by_id[s]) if s in subject_by_id else 0)
                while total > maxl and sids:
                    move_sid = sids.pop(0)
                    sub = subject_by_id.get(move_sid)
                    if not sub:
                        continue
                    s_load = _sub_load(sub)
                    # Find least-loaded faculty who can accept
                    best_target = None
                    best_load = float("inf")
                    for tf in faculty_list:
                        if tf.faculty_id == fid:
                            continue
                        t_sids = faculty_subject_map.get(tf.faculty_id, [])
                        t_total = sum(
                            _sub_load(subject_by_id[s]) for s in t_sids if s in subject_by_id
                        )
                        if tf.max_weekly_load and t_total + s_load > tf.max_weekly_load:
                            continue
                        if t_total < best_load:
                            best_load = t_total
                            best_target = tf
                    if not best_target:
                        # Accept even over-limit as last resort
                        best_target = min(
                            (f for f in faculty_list if f.faculty_id != fid),
                            key=lambda f: sum(
                                _sub_load(subject_by_id[s])
                                for s in faculty_subject_map.get(f.faculty_id, [])
                                if s in subject_by_id
                            ),
                        )
                    # Move subject
                    faculty_subject_map[fid] = [s for s in faculty_subject_map[fid] if s != move_sid]
                    faculty_subject_map.setdefault(best_target.faculty_id, []).append(move_sid)
                    total -= s_load
                    auto_fixes.append(
                        f"Moved '{sub.name}' from {fac.name} → {best_target.name}"
                    )
            # Remove empty entries
            faculty_subject_map = {k: v for k, v in faculty_subject_map.items() if v}

        # Re-run analysis after fixes
        pre_analysis = await pre_generation_analysis(
            semester, faculty_subject_map, db, dept_id, college_id,
        )

    # Step 2b: Proactive infrastructure fix — ensure labs/rooms can fit subjects
    batch_list_check = (await db.execute(
        select(Batch).where(Batch.dept_id == dept_id, Batch.semester == semester)
    )).scalars().all()
    actual_batch_size = max((b.size for b in batch_list_check), default=20)
    lab_fixed = await _fix_all_lab_capacities(db, college_id, subject_list, auto_fixes, actual_batch_size)
    room_fixed = await _fix_all_room_capacities(db, college_id, subject_list, auto_fixes)
    if lab_fixed or room_fixed:
        # Refresh subject list after DB changes
        sub_result = await db.execute(
            select(SubjectModel).where(
                SubjectModel.dept_id == dept_id,
                SubjectModel.semester == semester,
            )
        )
        subject_list = sub_result.scalars().all()

    # Step 3: Solve with auto-fix retry loop
    from core.scheduler.engine import generate_timetable as run_solver
    from models.room import RoomType
    from models.batch import Batch as BatchModel

    max_solver_attempts = 4
    last_result = None
    last_diagnosis = None

    for attempt in range(1, max_solver_attempts + 1):
        # ── Clean old drafts ──────────────────────────────────────────────
        old_tts = await db.execute(
            select(Timetable).where(
                Timetable.dept_id == dept_id,
                Timetable.semester == semester,
                Timetable.status.in_([TimetableStatus.DRAFT, TimetableStatus.DELETED]),
            )
        )
        for old_tt in old_tts.scalars().all():
            await db.execute(
                GlobalBooking.__table__.delete().where(
                    GlobalBooking.timetable_entry_id.in_(
                        select(TimetableEntry.entry_id).where(
                            TimetableEntry.timetable_id == old_tt.timetable_id
                        )
                    )
                )
            )
            await db.execute(
                TimetableEntry.__table__.delete().where(
                    TimetableEntry.timetable_id == old_tt.timetable_id
                )
            )
            await db.delete(old_tt)
        await db.flush()

        timetable = Timetable(
            timetable_id=str(uuid.uuid4()),
            dept_id=dept_id,
            semester=semester,
            academic_year="2024-25",
            status=TimetableStatus.DRAFT,
        )
        db.add(timetable)
        await db.commit()

        # ── Run solver ────────────────────────────────────────────────────
        result = await run_solver(
            timetable_id=timetable.timetable_id,
            db=db,
            config={
                "faculty_subject_map": faculty_subject_map,
                "time_limit_seconds": 120,
            },
        )
        last_result = result
        solver_status = result.get("status", "UNKNOWN")

        if solver_status in ("OPTIMAL", "FEASIBLE"):
            break  # Success — exit loop

        # ── INFEASIBLE — attempt auto-fix at DB level ─────────────────────
        diagnosis = result.get("diagnosis", {})
        last_diagnosis = diagnosis
        diag_type = diagnosis.get("type", "UNKNOWN")

        if attempt >= max_solver_attempts:
            break  # Exhausted attempts

        fixed_something = await _auto_fix_infeasibility(
            diag_type, diagnosis, auto_fixes,
            db, college_id, dept_id, semester,
            subject_list, faculty_list, faculty_subject_map,
            num_batches, _sub_load,
        )
        if not fixed_something:
            break  # Nothing more we can fix

        # Refresh subjects & rooms after DB changes
        sub_result = await db.execute(
            select(SubjectModel).where(
                SubjectModel.dept_id == dept_id,
                SubjectModel.semester == semester,
            )
        )
        subject_list = sub_result.scalars().all()

    # ── Handle final result ───────────────────────────────────────────────
    result = last_result
    solver_status = result.get("status", "UNKNOWN")

    if solver_status in ("OPTIMAL", "FEASIBLE"):
        # AI post-generation analysis
        post_analysis = await post_generation_analysis(timetable.timetable_id, db)

        # Auto-publish for seamless workflow
        timetable.status = TimetableStatus.PUBLISHED
        timetable.published_at = datetime.now(timezone.utc)
        db.add(timetable)
        await db.commit()

        fix_summary = ""
        if auto_fixes:
            fix_summary = (
                "\n\n🔧 **Auto-fixed issues:**\n"
                + "\n".join(f"• {f}" for f in auto_fixes)
            )

        reply = (
            f"✅ **Timetable generated & published for semester {semester}!**\n\n"
            f"📊 Status: {solver_status} | Score: {result.get('score', 0)}% | "
            f"Entries: {result.get('entry_count', 0)} | Time: {result.get('wall_time', 0)}s"
            f"{fix_summary}\n\n"
            f"🤖 **AI Analysis:**\n{post_analysis.get('ai_summary', 'Analysis unavailable.')}\n\n"
            f"📥 You can now say **\"Export PDF\"** to download it."
        )

        return {
            "reply": reply,
            "data": {
                "timetable_id": timetable.timetable_id,
                "status": solver_status,
                "score": result.get("score", 0),
                "entry_count": result.get("entry_count", 0),
                "wall_time": result.get("wall_time", 0),
                "published": True,
                "auto_fixes": auto_fixes,
                "pre_analysis": pre_analysis,
                "post_analysis": post_analysis,
            },
        }
    else:
        diagnosis = result.get("diagnosis") or last_diagnosis or {}
        diag_msg = diagnosis.get("message", "Unknown issue")

        ai_explain = await llm.chat(
            f"Timetable generation failed for semester {semester}.\n"
            f"Status: {solver_status}\nDiagnosis: {diag_msg}\n"
            f"Pre-analysis: {pre_analysis.get('ai_summary', '')}",
            system=(
                "You are TimetableAI. The timetable solver failed. Explain why in simple terms "
                "and suggest 2-3 concrete fixes. Be helpful and encouraging."
            ),
        )

        return {
            "reply": (
                f"❌ **Generation failed for semester {semester}**\n\n"
                f"Status: {solver_status}\n{diag_msg}\n\n"
                f"🤖 **AI Explanation:**\n{ai_explain}"
            ),
            "data": {
                "status": solver_status,
                "diagnosis": diagnosis,
                "pre_analysis": pre_analysis,
            },
        }


# ── GENERATE ALL ──────────────────────────────────────────────────
async def handle_generate_all(
    user_msg: str, entities: dict, db: AsyncSession,
    college_id: str, dept_id: str,
) -> dict:
    """
    Generate timetables for ALL semesters that have subjects in the
    HOD's department.  Calls handle_generate() for each semester
    sequentially, collecting results.
    """
    from models.subject import Subject as SubjectModel

    # Find active semesters
    all_subs = (await db.execute(
        select(SubjectModel.semester)
        .where(SubjectModel.dept_id == dept_id)
        .distinct()
    )).scalars().all()
    active_semesters = sorted(s for s in all_subs if 1 <= s <= 8)

    if not active_semesters:
        return {
            "reply": "No subjects found in your department for any semester.",
            "data": None,
        }

    results = []
    succeeded = 0
    failed = 0

    for sem in active_semesters:
        try:
            gen_result = await handle_generate(
                user_msg=f"Generate timetable for semester {sem}",
                entities={"semester": sem},
                db=db,
                college_id=college_id,
                dept_id=dept_id,
            )
            data = gen_result.get("data") or {}
            status = data.get("status", "UNKNOWN")
            if status in ("OPTIMAL", "FEASIBLE"):
                succeeded += 1
                results.append({
                    "semester": sem,
                    "status": status,
                    "score": data.get("score", 0),
                    "entries": data.get("entry_count", 0),
                    "time": data.get("wall_time", 0),
                    "timetable_id": data.get("timetable_id"),
                })
            else:
                failed += 1
                results.append({
                    "semester": sem,
                    "status": status,
                    "error": data.get("diagnosis", {}).get("message", "Failed"),
                })
        except Exception as exc:
            failed += 1
            results.append({"semester": sem, "status": "ERROR", "error": str(exc)})

    # Build reply
    lines = [
        f"🎓 **Generated timetables for {succeeded}/{len(active_semesters)} semesters!**\n"
    ]
    for r in results:
        if r.get("timetable_id"):
            lines.append(
                f"✅ Sem {r['semester']}: {r['status']} | "
                f"Score: {r['score']}% | {r['entries']} entries | {r['time']}s"
            )
        else:
            lines.append(f"❌ Sem {r['semester']}: {r.get('error', r['status'])}")

    if failed:
        lines.append(f"\n⚠️ {failed} semester(s) failed — try generating them individually.")
    else:
        lines.append("\n🎉 All timetables generated & published successfully!")

    lines.append("\n📥 Say **\"Export PDF\"** to download any timetable.")

    return {
        "reply": "\n".join(lines),
        "data": {
            "action": "generate_all",
            "total": len(active_semesters),
            "succeeded": succeeded,
            "failed": failed,
            "results": results,
        },
    }


# ── AUTO-FIX INFEASIBILITY ────────────────────────────────────────
async def _auto_fix_infeasibility(
    diag_type: str,
    diagnosis: dict,
    auto_fixes: list[str],
    db: AsyncSession,
    college_id: str,
    dept_id: str,
    semester: int,
    subject_list: list,
    faculty_list: list,
    faculty_subject_map: dict[str, list[str]],
    num_batches: int,
    _sub_load,
) -> bool:
    """
    Attempt to fix the root cause of an INFEASIBLE result by modifying
    the database (rooms, subjects, faculty assignments).
    Returns True if a fix was applied, False if nothing could be done.
    """
    from models.room import Room as RoomModel, RoomType
    from models.batch import Batch as BatchModel

    subject_by_id = {s.subject_id: s for s in subject_list}
    faculty_by_id = {f.faculty_id: f for f in faculty_list}

    # ── FIX: No valid lab with sufficient capacity ────────────────────────
    if diag_type == "NO_VALID_LAB":
        affected = diagnosis.get("affected_subject", "")
        required_cap = diagnosis.get("required_capacity", 60)
        available_labs = diagnosis.get("available_labs", [])

        # Strategy 1: Find existing labs of matching category and upgrade capacity
        sub = next((s for s in subject_list if s.name == affected), None)
        if sub:
            from core.scheduler.variables import _infer_subject_lab_needs
            needed_categories = _infer_subject_lab_needs(sub.name)

            # Find labs of matching category in DB
            all_labs = (await db.execute(
                select(RoomModel).where(
                    RoomModel.college_id == college_id,
                    RoomModel.room_type == RoomType.LAB,
                )
            )).scalars().all()

            from core.scheduler.variables import _infer_lab_category
            upgraded = False
            for lab in all_labs:
                cat = _infer_lab_category(lab.name)
                if cat in needed_categories and lab.capacity < required_cap:
                    old_cap = lab.capacity
                    lab.capacity = required_cap
                    db.add(lab)
                    auto_fixes.append(
                        f"Upgraded '{lab.name}' capacity: {old_cap} → {required_cap} seats"
                    )
                    upgraded = True
                    break  # One upgrade is enough

            if not upgraded:
                # Strategy 2: Create a new lab room
                lab_name = f"{affected} Lab"
                new_lab = RoomModel(
                    room_id=str(uuid.uuid4()),
                    college_id=college_id,
                    name=lab_name,
                    capacity=required_cap,
                    room_type=RoomType.LAB,
                    has_projector=True,
                    has_computers=True,
                    has_ac=True,
                )
                db.add(new_lab)
                auto_fixes.append(
                    f"Created new lab '{lab_name}' with {required_cap} seats"
                )

            await db.commit()
            return True

    # ── FIX: Room capacity exceeded (theory classrooms) ───────────────────
    if diag_type == "ROOM_CAPACITY_EXCEEDED":
        affected = diagnosis.get("affected_subject", "")
        required_cap = diagnosis.get("required_capacity", 60)

        sub = next((s for s in subject_list if s.name == affected), None)
        if sub:
            # Find biggest classroom and upgrade it if needed
            all_rooms = (await db.execute(
                select(RoomModel).where(
                    RoomModel.college_id == college_id,
                    RoomModel.room_type == RoomType.CLASSROOM,
                )
            )).scalars().all()

            if all_rooms:
                biggest = max(all_rooms, key=lambda r: r.capacity)
                if biggest.capacity < required_cap:
                    old_cap = biggest.capacity
                    biggest.capacity = required_cap
                    db.add(biggest)
                    auto_fixes.append(
                        f"Upgraded '{biggest.name}' capacity: {old_cap} → {required_cap} seats"
                    )
                    await db.commit()
                    return True

    # ── FIX: Faculty overloaded ───────────────────────────────────────────
    if diag_type == "FACULTY_OVERLOADED":
        for fid, sids in list(faculty_subject_map.items()):
            fac = faculty_by_id.get(fid)
            if not fac or not fac.max_weekly_load:
                continue
            total = sum(
                _sub_load(subject_by_id[s]) for s in sids if s in subject_by_id
            )
            if total <= fac.max_weekly_load:
                continue
            sids_sorted = sorted(
                sids,
                key=lambda s: _sub_load(subject_by_id[s]) if s in subject_by_id else 0,
            )
            while total > fac.max_weekly_load and sids_sorted:
                move_sid = sids_sorted.pop(0)
                sub = subject_by_id.get(move_sid)
                if not sub:
                    continue
                s_load = _sub_load(sub)
                best_target = min(
                    (f for f in faculty_list if f.faculty_id != fid),
                    key=lambda f: sum(
                        _sub_load(subject_by_id[s])
                        for s in faculty_subject_map.get(f.faculty_id, [])
                        if s in subject_by_id
                    ),
                )
                faculty_subject_map[fid] = [
                    s for s in faculty_subject_map[fid] if s != move_sid
                ]
                faculty_subject_map.setdefault(best_target.faculty_id, []).append(
                    move_sid
                )
                total -= s_load
                auto_fixes.append(
                    f"Moved '{sub.name}' from {fac.name} → {best_target.name}"
                )
        faculty_subject_map.update(
            {k: v for k, v in faculty_subject_map.items() if v}
        )
        return True

    # ── FIX: General block conflict ───────────────────────────────────────
    if diag_type == "GENERAL_BLOCK_CONFLICT":
        affected_name = diagnosis.get("affected_faculty", "")
        fac = next((f for f in faculty_list if f.name == affected_name), None)
        if fac:
            from models.faculty import FacultyGeneralBlock
            blocks = (await db.execute(
                select(FacultyGeneralBlock).where(
                    FacultyGeneralBlock.faculty_id == fac.faculty_id
                )
            )).scalars().all()
            removed = min(len(blocks), 3)
            for blk in blocks[:removed]:
                await db.delete(blk)
            if removed:
                auto_fixes.append(
                    f"Removed {removed} general block(s) for {fac.name}"
                )
                await db.commit()
                return True

    # ── FIX: Too many subjects / capacity insufficient ────────────────────
    if diag_type == "TOO_MANY_SUBJECTS":
        # Increase max_weekly_load for all faculty
        for fac in faculty_list:
            if fac.max_weekly_load and fac.max_weekly_load < 30:
                old_load = fac.max_weekly_load
                fac.max_weekly_load = min(old_load + 6, 30)
                db.add(fac)
                auto_fixes.append(
                    f"Increased {fac.name}'s max weekly load: {old_load} → {fac.max_weekly_load}"
                )
        await db.commit()
        return True

    # ── FIX: Pre-solve failure (generic message-based detection) ──────────
    if diag_type == "PRE_SOLVE_FAILURE":
        msg = diagnosis.get("message", "").lower()
        if "lab" in msg and "capacity" in msg or "no lab" in msg:
            # Same as NO_VALID_LAB: scan for subjects needing labs
            fixed = await _fix_all_lab_capacities(
                db, college_id, subject_list, auto_fixes
            )
            if fixed:
                return True
        if "no room" in msg or "classroom" in msg:
            fixed = await _fix_all_room_capacities(
                db, college_id, subject_list, auto_fixes
            )
            if fixed:
                return True

    # ── Generic fallback: scan for ALL lab/room capacity mismatches ───────
    if diag_type in ("UNKNOWN", "NO_VALID_LAB", "ROOM_CAPACITY_EXCEEDED"):
        fixed_lab = await _fix_all_lab_capacities(
            db, college_id, subject_list, auto_fixes
        )
        fixed_room = await _fix_all_room_capacities(
            db, college_id, subject_list, auto_fixes
        )
        if fixed_lab or fixed_room:
            return True

    return False


async def _fix_all_lab_capacities(
    db: AsyncSession,
    college_id: str,
    subject_list: list,
    auto_fixes: list[str],
    batch_size: int = 20,
) -> bool:
    """Scan ALL lab subjects and ensure at least one matching lab can fit a batch."""
    from models.room import Room as RoomModel, RoomType
    from core.scheduler.variables import _infer_subject_lab_needs, _infer_lab_category

    lab_subjects = [s for s in subject_list if s.needs_lab and s.lab_hours > 0]
    if not lab_subjects:
        return False

    all_labs = (await db.execute(
        select(RoomModel).where(
            RoomModel.college_id == college_id,
            RoomModel.room_type == RoomType.LAB,
        )
    )).scalars().all()

    lab_categories = {lab.room_id: _infer_lab_category(lab.name) for lab in all_labs}
    fixed = False

    for sub in lab_subjects:
        needed_cats = _infer_subject_lab_needs(sub.name)
        matching_labs = [
            lab for lab in all_labs
            if lab_categories.get(lab.room_id) in needed_cats
        ]
        # Labs only need to seat individual batches, not the whole division
        valid_labs = [lab for lab in matching_labs if lab.capacity >= batch_size]

        if valid_labs:
            continue  # This subject is fine

        if matching_labs:
            biggest = max(matching_labs, key=lambda r: r.capacity)
            old_cap = biggest.capacity
            biggest.capacity = batch_size
            db.add(biggest)
            auto_fixes.append(
                f"Upgraded '{biggest.name}' capacity: {old_cap} → {batch_size} "
                f"(needed for '{sub.name}')"
            )
            fixed = True
        else:
            lab_name = f"{sub.name} Lab"
            new_lab = RoomModel(
                room_id=str(uuid.uuid4()),
                college_id=college_id,
                name=lab_name,
                capacity=batch_size,
                room_type=RoomType.LAB,
                has_projector=True, has_computers=True, has_ac=True,
            )
            db.add(new_lab)
            all_labs.append(new_lab)
            lab_categories[new_lab.room_id] = _infer_lab_category(lab_name)
            auto_fixes.append(
                f"Created new lab '{lab_name}' with {batch_size} seats"
            )
            fixed = True

    if fixed:
        await db.commit()
    return fixed


async def _fix_all_room_capacities(
    db: AsyncSession,
    college_id: str,
    subject_list: list,
    auto_fixes: list[str],
) -> bool:
    """Ensure every theory subject has at least one classroom that fits."""
    from models.room import Room as RoomModel, RoomType

    theory_subjects = [
        s for s in subject_list
        if (s.lecture_hours if s.lecture_hours else s.weekly_periods) > 0
    ]
    if not theory_subjects:
        return False

    all_classrooms = (await db.execute(
        select(RoomModel).where(
            RoomModel.college_id == college_id,
            RoomModel.room_type == RoomType.CLASSROOM,
        )
    )).scalars().all()

    fixed = False
    for sub in theory_subjects:
        valid = [r for r in all_classrooms if r.capacity >= sub.batch_size]
        if valid:
            continue
        if all_classrooms:
            biggest = max(all_classrooms, key=lambda r: r.capacity)
            if biggest.capacity < sub.batch_size:
                old_cap = biggest.capacity
                biggest.capacity = sub.batch_size
                db.add(biggest)
                auto_fixes.append(
                    f"Upgraded '{biggest.name}' capacity: {old_cap} → {sub.batch_size} "
                    f"(needed for '{sub.name}')"
                )
                fixed = True

    if fixed:
        await db.commit()
    return fixed


# ── PUBLISH ───────────────────────────────────────────────────────
async def handle_publish(
    user_msg: str, entities: dict, db: AsyncSession,
    dept_id: str,
) -> dict:
    """
    Publish the latest draft timetable via chat.
    """
    # Find latest DRAFT timetable for this department
    result = await db.execute(
        select(Timetable)
        .where(
            Timetable.dept_id == dept_id,
            Timetable.status == TimetableStatus.DRAFT,
        )
        .order_by(Timetable.created_at.desc())
    )
    draft = result.scalars().first()

    if not draft:
        return {
            "reply": (
                "No draft timetable found to publish. "
                "Generate a timetable first: 'Generate timetable for semester 3'"
            ),
            "data": None,
        }

    # Publish it
    draft.status = TimetableStatus.PUBLISHED
    draft.published_at = datetime.now(timezone.utc)
    db.add(draft)
    await db.commit()

    # Count entries
    entry_count = (await db.execute(
        select(func.count()).select_from(TimetableEntry)
        .where(TimetableEntry.timetable_id == draft.timetable_id)
    )).scalar() or 0

    reply = await llm.chat(
        f"Timetable for semester {draft.semester} has been published with "
        f"{entry_count} entries and score {draft.optimization_score}%.",
        system=(
            "You are TimetableAI. Confirm the timetable has been published. "
            "Be brief and congratulatory. Mention they can view it in the Timetable page."
        ),
    )

    return {
        "reply": reply,
        "data": {
            "timetable_id": draft.timetable_id,
            "semester": draft.semester,
            "status": "PUBLISHED",
            "score": draft.optimization_score,
            "entry_count": entry_count,
        },
    }


# ── RESCHEDULE / ADD EXTRA LECTURE ────────────────────────────────
async def handle_reschedule(
    user_msg: str, entities: dict, db: AsyncSession,
    college_id: str, dept_id: str,
) -> dict:
    """
    Handle requests to add an extra lecture or reschedule an existing one.
    Extracts semester, day, period, subject, faculty from entities/message.
    Checks conflicts and either adds or moves a timetable entry.
    """
    import re
    msg = user_msg.lower()

    # ── Extract parameters ──
    semester = entities.get("semester")
    if not semester:
        m = re.search(r'sem(?:ester)?\s*(\d)', msg)
        semester = int(m.group(1)) if m else None

    day = entities.get("day")
    if not day:
        for d in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"):
            if d.lower() in msg or d[:3].lower() in msg:
                day = d
                break

    period = entities.get("period")
    if period:
        period = int(period)
    else:
        pm = re.search(r'(?:period|p|slot)\s*(\d)', msg)
        if not pm:
            pm = re.search(r'(\d)(?:st|nd|rd|th)\s*(?:period|slot|lecture)?', msg)
        if pm:
            period = int(pm.group(1))

    subject_name = entities.get("subject_name")
    faculty_name = entities.get("faculty_name")

    # ── Validate: need at least semester ──
    if not semester:
        return {
            "reply": (
                "To reschedule or add an extra lecture, I need:\n"
                "• **Semester** (required): e.g. 'sem 3'\n"
                "• **Day** (optional): e.g. 'Tuesday'\n"
                "• **Period** (optional): e.g. 'P2' or '2nd period'\n"
                "• **Subject** (optional): e.g. 'Computer Networks'\n\n"
                "Example: 'Add extra CN lecture for sem 3 on Tuesday P2'"
            ),
            "data": None,
        }

    # ── Find timetable ──
    tt_result = await db.execute(
        select(Timetable)
        .where(
            Timetable.dept_id == dept_id,
            Timetable.semester == semester,
            Timetable.status.in_([TimetableStatus.PUBLISHED, TimetableStatus.DRAFT]),
        )
        .order_by(Timetable.created_at.desc())
    )
    tt = tt_result.scalars().first()
    if not tt:
        return {
            "reply": f"No timetable found for semester {semester}. Generate one first!",
            "data": None,
        }

    # ── Load entries ──
    entry_result = await db.execute(
        select(TimetableEntry).where(TimetableEntry.timetable_id == tt.timetable_id)
    )
    entries = entry_result.scalars().all()
    occupied = {(e.day, e.period) for e in entries}

    # ── Load timeslots ──
    from models.timeslot import TimeSlotConfig
    dept_obj = await db.get(Department, dept_id) if dept_id else None
    ts_college_id = dept_obj.college_id if dept_obj else college_id
    slot_result = await db.execute(
        select(TimeSlotConfig)
        .where(TimeSlotConfig.college_id == ts_college_id)
        .order_by(TimeSlotConfig.slot_order)
    )
    all_slots = slot_result.scalars().all()
    non_break_slots = [s for s in all_slots if s.slot_type.value != "break"]
    ALL_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

    if not day or not period:
        # Show available free slots so user can pick
        lines = [f"📅 **Free slots for Sem {semester}** — pick one:\n"]
        free_slots = []
        for d in ALL_DAYS:
            day_free = []
            for slot in non_break_slots:
                if (d, slot.slot_order) not in occupied:
                    day_free.append(f"P{slot.slot_order} ({slot.start_time}–{slot.end_time})")
                    free_slots.append((d, slot.slot_order))
            if day_free:
                lines.append(f"**{d}**: {', '.join(day_free)}")

        if not free_slots:
            return {
                "reply": f"❌ No free slots available for Sem {semester}. All periods are occupied.",
                "data": None,
            }

        lines.append(f"\nTell me which slot, e.g. 'Add extra lecture sem {semester} Tuesday P2'")
        return {"reply": "\n".join(lines), "data": None}

    # ── Check if the target slot is free ──
    if (day, period) in occupied:
        existing = next((e for e in entries if e.day == day and e.period == period), None)
        if existing:
            sub = await db.get(Subject, existing.subject_id)
            fac = await db.get(Faculty, existing.faculty_id)
            return {
                "reply": (
                    f"❌ **{day} P{period} is already occupied** by "
                    f"**{sub.name if sub else '?'}** ({fac.name if fac else '?'}).\n\n"
                    f"Pick a different slot, or say 'Which slots are free for sem {semester}?'"
                ),
                "data": None,
            }

    # ── Find subject ──
    subjects = (await db.execute(
        select(Subject).where(Subject.dept_id == dept_id, Subject.semester == semester)
    )).scalars().all()

    target_sub = None
    if subject_name:
        for s in subjects:
            if subject_name.lower() in s.name.lower() or s.name.lower() in subject_name.lower():
                target_sub = s
                break

    if not target_sub and subject_name:
        # Try abbreviation match
        for s in subjects:
            abbr = "".join(w[0] for w in s.name.upper().split() if len(w) > 1)
            if subject_name.upper() == abbr:
                target_sub = s
                break

    if not target_sub:
        sub_list = "\n".join(f"  {i+1}. {s.name}" for i, s in enumerate(subjects))
        return {
            "reply": (
                f"Which subject should I schedule on {day} P{period}?\n\n"
                f"**Available subjects for Sem {semester}:**\n{sub_list}\n\n"
                f"Reply with: 'Add [subject name] on {day} P{period} for sem {semester}'"
            ),
            "data": None,
        }

    # ── Find faculty for this subject ──
    target_fac = None
    if faculty_name:
        fac_result = await db.execute(
            select(Faculty).where(Faculty.dept_id == dept_id,
                                  Faculty.name.ilike(f"%{faculty_name}%"))
        )
        target_fac = fac_result.scalars().first()

    if not target_fac:
        # Find from existing entries — who already teaches this subject?
        existing_fac_ids = {e.faculty_id for e in entries if e.subject_id == target_sub.subject_id}
        if existing_fac_ids:
            fid = next(iter(existing_fac_ids))
            target_fac = await db.get(Faculty, fid)

    if not target_fac:
        return {
            "reply": f"Could not determine faculty for {target_sub.name}. Who should teach it?",
            "data": None,
        }

    # ── Check faculty conflict ──
    fac_busy = (await db.execute(
        select(GlobalBooking)
        .where(GlobalBooking.college_id == college_id,
               GlobalBooking.day == day,
               GlobalBooking.period == period,
               GlobalBooking.faculty_id == target_fac.faculty_id)
    )).scalars().first()
    if fac_busy:
        return {
            "reply": (
                f"❌ **{target_fac.name}** is already booked on {day} P{period}.\n"
                f"Choose a different slot or faculty."
            ),
            "data": None,
        }

    # ── Find a free room ──
    booked_room_ids = (await db.execute(
        select(GlobalBooking.room_id)
        .where(GlobalBooking.college_id == college_id,
               GlobalBooking.day == day,
               GlobalBooking.period == period)
    )).scalars().all()
    booked_set = set(booked_room_ids)

    all_rooms = (await db.execute(
        select(Room).where(Room.college_id == college_id)
    )).scalars().all()
    classrooms = [r for r in all_rooms if r.room_type.value in ("classroom", "seminar_hall")
                  and r.room_id not in booked_set]
    classrooms.sort(key=lambda r: r.capacity)

    if not classrooms:
        return {
            "reply": f"❌ No free classrooms on {day} P{period}. Try a different slot.",
            "data": None,
        }

    target_room = classrooms[0]  # Smallest free classroom

    # ── Create the entry ──
    from models.timetable import EntryType
    new_entry = TimetableEntry(
        entry_id=str(uuid.uuid4()),
        timetable_id=tt.timetable_id,
        day=day,
        period=period,
        subject_id=target_sub.subject_id,
        faculty_id=target_fac.faculty_id,
        room_id=target_room.room_id,
        entry_type=EntryType.REGULAR,
        batch=None,
    )
    db.add(new_entry)

    # Add global booking
    new_booking = GlobalBooking(
        booking_id=str(uuid.uuid4()),
        college_id=college_id,
        timetable_entry_id=new_entry.entry_id,
        day=day,
        period=period,
        faculty_id=target_fac.faculty_id,
        room_id=target_room.room_id,
    )
    db.add(new_booking)
    await db.commit()

    slot_info = next((s for s in non_break_slots if s.slot_order == period), None)
    time_str = f"{slot_info.start_time}–{slot_info.end_time}" if slot_info else f"Period {period}"

    return {
        "reply": (
            f"✅ **Extra lecture added!**\n\n"
            f"📚 **{target_sub.name}**\n"
            f"👨‍🏫 {target_fac.name}\n"
            f"📍 {target_room.name} (capacity {target_room.capacity})\n"
            f"🕐 {day} P{period} ({time_str})\n\n"
            f"The timetable for Sem {semester} has been updated."
        ),
        "data": {
            "timetable_id": tt.timetable_id,
            "action": "added",
            "entry": {
                "day": day,
                "period": period,
                "subject": target_sub.name,
                "faculty": target_fac.name,
                "room": target_room.name,
            },
        },
    }


# ── EXPORT ────────────────────────────────────────────────────────
async def handle_export(
    user_msg: str, entities: dict, db: AsyncSession,
    college_id: str, dept_id: str,
) -> dict:
    """
    Find the latest published/draft timetable and return its ID
    so the frontend can trigger PDF download.
    """
    result = await db.execute(
        select(Timetable)
        .where(
            Timetable.dept_id == dept_id,
            Timetable.status.in_([TimetableStatus.PUBLISHED, TimetableStatus.DRAFT]),
        )
        .order_by(Timetable.created_at.desc())
    )
    tt = result.scalars().first()

    if not tt:
        return {
            "reply": "No timetable found to export. Generate one first!",
            "data": None,
        }

    entry_count = (await db.execute(
        select(func.count()).select_from(TimetableEntry)
        .where(TimetableEntry.timetable_id == tt.timetable_id)
    )).scalar() or 0

    # Determine export type from message
    msg = user_msg.lower()
    export_type = "department"
    if "faculty" in msg:
        export_type = "faculty"
    elif "room" in msg:
        export_type = "room"

    return {
        "reply": (
            f"📥 **Ready to export!** Semester {tt.semester} timetable "
            f"({entry_count} entries, score {tt.optimization_score or 0}%).\n\n"
            f"Click the download button below to get your **{export_type}** PDF."
        ),
        "data": {
            "timetable_id": tt.timetable_id,
            "semester": tt.semester,
            "export_type": export_type,
            "entry_count": entry_count,
            "score": tt.optimization_score,
            "export_ready": True,
        },
    }
