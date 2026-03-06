from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class FreeSlotQuery(BaseModel):
    day: Optional[str] = None  # filter by specific day
    timetable_id: str


class FreeSlotResponse(BaseModel):
    day: str
    period: int
    slot_label: str
    start_time: str
    end_time: str


class FreeSlotWithRoomsResponse(BaseModel):
    day: str
    period: int
    slot_label: str
    start_time: str
    end_time: str
    free_rooms: list["FreeRoomResponse"]


class FreeRoomResponse(BaseModel):
    room_id: str
    room_name: str
    room_type: str
    capacity: int


class FreeFacultyResponse(BaseModel):
    faculty_id: str
    name: str
    expertise: list[str]
    current_load: int
    max_weekly_load: int


class RescheduleRequest(BaseModel):
    original_entry_id: str = Field(..., description="Entry being rescheduled")
    new_day: str
    new_period: int
    new_room_id: str
    target_date: Optional[str] = None
    reason: Optional[str] = None


class ExtraLectureRequest(BaseModel):
    subject_id: str
    day: str
    period: int
    room_id: str
    target_date: Optional[str] = None
    reason: Optional[str] = None


class ProxyRequest(BaseModel):
    original_entry_id: str = Field(..., description="Entry needing proxy coverage")
    proxy_faculty_id: str = Field(..., description="Faculty covering the class")
    target_date: str = Field(..., description="Date of proxy, e.g. 2026-03-10")
    reason: Optional[str] = None


class SlotBookingResponse(BaseModel):
    booking_id: str
    booking_type: str
    status: str
    faculty_name: str
    subject_name: str
    day: str
    period: int
    room_name: str
    target_date: Optional[str] = None
    reason: Optional[str] = None
    requested_by_name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ApproveRejectRequest(BaseModel):
    booking_id: str
