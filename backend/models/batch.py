import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class Batch(Base):
    """Student batch within a department/semester for lab rotation scheduling."""
    __tablename__ = "batches"

    batch_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    dept_id: Mapped[str] = mapped_column(
        ForeignKey("departments.dept_id"), nullable=False
    )
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)   # "A", "B", "1A13"
    size: Mapped[int] = mapped_column(Integer, default=30)          # Students in this batch
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    department: Mapped["Department"] = relationship()
