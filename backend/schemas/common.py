# schemas/common.py
from pydantic import BaseModel
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class JobResponse(BaseModel):
    job_id: str
    timetable_id: str | None = None
    status: str


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
    conflict_type: str | None = None
    suggestions: list[str] = []


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    has_next: bool
