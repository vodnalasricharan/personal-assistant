from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from config.settings import Settings

logger = logging.getLogger(__name__)


class EmailTool:
    """
    Contact-form email tool.

    Flow:
      Visitor types a message in the chat
        → agent drafts a notification email
        → user reviews the draft in the UI
        → clicks "Send" → email lands in YOUR inbox (CONTACT_EMAIL)

    Required env vars:
      CONTACT_EMAIL      — your inbox, the only address you must set

    Optional env vars (enable actual SMTP sending):
      GMAIL_ADDRESS      — Gmail account used to send the notification
      GMAIL_APP_PASSWORD — App Password for that Gmail account
                          (if omitted, the app shows the message but can't send it)

    If you set GMAIL_ADDRESS = GMAIL_APP_PASSWORD = same as CONTACT_EMAIL
    the email is sent from you to yourself — the simplest setup.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def is_configured(self) -> bool:
        """True when at least a receive address is set."""
        return self.settings.email_enabled

    def smtp_configured(self) -> bool:
        """True when SMTP credentials are present and sending is possible."""
        return bool(self.settings.gmail_address and self.settings.gmail_app_password)

    def send_contact_message(
        self,
        visitor_name: str,
        visitor_message: str,
        subject: str = "",
    ) -> dict[str, Any]:
        """
        Send a visitor's contact message to the owner's inbox.

        Always sends TO the owner's CONTACT_EMAIL.
        Never exposes the owner's email to the visitor.
        Must only be called after explicit UI confirmation.
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": "CONTACT_EMAIL is not set. Add it to your .env file.",
            }

        recipient = str(self.settings.contact_email)
        email_subject = subject or f"New message via Personal AI Assistant from {visitor_name or 'a visitor'}"

        body = (
            f"You received a new message via your Personal AI Assistant.\n\n"
            f"From: {visitor_name or 'Anonymous visitor'}\n"
            f"{'─' * 50}\n\n"
            f"{visitor_message}\n\n"
            f"{'─' * 50}\n"
            f"Reply directly to this email to respond."
        )

        if not self.smtp_configured():
            # No SMTP credentials — return the draft so it can be shown in the UI
            return {
                "success": False,
                "draft_only": True,
                "to": recipient,
                "subject": email_subject,
                "body": body,
                "error": (
                    "SMTP not configured. Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD "
                    "to enable sending. The message is shown below for manual copying."
                ),
            }

        try:
            msg = MIMEMultipart()
            msg["From"] = self.settings.gmail_address
            msg["To"] = recipient
            msg["Subject"] = email_subject
            msg.attach(MIMEText(body, "plain", "utf-8"))

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(self.settings.gmail_address, self.settings.gmail_app_password)
                server.send_message(msg)

            logger.info("Contact email sent", extra={"extra_data": {"subject": email_subject[:60]}})
            return {"success": True, "to": recipient, "subject": email_subject}

        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP authentication failed")
            return {
                "success": False,
                "error": "SMTP authentication failed — check GMAIL_ADDRESS and GMAIL_APP_PASSWORD.",
            }
        except smtplib.SMTPException as exc:
            logger.error("SMTP error: %s", exc)
            return {"success": False, "error": f"SMTP error: {exc}"}
        except Exception as exc:
            logger.error("Unexpected email error: %s", exc)
            return {"success": False, "error": f"Unexpected error: {exc}"}
