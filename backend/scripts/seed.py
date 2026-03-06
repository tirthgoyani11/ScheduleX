# scripts/seed.py
"""
Seed the database with realistic initial data:
  - College, Department
  - Super admin + Dept admin users
  - 6 Faculty members
  - 7 Subjects (with lecture_hours + lab_hours)
  - 5 Rooms (classrooms + labs)
  - 8 Time slots (lectures, break, labs)
  - 4 Batches (A, B, C, D)

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
from models.batch import Batch
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
                max_weekly_load=24,
                preferred_time=pref,
            ))

        # ── Subjects (with lecture_hours + lab_hours) ──
        # lecture_hours = theory periods per week
        # lab_hours     = 2 consecutive periods per week (1 lab session = 2 hrs)
        # weekly_periods = lecture_hours + lab_hours (total contact per batch)
        subject_data = [
            # (name, code, sem, credits, lec_hrs, lab_hrs, batch_size)
            ("Computer Networks",       "CS301", 5, 4, 3, 2, 60),
            ("Operating Systems",       "CS302", 5, 4, 3, 2, 60),
            ("Database Management",     "CS303", 5, 3, 3, 2, 60),
            ("Software Engineering",    "CS304", 5, 3, 3, 0, 60),
            ("Design & Analysis of Algorithms", "CS305", 5, 4, 3, 0, 60),
            ("Theory of Computation",   "CS306", 5, 3, 3, 0, 60),
            ("Web Programming",         "CS307", 5, 3, 2, 2, 60),
        ]
        subject_ids = []
        for name, code, sem, credits, lh, lab_h, bs in subject_data:
            sid = str(uuid.uuid4())
            subject_ids.append(sid)
            db.add(Subject(
                subject_id=sid,
                dept_id=dept_id,
                name=name,
                subject_code=code,
                semester=sem,
                credits=credits,
                weekly_periods=lh + lab_h,
                lecture_hours=lh,
                lab_hours=lab_h,
                needs_lab=lab_h > 0,
                batch_size=bs,
            ))

        # ── Rooms ──
        room_data = [
            ("Room 301",  60, RoomType.CLASSROOM, True,  False, False),
            ("Room 302",  60, RoomType.CLASSROOM, True,  False, True),
            ("Room 303",  90, RoomType.CLASSROOM, True,  False, False),
            ("CS Lab 1",  30, RoomType.LAB,       True,  True,  True),
            ("CS Lab 2",  30, RoomType.LAB,       True,  True,  True),
            ("CS Lab 3",  30, RoomType.LAB,       True,  True,  True),
            ("CS Lab 4",  30, RoomType.LAB,       True,  True,  True),
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

        # ── Time Slots (uniform 1-hour periods) ──
        slot_data = [
            (1, "Period 1", "09:00", "10:00", SlotType.LECTURE),
            (2, "Period 2", "10:00", "11:00", SlotType.LECTURE),
            (3, "Period 3", "11:00", "12:00", SlotType.LECTURE),
            (4, "Period 4", "12:00", "13:00", SlotType.LECTURE),
            (5, "Lunch",    "13:00", "14:00", SlotType.BREAK),
            (6, "Period 5", "14:00", "15:00", SlotType.LECTURE),
            (7, "Period 6", "15:00", "16:00", SlotType.LECTURE),
            (8, "Period 7", "16:00", "17:00", SlotType.LECTURE),
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

        # ── Batches (4 batches for lab rotation) ──
        for batch_name in ["A", "B", "C", "D"]:
            db.add(Batch(
                batch_id=str(uuid.uuid4()),
                dept_id=dept_id,
                semester=5,
                name=batch_name,
                size=15,   # 60 students / 4 batches
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
        for name, code, sem, cr, lh, lab_h, *_ in subject_data:
            print(f"    {code} - {name} (L:{lh} Lab:{lab_h})")
        print(f"  Rooms: {len(room_data)} rooms")
        for name, cap, rtype, *_ in room_data:
            print(f"    {name} ({rtype.value}, cap={cap})")
        print(f"  Batches: A, B, C, D (15 students each)")
        print(f"  Time Slots: {len(slot_data)} slots")


if __name__ == "__main__":
    import models  # noqa: F401
    asyncio.run(seed())
