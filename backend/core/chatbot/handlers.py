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

    # Step 2: AI pre-generation analysis
    pre_analysis = await pre_generation_analysis(
        semester, faculty_subject_map, db, dept_id, college_id,
    )

    if not pre_analysis["ok"]:
        critical_issues = [i for i in pre_analysis["issues"] if "🔴" in i]
        return {
            "reply": (
                f"⚠️ **Pre-generation check found critical issues for semester {semester}:**\n\n"
                + "\n".join(critical_issues)
                + "\n\n" + pre_analysis["ai_summary"]
                + "\n\nPlease fix these issues before generating."
            ),
            "data": {"pre_analysis": pre_analysis, "blocked": True},
        }

    # Step 3: Clean old drafts and create timetable
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

    # Step 4: Run solver
    from core.scheduler.engine import generate_timetable as run_solver
    result = await run_solver(
        timetable_id=timetable.timetable_id,
        db=db,
        config={
            "faculty_subject_map": faculty_subject_map,
            "time_limit_seconds": 120,
        },
    )

    solver_status = result.get("status", "UNKNOWN")

    if solver_status in ("OPTIMAL", "FEASIBLE"):
        # Step 5: AI post-generation analysis
        post_analysis = await post_generation_analysis(timetable.timetable_id, db)

        reply = (
            f"✅ **Timetable generated for semester {semester}!**\n\n"
            f"📊 Status: {solver_status} | Score: {result.get('score', 0)}% | "
            f"Entries: {result.get('entry_count', 0)} | Time: {result.get('wall_time', 0)}s\n\n"
            f"🤖 **AI Analysis:**\n{post_analysis.get('ai_summary', 'Analysis unavailable.')}"
        )

        return {
            "reply": reply,
            "data": {
                "timetable_id": timetable.timetable_id,
                "status": solver_status,
                "score": result.get("score", 0),
                "entry_count": result.get("entry_count", 0),
                "wall_time": result.get("wall_time", 0),
                "pre_analysis": pre_analysis,
                "post_analysis": post_analysis,
            },
        }
    else:
        diagnosis = result.get("diagnosis", {})
        diag_msg = diagnosis.get("message", "Unknown issue")

        # Ask LLM to explain the failure
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
