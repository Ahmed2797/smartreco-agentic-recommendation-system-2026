import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from src.config.settings import settings

def send_email_digest(to_email: str, subject: str, html_content: str) -> bool:
    """Email Digest Delivery: Sends an HTML email digest to the specified recipient."""
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        print(f"⚠️ [SMTP Warning] Credentials missing. Email to {to_email} skipped (Simulated delivery).")
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

        print(f"✅ Email Digest successfully sent to: {to_email}")
        return True
    except Exception as e:
        print(f"❌ Error sending email to {to_email}: {str(e)}")
        return False