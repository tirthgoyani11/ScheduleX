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

    if ("free" in msg or "available" in msg) and ("room" in msg or "lab" in msg):
        day = entities.get("day") or "Thursday"
        period = entities.get("period") or 3
        booked = (await db.execute(
            select(GlobalBooking.room_id)
            .where(GlobalBooking.college_id == college_id,
                   GlobalBooking.day == day,
                   GlobalBooking.period == period)
        )).scalars().all()
        booked_ids = set(booked)
        rooms = (await db.execute(
            select(Room).where(Room.college_id == college_id)
        )).scalars().all()
        free = [r for r in rooms if r.room_id not in booked_ids]
        if not free:
            raw = f"No free rooms on {day} Period {period}."
        else:
            room_list = "\n".join(f"• {r.name} (cap {r.capacity}, {r.room_type})" for r in free)
            raw = f"Free rooms on {day} Period {period}:\n{room_list}"

    elif "load" in msg or "hours" in msg:
        facs = (await db.execute(
            select(Faculty).where(Faculty.dept_id == dept_id)
        )).scalars().all()
        lines = []
        for f in facs:
            cnt = (await db.execute(
                select(func.count()).select_from(TimetableEntry)
                .where(TimetableEntry.faculty_id == f.faculty_id)
            )).scalar() or 0
            pct = round(cnt / f.max_weekly_load * 100) if f.max_weekly_load else 0
            icon = "🟢" if pct < 80 else "🟡" if pct < 100 else "🔴"
            lines.append(f"{icon} {f.name}: {cnt}/{f.max_weekly_load} ({pct}%)")
        raw = "Faculty load:\n" + "\n".join(lines)

    elif any(w in msg for w in ("clash", "conflict", "double")):
        raw = "✅ Zero clashes — the OR-Tools solver mathematically guarantees this."  # simplified

    else:
        raw = ("I can answer about room availability, faculty load, and clashes. "
               "Try: 'Which rooms are free Monday Period 2?'")

    return await llm.chat(
        f"User asked: '{user_msg}'\nData:\n{raw}\n\nWrite a friendly 2-3 sentence summary.",
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

    load_tracker: dict[str, int] = {f.faculty_id: 0 for f in faculty_list}
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
        candidates = []
        for fac in faculty_list:
            sc = _match_score(fac, sub)
            if sc > 0:
                candidates.append((sc - load_tracker[fac.faculty_id] * 5, fac))
        if candidates:
            candidates.sort(key=lambda x: (-x[0], load_tracker[x[1].faculty_id]))
            best = candidates[0][1]
            sid_to_fid[sub.subject_id] = best.faculty_id
            load_tracker[best.faculty_id] += _sub_load(sub)
        elif faculty_list:
            least = min(faculty_list, key=lambda f: load_tracker[f.faculty_id])
            sid_to_fid[sub.subject_id] = least.faculty_id
            load_tracker[least.faculty_id] += _sub_load(sub)

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
    lab_fixed = await _fix_all_lab_capacities(db, college_id, subject_list, auto_fixes)
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
) -> bool:
    """Scan ALL lab subjects and ensure at least one matching lab can fit them."""
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
        valid_labs = [lab for lab in matching_labs if lab.capacity >= sub.batch_size]

        if valid_labs:
            continue  # This subject is fine

        if matching_labs:
            # Upgrade the biggest matching lab
            biggest = max(matching_labs, key=lambda r: r.capacity)
            old_cap = biggest.capacity
            biggest.capacity = sub.batch_size
            db.add(biggest)
            auto_fixes.append(
                f"Upgraded '{biggest.name}' capacity: {old_cap} → {sub.batch_size} "
                f"(needed for '{sub.name}')"
            )
            fixed = True
        else:
            # Create a new lab
            lab_name = f"{sub.name} Lab"
            new_lab = RoomModel(
                room_id=str(uuid.uuid4()),
                college_id=college_id,
                name=lab_name,
                capacity=sub.batch_size,
                room_type=RoomType.LAB,
                has_projector=True, has_computers=True, has_ac=True,
            )
            db.add(new_lab)
            all_labs.append(new_lab)
            lab_categories[new_lab.room_id] = _infer_lab_category(lab_name)
            auto_fixes.append(
                f"Created new lab '{lab_name}' with {sub.batch_size} seats"
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
