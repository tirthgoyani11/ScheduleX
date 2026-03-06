# scripts/seed.py
"""
Seed the database with realistic initial data:
  - College, Department
  - Super admin + Dept admin users
  - 6 Faculty members
  - 8 Subjects (with labs)
  - 5 Rooms (classrooms + labs)
  - 8 Time slots (lectures, break, labs)

Usage: python scripts/seed.py
"""
import asyncio
import sys
import os
import uuid

# Add parent directory to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, Base, AsyncSessionLocal
from models.college import College, Department
from models.user import User, UserRole
from models.faculty import Faculty
from models.subject import Subject
from models.room import Room, RoomType
from models.timeslot import TimeSlotConfig, SlotType
from utils.security import hash_password


async def seed():
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        from sqlalchemy import select

        # Check if already seeded
        existing = await db.execute(select(College).limit(1))
        if existing.scalar_one_or_none():
            print("Database already seeded. Skipping.")
            return

        # ── College ──
        college_id = str(uuid.uuid4())
        db.add(College(
            college_id=college_id,
            name="CVM University",
            affiliation="CVM",
            city="Anand",
        ))

        # ── Department ──
        dept_id = str(uuid.uuid4())
        db.add(Department(
            dept_id=dept_id,
            college_id=college_id,
            name="Computer Engineering",
            code="CE",
        ))

        # ── Users ──
        admin_id = str(uuid.uuid4())
        db.add(User(
            user_id=admin_id,
            email="admin@cvmu.edu.in",
            hashed_password=hash_password("admin123"),
            full_name="System Admin",
            role=UserRole.SUPER_ADMIN,
            college_id=college_id,
            dept_id=dept_id,
        ))
        db.add(User(
            user_id=str(uuid.uuid4()),
            email="hod.ce@cvmu.edu.in",
            hashed_password=hash_password("hod123"),
            full_name="HOD Computer Engineering",
            role=UserRole.DEPT_ADMIN,
            college_id=college_id,
            dept_id=dept_id,
        ))

        # ── Faculty ──
        faculty_data = [
            ("Dr. Rajesh Patel",   "FAC001", ["CN", "OS"],         "morning"),
            ("Prof. Meena Shah",   "FAC002", ["DBMS", "SE"],        "morning"),
            ("Dr. Amit Desai",     "FAC003", ["DAA", "TOC"],        "afternoon"),
            ("Prof. Priya Joshi",  "FAC004", ["WP", "CN"],          "any"),
            ("Dr. Kiran Mehta",    "FAC005", ["OS", "DAA"],         "morning"),
            ("Prof. Sneha Trivedi","FAC006", ["SE", "DBMS", "WP"],  "afternoon"),
        ]
        faculty_ids = []
        for name, emp_id, expertise, pref in faculty_data:
            fid = str(uuid.uuid4())
            faculty_ids.append(fid)
            db.add(Faculty(
                faculty_id=fid,
                dept_id=dept_id,
                name=name,
                employee_id=emp_id,
                expertise=expertise,
                max_weekly_load=18,
                preferred_time=pref,
            ))

        # ── Subjects ──
        subject_data = [
            # (name, code, semester, credits, weekly_periods, needs_lab, batch_size, batch)
            ("Computer Networks",       "CS301", 5, 4, 4, True,  60, "CE-3A"),
            ("Operating Systems",       "CS302", 5, 4, 4, True,  60, "CE-3A"),
            ("Database Management",     "CS303", 5, 3, 3, True,  60, "CE-3A"),
            ("Software Engineering",    "CS304", 5, 3, 3, False, 60, "CE-3A"),
            ("Design & Analysis of Algorithms", "CS305", 5, 4, 4, False, 60, "CE-3A"),
            ("Theory of Computation",   "CS306", 5, 3, 3, False, 60, "CE-3A"),
            ("Web Programming",         "CS307", 5, 3, 3, True,  60, "CE-3A"),
            ("Computer Networks",       "CS301B", 5, 4, 4, True,  60, "CE-3B"),
        ]
        subject_ids = []
        for name, code, sem, credits, wp, lab, bs, batch in subject_data:
            sid = str(uuid.uuid4())
            subject_ids.append(sid)
            db.add(Subject(
                subject_id=sid,
                dept_id=dept_id,
                name=name,
                subject_code=code,
                semester=sem,
                credits=credits,
                weekly_periods=wp,
                needs_lab=lab,
                batch_size=bs,
                batch=batch,
            ))

        # ── Rooms ──
        room_data = [
            ("Room 301",  60, RoomType.CLASSROOM, True,  False, False),
            ("Room 302",  60, RoomType.CLASSROOM, True,  False, True),
            ("Room 303",  90, RoomType.CLASSROOM, True,  False, False),
            ("CS Lab 1",  60, RoomType.LAB,       True,  True,  True),
            ("CS Lab 2",  60, RoomType.LAB,       True,  True,  True),
        ]
        for name, cap, rtype, proj, comp, ac in room_data:
            db.add(Room(
                room_id=str(uuid.uuid4()),
                college_id=college_id,
                name=name,
                capacity=cap,
                room_type=rtype,
                has_projector=proj,
                has_computers=comp,
                has_ac=ac,
            ))

        # ── Time Slots ──
        slot_data = [
            (1, "Period 1", "09:00", "10:00", SlotType.LECTURE),
            (2, "Period 2", "10:00", "11:00", SlotType.LECTURE),
            (3, "Period 3", "11:00", "12:00", SlotType.LECTURE),
            (4, "Period 4", "12:00", "13:00", SlotType.LECTURE),
            (5, "Lunch",    "13:00", "14:00", SlotType.BREAK),
            (6, "Period 5", "14:00", "15:00", SlotType.LECTURE),
            (7, "Lab 1",   "15:00", "17:00", SlotType.LAB),
            (8, "Lab 2",   "17:00", "19:00", SlotType.LAB),
        ]
        for order, label, start, end, stype in slot_data:
            db.add(TimeSlotConfig(
                slot_id=str(uuid.uuid4()),
                college_id=college_id,
                slot_order=order,
                label=label,
                start_time=start,
                end_time=end,
                slot_type=stype,
            ))

        await db.commit()
        print("Seed data created successfully!")
        print(f"  College: CVM University")
        print(f"  Department: Computer Engineering (CE)")
        print(f"  Users:")
        print(f"    Super Admin: admin@cvmu.edu.in / admin123")
        print(f"    Dept Admin:  hod.ce@cvmu.edu.in / hod123")
        print(f"  Faculty: {len(faculty_data)} members")
        for name, emp_id, *_ in faculty_data:
            print(f"    {emp_id} - {name}")
        print(f"  Subjects: {len(subject_data)} subjects")
        for name, code, *_ in subject_data:
            print(f"    {code} - {name}")
        print(f"  Rooms: {len(room_data)} rooms")
        for name, cap, rtype, *_ in room_data:
            print(f"    {name} ({rtype.value}, cap={cap})")
        print(f"  Time Slots: {len(slot_data)} slots")


if __name__ == "__main__":
    import models  # noqa: F401
    asyncio.run(seed())
