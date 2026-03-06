import uuid
import enum
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, Integer, Enum, Float, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class SubstitutionStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


class Substitution(Base):
    __tablename__ = "substitutions"

    substitution_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    original_entry_id: Mapped[str] = mapped_column(
        ForeignKey("timetable_entries.entry_id"), nullable=False
    )
    original_faculty_id: Mapped[str] = mapped_column(
        ForeignKey("faculty.faculty_id"), nullable=False
    )
    substitute_faculty_id: Mapped[str | None] = mapped_column(
        ForeignKey("faculty.faculty_id"), nullable=True
    )
    absence_date: Mapped[str] = mapped_column(String(20), nullable=False)     # "2026-03-05"
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[SubstitutionStatus] = mapped_column(
        Enum(SubstitutionStatus), default=SubstitutionStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class SubstitutionRequest(Base):
    """Tracks the multi-candidate escalation chain."""
    __tablename__ = "substitution_requests"

    request_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    substitution_id: Mapped[str] = mapped_column(
        ForeignKey("substitutions.substitution_id"), nullable=False
    )
    candidate_faculty_id: Mapped[str] = mapped_column(
        ForeignKey("faculty.faculty_id"), nullable=False
    )
    escalation_level: Mapped[int] = mapped_column(Integer, default=1)     # 1, 2, 3
    ranking_score: Mapped[float] = mapped_column(Float, nullable=False)
    notification_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    response_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[SubstitutionStatus] = mapped_column(
        Enum(SubstitutionStatus), default=SubstitutionStatus.PENDING
    )
    response_raw: Mapped[str | None] = mapped_column(Text, nullable=True)  # Raw WhatsApp reply
