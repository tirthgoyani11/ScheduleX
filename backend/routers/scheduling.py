# routers/scheduling.py
"""
Reschedule, Extra Lecture, and Proxy management.
Provides free-slot / free-room / free-faculty discovery and booking endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func as sqlfunc, or_
from dependencies import get_db, get_current_user, require_any_admin
from models.user import User, UserRole
from models.timetable import Timetable, TimetableEntry, TimetableStatus, EntryType
from models.global_booking import GlobalBooking
from models.faculty import Faculty
from models.subject import Subject
from models.room import Room
from models.timeslot import TimeSlotConfig
from models.slot_booking import SlotBooking, BookingType, BookingStatus
from schemas.scheduling import (
    FreeSlotResponse,
    FreeSlotWithRoomsResponse,
    FreeRoomResponse,
    FreeFacultyResponse,
    BusyFacultyResponse,
    DateSlotCheckResponse,
    DateCheckResponse,
    RescheduleRequest,
    ExtraLectureRequest,
    ProxyRequest,
    SlotBookingResponse,
)
from datetime import datetime, timezone, date as date_type
import uuid

router = APIRouter(prefix="/scheduling", tags=["Scheduling"])

ALL_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


# ── Helpers ───────────────────────────────────────────────────

async def _get_published_timetable(tt_id: str, user: User, db: AsyncSession) -> Timetable:
    tt = await db.get(Timetable, tt_id)
    if not tt:
        raise HTTPException(404, "Timetable not found")
    if tt.status != TimetableStatus.PUBLISHED:
        raise HTTPException(400, "Timetable must be published")
    return tt


async def _get_time_slots(college_id: str, db: AsyncSession) -> list[TimeSlotConfig]:
    result = await db.execute(
        select(TimeSlotConfig)
        .where(TimeSlotConfig.college_id == college_id)
        .order_by(TimeSlotConfig.slot_order)
    )
    return list(result.scalars().all())


async def _get_booked_faculty_slots(college_id: str, db: AsyncSession):
    """Return set of (day, period, faculty_id) that are booked."""
    result = await db.execute(
        select(GlobalBooking.day, GlobalBooking.period, GlobalBooking.faculty_id)
        .where(GlobalBooking.college_id == college_id)
    )
    return {(r.day, r.period, r.faculty_id) for r in result.all()}


async def _get_booked_room_slots(college_id: str, db: AsyncSession):
    """Return set of (day, period, room_id) that are booked."""
    result = await db.execute(
        select(GlobalBooking.day, GlobalBooking.period, GlobalBooking.room_id)
        .where(GlobalBooking.college_id == college_id)
    )
    return {(r.day, r.period, r.room_id) for r in result.all()}


async def _get_approved_booking_slots(college_id: str, db: AsyncSession, target_date: str | None = None):
    """Return set of (day, period, faculty_id) and (day, period, room_id) from approved slot_bookings.
    If target_date is given, only include bookings for that specific date."""
    query = select(
        SlotBooking.day, SlotBooking.period, SlotBooking.faculty_id,
        SlotBooking.room_id, SlotBooking.booking_type,
    ).where(
        SlotBooking.college_id == college_id,
        SlotBooking.status == BookingStatus.APPROVED,
    )
    if target_date:
        query = query.where(SlotBooking.target_date == target_date)
    result = await db.execute(query)
    rows = result.all()
    fac_set = {(r.day, r.period, r.faculty_id) for r in rows}
    room_set = {(r.day, r.period, r.room_id) for r in rows}
    return fac_set, room_set


async def _get_date_booking_details(college_id: str, target_date: str, db: AsyncSession):
    """Return detailed booking info for a specific date (faculty_id → booking_type mapping)."""
    result = await db.execute(
        select(
            SlotBooking.day, SlotBooking.period,
            SlotBooking.faculty_id, SlotBooking.room_id,
            SlotBooking.booking_type,
        ).where(
            SlotBooking.college_id == college_id,
            SlotBooking.status == BookingStatus.APPROVED,
            SlotBooking.target_date == target_date,
        )
    )
    rows = result.all()
    # faculty: {(day, period, faculty_id): booking_type}
    fac_map: dict[tuple, str] = {}
    room_set: set[tuple] = set()
    for r in rows:
        fac_map[(r.day, r.period, r.faculty_id)] = r.booking_type.value if hasattr(r.booking_type, 'value') else r.booking_type
        room_set.add((r.day, r.period, r.room_id))
    return fac_map, room_set


async def _get_student_busy_slots(timetable_id: str, db: AsyncSession):
    """Return set of (day, period) where students of this timetable already have a class.
    Students are identified by the timetable's dept+semester.
    For regular (non-batch) entries, the entire slot is busy.
    For batch entries, only that batch is busy — but we mark the whole slot as busy
    to be safe for rescheduling regular lectures.
    """
    result = await db.execute(
        select(TimetableEntry.day, TimetableEntry.period)
        .where(
            TimetableEntry.timetable_id == timetable_id,
            TimetableEntry.entry_type == EntryType.REGULAR,
            TimetableEntry.batch.is_(None),  # only non-batch (whole-class) entries
        )
    )
    return {(r.day, r.period) for r in result.all()}


async def _build_booking_response(booking: SlotBooking, db: AsyncSession) -> dict:
    fac = await db.get(Faculty, booking.faculty_id)
    subj = await db.get(Subject, booking.subject_id)
    room = await db.get(Room, booking.room_id)
    req_user = await db.get(User, booking.requested_by)
    return {
        "booking_id": booking.booking_id,
        "booking_type": booking.booking_type.value,
        "status": booking.status.value,
        "faculty_name": fac.name if fac else "Unknown",
        "subject_name": subj.name if subj else "Unknown",
        "day": booking.day,
        "period": booking.period,
        "room_name": room.name if room else "Unknown",
        "target_date": booking.target_date,
        "reason": booking.reason,
        "requested_by_name": req_user.full_name if req_user else "Unknown",
        "created_at": booking.created_at,
    }


# ── Free Slot Discovery ──────────────────────────────────────

@router.get("/free-slots/{timetable_id}", response_model=list[FreeSlotResponse])
async def get_free_slots_for_faculty(
    timetable_id: str,
    faculty_id: str,
    day: str | None = None,
    check_students: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all free slots for a specific faculty member.
    A slot is free if:
      1. The faculty has no global booking AND no approved extra booking there.
      2. (when check_students=True) The students of this timetable have no class there.
    """
    tt = await _get_published_timetable(timetable_id, current_user, db)
    slots = await _get_time_slots(current_user.college_id, db)
    booked_fac = await _get_booked_faculty_slots(current_user.college_id, db)
    extra_fac, _ = await _get_approved_booking_slots(current_user.college_id, db)
    student_busy = await _get_student_busy_slots(timetable_id, db) if check_students else set()

    days = [day] if day else ALL_DAYS
    free: list[FreeSlotResponse] = []
    for d in days:
        for s in slots:
            if s.slot_type.value == "break":
                continue
            fac_key = (d, s.slot_order, faculty_id)
            student_key = (d, s.slot_order)
            if fac_key not in booked_fac and fac_key not in extra_fac and student_key not in student_busy:
                free.append(FreeSlotResponse(
                    day=d, period=s.slot_order,
                    slot_label=s.label, start_time=s.start_time, end_time=s.end_time,
                ))
    return free


@router.get("/reschedule-options/{timetable_id}", response_model=list[FreeSlotWithRoomsResponse])
async def get_reschedule_options(
    timetable_id: str,
    entry_id: str,
    target_date: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Given a timetable entry to reschedule, return all slots where BOTH the faculty
    AND students are free, with available rooms at each slot.
    If target_date is provided, also checks date-specific approved bookings.
    """
    entry = await db.get(TimetableEntry, entry_id)
    if not entry:
        raise HTTPException(404, "Entry not found")

    tt = await _get_published_timetable(timetable_id, current_user, db)
    college_id = current_user.college_id

    slots = await _get_time_slots(college_id, db)
    booked_fac = await _get_booked_faculty_slots(college_id, db)
    booked_rooms = await _get_booked_room_slots(college_id, db)
    extra_fac, extra_rooms = await _get_approved_booking_slots(college_id, db)
    student_busy = await _get_student_busy_slots(timetable_id, db)

    # Date-specific bookings
    date_fac_set: set = set()
    date_room_set: set = set()
    filter_day: str | None = None
    if target_date:
        _, date_room_set = await _get_date_booking_details(college_id, target_date, db)
        date_fac_map, _ = await _get_date_booking_details(college_id, target_date, db)
        date_fac_set = set(date_fac_map.keys())
        try:
            filter_day = date_type.fromisoformat(target_date).strftime("%A")
        except ValueError:
            pass

    # Get all rooms
    room_result = await db.execute(
        select(Room).where(Room.college_id == college_id)
    )
    all_rooms = room_result.scalars().all()

    results: list[FreeSlotWithRoomsResponse] = []
    days = [filter_day] if filter_day else ALL_DAYS
    for d in days:
        for s in slots:
            if s.slot_type.value == "break":
                continue
            period = s.slot_order
            fac_key = (d, period, entry.faculty_id)
            student_key = (d, period)

            # Skip if faculty busy or students busy
            if fac_key in booked_fac or fac_key in extra_fac or fac_key in date_fac_set:
                continue
            if student_key in student_busy:
                continue

            # Find free rooms at this slot
            free_rooms = []
            for r in all_rooms:
                room_key = (d, period, r.room_id)
                if room_key not in booked_rooms and room_key not in extra_rooms and room_key not in date_room_set:
                    free_rooms.append(FreeRoomResponse(
                        room_id=r.room_id, room_name=r.name,
                        room_type=r.room_type.value, capacity=r.capacity,
                    ))

            if free_rooms:
                results.append(FreeSlotWithRoomsResponse(
                    day=d, period=period,
                    slot_label=s.label, start_time=s.start_time, end_time=s.end_time,
                    free_rooms=free_rooms,
                ))

    return results


@router.get("/date-check", response_model=DateCheckResponse)
async def check_date_availability(
    date: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Check room and faculty availability for every time slot on a specific date.
    Considers both the regular timetable (GlobalBooking) AND approved SlotBookings
    that target this specific date.

    `date` format: YYYY-MM-DD (e.g. "2026-03-10")
    """
    try:
        target = date_type.fromisoformat(date)
    except ValueError:
        raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD")

    day_name = target.strftime("%A")  # e.g. "Monday"
    if day_name == "Sunday":
        raise HTTPException(400, "Sunday is not a working day")

    college_id = current_user.college_id
    dept_id = current_user.dept_id

    slots = await _get_time_slots(college_id, db)
    booked_fac = await _get_booked_faculty_slots(college_id, db)
    booked_rooms = await _get_booked_room_slots(college_id, db)
    date_fac_map, date_room_set = await _get_date_booking_details(college_id, date, db)

    # All rooms
    room_result = await db.execute(select(Room).where(Room.college_id == college_id))
    all_rooms = room_result.scalars().all()

    # All faculty in this department
    fac_query = select(Faculty)
    if dept_id:
        fac_query = fac_query.where(Faculty.dept_id == dept_id)
    fac_result = await db.execute(fac_query)
    all_faculty = fac_result.scalars().all()

    # Faculty load map
    load_result = await db.execute(
        select(GlobalBooking.faculty_id, sqlfunc.count(GlobalBooking.booking_id))
        .where(GlobalBooking.college_id == college_id)
        .group_by(GlobalBooking.faculty_id)
    )
    load_map = {r[0]: r[1] for r in load_result.all()}

    slot_results: list[DateSlotCheckResponse] = []
    for s in slots:
        if s.slot_type.value == "break":
            continue
        period = s.slot_order

        free_rooms_list = []
        busy_rooms_list = []
        for r in all_rooms:
            room_key = (day_name, period, r.room_id)
            room_info = FreeRoomResponse(
                room_id=r.room_id, room_name=r.name,
                room_type=r.room_type.value, capacity=r.capacity,
            )
            if room_key in booked_rooms or room_key in date_room_set:
                busy_rooms_list.append(room_info)
            else:
                free_rooms_list.append(room_info)

        free_faculty_list = []
        busy_faculty_list = []
        for f in all_faculty:
            fac_key = (day_name, period, f.faculty_id)
            if fac_key in booked_fac:
                busy_faculty_list.append(BusyFacultyResponse(
                    faculty_id=f.faculty_id, name=f.name, reason="timetable",
                ))
            elif fac_key in date_fac_map:
                busy_faculty_list.append(BusyFacultyResponse(
                    faculty_id=f.faculty_id, name=f.name,
                    reason=date_fac_map[fac_key],
                ))
            else:
                free_faculty_list.append(FreeFacultyResponse(
                    faculty_id=f.faculty_id, name=f.name,
                    expertise=f.expertise or [],
                    current_load=load_map.get(f.faculty_id, 0),
                    max_weekly_load=f.max_weekly_load,
                ))

        slot_results.append(DateSlotCheckResponse(
            period=period,
            slot_label=s.label,
            start_time=s.start_time,
            end_time=s.end_time,
            free_rooms=free_rooms_list,
            busy_rooms=busy_rooms_list,
            free_faculty=free_faculty_list,
            busy_faculty=busy_faculty_list,
        ))

    return DateCheckResponse(date=date, day_of_week=day_name, slots=slot_results)


@router.get("/free-rooms/{timetable_id}", response_model=list[FreeRoomResponse])
async def get_free_rooms(
    timetable_id: str,
    day: str,
    period: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all rooms free at a specific day+period.
    Checks both global_bookings and approved slot_bookings.
    """
    tt = await _get_published_timetable(timetable_id, current_user, db)
    booked_rooms = await _get_booked_room_slots(current_user.college_id, db)
    _, extra_rooms = await _get_approved_booking_slots(current_user.college_id, db)

    # Get all rooms for this college
    result = await db.execute(
        select(Room).where(Room.college_id == current_user.college_id)
    )
    all_rooms = result.scalars().all()

    free: list[FreeRoomResponse] = []
    for r in all_rooms:
        key = (day, period, r.room_id)
        if key not in booked_rooms and key not in extra_rooms:
            free.append(FreeRoomResponse(
                room_id=r.room_id, room_name=r.name,
                room_type=r.room_type.value, capacity=r.capacity,
            ))
    return free


@router.get("/free-faculty/{timetable_id}", response_model=list[FreeFacultyResponse])
async def get_free_faculty(
    timetable_id: str,
    day: str,
    period: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all faculty free at a specific day+period within the user's department.
    """
    tt = await _get_published_timetable(timetable_id, current_user, db)
    booked_fac = await _get_booked_faculty_slots(current_user.college_id, db)
    extra_fac, _ = await _get_approved_booking_slots(current_user.college_id, db)

    dept_id = current_user.dept_id or tt.dept_id
    result = await db.execute(
        select(Faculty).where(Faculty.dept_id == dept_id)
    )
    all_faculty = result.scalars().all()

    # Count current load per faculty from global_bookings
    load_result = await db.execute(
        select(GlobalBooking.faculty_id, sqlfunc.count(GlobalBooking.booking_id))
        .where(GlobalBooking.college_id == current_user.college_id)
        .group_by(GlobalBooking.faculty_id)
    )
    load_map = {r[0]: r[1] for r in load_result.all()}

    free: list[FreeFacultyResponse] = []
    for f in all_faculty:
        key = (day, period, f.faculty_id)
        if key not in booked_fac and key not in extra_fac:
            free.append(FreeFacultyResponse(
                faculty_id=f.faculty_id, name=f.name,
                expertise=f.expertise or [],
                current_load=load_map.get(f.faculty_id, 0),
                max_weekly_load=f.max_weekly_load,
            ))
    return free


# ── Reschedule ────────────────────────────────────────────────

@router.post("/reschedule", response_model=SlotBookingResponse)
async def create_reschedule(
    req: RescheduleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Reschedule an existing lecture to a new slot.
    Faculty can reschedule their own lectures; HOD can reschedule any.
    """
    entry = await db.get(TimetableEntry, req.original_entry_id)
    if not entry:
        raise HTTPException(404, "Original timetable entry not found")

    # Permission: faculty can only reschedule own entries
    if current_user.role == UserRole.FACULTY:
        fac = await db.execute(
            select(Faculty).where(Faculty.user_id == current_user.user_id)
        )
        my_fac = fac.scalar_one_or_none()
        if not my_fac or my_fac.faculty_id != entry.faculty_id:
            raise HTTPException(403, "You can only reschedule your own lectures")

    tt = await db.get(Timetable, entry.timetable_id)
    if not tt:
        raise HTTPException(404, "Timetable not found")

    college_id = current_user.college_id
    dept_id = current_user.dept_id or tt.dept_id

    # Verify new slot is free for the faculty
    booked_fac = await _get_booked_faculty_slots(college_id, db)
    extra_fac, _ = await _get_approved_booking_slots(college_id, db)
    fac_key = (req.new_day, req.new_period, entry.faculty_id)
    if fac_key in booked_fac or fac_key in extra_fac:
        raise HTTPException(409, "Faculty is not free at the requested slot")

    # Verify new room is free
    booked_rooms = await _get_booked_room_slots(college_id, db)
    _, extra_rooms = await _get_approved_booking_slots(college_id, db)
    room_key = (req.new_day, req.new_period, req.new_room_id)
    if room_key in booked_rooms or room_key in extra_rooms:
        raise HTTPException(409, "Room is not free at the requested slot")

    booking = SlotBooking(
        booking_id=str(uuid.uuid4()),
        college_id=college_id,
        dept_id=dept_id,
        booking_type=BookingType.RESCHEDULE,
        status=BookingStatus.PENDING if current_user.role == UserRole.FACULTY else BookingStatus.APPROVED,
        faculty_id=entry.faculty_id,
        day=req.new_day,
        period=req.new_period,
        room_id=req.new_room_id,
        subject_id=entry.subject_id,
        original_entry_id=req.original_entry_id,
        target_date=req.target_date,
        reason=req.reason,
        requested_by=current_user.user_id,
        approved_by=current_user.user_id if current_user.role != UserRole.FACULTY else None,
    )
    db.add(booking)
    await db.commit()
    await db.refresh(booking)
    return await _build_booking_response(booking, db)


# ── Extra Lecture ─────────────────────────────────────────────

@router.post("/extra-lecture", response_model=SlotBookingResponse)
async def create_extra_lecture(
    req: ExtraLectureRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Book an extra lecture in a free slot.
    Faculty books for themselves; HOD can book for any faculty (faculty_id in query).
    Once approved, the slot is locked — no other faculty can claim it.
    """
    college_id = current_user.college_id
    dept_id = current_user.dept_id

    # Determine which faculty is teaching
    if current_user.role == UserRole.FACULTY:
        fac_result = await db.execute(
            select(Faculty).where(Faculty.user_id == current_user.user_id)
        )
        my_fac = fac_result.scalar_one_or_none()
        if not my_fac:
            raise HTTPException(404, "Faculty profile not found")
        faculty_id = my_fac.faculty_id
    else:
        # HOD must specify; for simplicity, take first faculty teaching this subject
        raise HTTPException(400, "HOD must use /extra-lecture-assign endpoint")

    # Verify slot is free for faculty
    booked_fac = await _get_booked_faculty_slots(college_id, db)
    extra_fac, _ = await _get_approved_booking_slots(college_id, db)
    if (req.day, req.period, faculty_id) in booked_fac or (req.day, req.period, faculty_id) in extra_fac:
        raise HTTPException(409, "You are not free at the requested slot")

    # Verify room is free
    booked_rooms = await _get_booked_room_slots(college_id, db)
    _, extra_rooms = await _get_approved_booking_slots(college_id, db)
    if (req.day, req.period, req.room_id) in booked_rooms or (req.day, req.period, req.room_id) in extra_rooms:
        raise HTTPException(409, "Room is not free at the requested slot")

    booking = SlotBooking(
        booking_id=str(uuid.uuid4()),
        college_id=college_id,
        dept_id=dept_id,
        booking_type=BookingType.EXTRA_LECTURE,
        status=BookingStatus.PENDING,
        faculty_id=faculty_id,
        day=req.day,
        period=req.period,
        room_id=req.room_id,
        subject_id=req.subject_id,
        target_date=req.target_date,
        reason=req.reason,
        requested_by=current_user.user_id,
    )
    db.add(booking)
    await db.commit()
    await db.refresh(booking)
    return await _build_booking_response(booking, db)


@router.post("/extra-lecture-assign", response_model=SlotBookingResponse)
async def assign_extra_lecture(
    req: ExtraLectureRequest,
    faculty_id: str,
    current_user: User = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    HOD assigns an extra lecture to a specific faculty member.
    Auto-approved since HOD is assigning directly.
    """
    college_id = current_user.college_id
    dept_id = current_user.dept_id

    # Verify faculty exists
    fac = await db.get(Faculty, faculty_id)
    if not fac:
        raise HTTPException(404, "Faculty not found")

    # Verify slot is free for faculty
    booked_fac = await _get_booked_faculty_slots(college_id, db)
    extra_fac, _ = await _get_approved_booking_slots(college_id, db)
    if (req.day, req.period, faculty_id) in booked_fac or (req.day, req.period, faculty_id) in extra_fac:
        raise HTTPException(409, "Faculty is not free at the requested slot")

    # Verify room is free
    booked_rooms = await _get_booked_room_slots(college_id, db)
    _, extra_rooms = await _get_approved_booking_slots(college_id, db)
    if (req.day, req.period, req.room_id) in booked_rooms or (req.day, req.period, req.room_id) in extra_rooms:
        raise HTTPException(409, "Room is not free at the requested slot")

    booking = SlotBooking(
        booking_id=str(uuid.uuid4()),
        college_id=college_id,
        dept_id=dept_id,
        booking_type=BookingType.EXTRA_LECTURE,
        status=BookingStatus.APPROVED,
        faculty_id=faculty_id,
        day=req.day,
        period=req.period,
        room_id=req.room_id,
        subject_id=req.subject_id,
        target_date=req.target_date,
        reason=req.reason,
        requested_by=current_user.user_id,
        approved_by=current_user.user_id,
    )
    db.add(booking)
    await db.commit()
    await db.refresh(booking)
    return await _build_booking_response(booking, db)


# ── Proxy Assignment ──────────────────────────────────────────

@router.post("/proxy", response_model=SlotBookingResponse)
async def create_proxy(
    req: ProxyRequest,
    current_user: User = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Assign a proxy faculty to cover a class when the original is unavailable.
    Only HOD/admin can assign proxies. Auto-approved.
    """
    entry = await db.get(TimetableEntry, req.original_entry_id)
    if not entry:
        raise HTTPException(404, "Timetable entry not found")

    tt = await db.get(Timetable, entry.timetable_id)
    if not tt:
        raise HTTPException(404, "Timetable not found")

    college_id = current_user.college_id
    dept_id = current_user.dept_id or tt.dept_id

    # Verify proxy faculty is free at that slot
    booked_fac = await _get_booked_faculty_slots(college_id, db)
    extra_fac, _ = await _get_approved_booking_slots(college_id, db)
    if (entry.day, entry.period, req.proxy_faculty_id) in booked_fac or \
       (entry.day, entry.period, req.proxy_faculty_id) in extra_fac:
        raise HTTPException(409, "Proxy faculty is not free at that slot")

    booking = SlotBooking(
        booking_id=str(uuid.uuid4()),
        college_id=college_id,
        dept_id=dept_id,
        booking_type=BookingType.PROXY,
        status=BookingStatus.APPROVED,
        faculty_id=req.proxy_faculty_id,
        day=entry.day,
        period=entry.period,
        room_id=entry.room_id,
        subject_id=entry.subject_id,
        original_entry_id=req.original_entry_id,
        absent_faculty_id=entry.faculty_id,
        target_date=req.target_date,
        reason=req.reason,
        requested_by=current_user.user_id,
        approved_by=current_user.user_id,
    )
    db.add(booking)
    await db.commit()
    await db.refresh(booking)
    return await _build_booking_response(booking, db)


# ── Approval / Rejection (HOD) ───────────────────────────────

@router.post("/approve/{booking_id}", response_model=SlotBookingResponse)
async def approve_booking(
    booking_id: str,
    current_user: User = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
):
    booking = await db.get(SlotBooking, booking_id)
    if not booking:
        raise HTTPException(404, "Booking not found")
    if booking.status != BookingStatus.PENDING:
        raise HTTPException(400, f"Booking is already {booking.status.value}")

    # Re-check slot availability before approving
    college_id = current_user.college_id
    booked_fac = await _get_booked_faculty_slots(college_id, db)
    extra_fac, extra_rooms = await _get_approved_booking_slots(college_id, db)
    booked_rooms = await _get_booked_room_slots(college_id, db)

    fac_key = (booking.day, booking.period, booking.faculty_id)
    room_key = (booking.day, booking.period, booking.room_id)

    if fac_key in booked_fac or fac_key in extra_fac:
        raise HTTPException(409, "Faculty slot is no longer free — cannot approve")
    if room_key in booked_rooms or room_key in extra_rooms:
        raise HTTPException(409, "Room slot is no longer free — cannot approve")

    booking.status = BookingStatus.APPROVED
    booking.approved_by = current_user.user_id
    booking.resolved_at = datetime.now(timezone.utc)
    db.add(booking)
    await db.commit()
    await db.refresh(booking)
    return await _build_booking_response(booking, db)


@router.post("/reject/{booking_id}", response_model=SlotBookingResponse)
async def reject_booking(
    booking_id: str,
    current_user: User = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
):
    booking = await db.get(SlotBooking, booking_id)
    if not booking:
        raise HTTPException(404, "Booking not found")
    if booking.status != BookingStatus.PENDING:
        raise HTTPException(400, f"Booking is already {booking.status.value}")

    booking.status = BookingStatus.REJECTED
    booking.resolved_at = datetime.now(timezone.utc)
    db.add(booking)
    await db.commit()
    await db.refresh(booking)
    return await _build_booking_response(booking, db)


@router.post("/cancel/{booking_id}", response_model=SlotBookingResponse)
async def cancel_booking(
    booking_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a booking. Faculty can cancel own; HOD can cancel any."""
    booking = await db.get(SlotBooking, booking_id)
    if not booking:
        raise HTTPException(404, "Booking not found")
    if booking.status not in (BookingStatus.PENDING, BookingStatus.APPROVED):
        raise HTTPException(400, f"Cannot cancel — status is {booking.status.value}")

    if current_user.role == UserRole.FACULTY and booking.requested_by != current_user.user_id:
        raise HTTPException(403, "You can only cancel your own bookings")

    booking.status = BookingStatus.CANCELLED
    booking.resolved_at = datetime.now(timezone.utc)
    db.add(booking)
    await db.commit()
    await db.refresh(booking)
    return await _build_booking_response(booking, db)


# ── Listing ───────────────────────────────────────────────────

@router.get("/bookings", response_model=list[SlotBookingResponse])
async def list_bookings(
    booking_type: str | None = None,
    status: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List bookings. HOD sees all department bookings.
    Faculty sees only their own.
    """
    query = select(SlotBooking).where(SlotBooking.college_id == current_user.college_id)

    if current_user.role == UserRole.FACULTY:
        # Faculty sees own bookings
        fac_result = await db.execute(
            select(Faculty.faculty_id).where(Faculty.user_id == current_user.user_id)
        )
        my_fac_id = fac_result.scalar_one_or_none()
        if my_fac_id:
            query = query.where(
                or_(
                    SlotBooking.faculty_id == my_fac_id,
                    SlotBooking.requested_by == current_user.user_id,
                )
            )
    elif current_user.dept_id:
        query = query.where(SlotBooking.dept_id == current_user.dept_id)

    if booking_type:
        query = query.where(SlotBooking.booking_type == booking_type)
    if status:
        query = query.where(SlotBooking.status == status)

    query = query.order_by(SlotBooking.created_at.desc())
    result = await db.execute(query)
    bookings = result.scalars().all()

    return [await _build_booking_response(b, db) for b in bookings]
