# schemas/college.py
from pydantic import BaseModel, Field
from datetime import datetime


class CollegeCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    affiliation: str | None = None
    city: str | None = None


class CollegeResponse(BaseModel):
    college_id: str
    name: str
    affiliation: str | None
    city: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    code: str = Field(..., min_length=2, max_length=20, description="e.g. CSE, IT, ME")


class DepartmentResponse(BaseModel):
    dept_id: str
    college_id: str
    name: str
    code: str
    created_at: datetime

    model_config = {"from_attributes": True}
