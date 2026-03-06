# scripts/test_substitution.py
"""
End-to-end test for the Substitution Chain (Phase 3).
Seeds faculty data, creates a timetable entry, reports absence,
previews candidates, and exercises the accept/reject/escalation flow.

Run:  python scripts/test_substitution.py
"""
import asyncio
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import delete
from database import engine, AsyncSessionLocal, Base
from models.college import College, Department
from models.user import User
from models.faculty import Faculty
from models.subject import Subject
from models.room import Room, RoomType
from models.timetable import Timetable, TimetableEntry, EntryType
from models.global_booking import GlobalBooking
from models.substitution import Substitution, SubstitutionRequest, SubstitutionStatus
from utils.security import hash_password
import uuid

# Fixed IDs for test isolation
TEST_COLLEGE = "sub-test-college"
TEST_DEPT = "sub-test-dept"
TEST_TT = "sub-test-tt"


async def seed_test_data(db):
    """Create minimal data for substitution testing."""
    # College + Dept
    college = College(college_id=TEST_COLLEGE, name="SubTest University")
    dept = Department(dept_id=TEST_DEPT, college_id=TEST_COLLEGE, name="Computer Science", code="CS")
    db.add_all([college, dept])

    # Admin user
    admin = User(
        user_id="sub-admin-001",
        email="sub.admin@test.edu",
        hashed_password=hash_password("test123"),
        role="DEPT_ADMIN",
        full_name="Test Admin",
        college_id=TEST_COLLEGE,
        dept_id=TEST_DEPT,
    )
    db.add(admin)

    # Faculty (4 members with different expertise)
    # Note: Faculty model has no email/college_id/current_weekly_load fields
    faculty_data = [
        ("sub-f1", "Alice", ["Data Structures", "Algorithms"], 18, "morning", 2),
        ("sub-f2", "Bob", ["Data Structures", "DBMS"], 18, "afternoon", 0),
        ("sub-f3", "Carol", ["Operating Systems", "Networks"], 18, "morning", 5),
        ("sub-f4", "Dave", ["Data Structures", "OS Lab"], 18, None, 1),
    ]
    for fid, name, expertise, max_load, pref, sub_count in faculty_data:
        f = Faculty(
            faculty_id=fid,
            name=name,
            dept_id=TEST_DEPT,
            expertise=expertise,
            max_weekly_load=max_load,
            preferred_time=pref,
            substitution_count=sub_count,
            last_substitution_date=None,
        )
        db.add(f)

    # Subject (uses subject_code, weekly_periods, batch_size — not code/credits/lecture_hours)
    subj = Subject(
        subject_id="sub-s1",
        name="Data Structures",
        subject_code="CS201",
        dept_id=TEST_DEPT,
        semester=3,
        weekly_periods=3,
        needs_lab=False,
    )
    db.add(subj)

    # Room (uses RoomType.CLASSROOM not LECTURE, no dept_id)
    room = Room(
        room_id="sub-r1",
        name="Room 101",
        capacity=60,
        room_type=RoomType.CLASSROOM,
        college_id=TEST_COLLEGE,
    )
    room2 = Room(
        room_id="sub-r2",
        name="Room 102",
        capacity=60,
        room_type=RoomType.CLASSROOM,
        college_id=TEST_COLLEGE,
    )
    db.add_all([room, room2])

    # Timetable + Entry (Alice teaches DS on Monday period 2)
    tt = Timetable(
        timetable_id=TEST_TT,
        dept_id=TEST_DEPT,
        semester=3,
        academic_year="2026",
        status="published",
    )
    db.add(tt)

    entry = TimetableEntry(
        entry_id="sub-entry-1",
        timetable_id=TEST_TT,
        day="Monday",
        period=2,
        subject_id="sub-s1",
        faculty_id="sub-f1",  # Alice
        room_id="sub-r1",
        entry_type=EntryType.REGULAR,
    )
    db.add(entry)

    # Bob's entry on Monday P2 (makes him busy)
    entry_bob = TimetableEntry(
        entry_id="sub-entry-bob",
        timetable_id=TEST_TT,
        day="Monday",
        period=2,
        subject_id="sub-s1",
        faculty_id="sub-f2",  # Bob
        room_id="sub-r2",
        entry_type=EntryType.REGULAR,
    )
    db.add(entry_bob)

    # Global booking for Alice on Monday P2
    gb = GlobalBooking(
        booking_id="sub-gb-1",
        college_id=TEST_COLLEGE,
        dept_id=TEST_DEPT,
        timetable_entry_id="sub-entry-1",
        day="Monday",
        period=2,
        faculty_id="sub-f1",
        room_id="sub-r1",
        booking_type="timetable",
    )
    db.add(gb)

    # Bob is busy Monday P2 (has GlobalBooking)
    gb_bob = GlobalBooking(
        booking_id="sub-gb-bob",
        college_id=TEST_COLLEGE,
        dept_id=TEST_DEPT,
        timetable_entry_id="sub-entry-bob",
        day="Monday",
        period=2,
        faculty_id="sub-f2",
        room_id="sub-r2",
        booking_type="timetable",
    )
    db.add(gb_bob)

    await db.commit()
    print("[OK] Test data seeded")


async def cleanup(db):
    """Remove test data."""
    try:
        await db.rollback()  # Ensure clean state
    except Exception:
        pass
    # Delete in reverse dependency order
    for model in [
        SubstitutionRequest, Substitution, GlobalBooking, TimetableEntry,
        Timetable, Room, Subject, Faculty, User, Department, College,
    ]:
        try:
            if hasattr(model, "college_id"):
                await db.execute(delete(model).where(model.college_id == TEST_COLLEGE))
            elif hasattr(model, "dept_id"):
                await db.execute(delete(model).where(model.dept_id == TEST_DEPT))
            elif hasattr(model, "timetable_id"):
                await db.execute(delete(model).where(model.timetable_id == TEST_TT))
        except Exception:
            await db.rollback()
    await db.commit()


async def test_find_candidates(db):
    """Test the candidate finder directly."""
    from core.substitution.finder import find_substitute_candidates

    candidates = await find_substitute_candidates(
        original_faculty_id="sub-f1",  # Alice is absent
        subject_id="sub-s1",  # Data Structures
        day="Monday",
        period=2,
        college_id=TEST_COLLEGE,
        dept_id=TEST_DEPT,
        db=db,
    )

    print(f"\n✓ Found {len(candidates)} substitute candidates for Alice (DS, Mon P2):")
    for i, c in enumerate(candidates, 1):
        print(f"  {i}. {c['name']} — score={c['score']:.3f} "
              f"(expertise={c['expertise_match']:.1f}, "
              f"headroom={c['load_headroom_pct']:.0f}%, "
              f"days_since={c['days_since_last_sub']})")

    # Bob should NOT be a candidate (busy Mon P2)
    candidate_ids = [c["faculty_id"] for c in candidates]
    assert "sub-f2" not in candidate_ids, "Bob should be excluded (busy Mon P2)"
    print("  [OK] Bob correctly excluded (busy Mon P2)")

    # Alice (original) should NOT be a candidate
    assert "sub-f1" not in candidate_ids, "Alice should not be candidate for own class"
    print("  [OK] Alice correctly excluded (original faculty)")

    # Dave should be top (has DS expertise, lowest load, low sub count)
    if candidates:
        assert candidates[0]["faculty_id"] == "sub-f4", \
            f"Expected Dave as top candidate, got {candidates[0]['name']}"
        print(f"  ✓ Dave is top candidate (best score)")

    return candidates


async def test_report_absence_and_accept(db):
    """Test the full substitution flow: report → find → accept."""
    from core.substitution.finder import find_substitute_candidates
    from core.substitution.escalator import send_to_next_candidate

    # Create substitution
    sub_id = str(uuid.uuid4())
    substitution = Substitution(
        substitution_id=sub_id,
        original_entry_id="sub-entry-1",
        original_faculty_id="sub-f1",
        absence_date="2026-03-10",
        reason="Sick leave",
        status=SubstitutionStatus.PENDING,
    )
    db.add(substitution)
    await db.commit()

    # Find candidates
    candidates = await find_substitute_candidates(
        original_faculty_id="sub-f1",
        subject_id="sub-s1",
        day="Monday",
        period=2,
        college_id=TEST_COLLEGE,
        dept_id=TEST_DEPT,
        db=db,
    )

    # Send to first candidate
    req = await send_to_next_candidate(
        substitution_id=sub_id,
        candidates=candidates,
        escalation_level=1,
        db=db,
    )

    assert req is not None, "Request should be created"
    assert req.status == SubstitutionStatus.PENDING
    print(f"\n✓ Substitution request created: {req.request_id}")
    print(f"  Candidate: {candidates[0]['name']} (level 1)")

    # Simulate REJECT → escalation
    req.status = SubstitutionStatus.REJECTED
    db.add(req)
    await db.commit()

    # Escalate to level 2
    req2 = await send_to_next_candidate(
        substitution_id=sub_id,
        candidates=candidates,
        escalation_level=2,
        db=db,
    )

    if req2:
        print(f"  ✓ Escalated to level 2: {candidates[1]['name'] if len(candidates) > 1 else 'N/A'}")

        # Simulate ACCEPT
        req2.status = SubstitutionStatus.ACCEPTED
        db.add(req2)

        substitution.status = SubstitutionStatus.ACCEPTED
        substitution.substitute_faculty_id = req2.candidate_faculty_id
        db.add(substitution)
        await db.commit()

        await db.refresh(substitution)
        assert substitution.status == SubstitutionStatus.ACCEPTED
        print(f"  ✓ Substitution ACCEPTED by {req2.candidate_faculty_id}")
    else:
        print("  ⚠ No second candidate available for escalation test")

    return sub_id


async def test_escalation_exhaustion(db):
    """Test that exhaustion is properly handled when all candidates reject."""
    from core.substitution.escalator import check_and_escalate

    sub_id = str(uuid.uuid4())
    substitution = Substitution(
        substitution_id=sub_id,
        original_entry_id="sub-entry-1",
        original_faculty_id="sub-f1",
        absence_date="2026-03-11",
        reason="Conference",
        status=SubstitutionStatus.PENDING,
    )
    db.add(substitution)

    # Create 3 requests: first 2 rejected, 3rd still pending (at max level)
    for i in range(1, 4):
        status = SubstitutionStatus.REJECTED if i < 3 else SubstitutionStatus.PENDING
        req = SubstitutionRequest(
            request_id=str(uuid.uuid4()),
            substitution_id=sub_id,
            candidate_faculty_id=f"sub-f{i+1}" if i < 4 else "sub-f2",
            escalation_level=i,
            ranking_score=0.5,
            status=status,
        )
        db.add(req)

    await db.commit()

    # Check escalation — should be exhausted (3 rejections = max)
    result = await check_and_escalate(sub_id, db)
    await db.refresh(substitution)

    print(f"\n✓ Escalation exhaustion test:")
    print(f"  Status: {substitution.status.value}")
    print(f"  Result: {result}")

    assert substitution.status == SubstitutionStatus.CANCELLED, \
        f"Expected CANCELLED, got {substitution.status.value}"
    print("  ✓ Correctly cancelled after max escalations")

    return sub_id


async def test_notification_templates():
    """Test notification template rendering."""
    from core.notifications.templates import render_template

    # Test substitution_request template
    html = render_template("substitution_request", "email_html",
        candidate_name="Dave",
        absent_faculty="Alice",
        subject_name="Data Structures",
        day="Monday",
        period=2,
        date="2026-03-10",
        room_name="Room 101",
        expertise="Data Structures",
        accept_url="#",
        reject_url="#",
    )
    assert "Dave" in html, "Template should contain candidate name"
    assert "Data Structures" in html, "Template should contain subject"
    print("\n✓ Notification templates render correctly")
    print(f"  Sample output length: {len(html)} chars")


async def main():
    print("=" * 60)
    print("Phase 3: Substitution Chain E2E Test")
    print("=" * 60)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        try:
            # Clean up any previous test data
            await cleanup(db)

            # Seed
            await seed_test_data(db)

            # Test 1: Candidate finder
            await test_find_candidates(db)

            # Test 2: Report → escalate → accept flow
            await test_report_absence_and_accept(db)

            # Test 3: Escalation exhaustion
            await test_escalation_exhaustion(db)

            # Test 4: Notification templates
            await test_notification_templates()

            print("\n" + "=" * 60)
            print("ALL PHASE 3 TESTS PASSED ✓")
            print("=" * 60)

        finally:
            await cleanup(db)
            print("\n✓ Test data cleaned up")


if __name__ == "__main__":
    asyncio.run(main())
