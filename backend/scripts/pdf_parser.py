"""
PDF Parser for ScheduleX Seed Data.

Extracts structured data (departments, faculty, subjects, rooms, batches,
time-slots) from PDF files whose pages contain tables.

Expected PDF files and their required column headers:
───────────────────────────────────────────────────────
  college.pdf      → Name, Affiliation, City
  departments.pdf  → Code, Name
  faculty.pdf      → Department, Name, EmployeeID, Email, Phone, Expertise,
                      MaxLoad, PreferredTime, Role (HOD / Faculty)
  subjects.pdf     → Department, Name, Code, Semester, Credits,
                      LectureHours, LabHours, BatchSize
  rooms.pdf        → Name, Capacity, Type (CLASSROOM/LAB/SEMINAR),
                      Projector (Y/N), Computers (Y/N), AC (Y/N)
  venues.pdf       → Name, Capacity, Type (HALL/LAB/OUTDOOR)
  timeslots.pdf    → Order, Label, StartTime, EndTime, Type (LECTURE/LAB/BREAK)
  batches.pdf      → Department, Semester, Name, Size

Column matching is case-insensitive and strips whitespace, so
"employee id", "Employee_ID" and "EmployeeID" all map to the same field.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pdfplumber


# ────────────────────────────────────────────────────────
# helpers
# ────────────────────────────────────────────────────────

def _normalise_header(raw: str) -> str:
    """Lower-case, strip, collapse whitespace/underscores."""
    return re.sub(r"[\s_]+", "", raw.strip().lower())


_HEADER_ALIASES: dict[str, list[str]] = {
    # canonical  →  acceptable raw variants (all normalised)
    "name":           ["name", "subjectname", "facultyname", "roomname", "collegename"],
    "code":           ["code", "deptcode", "departmentcode", "subjectcode"],
    "department":     ["department", "dept", "deptcode", "branch"],
    "affiliation":    ["affiliation", "affiliatedto", "university"],
    "city":           ["city", "location"],
    "employeeid":     ["employeeid", "empid", "employeeno", "facultyid"],
    "email":          ["email", "emailid", "emailaddress"],
    "phone":          ["phone", "phoneno", "mobile", "contact"],
    "expertise":      ["expertise", "specialization", "skills", "subjects"],
    "maxload":        ["maxload", "maxweeklyload", "weeklyload", "load"],
    "preferredtime":  ["preferredtime", "timepref", "preference", "preferred"],
    "role":           ["role", "designation", "position"],
    "semester":       ["semester", "sem"],
    "credits":        ["credits", "credit"],
    "lecturehours":   ["lecturehours", "lec", "lecture", "theoryhours", "theory"],
    "labhours":       ["labhours", "lab", "practicalhours", "practical"],
    "batchsize":      ["batchsize", "classsize", "strength", "students"],
    "capacity":       ["capacity", "seats", "seating"],
    "type":           ["type", "roomtype", "venuetype", "slottype"],
    "projector":      ["projector", "hasprojector"],
    "computers":      ["computers", "hascomputers", "pcs"],
    "ac":             ["ac", "hasac", "airconditioned"],
    "order":          ["order", "slotorder", "sno", "srno", "serialno"],
    "label":          ["label", "slotlabel", "period"],
    "starttime":      ["starttime", "start", "from"],
    "endtime":        ["endtime", "end", "to"],
    "size":           ["size", "batchsize", "students", "count"],
}

_REVERSE_ALIAS: dict[str, str] = {}
for canonical, aliases in _HEADER_ALIASES.items():
    for alias in aliases:
        _REVERSE_ALIAS[alias] = canonical


def _map_header(raw: str) -> str:
    """Map a raw column header to its canonical field name."""
    norm = _normalise_header(raw)
    return _REVERSE_ALIAS.get(norm, norm)


def _yn_to_bool(val: Any) -> bool:
    if isinstance(val, bool):
        return val
    if val is None:
        return False
    return str(val).strip().lower() in ("y", "yes", "true", "1")


def _int_or(val: Any, default: int = 0) -> int:
    try:
        return int(float(str(val).strip()))
    except (ValueError, TypeError):
        return default


def _clean_str(val: Any, default: str = "") -> str:
    if val is None:
        return default
    return str(val).strip()


def _parse_list(val: Any) -> list[str]:
    """Parse a comma / semicolon separated string into a list."""
    if val is None:
        return []
    if isinstance(val, list):
        return val
    raw = str(val).strip()
    return [item.strip() for item in re.split(r"[;,|]+", raw) if item.strip()]


# ────────────────────────────────────────────────────────
# core extractor
# ────────────────────────────────────────────────────────

def _extract_tables_from_pdf(pdf_path: str | Path) -> list[list[dict[str, str]]]:
    """
    Open a PDF and return a list of tables.  Each table is a list of dicts
    keyed by canonical column name.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    tables: list[list[dict[str, str]]] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_tables = page.extract_tables()
            for raw_table in page_tables:
                if not raw_table or len(raw_table) < 2:
                    continue
                # First row = headers
                headers = [_map_header(h) for h in raw_table[0] if h]
                rows: list[dict[str, str]] = []
                for raw_row in raw_table[1:]:
                    if not raw_row or all(c is None or str(c).strip() == "" for c in raw_row):
                        continue
                    row = {}
                    for idx, hdr in enumerate(headers):
                        if idx < len(raw_row):
                            row[hdr] = _clean_str(raw_row[idx])
                    rows.append(row)
                if rows:
                    tables.append(rows)
    return tables


def _flat_rows(pdf_path: str | Path) -> list[dict[str, str]]:
    """Flatten all tables from a PDF into one list of row-dicts."""
    result: list[dict[str, str]] = []
    for table in _extract_tables_from_pdf(pdf_path):
        result.extend(table)
    return result


# ────────────────────────────────────────────────────────
# public parsing functions
# ────────────────────────────────────────────────────────

def parse_college(pdf_path: str | Path) -> dict[str, str]:
    """Return {'name': ..., 'affiliation': ..., 'city': ...}."""
    rows = _flat_rows(pdf_path)
    if not rows:
        raise ValueError(f"No college data found in {pdf_path}")
    r = rows[0]
    return {
        "name": r.get("name", ""),
        "affiliation": r.get("affiliation", ""),
        "city": r.get("city", ""),
    }


def parse_departments(pdf_path: str | Path) -> list[dict[str, str]]:
    """Return [{'code': 'CP', 'name': 'Computer Engineering'}, ...]."""
    rows = _flat_rows(pdf_path)
    return [{"code": r.get("code", ""), "name": r.get("name", "")} for r in rows]


def parse_faculty(pdf_path: str | Path) -> list[dict[str, Any]]:
    """
    Return list of faculty dicts:
      department, name, employee_id, email, phone, expertise (list),
      max_load (int), preferred_time, role ('hod' / 'faculty')
    """
    rows = _flat_rows(pdf_path)
    result = []
    for r in rows:
        result.append({
            "department": _clean_str(r.get("department")),
            "name": _clean_str(r.get("name")),
            "employee_id": _clean_str(r.get("employeeid")),
            "email": _clean_str(r.get("email")),
            "phone": _clean_str(r.get("phone")),
            "expertise": _parse_list(r.get("expertise")),
            "max_load": _int_or(r.get("maxload"), 24),
            "preferred_time": _clean_str(r.get("preferredtime"), "any"),
            "role": _clean_str(r.get("role"), "faculty").lower(),
        })
    return result


def parse_subjects(pdf_path: str | Path) -> list[dict[str, Any]]:
    """
    Return list of subject dicts:
      department, name, code, semester, credits,
      lecture_hours, lab_hours, batch_size
    """
    rows = _flat_rows(pdf_path)
    result = []
    for r in rows:
        result.append({
            "department": _clean_str(r.get("department")),
            "name": _clean_str(r.get("name")),
            "code": _clean_str(r.get("code")),
            "semester": _int_or(r.get("semester")),
            "credits": _int_or(r.get("credits")),
            "lecture_hours": _int_or(r.get("lecturehours")),
            "lab_hours": _int_or(r.get("labhours")),
            "batch_size": _int_or(r.get("batchsize"), 60),
        })
    return result


def parse_rooms(pdf_path: str | Path) -> list[dict[str, Any]]:
    """
    Return list of room dicts:
      name, capacity, type, projector (bool), computers (bool), ac (bool)
    """
    rows = _flat_rows(pdf_path)
    result = []
    for r in rows:
        result.append({
            "name": _clean_str(r.get("name")),
            "capacity": _int_or(r.get("capacity"), 60),
            "type": _clean_str(r.get("type"), "CLASSROOM").upper(),
            "projector": _yn_to_bool(r.get("projector")),
            "computers": _yn_to_bool(r.get("computers")),
            "ac": _yn_to_bool(r.get("ac")),
        })
    return result


def parse_venues(pdf_path: str | Path) -> list[dict[str, Any]]:
    """Return [{'name': ..., 'capacity': int, 'type': 'HALL'/'LAB'/'OUTDOOR'}]."""
    rows = _flat_rows(pdf_path)
    result = []
    for r in rows:
        result.append({
            "name": _clean_str(r.get("name")),
            "capacity": _int_or(r.get("capacity"), 100),
            "type": _clean_str(r.get("type"), "HALL").upper(),
        })
    return result


def parse_timeslots(pdf_path: str | Path) -> list[dict[str, Any]]:
    """
    Return list of timeslot dicts:
      order, label, start_time, end_time, type (LECTURE/LAB/BREAK)
    """
    rows = _flat_rows(pdf_path)
    result = []
    for r in rows:
        result.append({
            "order": _int_or(r.get("order")),
            "label": _clean_str(r.get("label")),
            "start_time": _clean_str(r.get("starttime")),
            "end_time": _clean_str(r.get("endtime")),
            "type": _clean_str(r.get("type"), "LECTURE").upper(),
        })
    return result


def parse_batches(pdf_path: str | Path) -> list[dict[str, Any]]:
    """
    Return list of batch dicts:
      department, semester, name, size
    """
    rows = _flat_rows(pdf_path)
    result = []
    for r in rows:
        result.append({
            "department": _clean_str(r.get("department")),
            "semester": _int_or(r.get("semester")),
            "name": _clean_str(r.get("name")),
            "size": _int_or(r.get("size"), 20),
        })
    return result
