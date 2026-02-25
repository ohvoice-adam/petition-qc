"""SMTP email service."""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def is_configured() -> bool:
    """Return True if all required SMTP settings are present."""
    from app.models import Settings

    return all(
        Settings.get(k)
        for k in ("smtp_host", "smtp_user", "smtp_from_email")
    )


def send_email(to: str, subject: str, body_html: str, body_text: str) -> None:
    """Send an email via SMTP. Raises on failure."""
    from app.models import Settings

    host = Settings.get("smtp_host", "")
    port = int(Settings.get("smtp_port", "587") or "587")
    user = Settings.get("smtp_user", "")
    password = Settings.get("smtp_password", "")
    from_email = Settings.get("smtp_from_email", "")
    use_tls = Settings.get("smtp_use_tls", "true").lower() != "false"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to
    msg.attach(MIMEText(body_text, "plain"))
    msg.attach(MIMEText(body_html, "html"))

    with smtplib.SMTP(host, port, timeout=15) as smtp:
        if use_tls:
            smtp.starttls()
        if user and password:
            smtp.login(user, password)
        smtp.sendmail(from_email, [to], msg.as_string())

    logger.info("Email sent to %s: %s", to, subject)


def send_password_reset_email(to: str, reset_url: str) -> None:
    """Send a password reset email with the given reset URL."""
    subject = "Password Reset Request"
    body_text = (
        f"You requested a password reset.\n\n"
        f"Click the link below to set a new password (expires in 1 hour):\n\n"
        f"{reset_url}\n\n"
        f"If you did not request this, you can safely ignore this email."
    )
    body_html = f"""
<p>You requested a password reset.</p>
<p>Click the link below to set a new password (expires in 1 hour):</p>
<p><a href="{reset_url}">{reset_url}</a></p>
<p>If you did not request this, you can safely ignore this email.</p>
"""
    send_email(to, subject, body_html, body_text)
