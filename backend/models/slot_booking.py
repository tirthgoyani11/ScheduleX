import uuid
import enum
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, Integer, Enum, Text, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class BookingType(str, enum.Enum):
    RESCHEDULE = "reschedule"
    EXTRA_LECTURE = "extra_lecture"
    PROXY = "proxy"


class BookingStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class SlotBooking(Base):
    """
    Manages reschedules, extra lectures, and proxy assignments.
    Once a slot is booked here (status=APPROVED), it is locked and
    no other faculty can claim it for an extra lecture.
    """
    __tablename__ = "slot_bookings"

    booking_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    college_id: Mapped[str] = mapped_column(
        ForeignKey("colleges.college_id"), nullable=False
    )
    dept_id: Mapped[str] = mapped_column(
        ForeignKey("departments.dept_id"), nullable=False
    )
    booking_type: Mapped[BookingType] = mapped_column(
        Enum(BookingType), nullable=False
    )
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus), default=BookingStatus.PENDING
    )

    # Who is teaching
    faculty_id: Mapped[str] = mapped_column(
        ForeignKey("faculty.faculty_id"), nullable=False
    )
    # The slot being booked
    day: Mapped[str] = mapped_column(String(10), nullable=False)
    period: Mapped[int] = mapped_column(Integer, nullable=False)
    room_id: Mapped[str] = mapped_column(
        ForeignKey("rooms_labs.room_id"), nullable=False
    )
    subject_id: Mapped[str] = mapped_column(
        ForeignKey("subjects.subject_id"), nullable=False
    )

    # For reschedule — original entry being moved
    original_entry_id: Mapped[str | None] = mapped_column(
        ForeignKey("timetable_entries.entry_id"), nullable=True
    )
    # For proxy — the absent faculty being covered
    absent_faculty_id: Mapped[str | None] = mapped_column(
        ForeignKey("faculty.faculty_id"), nullable=True
    )

    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_date: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # specific date e.g. "2026-03-10"

    requested_by: Mapped[str] = mapped_column(
        ForeignKey("users.user_id"), nullable=False
    )
    approved_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.user_id"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        # Prevent double-booking: one approved booking per slot
        UniqueConstraint(
            "college_id", "day", "period", "room_id", "target_date",
            name="uq_slot_booking_room"
        ),
    )
