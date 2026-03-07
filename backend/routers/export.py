# routers/export.py
"""
PDF export endpoints using WeasyPrint + Jinja2 HTML templates.
"""
from __future__ import annotations

import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from jinja2 import Environment, FileSystemLoader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from weasyprint import HTML as WeasyHTML
    _HAS_WEASYPRINT = True
except ImportError:
    _HAS_WEASYPRINT = False

from database import AsyncSessionLocal
from dependencies import get_db, get_current_user
from models.user import User
from models.timetable import Timetable, TimetableEntry
from models.timeslot import TimeSlotConfig
from models.subject import Subject
from models.faculty import Faculty
from models.room import Room
from models.college import College
from models.college import Department

router = APIRouter(prefix="/export", tags=["Export"])

# ── Jinja2 setup ──────────────────────────────────────────
_TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
_jinja_env = Environment(
    loader=FileSystemLoader(_TEMPLATE_DIR),
    autoescape=True,
)

ALL_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


def _render_pdf(html_str: str) -> bytes:
    if not _HAS_WEASYPRINT:
        raise HTTPException(
            501,
            "PDF export requires WeasyPrint which is not installed. "
            "Use the Excel export instead, or install WeasyPrint.",
        )
    return WeasyHTML(string=html_str).write_pdf()


# ── Helpers ───────────────────────────────────────────────
def _faculty_abbr(name: str) -> str:
    parts = name.split()
    filtered = [p for p in parts if not p.endswith(".")]
    if not filtered:
        return "".join(p[0] for p in parts).upper()
    if len(filtered) <= 1:
        return name[:4].upper()
    return "".join(p[0] for p in filtered).upper()


_ABBR_SKIP = {"AND", "OF", "THE", "FOR", "IN", "TO", "A", "AN", "&"}


def _subject_abbr(name: str) -> str:
    """Generate a short abbreviation from a subject name."""
    words = name.upper().split()
    if len(words) == 1:
        return words[0]
    for w in words:
        if "/" in w:
            return w
    significant = [w for w in words if w not in _ABBR_SKIP]
    if not significant:
        significant = words
    return "".join(w[0] for w in significant)


async def _load_timetable_data(timetable_id: str, user: User, db: AsyncSession):
    """Load timetable, entries with resolved names, slots."""
    result = await db.execute(
        select(Timetable).where(Timetable.timetable_id == timetable_id)
    )
    tt = result.scalar_one_or_none()
    if not tt:
        raise HTTPException(404, "Timetable not found")

    # Load entries
    entry_result = await db.execute(
        select(TimetableEntry).where(TimetableEntry.timetable_id == timetable_id)
    )
    entries_raw = entry_result.scalars().all()

    # Resolve names for each entry
    entries = []
    for e in entries_raw:
        subject = await db.get(Subject, e.subject_id)
        faculty = await db.get(Faculty, e.faculty_id)
        room = await db.get(Room, e.room_id)
        entries.append({
            "day": e.day,
            "period": e.period,
            "subject_name": subject.name if subject else "Unknown",
            "subject_code": subject.subject_code if subject else "",
            "subject_abbr": _subject_abbr(subject.name if subject else "Unknown"),
            "faculty_name": faculty.name if faculty else "Unknown",
            "faculty_abbr": _faculty_abbr(faculty.name) if faculty else "??",
            "room_name": room.name if room else "Unknown",
            "entry_type": e.entry_type.value if e.entry_type else "regular",
            "batch": e.batch,
            "subject_id": e.subject_id,
        })

    # Load slots
    dept = await db.get(Department, tt.dept_id) if tt.dept_id else None
    college_id = dept.college_id if dept else user.college_id
    slot_result = await db.execute(
        select(TimeSlotConfig)
        .where(TimeSlotConfig.college_id == college_id)
        .order_by(TimeSlotConfig.slot_order)
    )
    slots = slot_result.scalars().all()

    # College & dept names
    college = await db.get(College, college_id) if college_id else None
    college_name = college.name if college else "University"
    dept_name = dept.name if dept else "Department"

    return tt, entries, slots, college_name, dept_name


def _get_days(entries):
    return list(ALL_DAYS)


def _get_batch_names(entries):
    names = sorted({e["batch"] for e in entries if e["batch"]})
    return names


def _get_lab_periods(entries):
    return {e["period"] for e in entries if e["batch"]}


def _build_lookup(entries):
    lookup: dict[str, list] = {}
    for e in entries:
        key = f"{e['day']}|{e['period']}"
        lookup.setdefault(key, []).append(e)
    return lookup


def _detect_blocks(slots, days, lookup, *, multi=False):
    """Detect consecutive identical blocks for merging.
    multi=True: lookup values are lists (department PDF).
    multi=False: lookup values are single entries (faculty/room PDF).
    """
    result = {}
    non_break = [s for s in slots if s.slot_type.value != "break"]
    non_break.sort(key=lambda s: s.slot_order)

    for day in days:
        i = 0
        while i < len(non_break):
            curr = non_break[i]
            key = f"{day}|{curr.slot_order}"

            if multi:
                curr_entries = [e for e in lookup.get(key, []) if e["batch"]]
                if not curr_entries:
                    i += 1
                    continue
                curr_sig = ",".join(
                    sorted(
                        f"{e['subject_name']}|{e['batch']}|{e['faculty_name']}|{e['room_name']}"
                        for e in curr_entries
                    )
                )
            else:
                curr_entry = lookup.get(key)
                if not curr_entry:
                    i += 1
                    continue
                curr_sig = f"{curr_entry['subject_name']}|{curr_entry['faculty_name']}|{curr_entry['room_name']}|{curr_entry.get('batch', '')}"

            span = 1
            while i + span < len(non_break):
                nxt = non_break[i + span]
                nkey = f"{day}|{nxt.slot_order}"
                if multi:
                    nxt_entries = [e for e in lookup.get(nkey, []) if e["batch"]]
                    nxt_sig = ",".join(
                        sorted(
                            f"{e['subject_name']}|{e['batch']}|{e['faculty_name']}|{e['room_name']}"
                            for e in nxt_entries
                        )
                    )
                else:
                    nxt_entry = lookup.get(nkey)
                    if not nxt_entry:
                        break
                    nxt_sig = f"{nxt_entry['subject_name']}|{nxt_entry['faculty_name']}|{nxt_entry['room_name']}|{nxt_entry.get('batch', '')}"

                if nxt_sig == curr_sig:
                    span += 1
                else:
                    break

            if span > 1:
                end_slot = non_break[i + span - 1]
                result[key] = {"type": "start", "span": span, "end_time": end_slot.end_time}
                for j in range(1, span):
                    result[f"{day}|{non_break[i + j].slot_order}"] = {"type": "skip"}
                i += span
            else:
                i += 1

    return result


# ── Department PDF ────────────────────────────────────────
@router.get("/department/{timetable_id}")
async def export_department_pdf(
    timetable_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tt, entries, slots, college_name, dept_name = await _load_timetable_data(
        timetable_id, current_user, db
    )

    days = _get_days(entries)
    batch_names = _get_batch_names(entries)
    lab_periods = _get_lab_periods(entries)
    lookup = _build_lookup(entries)
    lab_blocks = _detect_blocks(slots, days, lookup, multi=True)

    # Subject details
    subject_ids = {e["subject_id"] for e in entries}
    subject_details = []
    seen_subjects = set()
    for e in entries:
        if e["subject_name"] in seen_subjects:
            continue
        seen_subjects.add(e["subject_name"])
        subj = await db.get(Subject, e["subject_id"])
        if subj:
            subject_details.append({
                "code": subj.subject_code,
                "name": subj.name,
                "l": subj.lecture_hours or subj.weekly_periods,
                "p": subj.lab_hours or 0,
                "t": 0,
                "c": subj.credits,
            })
        else:
            is_lab = e["entry_type"] == "lab" or bool(e["batch"])
            subject_details.append({
                "code": "—",
                "name": e["subject_name"],
                "l": 0 if is_lab else 3,
                "p": 2 if is_lab else 0,
                "t": 0,
                "c": "—",
            })

    # Faculty legend
    faculty_names = sorted({e["faculty_name"] for e in entries})
    faculty_legend = [{"abbr": _faculty_abbr(fn), "name": fn} for fn in faculty_names]

    total_day_cols = len(days) * (len(batch_names) if batch_names else 1)

    date_str = tt.created_at.strftime("%d/%m/%Y") if tt.created_at else datetime.now().strftime("%d/%m/%Y")

    semester_label = "EVEN" if tt.semester % 2 == 0 else "ODD"

    template = _jinja_env.get_template("department.html")
    html_str = template.render(
        college_name=college_name,
        dept_name=dept_name,
        semester=tt.semester,
        semester_label=semester_label,
        academic_year=tt.academic_year,
        score=f"{tt.optimization_score}/100" if tt.optimization_score else "N/A",
        status=tt.status.value.upper(),
        date_str=date_str,
        days=days,
        batch_names=batch_names,
        slots=slots,
        lookup=lookup,
        lab_blocks=lab_blocks,
        is_lab_period=lambda p: p in lab_periods,
        total_day_cols=total_day_cols,
        subject_details=subject_details,
        faculty_legend=faculty_legend,
    )

    pdf_bytes = _render_pdf(html_str)

    filename = f"Timetable_Sem{tt.semester}_{tt.academic_year}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Faculty PDF ───────────────────────────────────────────

def _build_faculty_schedule(faculty_name: str, all_entries, slots, days):
    """Build rows + teaching_summary for a single faculty member."""
    entries = [e for e in all_entries if e["faculty_name"] == faculty_name]

    lookup = {}
    for e in entries:
        lookup[f"{e['day']}|{e['period']}"] = e

    blocks = _detect_blocks(slots, days, lookup, multi=False)

    rows = []
    for slot in slots:
        if slot.slot_type.value != "break":
            all_skip = all(
                blocks.get(f"{d}|{slot.slot_order}", {}).get("type") == "skip"
                or (
                    blocks.get(f"{d}|{slot.slot_order}", {}).get("type") != "start"
                    and f"{d}|{slot.slot_order}" not in lookup
                )
                for d in days
            )
            if all_skip:
                continue

        time_label = f"{slot.start_time} – {slot.end_time}"
        if slot.slot_type.value != "break":
            for day in days:
                info = blocks.get(f"{day}|{slot.slot_order}")
                if info and info["type"] == "start":
                    time_label = f"{slot.start_time} – {info['end_time']}"
                    break

        cells = []
        for day in days:
            if slot.slot_type.value == "break":
                cells.append({"type": "break", "label": slot.label})
                continue

            key = f"{day}|{slot.slot_order}"
            block_info = blocks.get(key)
            if block_info and block_info["type"] == "skip":
                cells.append({"type": "skip"})
                continue

            entry = lookup.get(key)
            if entry:
                hours = block_info["span"] if block_info and block_info["type"] == "start" else None
                cells.append({
                    "type": "entry",
                    "subject": entry["subject_name"],
                    "room": entry["room_name"],
                    "batch": entry["batch"],
                    "hours": hours,
                    "rowspan": block_info["span"] if block_info and block_info["type"] == "start" else 1,
                })
            else:
                cells.append({"type": "empty"})

        rows.append({"time": time_label, "cells": cells})

    subject_map: dict[str, dict] = {}
    for e in entries:
        if e["subject_name"] not in subject_map:
            subject_map[e["subject_name"]] = {"rooms": set(), "periods": 0, "batches": set()}
        s = subject_map[e["subject_name"]]
        s["rooms"].add(e["room_name"])
        s["periods"] += 1
        if e["batch"]:
            s["batches"].add(e["batch"])

    teaching_summary = [
        {
            "name": name,
            "rooms": ", ".join(sorted(info["rooms"])),
            "periods": info["periods"],
            "batches": ", ".join(sorted(info["batches"])) if info["batches"] else "—",
        }
        for name, info in sorted(subject_map.items())
    ]

    return entries, rows, teaching_summary, subject_map


@router.get("/faculty/{timetable_id}")
async def export_faculty_pdf(
    timetable_id: str,
    faculty_name: str | None = Query(None, description="Faculty member's full name (omit for all faculty)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tt, all_entries, slots, _, _ = await _load_timetable_data(
        timetable_id, current_user, db
    )
    days = _get_days(all_entries)

    if faculty_name:
        # ── Single faculty ──
        entries, rows, teaching_summary, subject_map = _build_faculty_schedule(
            faculty_name, all_entries, slots, days
        )
        if not entries:
            raise HTTPException(404, f"No entries found for faculty '{faculty_name}'")

        template = _jinja_env.get_template("faculty.html")
        html_str = template.render(
            faculty_name=faculty_name,
            semester=tt.semester,
            academic_year=tt.academic_year,
            total_periods=len(entries),
            subject_count=len(subject_map),
            days=days,
            rows=rows,
            teaching_summary=teaching_summary,
        )
        safe_name = faculty_name.replace(" ", "_")
        filename = f"Schedule_{safe_name}.pdf"
    else:
        # ── All faculty ──
        faculty_names = sorted({e["faculty_name"] for e in all_entries})
        faculty_list = []
        for fn in faculty_names:
            entries, rows, teaching_summary, subject_map = _build_faculty_schedule(
                fn, all_entries, slots, days
            )
            faculty_list.append({
                "name": fn,
                "rows": rows,
                "total_periods": len(entries),
                "subject_count": len(subject_map),
                "teaching_summary": teaching_summary,
            })

        template = _jinja_env.get_template("faculty_all.html")
        html_str = template.render(
            semester=tt.semester,
            academic_year=tt.academic_year,
            faculty_count=len(faculty_names),
            total_entries=len(all_entries),
            days=days,
            faculty_list=faculty_list,
        )
        filename = f"Faculty_Schedules_Sem{tt.semester}_{tt.academic_year}.pdf"

    pdf_bytes = _render_pdf(html_str)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Room PDF ─────────────────────────────────────────────
@router.get("/room/{timetable_id}")
async def export_room_pdf(
    timetable_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tt, all_entries, slots, _, _ = await _load_timetable_data(
        timetable_id, current_user, db
    )

    days = _get_days(all_entries)
    room_names = sorted({e["room_name"] for e in all_entries})
    non_break_count = len([s for s in slots if s.slot_type.value != "break"])
    total_possible = non_break_count * len(days)

    rooms_data = []
    for room_name in room_names:
        room_entries = [e for e in all_entries if e["room_name"] == room_name]

        lookup = {}
        for e in room_entries:
            lookup[f"{e['day']}|{e['period']}"] = e

        blocks = _detect_blocks(slots, days, lookup, multi=False)

        rows = []
        for slot in slots:
            if slot.slot_type.value != "break":
                all_skip = all(
                    blocks.get(f"{d}|{slot.slot_order}", {}).get("type") == "skip"
                    or (
                        blocks.get(f"{d}|{slot.slot_order}", {}).get("type") != "start"
                        and f"{d}|{slot.slot_order}" not in lookup
                    )
                    for d in days
                )
                if all_skip:
                    continue

            time_label = f"{slot.start_time} – {slot.end_time}"
            if slot.slot_type.value != "break":
                for day in days:
                    info = blocks.get(f"{day}|{slot.slot_order}")
                    if info and info["type"] == "start":
                        time_label = f"{slot.start_time} – {info['end_time']}"
                        break

            cells = []
            for day in days:
                if slot.slot_type.value == "break":
                    cells.append({"type": "break", "label": slot.label})
                    continue

                key = f"{day}|{slot.slot_order}"
                block_info = blocks.get(key)
                if block_info and block_info["type"] == "skip":
                    cells.append({"type": "skip"})
                    continue

                entry = lookup.get(key)
                if entry:
                    hours = block_info["span"] if block_info and block_info["type"] == "start" else None
                    cells.append({
                        "type": "entry",
                        "subject": entry["subject_name"],
                        "faculty": entry["faculty_name"],
                        "batch": entry["batch"],
                        "hours": hours,
                        "rowspan": block_info["span"] if block_info and block_info["type"] == "start" else 1,
                    })
                else:
                    cells.append({"type": "empty"})

            rows.append({"time": time_label, "cells": cells})

        used_slots = len(room_entries)
        utilization = round((used_slots / total_possible) * 100) if total_possible > 0 else 0

        rooms_data.append({
            "name": room_name,
            "rows": rows,
            "used_slots": used_slots,
            "utilization": utilization,
        })

    template = _jinja_env.get_template("room.html")
    html_str = template.render(
        semester=tt.semester,
        academic_year=tt.academic_year,
        room_count=len(room_names),
        total_entries=len(all_entries),
        days=days,
        rooms=rooms_data,
    )

    pdf_bytes = _render_pdf(html_str)

    filename = f"Room_Allocation_Sem{tt.semester}_{tt.academic_year}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
