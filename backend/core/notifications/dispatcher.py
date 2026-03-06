# core/notifications/dispatcher.py
"""
Redis Pub/Sub event dispatcher.
Core engine publishes events here. Notification worker consumes them.
This decoupling ensures a WhatsApp failure NEVER blocks scheduling operations.
"""
import json
from config import settings

try:
    import redis
    redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
except Exception:
    redis_client = None


def dispatch_event(event_type: str, payload: dict):
    """
    Publish a scheduling event to Redis Pub/Sub.
    The notification_worker consumes this and sends WhatsApp/Email.
    Non-blocking — returns immediately.
    """
    if redis_client is None:
        return
    try:
        message = json.dumps({"event_type": event_type, "payload": payload})
        redis_client.publish(settings.REDIS_PUBSUB_CHANNEL, message)
    except Exception:
        pass  # Never let notification dispatch break the API
