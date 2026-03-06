import uuid
import enum
from datetime import datetime, date
from sqlalchemy import String, ForeignKey, DateTime, Date, Integer, Enum, Float, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class ExamTimetableStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class InvigilatorRole(str, enum.Enum):
    CHIEF = "chief"
    FLYING_SQUAD = "flying_squad"


class ExamTimetable(Base):
    __tablename__ = "exam_timetables"

    exam_tt_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    dept_id: Mapped[str] = mapped_column(
        ForeignKey("departments.dept_id"), nullable=False
    )
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    academic_year: Mapped[str] = mapped_column(String(20), nullable=False)
    exam_period_start: Mapped[date] = mapped_column(Date, nullable=False)
    exam_period_end: Mapped[date] = mapped_column(Date, nullable=False)
    buffer_days: Mapped[int] = mapped_column(Integer, default=1)         # Min days between papers
    status: Mapped[ExamTimetableStatus] = mapped_column(
        Enum(ExamTimetableStatus), default=ExamTimetableStatus.DRAFT
    )
    optimization_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    entries: Mapped[list["ExamEntry"]] = relationship(
        back_populates="exam_timetable", cascade="all, delete-orphan"
    )


class ExamEntry(Base):
    __tablename__ = "exam_entries"

    entry_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    exam_tt_id: Mapped[str] = mapped_column(
        ForeignKey("exam_timetables.exam_tt_id"), nullable=False
    )
    subject_id: Mapped[str] = mapped_column(
        ForeignKey("subjects.subject_id"), nullable=False
    )
    exam_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[str] = mapped_column(String(10), nullable=False)    # "09:00"
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)  # 180 | 120 | 30
    venue_id: Mapped[str] = mapped_column(
        ForeignKey("venues.venue_id"), nullable=False
    )
    enrolled_count: Mapped[int] = mapped_column(Integer, nullable=False)

    exam_timetable: Mapped["ExamTimetable"] = relationship(back_populates="entries")
    invigilator_assignments: Mapped[list["InvigilatorAssignment"]] = relationship(
        back_populates="exam_entry"
    )


class InvigilatorAssignment(Base):
    __tablename__ = "invigilator_assignments"

    assignment_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    entry_id: Mapped[str] = mapped_column(
        ForeignKey("exam_entries.entry_id"), nullable=False
    )
    faculty_id: Mapped[str] = mapped_column(
        ForeignKey("faculty.faculty_id"), nullable=False
    )
    role: Mapped[InvigilatorRole] = mapped_column(Enum(InvigilatorRole), nullable=False)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)

    exam_entry: Mapped["ExamEntry"] = relationship(back_populates="invigilator_assignments")


class StudentExamEnrolment(Base):
    __tablename__ = "student_exam_enrolments"

    enrolment_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    student_id: Mapped[str] = mapped_column(String(36), nullable=False)       # External student ID
    subject_id: Mapped[str] = mapped_column(
        ForeignKey("subjects.subject_id"), nullable=False
    )
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    is_backlog: Mapped[bool] = mapped_column(Boolean, default=False)
    college_id: Mapped[str] = mapped_column(
        ForeignKey("colleges.college_id"), nullable=False
    )
