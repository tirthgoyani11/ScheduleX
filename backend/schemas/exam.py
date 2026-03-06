# schemas/exam.py
from pydantic import BaseModel, Field
from datetime import date


class ExamTimetableCreate(BaseModel):
    semester: int = Field(..., ge=1, le=8)
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    exam_period_start: date
    exam_period_end: date
    buffer_days: int = Field(1, ge=0, le=7)


class ExamEntryResponse(BaseModel):
    entry_id: str
    subject_name: str
    exam_date: date
    start_time: str
    duration_minutes: int
    venue_name: str
    enrolled_count: int

    model_config = {"from_attributes": True}


class ExamTimetableResponse(BaseModel):
    exam_tt_id: str
    semester: int
    academic_year: str
    status: str
    optimization_score: float | None
    entries: list[ExamEntryResponse]

    model_config = {"from_attributes": True}
