"""
Email Module — Send and read emails via SMTP/IMAP.
"""

import smtplib
import imaplib
import email as email_lib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from datetime import datetime
import config


def send_email(to: str, subject: str, body: str) -> str:
    """Send an email."""
    if not config.EMAIL_ADDRESS or not config.EMAIL_PASSWORD:
        return "Email not configured. Set JARVIS_EMAIL and JARVIS_EMAIL_PASSWORD environment variables."

    try:
        msg = MIMEMultipart()
        msg["From"] = config.EMAIL_ADDRESS
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(config.EMAIL_SMTP_SERVER, config.EMAIL_SMTP_PORT) as server:
            server.starttls()
            server.login(config.EMAIL_ADDRESS, config.EMAIL_PASSWORD)
            server.send_message(msg)

        return f"Email sent to {to} with subject '{subject}'."
    except Exception as e:
        return f"Failed to send email: {e}"


def read_emails(count: int = 5, folder: str = "INBOX") -> str:
    """Read recent emails from inbox."""
    if not config.EMAIL_ADDRESS or not config.EMAIL_PASSWORD:
        return "Email not configured. Set JARVIS_EMAIL and JARVIS_EMAIL_PASSWORD environment variables."

    try:
        mail = imaplib.IMAP4_SSL(config.EMAIL_IMAP_SERVER)
        mail.login(config.EMAIL_ADDRESS, config.EMAIL_PASSWORD)
        mail.select(folder)

        _, message_numbers = mail.search(None, "ALL")
        msg_nums = message_numbers[0].split()

        if not msg_nums:
            mail.logout()
            return "No emails found."

        recent = msg_nums[-count:]
        emails = []

        for num in reversed(recent):
            _, msg_data = mail.fetch(num, "(RFC822)")
            raw = msg_data[0][1]
            msg = email_lib.message_from_bytes(raw)

            subject_raw = decode_header(msg["Subject"])[0]
            subject = subject_raw[0].decode() if isinstance(subject_raw[0], bytes) else str(subject_raw[0])
            sender = msg.get("From", "Unknown")
            date = msg.get("Date", "Unknown")

            # Get body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        try:
                            body = part.get_payload(decode=True).decode()[:200]
                        except Exception:
                            body = "(could not decode)"
                        break
            else:
                try:
                    body = msg.get_payload(decode=True).decode()[:200]
                except Exception:
                    body = "(could not decode)"

            emails.append(f"  From: {sender}\n  Subject: {subject}\n  Date: {date}\n  Preview: {body}...")

        mail.logout()
        return f"Recent {len(emails)} emails:\n\n" + "\n\n".join(emails)
    except Exception as e:
        return f"Failed to read emails: {e}"


def count_unread_emails() -> str:
    """Count unread emails."""
    if not config.EMAIL_ADDRESS or not config.EMAIL_PASSWORD:
        return "Email not configured."
    try:
        mail = imaplib.IMAP4_SSL(config.EMAIL_IMAP_SERVER)
        mail.login(config.EMAIL_ADDRESS, config.EMAIL_PASSWORD)
        mail.select("INBOX")
        _, messages = mail.search(None, "UNSEEN")
        count = len(messages[0].split()) if messages[0] else 0
        mail.logout()
        return f"You have {count} unread email(s)."
    except Exception as e:
        return f"Error checking emails: {e}"
