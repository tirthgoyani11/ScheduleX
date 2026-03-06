import uuid
from enum import Enum as PyEnum
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, Enum, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class UserRole(str, PyEnum):
    SUPER_ADMIN = "super_admin"       # College-level: user management only
    DEPT_ADMIN = "dept_admin"         # Department-level: full operational control
    FACULTY = "faculty"               # View-only: own timetable, assignments


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    college_id: Mapped[str] = mapped_column(
        ForeignKey("colleges.college_id"), nullable=False
    )
    dept_id: Mapped[str | None] = mapped_column(
        ForeignKey("departments.dept_id"), nullable=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)  # For WhatsApp
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # One-to-one link to faculty profile (for FACULTY role users)
    faculty_profile: Mapped["Faculty | None"] = relationship(back_populates="user")
