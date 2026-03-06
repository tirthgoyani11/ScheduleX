# schemas/timetable.py
from pydantic import BaseModel, Field
from typing import Optional


class TimetableCreateRequest(BaseModel):
    semester: int = Field(..., ge=1, le=8, description="Semester number 1–8")
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$", description="e.g. 2025-26")
    faculty_subject_map: dict[str, list[str]] = Field(
        ..., description="Map of faculty_id → list of subject_ids assigned to them"
    )
    time_limit_seconds: Optional[int] = Field(120, ge=30, le=600)


class TimetableEntryResponse(BaseModel):
    entry_id: str
    day: str
    period: int
    subject_name: str
    faculty_name: str
    room_name: str
    entry_type: str
    batch: str | None = None


class TimetableResponse(BaseModel):
    timetable_id: str
    semester: int
    academic_year: str
    status: str
    optimization_score: float | None
    entries: list[TimetableEntryResponse]
    created_at: str
    published_at: str | None


class TimetablePublishResponse(BaseModel):
    message: str
    timetable_id: str
