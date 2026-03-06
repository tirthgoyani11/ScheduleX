import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, Integer, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class Subject(Base):
    __tablename__ = "subjects"

    subject_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    dept_id: Mapped[str] = mapped_column(
        ForeignKey("departments.dept_id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    subject_code: Mapped[str] = mapped_column(String(20), nullable=False)  # BBSSNNVV e.g. "01030100"
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    credits: Mapped[int] = mapped_column(Integer, default=3)
    weekly_periods: Mapped[int] = mapped_column(Integer, default=3)  # Total teaching hours/week (legacy)
    lecture_hours: Mapped[int] = mapped_column(Integer, default=0)    # Theory lectures per week
    lab_hours: Mapped[int] = mapped_column(Integer, default=0)       # Lab sessions per week (each = 1 lab-type period)
    needs_lab: Mapped[bool] = mapped_column(Boolean, default=False)
    batch_size: Mapped[int] = mapped_column(Integer, default=60)     # Expected student count (whole division)
    batch: Mapped[str | None] = mapped_column(String(20), nullable=True)  # Legacy — use Batch model instead
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    department: Mapped["Department"] = relationship(back_populates="subjects")
