# schemas/room.py
from pydantic import BaseModel, Field


class RoomCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    capacity: int = Field(..., ge=1, le=1000)
    room_type: str = Field(..., description="classroom | lab | seminar")
    has_projector: bool = False
    has_computers: bool = False
    has_ac: bool = False


class RoomUpdate(BaseModel):
    name: str | None = None
    capacity: int | None = Field(None, ge=1, le=1000)
    room_type: str | None = None
    has_projector: bool | None = None
    has_computers: bool | None = None
    has_ac: bool | None = None


class RoomResponse(BaseModel):
    room_id: str
    college_id: str
    name: str
    capacity: int
    room_type: str
    has_projector: bool
    has_computers: bool
    has_ac: bool

    model_config = {"from_attributes": True}


class VenueCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    capacity: int = Field(..., ge=1, le=2000)
    venue_type: str = Field(..., description="hall | lab | outdoor")


class VenueResponse(BaseModel):
    venue_id: str
    college_id: str
    name: str
    capacity: int
    venue_type: str

    model_config = {"from_attributes": True}
