# core/notifications/whatsapp.py
"""
WhatsApp Business API sender.
Uses the college's own registered WhatsApp Business API credentials.
No third-party service. No data leaves the college's network (except to Meta's API).

Falls back gracefully if httpx is not installed or credentials not configured.
"""
import structlog
from config import settings

log = structlog.get_logger()


class WhatsAppSender:
    def __init__(self):
        self.api_url = f"{settings.WHATSAPP_API_URL}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
        self.headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }

    async def send_text(self, to_phone: str, message: str) -> dict:
        """Send a plain text WhatsApp message."""
        try:
            import httpx
        except ImportError:
            log.warning("httpx_not_installed", action="whatsapp_send_text")
            return {"success": False, "error": "httpx not installed"}

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "text",
            "text": {"preview_url": False, "body": message},
        }
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                response = await client.post(self.api_url, headers=self.headers, json=payload)
                response.raise_for_status()
                result = response.json()
                msg_id = result.get("messages", [{}])[0].get("id")
                log.info("whatsapp_sent", to=to_phone, message_id=msg_id)
                return {"success": True, "message_id": msg_id}
            except Exception as e:
                log.error("whatsapp_failed", to=to_phone, error=str(e))
                return {"success": False, "error": str(e)}

    async def send_interactive_yes_no(
        self, to_phone: str, body: str, substitution_request_id: str
    ) -> dict:
        """Send a Yes/No interactive button message for substitution requests."""
        try:
            import httpx
        except ImportError:
            log.warning("httpx_not_installed", action="whatsapp_interactive")
            return {"success": False, "error": "httpx not installed"}

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body},
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {
                                "id": f"ACCEPT_{substitution_request_id}",
                                "title": "✅ Yes, I'll substitute",
                            },
                        },
                        {
                            "type": "reply",
                            "reply": {
                                "id": f"REJECT_{substitution_request_id}",
                                "title": "❌ No, I can't",
                            },
                        },
                    ]
                },
            },
        }
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                response = await client.post(self.api_url, headers=self.headers, json=payload)
                response.raise_for_status()
                return {"success": True}
            except Exception as e:
                log.error("whatsapp_interactive_failed", error=str(e))
                return {"success": False, "error": str(e)}


whatsapp = WhatsAppSender()
