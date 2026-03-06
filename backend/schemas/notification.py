# schemas/notification.py
from pydantic import BaseModel
from datetime import datetime


class NotificationLogResponse(BaseModel):
    log_id: str
    event_type: str
    channel: str
    message_body: str
    status: str
    sent_at: datetime | None
    delivered_at: datetime | None

    model_config = {"from_attributes": True}
