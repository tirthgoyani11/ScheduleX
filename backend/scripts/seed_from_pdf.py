# scripts/seed_from_pdf.py
"""
Seed the database from multiple PDF files.

Each PDF contains tables for a specific entity type.
Drop your PDFs into a folder (default: ./seed_pdfs/) and run:

    python scripts/seed_from_pdf.py                       # uses ./seed_pdfs/
    python scripts/seed_from_pdf.py /path/to/pdf_folder   # custom folder

Expected PDF files (all optional — only present ones are processed):
───────────────────────────────────────────────────────────────────
  college.pdf      — College info (1 row: Name, Affiliation, City)
  departments.pdf  — Department list (Code, Name)
  faculty.pdf      — All faculty incl. HODs (Department, Name, EmployeeID,
                     Email, Phone, Expertise, MaxLoad, PreferredTime, Role)
  subjects.pdf     — Subjects (Department, Name, Code, Semester, Credits,
                     LectureHours, LabHours, BatchSize)
  rooms.pdf        — Rooms & labs (Name, Capacity, Type, Projector, Computers, AC)
  venues.pdf       — Exam venues (Name, Capacity, Type)
  timeslots.pdf    — Period config (Order, Label, StartTime, EndTime, Type)
  batches.pdf      — Batches (Department, Semester, Name, Size)

Column names are flexible — see pdf_parser.py for accepted aliases.
"""
import asyncio
import sys
import os
import uuid
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, Base, AsyncSessionLocal
from models.college import College, Department
from models.user import User, UserRole
from models.faculty import Faculty
from models.subject import Subject
from models.room import Room, RoomType, Venue, VenueType
from models.timeslot import TimeSlotConfig, SlotType
from models.batch import Batch
from utils.security import hash_password

from pdf_parser import (
    parse_college,
    parse_departments,
    parse_faculty,
    parse_subjects,
    parse_rooms,
    parse_venues,
    parse_timeslots,
    parse_batches,
)


def _id():
    return str(uuid.uuid4())


ROOM_TYPE_MAP = {
    "CLASSROOM": RoomType.CLASSROOM,
    "LAB": RoomType.LAB,
    "SEMINAR": RoomType.SEMINAR,
}

VENUE_TYPE_MAP = {
    "HALL": VenueType.HALL,
    "LAB": VenueType.LAB,
    "OUTDOOR": VenueType.OUTDOOR,
}

SLOT_TYPE_MAP = {
    "LECTURE": SlotType.LECTURE,
    "LAB": SlotType.LAB,
    "BREAK": SlotType.BREAK,
}


def _find_pdf(folder: Path, name: str) -> Path | None:
    """Find a PDF file by name (case-insensitive) in the folder."""
    for f in folder.iterdir():
        if f.suffix.lower() == ".pdf" and f.stem.lower() == name.lower():
            return f
    return None


async def seed_from_pdfs(pdf_folder: str | Path):
    pdf_folder = Path(pdf_folder)
    if not pdf_folder.is_dir():
        print(f"ERROR: PDF folder not found: {pdf_folder}")
        print(f"Create the folder and add your PDF files, then re-run.")
        sys.exit(1)

    pdfs_found = list(pdf_folder.glob("*.pdf"))
    if not pdfs_found:
        print(f"ERROR: No PDF files found in {pdf_folder}")
        print(f"Add PDF files (college.pdf, departments.pdf, etc.) and re-run.")
        sys.exit(1)

    print(f"PDF folder: {pdf_folder.resolve()}")
    print(f"PDFs found: {', '.join(p.name for p in pdfs_found)}")
    print()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        from sqlalchemy import select

        existing = await db.execute(select(College).limit(1))
        if existing.scalar_one_or_none():
            print("Database already seeded. Skipping.")
            print("Delete timetable_dev.db and re-run to reseed.")
            return

        # ══════════════════════════════════════════
        # 1. COLLEGE
        # ══════════════════════════════════════════
        college_pdf = _find_pdf(pdf_folder, "college")
        if college_pdf:
            college_data = parse_college(college_pdf)
            print(f"[✓] College: {college_data['name']}")
        else:
            college_data = {
                "name": "My University",
                "affiliation": "University",
                "city": "City",
            }
            print("[!] college.pdf not found — using defaults")

        college_id = _id()
        db.add(College(
            college_id=college_id,
            name=college_data["name"],
            affiliation=college_data["affiliation"],
            city=college_data["city"],
        ))

        # ══════════════════════════════════════════
        # 2. DEPARTMENTS
        # ══════════════════════════════════════════
        dept_pdf = _find_pdf(pdf_folder, "departments")
        if dept_pdf:
            dept_rows = parse_departments(dept_pdf)
            print(f"[✓] Departments: {len(dept_rows)} loaded")
        else:
            dept_rows = []
            print("[!] departments.pdf not found — no departments created")

        departments: dict[str, str] = {}  # code → dept_id
        dept_names: dict[str, str] = {}   # code → full name
        for d in dept_rows:
            dept_id = _id()
            code = d["code"].strip().upper()
            name = d["name"].strip()
            departments[code] = dept_id
            dept_names[code] = name
            db.add(Department(
                dept_id=dept_id,
                college_id=college_id,
                name=name,
                code=code,
            ))

        # ══════════════════════════════════════════
        # 3. SUPER ADMIN (always created)
        # ══════════════════════════════════════════
        admin_email = f"admin@{college_data['name'].lower().replace(' ', '')}.edu.in"
        db.add(User(
            user_id=_id(),
            email=admin_email,
            phone="+910000000000",
            hashed_password=hash_password("admin123"),
            full_name="Super Admin",
            role=UserRole.SUPER_ADMIN,
            college_id=college_id,
            dept_id=None,
        ))
        print(f"[✓] Super Admin: {admin_email} / admin123")

        # ══════════════════════════════════════════
        # 4. FACULTY (incl. HODs)
        # ══════════════════════════════════════════
        faculty_pdf = _find_pdf(pdf_folder, "faculty")
        total_faculty = 0
        total_hods = 0
        if faculty_pdf:
            faculty_rows = parse_faculty(faculty_pdf)
            print(f"[✓] Faculty: {len(faculty_rows)} records loaded")
            for f in faculty_rows:
                dept_code = f["department"].strip().upper()
                if dept_code not in departments:
                    print(f"  [WARN] Skipping faculty {f['name']}: "
                          f"department '{dept_code}' not found")
                    continue

                dept_id = departments[dept_code]
                uid, fid = _id(), _id()
                is_hod = f["role"] in ("hod", "dept_admin", "head")

                db.add(User(
                    user_id=uid,
                    email=f["email"],
                    phone=f["phone"],
                    hashed_password=hash_password("hod123" if is_hod else "faculty123"),
                    full_name=f["name"],
                    role=UserRole.DEPT_ADMIN if is_hod else UserRole.FACULTY,
                    college_id=college_id,
                    dept_id=dept_id,
                ))
                db.add(Faculty(
                    faculty_id=fid,
                    dept_id=dept_id,
                    user_id=uid,
                    name=f["name"],
                    employee_id=f["employee_id"],
                    expertise=f["expertise"],
                    max_weekly_load=f["max_load"],
                    preferred_time=f["preferred_time"],
                ))
                if is_hod:
                    total_hods += 1
                else:
                    total_faculty += 1
            print(f"    → {total_hods} HODs, {total_faculty} regular faculty")
        else:
            print("[!] faculty.pdf not found — no faculty created")

        # ══════════════════════════════════════════
        # 5. SUBJECTS
        # ══════════════════════════════════════════
        subjects_pdf = _find_pdf(pdf_folder, "subjects")
        total_subjects = 0
        if subjects_pdf:
            subject_rows = parse_subjects(subjects_pdf)
            print(f"[✓] Subjects: {len(subject_rows)} records loaded")
            for s in subject_rows:
                dept_code = s["department"].strip().upper()
                if dept_code not in departments:
                    # Check if it's a "common" / "all" subject
                    if dept_code.lower() in ("common", "all", ""):
                        # Add to every department
                        for dc, did in departments.items():
                            lh = s["lecture_hours"]
                            lab_h = s["lab_hours"]
                            db.add(Subject(
                                subject_id=_id(), dept_id=did, name=s["name"],
                                subject_code=s["code"], semester=s["semester"],
                                credits=s["credits"],
                                weekly_periods=lh + lab_h,
                                lecture_hours=lh, lab_hours=lab_h,
                                needs_lab=lab_h > 0, batch_size=s["batch_size"],
                            ))
                            total_subjects += 1
                    else:
                        print(f"  [WARN] Skipping subject {s['name']}: "
                              f"department '{dept_code}' not found")
                    continue

                dept_id = departments[dept_code]
                lh = s["lecture_hours"]
                lab_h = s["lab_hours"]
                db.add(Subject(
                    subject_id=_id(), dept_id=dept_id, name=s["name"],
                    subject_code=s["code"], semester=s["semester"],
                    credits=s["credits"],
                    weekly_periods=lh + lab_h,
                    lecture_hours=lh, lab_hours=lab_h,
                    needs_lab=lab_h > 0, batch_size=s["batch_size"],
                ))
                total_subjects += 1
            print(f"    → {total_subjects} subjects inserted")
        else:
            print("[!] subjects.pdf not found — no subjects created")

        # ══════════════════════════════════════════
        # 6. ROOMS & LABS
        # ══════════════════════════════════════════
        rooms_pdf = _find_pdf(pdf_folder, "rooms")
        total_rooms = 0
        if rooms_pdf:
            room_rows = parse_rooms(rooms_pdf)
            print(f"[✓] Rooms: {len(room_rows)} records loaded")
            for r in room_rows:
                rtype = ROOM_TYPE_MAP.get(r["type"], RoomType.CLASSROOM)
                db.add(Room(
                    room_id=_id(), college_id=college_id,
                    name=r["name"], capacity=r["capacity"],
                    room_type=rtype,
                    has_projector=r["projector"],
                    has_computers=r["computers"],
                    has_ac=r["ac"],
                ))
                total_rooms += 1
            print(f"    → {total_rooms} rooms inserted")
        else:
            print("[!] rooms.pdf not found — no rooms created")

        # ══════════════════════════════════════════
        # 7. EXAM VENUES
        # ══════════════════════════════════════════
        venues_pdf = _find_pdf(pdf_folder, "venues")
        total_venues = 0
        if venues_pdf:
            venue_rows = parse_venues(venues_pdf)
            print(f"[✓] Venues: {len(venue_rows)} records loaded")
            for v in venue_rows:
                vtype = VENUE_TYPE_MAP.get(v["type"], VenueType.HALL)
                db.add(Venue(
                    venue_id=_id(), college_id=college_id,
                    name=v["name"], capacity=v["capacity"],
                    venue_type=vtype,
                ))
                total_venues += 1
            print(f"    → {total_venues} venues inserted")
        else:
            print("[!] venues.pdf not found — no venues created")

        # ══════════════════════════════════════════
        # 8. TIME SLOTS
        # ══════════════════════════════════════════
        timeslots_pdf = _find_pdf(pdf_folder, "timeslots")
        total_slots = 0
        if timeslots_pdf:
            slot_rows = parse_timeslots(timeslots_pdf)
            print(f"[✓] Time Slots: {len(slot_rows)} records loaded")
            for s in slot_rows:
                stype = SLOT_TYPE_MAP.get(s["type"], SlotType.LECTURE)
                db.add(TimeSlotConfig(
                    slot_id=_id(), college_id=college_id,
                    slot_order=s["order"], label=s["label"],
                    start_time=s["start_time"], end_time=s["end_time"],
                    slot_type=stype,
                ))
                total_slots += 1
            print(f"    → {total_slots} time slots inserted")
        else:
            print("[!] timeslots.pdf not found — no time slots created")

        # ══════════════════════════════════════════
        # 9. BATCHES
        # ══════════════════════════════════════════
        batches_pdf = _find_pdf(pdf_folder, "batches")
        total_batches = 0
        if batches_pdf:
            batch_rows = parse_batches(batches_pdf)
            print(f"[✓] Batches: {len(batch_rows)} records loaded")
            for b in batch_rows:
                dept_code = b["department"].strip().upper()
                if dept_code not in departments:
                    print(f"  [WARN] Skipping batch {b['name']}: "
                          f"department '{dept_code}' not found")
                    continue
                dept_id = departments[dept_code]
                db.add(Batch(
                    batch_id=_id(), dept_id=dept_id,
                    semester=b["semester"], name=b["name"], size=b["size"],
                ))
                total_batches += 1
            print(f"    → {total_batches} batches inserted")
        else:
            print("[!] batches.pdf not found — no batches created")

        # ── Commit ──
        await db.commit()

        # ══════════════════════════════════════════
        # SUMMARY
        # ══════════════════════════════════════════
        print()
        print("=" * 60)
        print("  Database Seeded from PDFs Successfully!")
        print("=" * 60)
        print(f"  College     : {college_data['name']}")
        print(f"  Departments : {len(departments)}")
        for code, name in dept_names.items():
            print(f"    {code:6s} — {name}")
        print(f"  Faculty     : {total_hods} HODs + {total_faculty} regular = {total_hods + total_faculty}")
        print(f"  Subjects    : {total_subjects}")
        print(f"  Rooms/Labs  : {total_rooms}")
        print(f"  Venues      : {total_venues}")
        print(f"  Time Slots  : {total_slots}")
        print(f"  Batches     : {total_batches}")
        print(f"  Admin Login : {admin_email} / admin123")
        print("=" * 60)


if __name__ == "__main__":
    import models  # noqa: F401

    folder = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "seed_pdfs"
    )
    asyncio.run(seed_from_pdfs(folder))
