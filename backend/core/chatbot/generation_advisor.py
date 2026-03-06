# core/chatbot/generation_advisor.py
"""
AI-powered pre-generation advisor and post-generation analyzer.

Uses the LLM to:
  1. Pre-generation: Validate faculty-subject assignments, detect issues, suggest fixes
  2. Post-generation: Analyze timetable quality and provide improvement suggestions
  3. Smart auto-assign: AI-enhanced faculty-subject matching recommendations
"""
from __future__ import annotations

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.faculty import Faculty
from models.subject import Subject
from models.room import Room
from models.batch import Batch
from models.timetable import Timetable, TimetableEntry, TimetableStatus

from .llm_client import llm


async def pre_generation_analysis(
    semester: int,
    faculty_subject_map: dict[str, list[str]],
    db: AsyncSession,
    dept_id: str,
    college_id: str,
) -> dict:
    """
    Run AI analysis BEFORE generating timetable.
    Checks for issues like faculty overload, unassigned subjects,
    room shortage, and provides suggestions.

    Returns: {ok: bool, issues: [...], suggestions: [...], ai_summary: str}
    """
    # Load data
    faculty_list = (await db.execute(
        select(Faculty).where(Faculty.dept_id == dept_id)
    )).scalars().all()
    subject_list = (await db.execute(
        select(Subject).where(Subject.dept_id == dept_id, Subject.semester == semester)
    )).scalars().all()
    room_list = (await db.execute(
        select(Room).where(Room.college_id == college_id)
    )).scalars().all()
    batch_list = (await db.execute(
        select(Batch).where(Batch.dept_id == dept_id, Batch.semester == semester)
    )).scalars().all()

    faculty_by_id = {f.faculty_id: f for f in faculty_list}
    subject_by_id = {s.subject_id: s for s in subject_list}
    num_batches = len(batch_list) or 1

    issues = []
    suggestions = []

    # ── Check 1: Unassigned subjects ──────────────────────────────────────
    assigned_subject_ids = set()
    for sids in faculty_subject_map.values():
        assigned_subject_ids.update(sids)

    unassigned = [s for s in subject_list if s.subject_id not in assigned_subject_ids]
    if unassigned:
        names = [s.name for s in unassigned]
        issues.append(f"⚠️ {len(unassigned)} unassigned subjects: {', '.join(names)}")
        suggestions.append("Use 'Auto-Assign' or manually assign faculty to all subjects before generating.")

    # ── Check 2: Faculty overload ─────────────────────────────────────────
    for fid, sids in faculty_subject_map.items():
        fac = faculty_by_id.get(fid)
        if not fac:
            continue
        total_load = 0
        for sid in sids:
            sub = subject_by_id.get(sid)
            if sub:
                lh = sub.lecture_hours if sub.lecture_hours else sub.weekly_periods
                total_load += lh + sub.lab_hours * num_batches
        if fac.max_weekly_load and total_load > fac.max_weekly_load:
            issues.append(
                f"🔴 {fac.name} overloaded: {total_load} hours assigned vs {fac.max_weekly_load} max"
            )
            suggestions.append(
                f"Redistribute some subjects from {fac.name} to other faculty."
            )

    # ── Check 3: Room capacity ────────────────────────────────────────────
    classrooms = [r for r in room_list if r.room_type == "classroom"]
    labs = [r for r in room_list if r.room_type == "lab"]

    theory_subjects = [s for s in subject_list
                       if (s.lecture_hours if s.lecture_hours else s.weekly_periods) > 0]
    lab_subjects = [s for s in subject_list if s.lab_hours and s.lab_hours > 0]

    if theory_subjects and not classrooms:
        issues.append("🔴 No classrooms available! Theory lectures cannot be scheduled.")
    if lab_subjects and not labs:
        issues.append("🔴 No lab rooms available! Lab sessions cannot be scheduled.")

    # ── Check 4: Total weekly hours vs available slots ────────────────────
    total_theory_hours = sum(
        s.lecture_hours if s.lecture_hours else s.weekly_periods
        for s in theory_subjects
    )
    total_lab_hours = sum(s.lab_hours * num_batches for s in lab_subjects)
    available_slots_per_day = 7  # approximate
    available_days = 6
    max_theory_slots = len(classrooms) * available_slots_per_day * available_days if classrooms else 0
    max_lab_slots = len(labs) * available_slots_per_day * available_days if labs else 0

    if total_theory_hours > max_theory_slots:
        issues.append(
            f"⚠️ Theory demand ({total_theory_hours}h) exceeds classroom capacity ({max_theory_slots} slots). "
            "Solver may struggle."
        )
    if total_lab_hours > max_lab_slots:
        issues.append(
            f"⚠️ Lab demand ({total_lab_hours}h) exceeds lab capacity ({max_lab_slots} slots)."
        )

    # ── Check 5: Faculty without subjects ─────────────────────────────────
    assigned_faculty_ids = set(faculty_subject_map.keys())
    idle_faculty = [f for f in faculty_list if f.faculty_id not in assigned_faculty_ids]
    if idle_faculty and unassigned:
        suggestions.append(
            f"{len(idle_faculty)} faculty members have no assignments — "
            "consider using them for unassigned subjects."
        )

    # ── Build context and ask LLM for summary ────────────────────────────
    context_lines = [
        f"Department analysis for Semester {semester}:",
        f"- {len(faculty_list)} faculty, {len(subject_list)} subjects, "
        f"{len(classrooms)} classrooms, {len(labs)} labs, {num_batches} batches",
        f"- Theory demand: {total_theory_hours}h, Lab demand: {total_lab_hours}h",
        f"- Assignments: {len(faculty_subject_map)} faculty assigned to {len(assigned_subject_ids)} subjects",
    ]
    if issues:
        context_lines.append("Issues found:")
        context_lines.extend(f"  {i}" for i in issues)
    else:
        context_lines.append("No critical issues detected.")

    ai_summary = await llm.chat(
        "\n".join(context_lines),
        system=(
            "You are TimetableAI, a scheduling advisor. Analyze this pre-generation report "
            "and give a brief 3-4 sentence summary. If there are issues, prioritize them. "
            "If everything looks good, confirm readiness. Be concise and actionable."
        ),
    )

    return {
        "ok": len([i for i in issues if "🔴" in i]) == 0,
        "issues": issues,
        "suggestions": suggestions,
        "ai_summary": ai_summary,
        "stats": {
            "faculty_count": len(faculty_list),
            "subject_count": len(subject_list),
            "classroom_count": len(classrooms),
            "lab_count": len(labs),
            "batch_count": num_batches,
            "theory_hours": total_theory_hours,
            "lab_hours": total_lab_hours,
            "assigned_subjects": len(assigned_subject_ids),
            "unassigned_subjects": len(unassigned),
        },
    }


async def post_generation_analysis(
    timetable_id: str,
    db: AsyncSession,
) -> dict:
    """
    Run AI analysis AFTER timetable generation.
    Evaluates quality, finds patterns, and provides improvement suggestions.

    Returns: {score_analysis: str, patterns: [...], improvements: [...], ai_summary: str}
    """
    tt = await db.get(Timetable, timetable_id)
    if not tt:
        return {"error": "Timetable not found"}

    entries = (await db.execute(
        select(TimetableEntry).where(TimetableEntry.timetable_id == timetable_id)
    )).scalars().all()

    if not entries:
        return {"error": "No entries in timetable — generation may have failed"}

    # Load supplementary data
    faculty_ids = set(e.faculty_id for e in entries)
    subject_ids = set(e.subject_id for e in entries)

    faculty_map = {}
    for fid in faculty_ids:
        f = await db.get(Faculty, fid)
        if f:
            faculty_map[fid] = f

    subject_map = {}
    for sid in subject_ids:
        s = await db.get(Subject, sid)
        if s:
            subject_map[sid] = s

    # ── Analyze patterns ──────────────────────────────────────────────────
    patterns = []
    improvements = []

    # Faculty load distribution
    faculty_hours: dict[str, int] = {}
    for e in entries:
        faculty_hours[e.faculty_id] = faculty_hours.get(e.faculty_id, 0) + 1

    overloaded = []
    underloaded = []
    for fid, hours in faculty_hours.items():
        fac = faculty_map.get(fid)
        if fac:
            pct = round(hours / fac.max_weekly_load * 100) if fac.max_weekly_load else 0
            if pct > 90:
                overloaded.append(f"{fac.name} ({pct}%)")
            elif pct < 40:
                underloaded.append(f"{fac.name} ({pct}%)")

    if overloaded:
        patterns.append(f"Heavy load: {', '.join(overloaded)}")
    if underloaded:
        patterns.append(f"Light load: {', '.join(underloaded)}")

    # Day distribution analysis
    day_counts: dict[str, int] = {}
    for e in entries:
        day_counts[e.day] = day_counts.get(e.day, 0) + 1

    if day_counts:
        max_day = max(day_counts, key=day_counts.get)
        min_day = min(day_counts, key=day_counts.get)
        if day_counts[max_day] > day_counts[min_day] * 1.5:
            patterns.append(
                f"Uneven distribution: {max_day} has {day_counts[max_day]} slots vs "
                f"{min_day} with {day_counts[min_day]}"
            )
            improvements.append("Consider enforcing stricter day-balance constraints.")

    # Morning vs afternoon
    morning_count = sum(1 for e in entries if e.period <= 4)
    afternoon_count = sum(1 for e in entries if e.period > 4)
    total = morning_count + afternoon_count
    if total > 0:
        morning_pct = round(morning_count / total * 100)
        patterns.append(f"Morning: {morning_pct}%, Afternoon: {100 - morning_pct}%")

    # Lab continuity check
    lab_entries = [e for e in entries if e.batch]
    lab_by_day_batch: dict[tuple, list[int]] = {}
    for e in lab_entries:
        key = (e.day, e.batch, e.subject_id)
        lab_by_day_batch.setdefault(key, []).append(e.period)
    for key, periods in lab_by_day_batch.items():
        periods.sort()
        for i in range(len(periods) - 1):
            if periods[i + 1] - periods[i] > 1:
                sub = subject_map.get(key[2])
                patterns.append(f"Non-consecutive lab: {sub.name if sub else key[2]} batch {key[1]} on {key[0]}")
                break

    # ── Build LLM context ──────────────────────────────────────────────────
    context_lines = [
        f"Timetable analysis (Score: {tt.optimization_score or 0}%):",
        f"- Total entries: {len(entries)} ({len([e for e in entries if not e.batch])} theory, {len(lab_entries)} lab)",
        f"- Faculty used: {len(faculty_hours)}",
        f"- Days used: {', '.join(f'{d}: {c}' for d, c in sorted(day_counts.items()))}",
    ]
    if patterns:
        context_lines.append("Patterns found:")
        context_lines.extend(f"  • {p}" for p in patterns)
    if improvements:
        context_lines.append("Suggested improvements:")
        context_lines.extend(f"  • {imp}" for imp in improvements)

    ai_summary = await llm.chat(
        "\n".join(context_lines),
        system=(
            "You are TimetableAI, a scheduling quality analyst. Analyze this generated timetable "
            "and provide a brief quality assessment in 4-5 sentences. Highlight what's good, "
            "what could be improved, and give actionable advice. Be specific and constructive."
        ),
    )

    return {
        "timetable_id": timetable_id,
        "optimization_score": tt.optimization_score,
        "entry_count": len(entries),
        "patterns": patterns,
        "improvements": improvements,
        "ai_summary": ai_summary,
        "distribution": {
            "by_day": day_counts,
            "morning_pct": morning_pct if total > 0 else 50,
            "faculty_load": {
                faculty_map[fid].name: hours
                for fid, hours in faculty_hours.items()
                if fid in faculty_map
            },
        },
    }


async def ai_suggest_assignments(
    semester: int,
    db: AsyncSession,
    dept_id: str,
) -> dict:
    """
    Use AI to suggest optimal faculty-subject assignments.
    Considers expertise, load balancing, and preferences.
    """
    faculty_list = (await db.execute(
        select(Faculty).where(Faculty.dept_id == dept_id)
    )).scalars().all()
    subject_list = (await db.execute(
        select(Subject).where(Subject.dept_id == dept_id, Subject.semester == semester)
    )).scalars().all()
    batch_list = (await db.execute(
        select(Batch).where(Batch.dept_id == dept_id, Batch.semester == semester)
    )).scalars().all()

    num_batches = len(batch_list) or 1

    # Build a rich context for the LLM
    faculty_info = []
    for f in faculty_list:
        exp_str = ", ".join(f.expertise or []) or "none listed"
        pref = f.preferred_time or "any"
        faculty_info.append(
            f"- {f.name} (ID: {f.faculty_id[:8]}): expertise=[{exp_str}], "
            f"max_load={f.max_weekly_load}, preferred_time={pref}"
        )

    subject_info = []
    for s in subject_list:
        lh = s.lecture_hours if s.lecture_hours else s.weekly_periods
        subject_info.append(
            f"- {s.name} (ID: {s.subject_id[:8]}): "
            f"theory={lh}h/week, lab={s.lab_hours}h/week, "
            f"needs_lab={'yes' if s.needs_lab else 'no'}, batch_size={s.batch_size}"
        )

    prompt = (
        f"Department has {len(faculty_list)} faculty and {len(subject_list)} subjects "
        f"for semester {semester} with {num_batches} lab batches.\n\n"
        f"Faculty:\n" + "\n".join(faculty_info) + "\n\n"
        f"Subjects:\n" + "\n".join(subject_info) + "\n\n"
        "Suggest the best faculty-subject assignments considering:\n"
        "1. Expertise match (highest priority)\n"
        "2. Load balancing (distribute hours evenly)\n"
        "3. Time preferences\n"
        "4. Lab subjects may need faculty with practical expertise\n\n"
        "Return a brief analysis with your recommended assignments and reasoning."
    )

    ai_response = await llm.chat(
        prompt,
        system=(
            "You are TimetableAI, an expert scheduling consultant. "
            "Analyze the faculty and subjects and recommend optimal assignments. "
            "Be specific — mention names and subjects. Keep it under 10 sentences."
        ),
        thinking=True,
    )

    return {
        "semester": semester,
        "faculty_count": len(faculty_list),
        "subject_count": len(subject_list),
        "ai_recommendation": ai_response,
    }
