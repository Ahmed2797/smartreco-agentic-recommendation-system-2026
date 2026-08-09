import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

def send_email_digest(to_email: str, subject: str, html_content: str) -> bool:
    """Email Digest Delivery: Sends an HTML email digest to the specified recipient."""
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning("SMTP credentials are missing; skipped digest delivery")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.SENDER_EMAIL
        msg["To"] = to_email

        html_part = MIMEText(html_content, "html")
        msg.attach(html_part)

        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SENDER_EMAIL, to_email, msg.as_string())

        logger.info("Email digest sent")
        return True
    except Exception:
        logger.exception("Email digest delivery failed")
        return False
