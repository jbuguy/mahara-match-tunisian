"""Transactional email delivery with Resend preferred and SMTP fallback."""

from email.message import EmailMessage
import logging
import smtplib
import ssl

from .config import Settings

logger = logging.getLogger(__name__)


def resend_configured(settings: Settings) -> bool:
    return bool(settings.resend_api_key and settings.resend_from_email)


def smtp_configured(settings: Settings) -> bool:
    return bool(settings.smtp_host and settings.smtp_from_email)


def mail_configured(settings: Settings) -> bool:
    return resend_configured(settings) or smtp_configured(settings)


def _send_with_resend(settings: Settings, recipient: str, subject: str, body: str) -> bool:
    if not resend_configured(settings):
        return False
    try:
        import resend

        resend.api_key = settings.resend_api_key
        response = resend.Emails.send({
            "from": f"{settings.resend_from_name} <{settings.resend_from_email}>",
            "to": [recipient],
            "subject": subject,
            "text": body,
        })
        error = getattr(response, "error", None)
        if error:
            logger.warning("Resend rejected transactional email: %s", error)
            return False
        return True
    except Exception:
        logger.exception("Unable to send transactional email with Resend")
        return False


def _send_with_smtp(settings: Settings, recipient: str, subject: str, body: str, message_id: str | None = None) -> bool:
    if not smtp_configured(settings):
        return False
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    message["To"] = recipient
    if message_id:
        message["Message-ID"] = message_id
    message.set_content(body)
    try:
        if settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=20, context=ssl.create_default_context()) as client:
                if settings.smtp_username:
                    client.login(settings.smtp_username, settings.smtp_password or "")
                client.send_message(message)
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as client:
                client.ehlo()
                if settings.smtp_starttls:
                    client.starttls(context=ssl.create_default_context())
                    client.ehlo()
                if settings.smtp_username:
                    client.login(settings.smtp_username, settings.smtp_password or "")
                client.send_message(message)
        return True
    except (OSError, smtplib.SMTPException):
        logger.exception("Unable to send transactional email with SMTP")
        return False


def send_email(settings: Settings, recipient: str, subject: str, body: str, message_id: str | None = None) -> bool:
    """Send through Resend first, then fall back to SMTP when configured."""
    if _send_with_resend(settings, recipient, subject, body):
        return True
    return _send_with_smtp(settings, recipient, subject, body, message_id)
