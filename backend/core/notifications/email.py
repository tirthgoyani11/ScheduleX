# core/notifications/email.py
"""
Async SMTP email sender using the college's own Postfix relay.
All email stays on-premise.
Falls back gracefully if aiosmtplib is not installed.
"""
import structlog
from config import settings

log = structlog.get_logger()


async def send_email(to_email: str, subject: str, html_body: str, text_body: str = "") -> dict:
    """
    Send an email via the configured SMTP relay.

    Args:
        to_email: Recipient email address
        subject: Email subject line
        html_body: HTML email body
        text_body: Optional plain text alternative body

    Returns:
        {"success": True/False, ...}
    """
    try:
        import aiosmtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
    except ImportError:
        log.warning("aiosmtplib_not_installed", action="send_email")
        return {"success": False, "error": "aiosmtplib not installed"}

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    message["To"] = to_email

    if text_body:
        message.attach(MIMEText(text_body, "plain"))
    message.attach(MIMEText(html_body, "html"))

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            use_tls=settings.SMTP_TLS,
        )
        log.info("email_sent", to=to_email, subject=subject)
        return {"success": True}
    except Exception as e:
        log.error("email_failed", to=to_email, error=str(e))
        return {"success": False, "error": str(e)}
