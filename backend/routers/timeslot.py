# routers/timeslot.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sa_func
from dependencies import get_db, get_current_user, require_any_admin
from models.user import User
from models.timeslot import TimeSlotConfig, SlotType
from schemas.timeslot import (
    TimeSlotCreate, TimeSlotUpdate, TimeSlotResponse, TimeSlotReorder,
)

router = APIRouter(prefix="/timeslots", tags=["Time Slots"])

# ── Default seed data ────────────────────────────────────────────────────────
_DEFAULT_SLOTS = [
    {"slot_order": 1, "label": "Period 1", "start_time": "09:00", "end_time": "10:00", "slot_type": SlotType.LECTURE},
    {"slot_order": 2, "label": "Period 2", "start_time": "10:00", "end_time": "11:00", "slot_type": SlotType.LECTURE},
    {"slot_order": 3, "label": "Period 3", "start_time": "11:00", "end_time": "12:00", "slot_type": SlotType.LECTURE},
    {"slot_order": 4, "label": "Period 4", "start_time": "12:00", "end_time": "13:00", "slot_type": SlotType.LECTURE},
    {"slot_order": 5, "label": "Lunch",    "start_time": "13:00", "end_time": "14:00", "slot_type": SlotType.BREAK},
    {"slot_order": 6, "label": "Period 5", "start_time": "14:00", "end_time": "15:00", "slot_type": SlotType.LECTURE},
    {"slot_order": 7, "label": "Lab 1",    "start_time": "15:00", "end_time": "17:00", "slot_type": SlotType.LAB},
    {"slot_order": 8, "label": "Lab 2",    "start_time": "17:00", "end_time": "19:00", "slot_type": SlotType.LAB},
]


@router.get("", response_model=list[TimeSlotResponse])
async def list_timeslots(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all time slots for the current user's college, sorted by slot_order."""
    result = await db.execute(
        select(TimeSlotConfig)
        .where(TimeSlotConfig.college_id == current_user.college_id)
        .order_by(TimeSlotConfig.slot_order)
    )
    slots = result.scalars().all()
    return [TimeSlotResponse.model_validate(s) for s in slots]


@router.post("", response_model=TimeSlotResponse, status_code=201)
async def create_timeslot(
    request: TimeSlotCreate,
    current_user: User = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new time slot."""
    slot = TimeSlotConfig(
        college_id=current_user.college_id,
        slot_order=request.slot_order,
        label=request.label,
        start_time=request.start_time,
        end_time=request.end_time,
        slot_type=SlotType(request.slot_type),
    )
    db.add(slot)
    await db.commit()
    await db.refresh(slot)
    return TimeSlotResponse.model_validate(slot)


@router.put("/{slot_id}", response_model=TimeSlotResponse)
async def update_timeslot(
    slot_id: str,
    request: TimeSlotUpdate,
    current_user: User = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing time slot."""
    slot = await db.get(TimeSlotConfig, slot_id)
    if not slot:
        raise HTTPException(status_code=404, detail="Time slot not found")
    if slot.college_id != current_user.college_id:
        raise HTTPException(status_code=403, detail="Cannot modify slots from other colleges")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "slot_type" and value is not None:
            value = SlotType(value)
        setattr(slot, field, value)

    db.add(slot)
    await db.commit()
    await db.refresh(slot)
    return TimeSlotResponse.model_validate(slot)


@router.delete("/{slot_id}")
async def delete_timeslot(
    slot_id: str,
    current_user: User = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a time slot."""
    slot = await db.get(TimeSlotConfig, slot_id)
    if not slot:
        raise HTTPException(status_code=404, detail="Time slot not found")
    if slot.college_id != current_user.college_id:
        raise HTTPException(status_code=403, detail="Cannot delete slots from other colleges")

    await db.delete(slot)
    await db.commit()
    return {"message": "Time slot deleted"}


@router.put("/reorder/bulk", response_model=list[TimeSlotResponse])
async def reorder_timeslots(
    request: TimeSlotReorder,
    current_user: User = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
):
    """Reorder time slots. Accepts ordered list of slot IDs."""
    result = await db.execute(
        select(TimeSlotConfig)
        .where(
            TimeSlotConfig.college_id == current_user.college_id,
            TimeSlotConfig.slot_id.in_(request.slot_ids),
        )
    )
    slots_by_id = {s.slot_id: s for s in result.scalars().all()}

    if len(slots_by_id) != len(request.slot_ids):
        raise HTTPException(status_code=400, detail="Some slot IDs not found")

    for idx, slot_id in enumerate(request.slot_ids, start=1):
        slots_by_id[slot_id].slot_order = idx
        db.add(slots_by_id[slot_id])

    await db.commit()

    # Return updated list
    result2 = await db.execute(
        select(TimeSlotConfig)
        .where(TimeSlotConfig.college_id == current_user.college_id)
        .order_by(TimeSlotConfig.slot_order)
    )
    return [TimeSlotResponse.model_validate(s) for s in result2.scalars().all()]


@router.post("/seed-defaults", response_model=list[TimeSlotResponse])
async def seed_default_timeslots(
    current_user: User = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
):
    """Seed the college with default time slots (only if none exist)."""
    count_result = await db.execute(
        select(sa_func.count())
        .select_from(TimeSlotConfig)
        .where(TimeSlotConfig.college_id == current_user.college_id)
    )
    existing_count = count_result.scalar()
    if existing_count and existing_count > 0:
        raise HTTPException(
            status_code=409,
            detail="Time slots already exist. Delete them first or manage individually.",
        )

    for slot_data in _DEFAULT_SLOTS:
        slot = TimeSlotConfig(college_id=current_user.college_id, **slot_data)
        db.add(slot)

    await db.commit()

    result = await db.execute(
        select(TimeSlotConfig)
        .where(TimeSlotConfig.college_id == current_user.college_id)
        .order_by(TimeSlotConfig.slot_order)
    )
    return [TimeSlotResponse.model_validate(s) for s in result.scalars().all()]
