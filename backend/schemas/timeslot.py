# schemas/timeslot.py
from pydantic import BaseModel, Field
import re


def _validate_time(v: str) -> str:
    if not re.match(r"^\d{2}:\d{2}$", v):
        raise ValueError("Time must be in HH:MM format")
    return v


class TimeSlotCreate(BaseModel):
    label: str = Field(..., min_length=1, max_length=50)
    start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    slot_type: str = Field(..., description="lecture | lab | break")
    slot_order: int = Field(..., ge=1, le=20)


class TimeSlotUpdate(BaseModel):
    label: str | None = Field(None, min_length=1, max_length=50)
    start_time: str | None = Field(None, pattern=r"^\d{2}:\d{2}$")
    end_time: str | None = Field(None, pattern=r"^\d{2}:\d{2}$")
    slot_type: str | None = None
    slot_order: int | None = Field(None, ge=1, le=20)


class TimeSlotResponse(BaseModel):
    slot_id: str
    college_id: str
    slot_order: int
    label: str
    start_time: str
    end_time: str
    slot_type: str

    model_config = {"from_attributes": True}


class TimeSlotReorder(BaseModel):
    """List of slot_id in the desired order."""
    slot_ids: list[str] = Field(..., min_length=1, max_length=20)
