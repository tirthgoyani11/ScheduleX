import uuid
import enum
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, Integer, Float, Enum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class TimetableStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    DELETED = "deleted"


class EntryType(str, enum.Enum):
    REGULAR = "regular"
    SUBSTITUTION = "substitution"
    CANCELLED = "cancelled"


class Timetable(Base):
    __tablename__ = "timetables"

    timetable_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    dept_id: Mapped[str] = mapped_column(
        ForeignKey("departments.dept_id"), nullable=False
    )
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    academic_year: Mapped[str] = mapped_column(String(20), nullable=False)  # "2025-26"
    status: Mapped[TimetableStatus] = mapped_column(
        Enum(TimetableStatus), default=TimetableStatus.DRAFT
    )
    optimization_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    job_id: Mapped[str | None] = mapped_column(String(36), nullable=True)   # RQ job reference
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    department: Mapped["Department"] = relationship(back_populates="timetables")
    entries: Mapped[list["TimetableEntry"]] = relationship(
        back_populates="timetable", cascade="all, delete-orphan"
    )


class TimetableEntry(Base):
    __tablename__ = "timetable_entries"

    entry_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    timetable_id: Mapped[str] = mapped_column(
        ForeignKey("timetables.timetable_id"), nullable=False
    )
    day: Mapped[str] = mapped_column(String(10), nullable=False)
    period: Mapped[int] = mapped_column(Integer, nullable=False)
    subject_id: Mapped[str] = mapped_column(
        ForeignKey("subjects.subject_id"), nullable=False
    )
    faculty_id: Mapped[str] = mapped_column(
        ForeignKey("faculty.faculty_id"), nullable=False
    )
    room_id: Mapped[str] = mapped_column(
        ForeignKey("rooms_labs.room_id"), nullable=False
    )
    entry_type: Mapped[EntryType] = mapped_column(
        Enum(EntryType), default=EntryType.REGULAR
    )
    batch: Mapped[str | None] = mapped_column(String(20), nullable=True)    # "CE-3A", "CE-3B"

    timetable: Mapped["Timetable"] = relationship(back_populates="entries")
    faculty: Mapped["Faculty"] = relationship(back_populates="timetable_entries")
    subject: Mapped["Subject"] = relationship()
    room: Mapped["Room"] = relationship()
