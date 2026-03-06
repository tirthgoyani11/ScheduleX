# schemas/nlq.py
from pydantic import BaseModel, Field
from typing import Any


class NLQueryRequest(BaseModel):
    question: str = Field(..., min_length=5, description="Natural language question about the timetable")


class NLQueryResponse(BaseModel):
    success: bool
    question: str | None = None
    sql: str | None = None
    results: list[dict[str, Any]] = []
    row_count: int = 0
    visualisation: str | None = None
    error: str | None = None
