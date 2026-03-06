import uuid
import enum
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, Enum, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class NotificationChannel(str, enum.Enum):
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    BOTH = "both"


class NotificationStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class NotificationEventType(str, enum.Enum):
    TIMETABLE_PUBLISHED = "timetable_published"
    TIMETABLE_UPDATED = "timetable_updated"
    TIMETABLE_DELETED = "timetable_deleted"
    SUBSTITUTION_REQUEST = "substitution_request"
    SUBSTITUTION_ACCEPTED = "substitution_accepted"
    SUBSTITUTION_ESCALATED = "substitution_escalated"
    CLASH_DETECTED = "clash_detected"
    LOAD_WARNING = "load_warning"
    EXAM_PUBLISHED = "exam_published"
    INVIGILATOR_ASSIGNED = "invigilator_assigned"


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    log_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    event_type: Mapped[NotificationEventType] = mapped_column(
        Enum(NotificationEventType), nullable=False
    )
    recipient_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.user_id"), nullable=False
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel), nullable=False
    )
    message_template_id: Mapped[str] = mapped_column(String(100), nullable=False)
    message_body: Mapped[str] = mapped_column(Text, nullable=False)
    related_entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus), default=NotificationStatus.PENDING
    )
