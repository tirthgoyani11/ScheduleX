import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, Integer, DateTime, UniqueConstraint, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class GlobalBooking(Base):
    """
    THE CLASH PREVENTION TABLE.

    Every published timetable entry — from every department — writes a row here.
    Two PostgreSQL UNIQUE constraints make it physically impossible to double-book
    a faculty member or room, even with concurrent department publishes.

    NEVER remove the unique constraints.
    NEVER bypass this table for any booking operation.
    ALWAYS check this table before writing timetable_entries.
    """
    __tablename__ = "global_bookings"

    booking_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    college_id: Mapped[str] = mapped_column(
        ForeignKey("colleges.college_id"), nullable=False
    )
    dept_id: Mapped[str] = mapped_column(
        ForeignKey("departments.dept_id"), nullable=False
    )
    timetable_entry_id: Mapped[str | None] = mapped_column(
        ForeignKey("timetable_entries.entry_id"), nullable=True
    )
    day: Mapped[str] = mapped_column(String(10), nullable=False)
    period: Mapped[int] = mapped_column(Integer, nullable=False)
    faculty_id: Mapped[str] = mapped_column(
        ForeignKey("faculty.faculty_id"), nullable=False
    )
    room_id: Mapped[str] = mapped_column(
        ForeignKey("rooms_labs.room_id"), nullable=False
    )
    booking_type: Mapped[str] = mapped_column(
        String(20), default="timetable"
    )  # "timetable" | "general_block" | "exam"
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    college: Mapped["College"] = relationship(back_populates="global_bookings")

    __table_args__ = (
        # HARD GUARANTEE: One faculty, one slot, college-wide
        UniqueConstraint("college_id", "day", "period", "faculty_id", name="uq_faculty_slot"),
        # HARD GUARANTEE: One room, one slot, college-wide
        UniqueConstraint("college_id", "day", "period", "room_id", name="uq_room_slot"),
        # Fast lookup during generation
        Index("idx_bookings_college_day_period", "college_id", "day", "period"),
        Index("idx_bookings_faculty", "college_id", "faculty_id"),
        Index("idx_bookings_room", "college_id", "room_id"),
    )
