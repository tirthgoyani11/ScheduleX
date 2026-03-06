import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class College(Base):
    __tablename__ = "colleges"

    college_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    affiliation: Mapped[str | None] = mapped_column(String(200), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    departments: Mapped[list["Department"]] = relationship(back_populates="college")
    rooms: Mapped[list["Room"]] = relationship(back_populates="college")
    global_bookings: Mapped[list["GlobalBooking"]] = relationship(back_populates="college")


class Department(Base):
    __tablename__ = "departments"

    dept_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    college_id: Mapped[str] = mapped_column(
        ForeignKey("colleges.college_id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g. "CSE", "IT", "ME"
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    college: Mapped["College"] = relationship(back_populates="departments")
    faculty: Mapped[list["Faculty"]] = relationship(back_populates="department")
    subjects: Mapped[list["Subject"]] = relationship(back_populates="department")
    timetables: Mapped[list["Timetable"]] = relationship(back_populates="department")
