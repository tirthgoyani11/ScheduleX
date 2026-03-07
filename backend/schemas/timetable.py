# schemas/timetable.py
from pydantic import BaseModel, Field
from typing import Optional

VALID_DAYS = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"}


class TimetableCreateRequest(BaseModel):
    semester: int = Field(..., ge=1, le=8, description="Semester number 1–8")
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$", description="e.g. 2025-26")
    faculty_subject_map: dict[str, list[str]] = Field(
        ..., description="Map of faculty_id → list of subject_ids assigned to them"
    )
    working_days: list[str] = Field(
        default=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        description="Days to schedule classes on",
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
    dept_id: str | None = None
    dept_name: str | None = None
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


class GenerateAllRequest(BaseModel):
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$", description="e.g. 2025-26")
    working_days: list[str] = Field(
        default=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        description="Days to schedule classes on",
    )
    time_limit_seconds: Optional[int] = Field(120, ge=30, le=600)


class SemesterResult(BaseModel):
    semester: int
    timetable_id: str | None = None
    status: str
    score: float | None = None
    entry_count: int = 0
    wall_time: float = 0
    error: str | None = None


class GenerateAllResponse(BaseModel):
    total: int
    succeeded: int
    failed: int
    results: list[SemesterResult]
