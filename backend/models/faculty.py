import uuid
from datetime import datetime, date
from sqlalchemy import String, ForeignKey, DateTime, Integer, Date, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class Faculty(Base):
    __tablename__ = "faculty"

    faculty_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    dept_id: Mapped[str] = mapped_column(
        ForeignKey("departments.dept_id"), nullable=False
    )
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.user_id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    employee_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    expertise: Mapped[list] = mapped_column(JSON, default=list)   # ["CN", "OS", "DBMS"]
    max_weekly_load: Mapped[int] = mapped_column(Integer, default=18)  # Hours/week
    preferred_time: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # "morning" | "afternoon" | "any"
    # Substitution tracking
    substitution_count: Mapped[int] = mapped_column(Integer, default=0)
    last_substitution_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    department: Mapped["Department"] = relationship(back_populates="faculty")
    user: Mapped["User | None"] = relationship(back_populates="faculty_profile")
    timetable_entries: Mapped[list["TimetableEntry"]] = relationship(back_populates="faculty")
    general_blocks: Mapped[list["FacultyGeneralBlock"]] = relationship(back_populates="faculty")


class FacultyGeneralBlock(Base):
    """Persistent blocks that survive timetable deletions. Cross-semester, cross-department."""
    __tablename__ = "faculty_general_blocks"

    block_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    faculty_id: Mapped[str] = mapped_column(
        ForeignKey("faculty.faculty_id"), nullable=False
    )
    day: Mapped[str] = mapped_column(String(10), nullable=False)     # "Monday"–"Saturday"
    period: Mapped[int] = mapped_column(Integer, nullable=False)      # 1–8
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    faculty: Mapped["Faculty"] = relationship(back_populates="general_blocks")
