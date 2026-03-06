# routers/room.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from dependencies import get_db, get_current_user, require_any_admin
from models.user import User
from models.room import Room, RoomType
from schemas.room import RoomCreate, RoomUpdate, RoomResponse

router = APIRouter(prefix="/rooms", tags=["Rooms"])


@router.get("", response_model=list[RoomResponse])
async def list_rooms(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all rooms in the user's college. All roles can view."""
    result = await db.execute(
        select(Room).where(Room.college_id == current_user.college_id)
    )
    rooms = result.scalars().all()
    return [RoomResponse.model_validate(r) for r in rooms]


@router.post("", response_model=RoomResponse)
async def create_room(
    request: RoomCreate,
    current_user: User = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new room. Super admin only."""
    room = Room(
        college_id=current_user.college_id,
        name=request.name,
        capacity=request.capacity,
        room_type=RoomType(request.room_type),
        has_projector=request.has_projector,
        has_computers=request.has_computers,
        has_ac=request.has_ac,
    )
    db.add(room)
    await db.commit()
    await db.refresh(room)
    return RoomResponse.model_validate(room)


@router.get("/{room_id}", response_model=RoomResponse)
async def get_room(
    room_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get room details."""
    room = await db.get(Room, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if room.college_id != current_user.college_id:
        raise HTTPException(status_code=403, detail="Cannot access rooms from other colleges")
    return RoomResponse.model_validate(room)


@router.put("/{room_id}", response_model=RoomResponse)
async def update_room(
    room_id: str,
    request: RoomUpdate,
    current_user: User = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update a room. Super admin only."""
    room = await db.get(Room, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if room.college_id != current_user.college_id:
        raise HTTPException(status_code=403, detail="Cannot modify rooms from other colleges")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "room_type" and value is not None:
            value = RoomType(value)
        setattr(room, field, value)

    db.add(room)
    await db.commit()
    await db.refresh(room)
    return RoomResponse.model_validate(room)


@router.delete("/{room_id}")
async def delete_room(
    room_id: str,
    current_user: User = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a room. Super admin only."""
    room = await db.get(Room, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if room.college_id != current_user.college_id:
        raise HTTPException(status_code=403, detail="Cannot delete rooms from other colleges")

    await db.delete(room)
    await db.commit()
    return {"message": "Room deleted"}
