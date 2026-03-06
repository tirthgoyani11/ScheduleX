import uuid
import enum
from sqlalchemy import String, ForeignKey, Integer, Boolean, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class RoomType(str, enum.Enum):
    CLASSROOM = "classroom"
    LAB = "lab"
    SEMINAR = "seminar"


class VenueType(str, enum.Enum):
    HALL = "hall"
    LAB = "lab"
    OUTDOOR = "outdoor"


class Room(Base):
    """Classrooms and labs used for regular lecture timetabling."""
    __tablename__ = "rooms_labs"

    room_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    college_id: Mapped[str] = mapped_column(
        ForeignKey("colleges.college_id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)       # "Room 301", "CS Lab 2"
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    room_type: Mapped[RoomType] = mapped_column(Enum(RoomType), nullable=False)
    has_projector: Mapped[bool] = mapped_column(Boolean, default=False)
    has_computers: Mapped[bool] = mapped_column(Boolean, default=False)
    has_ac: Mapped[bool] = mapped_column(Boolean, default=False)

    college: Mapped["College"] = relationship(back_populates="rooms")


class Venue(Base):
    """Large exam halls — used only for exam scheduling."""
    __tablename__ = "venues"

    venue_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    college_id: Mapped[str] = mapped_column(
        ForeignKey("colleges.college_id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)       # "Main Hall A"
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)       # 100–500 seats
    venue_type: Mapped[VenueType] = mapped_column(Enum(VenueType), nullable=False)
