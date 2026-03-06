from pydantic import BaseModel, Field
from datetime import datetime


class BatchCreate(BaseModel):
    semester: int = Field(..., ge=1, le=8)
    name: str = Field(..., min_length=1, max_length=50)
    size: int = Field(30, ge=1, le=200)


class BatchResponse(BaseModel):
    batch_id: str
    dept_id: str
    semester: int
    name: str
    size: int
    created_at: datetime

    model_config = {"from_attributes": True}
