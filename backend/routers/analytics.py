# routers/analytics.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from dependencies import get_db, require_any_admin
from models.user import User
from models.faculty import Faculty
from models.timetable import Timetable, TimetableEntry, TimetableStatus
from models.room import Room
from models.substitution import Substitution
from models.college import Department

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def _dept_filter(col, user: User):
    """Return a WHERE clause scoped to the user's department,
    or all departments in their college if they are a super admin."""
    if user.dept_id is not None:
        return col == user.dept_id
    # Super admin: all departments in the college
    return col.in_(
        select(Department.dept_id).where(Department.college_id == user.college_id)
    )


@router.get("/dashboard")
async def dashboard(
    current_user: User = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
):
    """Overview dashboard for dept admin."""
    from models.subject import Subject

    # Count faculty
    faculty_count = await db.execute(
        select(func.count(Faculty.faculty_id)).where(
            _dept_filter(Faculty.dept_id, current_user)
        )
    )
    # Count timetables
    tt_count = await db.execute(
        select(func.count(Timetable.timetable_id)).where(
            _dept_filter(Timetable.dept_id, current_user),
            Timetable.status != TimetableStatus.DELETED,
        )
    )
    # Count subjects
    subject_count = await db.execute(
        select(func.count(Subject.subject_id)).where(
            _dept_filter(Subject.dept_id, current_user)
        )
    )
    # Count rooms
    room_count = await db.execute(
        select(func.count(Room.room_id)).where(
            Room.college_id == current_user.college_id
        )
    )
    return {
        "faculty_count": faculty_count.scalar() or 0,
        "timetable_count": tt_count.scalar() or 0,
        "subject_count": subject_count.scalar() or 0,
        "room_count": room_count.scalar() or 0,
    }


@router.get("/faculty-load")
async def faculty_load(
    current_user: User = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
):
    """Faculty weekly load analysis."""
    result = await db.execute(
        select(
            Faculty.faculty_id,
            Faculty.name,
            Faculty.max_weekly_load,
            func.count(TimetableEntry.entry_id).label("assigned_periods"),
        )
        .outerjoin(TimetableEntry, Faculty.faculty_id == TimetableEntry.faculty_id)
        .where(_dept_filter(Faculty.dept_id, current_user))
        .group_by(Faculty.faculty_id, Faculty.name, Faculty.max_weekly_load)
    )
    rows = result.all()
    return [
        {
            "faculty_id": r.faculty_id,
            "name": r.name,
            "max_weekly_load": r.max_weekly_load,
            "assigned_periods": r.assigned_periods,
            "utilisation_pct": round(
                (r.assigned_periods / r.max_weekly_load * 100) if r.max_weekly_load > 0 else 0,
                1,
            ),
        }
        for r in rows
    ]


@router.get("/room-utilisation")
async def room_utilisation(
    current_user: User = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
):
    """Room utilisation across the college."""
    from models.global_booking import GlobalBooking

    result = await db.execute(
        select(
            Room.room_id,
            Room.name,
            Room.capacity,
            func.count(GlobalBooking.booking_id).label("booked_slots"),
        )
        .outerjoin(GlobalBooking, Room.room_id == GlobalBooking.room_id)
        .where(Room.college_id == current_user.college_id)
        .group_by(Room.room_id, Room.name, Room.capacity)
    )
    rows = result.all()
    total_slots = 6 * 8  # 6 days × 8 periods
    return [
        {
            "room_id": r.room_id,
            "name": r.name,
            "capacity": r.capacity,
            "booked_slots": r.booked_slots,
            "total_slots": total_slots,
            "utilisation_pct": round(
                (r.booked_slots / total_slots * 100) if total_slots > 0 else 0, 1
            ),
        }
        for r in rows
    ]
