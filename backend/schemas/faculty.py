# schemas/faculty.py
from pydantic import BaseModel, Field
from datetime import date, datetime


class FacultyCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    employee_id: str | None = None
    expertise: list[str] = Field(default_factory=list, description='e.g. ["CN", "OS", "DBMS"]')
    max_weekly_load: int = Field(18, ge=1, le=40)
    preferred_time: str | None = Field(None, description="morning | afternoon | any")
    user_id: str | None = None
    dept_id: str | None = None


class FacultyUpdate(BaseModel):
    name: str | None = None
    employee_id: str | None = None
    expertise: list[str] | None = None
    max_weekly_load: int | None = Field(None, ge=1, le=40)
    preferred_time: str | None = None


class FacultyResponse(BaseModel):
    faculty_id: str
    dept_id: str
    name: str
    employee_id: str | None
    expertise: list[str]
    max_weekly_load: int
    preferred_time: str | None
    substitution_count: int
    last_substitution_date: date | None
    created_at: datetime

    model_config = {"from_attributes": True}


class GeneralBlockCreate(BaseModel):
    day: str = Field(..., description="Monday–Saturday")
    period: int = Field(..., ge=1, le=8)
    reason: str | None = None


class GeneralBlockResponse(BaseModel):
    block_id: str
    faculty_id: str
    day: str
    period: int
    reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
