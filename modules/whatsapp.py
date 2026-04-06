"""
WhatsApp Module — Send messages via WhatsApp Web using pywhatkit.
"""

import pywhatkit
from datetime import datetime


def send_whatsapp(to: str, message: str) -> str:
    """
    Send a WhatsApp message.
    'to' can be a phone number with country code (e.g., +1234567890)
    """
    if not to.startswith("+"):
        return f"Please provide a phone number with country code (e.g., +1234567890). Got: {to}"

    now = datetime.now()
    hour = now.hour
    minute = now.minute + 2
    if minute >= 60:
        minute -= 60
        hour = (hour + 1) % 24

    try:
        pywhatkit.sendwhatmsg(
            phone_no=to,
            message=message,
            time_hour=hour,
            time_min=minute,
            wait_time=15,
            tab_close=True,
        )
        return f"WhatsApp message sent to {to}: '{message[:50]}...'"
    except Exception as e:
        return f"Failed to send WhatsApp message: {e}"


def send_whatsapp_instant(to: str, message: str) -> str:
    """Send an instant WhatsApp message."""
    if not to.startswith("+"):
        return f"Please provide a phone number with country code. Got: {to}"
    try:
        pywhatkit.sendwhatmsg_instantly(
            phone_no=to,
            message=message,
            wait_time=15,
            tab_close=True,
        )
        return f"WhatsApp message sent instantly to {to}."
    except Exception as e:
        return f"Failed to send WhatsApp message: {e}"
