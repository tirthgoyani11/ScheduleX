# routers/notification.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from dependencies import get_db, get_current_user
from models.user import User
from models.notification import NotificationLog
from schemas.notification import NotificationLogResponse

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=list[NotificationLogResponse])
async def list_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List notification logs for the current user."""
    result = await db.execute(
        select(NotificationLog)
        .where(NotificationLog.recipient_user_id == current_user.user_id)
        .order_by(NotificationLog.sent_at.desc())
        .limit(50)
    )
    logs = result.scalars().all()
    return [NotificationLogResponse.model_validate(log) for log in logs]
