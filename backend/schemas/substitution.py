# schemas/substitution.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class ReportAbsenceRequest(BaseModel):
    entry_id: str = Field(..., description="The timetable entry ID for the missed class")
    absence_date: str = Field(..., description="Date of absence, e.g. 2026-03-05")
    reason: str | None = None


class SubstitutionCandidateResponse(BaseModel):
    faculty_id: str
    name: str
    score: float
    expertise_match: float
    load_headroom_pct: float
    days_since_last_sub: int
    preferred_time: str | None


class SubstitutionResponse(BaseModel):
    substitution_id: str
    original_faculty_name: str
    substitute_faculty_name: str | None
    subject_name: str
    absence_date: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SubstitutionDetailResponse(BaseModel):
    """Extended substitution response used in history listing."""
    substitution_id: str
    original_faculty_name: str
    substitute_faculty_name: Optional[str] = None
    subject_name: str
    day: str
    period: int
    absence_date: str
    reason: Optional[str] = None
    status: str
    created_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SubstitutionRequestResponse(BaseModel):
    """Details of a single substitution request attempt."""
    request_id: str
    candidate_faculty_id: str
    candidate_name: str
    escalation_level: int
    ranking_score: float
    status: str
    notification_sent_at: Optional[datetime] = None
    response_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
