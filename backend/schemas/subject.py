# schemas/subject.py
from pydantic import BaseModel, Field
from datetime import datetime


class SubjectCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    subject_code: str = Field(..., min_length=2, max_length=20)
    semester: int = Field(..., ge=1, le=8)
    credits: int = Field(3, ge=1, le=6)
    weekly_periods: int = Field(3, ge=1, le=10)
    lecture_hours: int = Field(0, ge=0, le=10)
    lab_hours: int = Field(0, ge=0, le=10)
    needs_lab: bool = False
    batch_size: int = Field(60, ge=1, le=500)
    batch: str | None = None


class SubjectUpdate(BaseModel):
    name: str | None = None
    subject_code: str | None = None
    semester: int | None = Field(None, ge=1, le=8)
    credits: int | None = Field(None, ge=1, le=6)
    weekly_periods: int | None = Field(None, ge=1, le=10)
    lecture_hours: int | None = Field(None, ge=0, le=10)
    lab_hours: int | None = Field(None, ge=0, le=10)
    needs_lab: bool | None = None
    batch_size: int | None = Field(None, ge=1, le=500)
    batch: str | None = None


class SubjectResponse(BaseModel):
    subject_id: str
    dept_id: str
    name: str
    subject_code: str
    semester: int
    credits: int
    weekly_periods: int
    lecture_hours: int
    lab_hours: int
    needs_lab: bool
    batch_size: int
    batch: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
