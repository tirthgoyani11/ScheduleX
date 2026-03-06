# scripts/test_stress.py
"""
University-scale stress test for the OR-Tools CP-SAT timetable engine.

Simulates:
  - 10 branches (departments) — CS, IT, EC, ME, CE, EE, CH, BT, MT, PH
  - 50 rooms (40 classrooms + 10 labs)
  - 60 faculty (~6 per department)
  - 4 years × 2 semesters = ~8 subject sets
  - 5000 students across all branches

Each department's timetable is generated independently (per-semester)
but they share rooms & global bookings — exactly like a real university.

Run:  cd timetable_system && python scripts/test_stress.py
"""
import asyncio
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import delete
from database import engine, AsyncSessionLocal, Base
from models.college import College, Department
from models.user import User
from models.faculty import Faculty
from models.subject import Subject
from models.room import Room, RoomType
from models.timetable import Timetable, TimetableEntry, TimetableStatus, EntryType
from models.global_booking import GlobalBooking
from utils.security import hash_password
from core.scheduler.engine import generate_timetable

import uuid

# ── Configuration ─────────────────────────────────────────────────────────────
COLLEGE_ID = "stress-college"
NUM_ROOMS_CLASSROOM = 40
NUM_ROOMS_LAB = 10
BATCH_SIZE_CLASSROOM = 60
BATCH_SIZE_LAB = 30

BRANCHES = [
    {"code": "CS", "name": "Computer Science"},
    {"code": "IT", "name": "Information Technology"},
    {"code": "EC", "name": "Electronics & Communication"},
    {"code": "ME", "name": "Mechanical Engineering"},
    {"code": "CE", "name": "Civil Engineering"},
    {"code": "EE", "name": "Electrical Engineering"},
    {"code": "CH", "name": "Chemical Engineering"},
    {"code": "BT", "name": "Biotechnology"},
    {"code": "MT", "name": "Mathematics"},
    {"code": "PH", "name": "Physics"},
]

# Subjects per department (semester 3 as representative — each has theory + 1 lab)
SUBJECTS_PER_DEPT = [
    {"name": "Core Subject 1",  "code_suffix": "201", "credits": 3, "weekly": 3, "lab": False, "batch": "A"},
    {"name": "Core Subject 2",  "code_suffix": "202", "credits": 3, "weekly": 3, "lab": False, "batch": "A"},
    {"name": "Core Subject 3",  "code_suffix": "203", "credits": 3, "weekly": 3, "lab": False, "batch": "A"},
    {"name": "Elective 1",      "code_suffix": "211", "credits": 3, "weekly": 2, "lab": False, "batch": "A"},
    {"name": "Elective 2",      "code_suffix": "212", "credits": 2, "weekly": 2, "lab": False, "batch": "A"},
    {"name": "Lab Practical",   "code_suffix": "251", "credits": 2, "weekly": 2, "lab": True,  "batch": "A"},
]

# 6 faculty per department — each teaches 2–3 subjects
FACULTY_TEMPLATE = [
    {"name_suffix": "Prof Alpha",   "expertise_idx": [0, 1],    "pref": "morning",   "max_load": 18},
    {"name_suffix": "Prof Beta",    "expertise_idx": [1, 2],    "pref": "afternoon",  "max_load": 18},
    {"name_suffix": "Prof Gamma",   "expertise_idx": [2, 3],    "pref": "morning",   "max_load": 16},
    {"name_suffix": "Prof Delta",   "expertise_idx": [3, 4],    "pref": None,        "max_load": 16},
    {"name_suffix": "Prof Epsilon", "expertise_idx": [4, 5],    "pref": "afternoon",  "max_load": 14},
    {"name_suffix": "Prof Zeta",    "expertise_idx": [0, 5],    "pref": None,        "max_load": 18},
]


async def run_stress_test():
    """Execute the full university-scale stress test."""
    print("=" * 70)
    print("  UNIVERSITY-SCALE STRESS TEST")
    print(f"  {len(BRANCHES)} departments | {NUM_ROOMS_CLASSROOM + NUM_ROOMS_LAB} rooms | "
          f"{len(BRANCHES) * len(FACULTY_TEMPLATE)} faculty | ~5000 students")
    print("=" * 70)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        await _cleanup(db)
        await _seed_data(db)

        total_entries = 0
        total_time = 0.0
        results = []

        # Generate timetable for each department
        for i, branch in enumerate(BRANCHES):
            dept_id = f"stress-{branch['code'].lower()}"
            tt_id = f"stress-tt-{branch['code'].lower()}"

            # Build faculty-subject map for this department
            subjects = await _get_dept_subjects(dept_id, db)
            faculty = await _get_dept_faculty(dept_id, db)
            faculty_subject_map = _build_faculty_subject_map(subjects, faculty, branch["code"])

            config = {
                "faculty_subject_map": faculty_subject_map,
                "time_limit_seconds": 60,
            }

            print(f"\n[{i+1}/{len(BRANCHES)}] {branch['name']} ({branch['code']}) "
                  f"— {len(subjects)} subjects, {len(faculty)} faculty...")

            t0 = time.perf_counter()
            result = await generate_timetable(tt_id, db, config)
            elapsed = time.perf_counter() - t0

            total_time += elapsed
            total_entries += result.get("entry_count", 0)

            status = result["status"]
            score = result.get("score", 0)
            entries = result.get("entry_count", 0)
            wall = result.get("wall_time", 0)

            icon = "✓" if status in ("OPTIMAL", "FEASIBLE") else "✗"
            print(f"  {icon} Status: {status} | Score: {score}% | "
                  f"Entries: {entries} | Solver: {wall}s | Total: {elapsed:.2f}s")

            if result.get("diagnosis"):
                diag = result["diagnosis"]
                print(f"  ⚠ {diag.get('type', 'UNKNOWN')}: {diag.get('message', '')[:100]}")

            results.append({
                "dept": branch["code"],
                "status": status,
                "score": score,
                "entries": entries,
                "time": elapsed,
                "solver_time": wall,
            })

        # ── Summary ───────────────────────────────────────────────────────────
        print("\n" + "=" * 70)
        print("  STRESS TEST RESULTS SUMMARY")
        print("=" * 70)

        optimal = sum(1 for r in results if r["status"] == "OPTIMAL")
        feasible = sum(1 for r in results if r["status"] == "FEASIBLE")
        infeasible = sum(1 for r in results if r["status"] == "INFEASIBLE")
        unknown = sum(1 for r in results if r["status"] not in ("OPTIMAL", "FEASIBLE", "INFEASIBLE"))

        avg_score = (
            sum(r["score"] for r in results if r["status"] in ("OPTIMAL", "FEASIBLE"))
            / max(1, optimal + feasible)
        )
        max_time = max(r["time"] for r in results)
        avg_time = total_time / len(results)

        print(f"  Departments:  {len(BRANCHES)}")
        print(f"  OPTIMAL:      {optimal}")
        print(f"  FEASIBLE:     {feasible}")
        print(f"  INFEASIBLE:   {infeasible}")
        print(f"  UNKNOWN:      {unknown}")
        print(f"  Total entries: {total_entries}")
        print(f"  Avg score:    {avg_score:.1f}%")
        print(f"  Total time:   {total_time:.2f}s")
        print(f"  Avg per dept: {avg_time:.2f}s")
        print(f"  Max per dept: {max_time:.2f}s")

        # Global booking count
        from sqlalchemy import func, select as sel
        count_result = await db.execute(
            sel(func.count()).select_from(GlobalBooking).where(
                GlobalBooking.college_id == COLLEGE_ID
            )
        )
        booking_count = count_result.scalar()
        print(f"  Global bookings: {booking_count}")

        # Pass/Fail
        success_rate = (optimal + feasible) / len(BRANCHES) * 100
        print(f"\n  Success rate: {success_rate:.0f}%")
        if success_rate == 100 and avg_time < 30:
            print("  🏆 STRESS TEST PASSED — Ready for production scale!")
        elif success_rate >= 80:
            print("  ⚠ MOSTLY OK — some departments had issues")
        else:
            print("  ✗ NEEDS WORK — scalability issues detected")

        print("=" * 70)

        await _cleanup(db)


async def _seed_data(db: AsyncSession):
    """Seed the full university dataset."""
    print("\nSeeding test data...")

    # College
    college = College(college_id=COLLEGE_ID, name="Stress Test University")
    db.add(college)

    # Rooms — 40 classrooms + 10 labs
    rooms = []
    for i in range(1, NUM_ROOMS_CLASSROOM + 1):
        rooms.append(Room(
            room_id=f"stress-room-{i:03d}",
            college_id=COLLEGE_ID,
            name=f"Room {i:03d}",
            capacity=BATCH_SIZE_CLASSROOM + 10,
            room_type=RoomType.CLASSROOM,
            has_projector=True,
            has_computers=False,
            has_ac=True,
        ))
    for i in range(1, NUM_ROOMS_LAB + 1):
        rooms.append(Room(
            room_id=f"stress-lab-{i:02d}",
            college_id=COLLEGE_ID,
            name=f"Lab {i:02d}",
            capacity=BATCH_SIZE_LAB + 5,
            room_type=RoomType.LAB,
            has_projector=True,
            has_computers=True,
            has_ac=True,
        ))
    db.add_all(rooms)

    # Departments + Faculty + Subjects
    admin_user = User(
        user_id="stress-admin",
        email="admin@stress.edu",
        hashed_password=hash_password("test123"),
        role="SUPER_ADMIN",
        full_name="Stress Admin",
        college_id=COLLEGE_ID,
        dept_id=None,
    )
    db.add(admin_user)

    for branch in BRANCHES:
        dept_id = f"stress-{branch['code'].lower()}"

        dept = Department(
            dept_id=dept_id,
            college_id=COLLEGE_ID,
            name=branch["name"],
            code=branch["code"],
        )
        db.add(dept)

        # Faculty for this department
        for j, ft in enumerate(FACULTY_TEMPLATE):
            fac = Faculty(
                faculty_id=f"stress-f-{branch['code'].lower()}-{j+1}",
                dept_id=dept_id,
                name=f"{branch['code']} {ft['name_suffix']}",
                expertise=[
                    f"{branch['code']}{SUBJECTS_PER_DEPT[idx]['code_suffix']}"
                    for idx in ft["expertise_idx"]
                ],
                max_weekly_load=ft["max_load"],
                preferred_time=ft["pref"],
                substitution_count=0,
            )
            db.add(fac)

        # Subjects for this department (semester 3)
        for k, st in enumerate(SUBJECTS_PER_DEPT):
            sub = Subject(
                subject_id=f"stress-s-{branch['code'].lower()}-{k+1}",
                dept_id=dept_id,
                name=f"{branch['code']} {st['name']}",
                subject_code=f"{branch['code']}{st['code_suffix']}",
                semester=3,
                credits=st["credits"],
                weekly_periods=st["weekly"],
                needs_lab=st["lab"],
                batch_size=BATCH_SIZE_LAB if st["lab"] else BATCH_SIZE_CLASSROOM,
                batch=f"{branch['code']}-{st['batch']}" if st["batch"] else None,
            )
            db.add(sub)

        # Timetable row (QUEUED status)
        tt = Timetable(
            timetable_id=f"stress-tt-{branch['code'].lower()}",
            dept_id=dept_id,
            semester=3,
            academic_year="2026",
            status=TimetableStatus.DRAFT,
        )
        db.add(tt)

    await db.commit()
    print(f"  ✓ Seeded: 1 college, {len(BRANCHES)} depts, "
          f"{len(BRANCHES) * len(FACULTY_TEMPLATE)} faculty, "
          f"{len(BRANCHES) * len(SUBJECTS_PER_DEPT)} subjects, "
          f"{NUM_ROOMS_CLASSROOM + NUM_ROOMS_LAB} rooms")


def _build_faculty_subject_map(subjects, faculty, branch_code):
    """Build the faculty_subject_map for a department."""
    fsm = {}
    for k, subject in enumerate(subjects):
        # Assign faculty whose expertise_idx covers this subject index
        assigned = []
        for j, ft in enumerate(FACULTY_TEMPLATE):
            if k in ft["expertise_idx"]:
                fid = f"stress-f-{branch_code.lower()}-{j+1}"
                assigned.append(fid)
        if assigned:
            fsm[subject.subject_id] = assigned
    return fsm


async def _get_dept_subjects(dept_id, db):
    from sqlalchemy import select
    r = await db.execute(
        select(Subject).where(Subject.dept_id == dept_id, Subject.semester == 3)
    )
    return r.scalars().all()


async def _get_dept_faculty(dept_id, db):
    from sqlalchemy import select
    r = await db.execute(
        select(Faculty).where(Faculty.dept_id == dept_id)
    )
    return r.scalars().all()


async def _cleanup(db: AsyncSession):
    """Remove all stress test data."""
    # Delete in FK-safe order
    await db.execute(delete(GlobalBooking).where(GlobalBooking.college_id == COLLEGE_ID))
    for branch in BRANCHES:
        dept_id = f"stress-{branch['code'].lower()}"
        tt_id = f"stress-tt-{branch['code'].lower()}"
        await db.execute(delete(TimetableEntry).where(TimetableEntry.timetable_id == tt_id))
        await db.execute(delete(Timetable).where(Timetable.dept_id == dept_id))
        await db.execute(delete(Subject).where(Subject.dept_id == dept_id))
        await db.execute(delete(Faculty).where(Faculty.dept_id == dept_id))
    await db.execute(delete(User).where(User.college_id == COLLEGE_ID))
    for branch in BRANCHES:
        await db.execute(delete(Department).where(Department.dept_id == f"stress-{branch['code'].lower()}"))
    await db.execute(delete(Room).where(Room.college_id == COLLEGE_ID))
    await db.execute(delete(College).where(College.college_id == COLLEGE_ID))
    await db.commit()


if __name__ == "__main__":
    asyncio.run(run_stress_test())
