# models/timeslot.py
import uuid
import enum
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, Integer, Enum, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class SlotType(str, enum.Enum):
    LECTURE = "lecture"
    LAB = "lab"
    BREAK = "break"


class TimeSlotConfig(Base):
    """
    Configurable time-slot definitions per college.
    Each row is one period in the daily schedule.
    Only LECTURE and LAB slots are passed to the solver; BREAK slots are display-only.
    """
    __tablename__ = "time_slot_configs"
    __table_args__ = (
        UniqueConstraint("college_id", "slot_order", name="uq_college_slot_order"),
    )

    slot_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    college_id: Mapped[str] = mapped_column(
        ForeignKey("colleges.college_id"), nullable=False
    )
    slot_order: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(50), nullable=False)
    start_time: Mapped[str] = mapped_column(String(5), nullable=False)   # "09:00"
    end_time: Mapped[str] = mapped_column(String(5), nullable=False)     # "10:00"
    slot_type: Mapped[SlotType] = mapped_column(Enum(SlotType), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
