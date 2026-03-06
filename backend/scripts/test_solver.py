# scripts/test_solver.py
"""
End-to-end test for the CP-SAT timetable generator.
Seeds test data (faculty, subjects, rooms), then calls the solver directly.

Usage:
    cd timetable_system
    python scripts/test_solver.py
"""
import asyncio
import sys
import uuid

sys.path.insert(0, ".")

from database import AsyncSessionLocal, engine, Base
from models.college import College, Department
from models.faculty import Faculty
from models.subject import Subject
from models.room import Room, RoomType
from core.scheduler.engine import generate_timetable


COLLEGE_ID = "test-college-001"
DEPT_ID = "test-dept-001"


async def seed_test_data(db):
    """Insert test college, department, faculty, subjects, and rooms."""
    from sqlalchemy import select

    # Check if already seeded
    existing = await db.execute(select(College).where(College.college_id == COLLEGE_ID))
    if existing.scalar_one_or_none():
        print("[SEED] Test data already exists, skipping seed.")
        return

    # College
    college = College(college_id=COLLEGE_ID, name="Test University", city="TestCity")
    db.add(college)

    # Department
    dept = Department(dept_id=DEPT_ID, college_id=COLLEGE_ID, name="Computer Science", code="CS")
    db.add(dept)

    # 4 Faculty members
    faculty_data = [
        ("f1", "Dr. Alice", ["OS", "CN"], 18, "morning"),
        ("f2", "Dr. Bob", ["DBMS", "SE"], 18, "afternoon"),
        ("f3", "Dr. Carol", ["DAA", "TOC"], 16, "any"),
        ("f4", "Prof. Dave", ["OS-Lab", "CN-Lab"], 12, "morning"),
    ]
    for fid, name, expertise, load, pref in faculty_data:
        db.add(Faculty(
            faculty_id=fid, dept_id=DEPT_ID, name=name,
            expertise=expertise, max_weekly_load=load, preferred_time=pref,
        ))

    # 6 Subjects (semester 3)
    subject_data = [
        ("s1", "Operating Systems", "CS301", 3, 3, 3, False, 60, "CS-3A"),
        ("s2", "Computer Networks", "CS302", 3, 3, 3, False, 60, "CS-3A"),
        ("s3", "DBMS",             "CS303", 3, 3, 3, False, 60, "CS-3A"),
        ("s4", "Software Engg",    "CS304", 3, 2, 2, False, 60, "CS-3A"),
        ("s5", "OS Lab",           "CS351", 3, 1, 2, True,  30, "CS-3A"),
        ("s6", "CN Lab",           "CS352", 3, 1, 2, True,  30, "CS-3A"),
    ]
    for sid, name, code, sem, credits, wp, lab, bs, batch in subject_data:
        db.add(Subject(
            subject_id=sid, dept_id=DEPT_ID, name=name, subject_code=code,
            semester=sem, credits=credits, weekly_periods=wp,
            needs_lab=lab, batch_size=bs, batch=batch,
        ))

    # 4 Rooms (2 classrooms, 2 labs)
    room_data = [
        ("r1", "Room 301", 70, RoomType.CLASSROOM),
        ("r2", "Room 302", 70, RoomType.CLASSROOM),
        ("r3", "CS Lab 1", 40, RoomType.LAB),
        ("r4", "CS Lab 2", 40, RoomType.LAB),
    ]
    for rid, name, cap, rtype in room_data:
        db.add(Room(
            room_id=rid, college_id=COLLEGE_ID, name=name,
            capacity=cap, room_type=rtype,
        ))

    await db.commit()
    print("[SEED] Test data seeded successfully.")


async def run_test():
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        await seed_test_data(db)

    # Create a timetable record
    from models.timetable import Timetable, TimetableStatus

    async with AsyncSessionLocal() as db:
        tt_id = str(uuid.uuid4())
        tt = Timetable(
            timetable_id=tt_id,
            dept_id=DEPT_ID,
            semester=3,
            academic_year="2025-26",
            status=TimetableStatus.DRAFT,
        )
        db.add(tt)
        await db.commit()

        # Faculty-Subject mapping
        faculty_subject_map = {
            "s1": ["f1"],       # OS -> Dr. Alice
            "s2": ["f1"],       # CN -> Dr. Alice
            "s3": ["f2"],       # DBMS -> Dr. Bob
            "s4": ["f2"],       # SE -> Dr. Bob
            "s5": ["f4"],       # OS Lab -> Prof. Dave
            "s6": ["f4"],       # CN Lab -> Prof. Dave
        }

        config = {
            "faculty_subject_map": faculty_subject_map,
            "time_limit_seconds": 60,
        }

        print(f"\n{'='*60}")
        print(f"  TIMETABLE GENERATION TEST")
        print(f"  Timetable ID: {tt_id}")
        print(f"  Subjects: 6 (4 theory + 2 labs)")
        print(f"  Faculty: 4")
        print(f"  Rooms: 4 (2 classrooms + 2 labs)")
        print(f"{'='*60}\n")

        result = await generate_timetable(tt_id, db, config)

        print(f"\n{'='*60}")
        print(f"  SOLVER RESULT")
        print(f"  Status:      {result['status']}")
        print(f"  Score:       {result['score']}%")
        print(f"  Entries:     {result['entry_count']}")
        print(f"  Wall time:   {result['wall_time']}s")
        if result.get("diagnosis"):
            print(f"  Diagnosis:   {result['diagnosis']}")
        print(f"{'='*60}\n")

        if result["status"] in ("OPTIMAL", "FEASIBLE"):
            # Print the generated timetable
            from sqlalchemy import select
            from models.timetable import TimetableEntry

            entries_result = await db.execute(
                select(TimetableEntry).where(TimetableEntry.timetable_id == tt_id)
            )
            entries = entries_result.scalars().all()

            # Build lookup tables
            subject_names = {
                "s1": "OS", "s2": "CN", "s3": "DBMS", "s4": "SE",
                "s5": "OS Lab", "s6": "CN Lab",
            }
            faculty_names = {
                "f1": "Alice", "f2": "Bob", "f3": "Carol", "f4": "Dave",
            }
            room_names = {
                "r1": "R301", "r2": "R302", "r3": "Lab1", "r4": "Lab2",
            }

            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
            periods = list(range(1, 9))

            # Print grid
            print(f"{'Day':<12}", end="")
            for p in periods:
                print(f"{'P'+str(p):<14}", end="")
            print()
            print("-" * (12 + 14 * 8))

            for day in days:
                print(f"{day:<12}", end="")
                for period in periods:
                    matching = [
                        e for e in entries
                        if e.day == day and e.period == period
                    ]
                    if matching:
                        e = matching[0]
                        subj = subject_names.get(e.subject_id, e.subject_id[:6])
                        fac = faculty_names.get(e.faculty_id, e.faculty_id[:6])
                        room = room_names.get(e.room_id, e.room_id[:6])
                        print(f"{subj}/{fac:<13}", end="")
                    else:
                        print(f"{'---':<14}", end="")
                print()

            print()
            print(f"Total entries: {len(entries)}")
        else:
            print("No timetable generated. See diagnosis above.")


if __name__ == "__main__":
    asyncio.run(run_test())
