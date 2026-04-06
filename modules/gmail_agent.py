"""
Gmail Agent Module — Read, summarize, and manage Gmail using OAuth2.
Handles authentication, unread mail fetching, email summarization,
and attachment saving.
"""

import os
import re
import json
import base64
import asyncio
from pathlib import Path
from datetime import datetime
from core.logger import get_logger
import config

log = get_logger("gmail")

MAIL_DIR = config.DATA_DIR / "mails"
MAIL_DIR.mkdir(parents=True, exist_ok=True)
TOKEN_FILE = config.BASE_DIR / "token.json"
CREDENTIALS_FILE = config.BASE_DIR / "credentials.json"
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


def _get_gmail_service():
    """Authenticate and return Gmail API service."""
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        from google.auth.transport.requests import Request
    except ImportError:
        return None, "Google API libraries not installed. Run: pip install google-api-python-client google-auth-oauthlib"

    if not CREDENTIALS_FILE.exists():
        return None, f"Missing {CREDENTIALS_FILE}. Download from Google Cloud Console (Gmail API OAuth credentials)."

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())

    service = build('gmail', 'v1', credentials=creds)
    return service, None


def _is_public_email(sender: str, headers: list) -> bool:
    """Check if an email is from a public/automated source."""
    public_keywords = [
        "noreply", "no-reply", "newsletter", "promotions", "notification",
        "support", "donotreply", "mailer-daemon", "updates", "info", "offers",
        "marketing", "automated", "system", "alert",
    ]
    sender_lower = sender.lower()
    for kw in public_keywords:
        if kw in sender_lower:
            return True
    for h in headers:
        if h.get('name', '').lower() == 'list-unsubscribe':
            return True
    return False


def _extract_email_text(payload: dict) -> str:
    """Extract readable text from email payload."""
    parts = payload.get('parts', [payload])
    for part in parts:
        mime = part.get('mimeType', '')
        if mime == 'text/plain':
            data = part.get('body', {}).get('data')
            if data:
                return base64.urlsafe_b64decode(data).decode(errors='replace')
        if mime == 'text/html':
            data = part.get('body', {}).get('data')
            if data:
                html = base64.urlsafe_b64decode(data).decode(errors='replace')
                try:
                    from bs4 import BeautifulSoup
                    return BeautifulSoup(html, "html.parser").get_text(separator="\n")
                except ImportError:
                    # Strip HTML tags manually
                    import re as _re
                    return _re.sub(r'<[^>]+>', ' ', html)
        if 'parts' in part:
            text = _extract_email_text(part)
            if text:
                return text
    return "No readable content."


def _save_attachments(parts: list, folder: str, service, msg_id: str):
    """Save email attachments to a folder."""
    os.makedirs(folder, exist_ok=True)
    for part in parts:
        filename = part.get('filename')
        if filename and part.get('body', {}).get('attachmentId'):
            att_id = part['body']['attachmentId']
            att = service.users().messages().attachments().get(
                userId='me', messageId=msg_id, id=att_id
            ).execute()
            file_data = base64.urlsafe_b64decode(att['data'])
            filepath = os.path.join(folder, filename)
            with open(filepath, 'wb') as f:
                f.write(file_data)
        if 'parts' in part:
            _save_attachments(part['parts'], folder, service, msg_id)


async def _summarize_email(email_text: str) -> str:
    """Summarize an email using AI (OpenAI or Ollama)."""
    # Try OpenAI first
    try:
        if config.OPENAI_API_KEY:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
            resp = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": f"Summarize this email in 2-3 sentences:\n\n{email_text[:3000]}"}],
                max_tokens=200, temperature=0.3,
            )
            return resp.choices[0].message.content.strip()
    except Exception:
        pass

    # Try Ollama
    try:
        from modules.ollama_llm import ask_ollama
        result = await ask_ollama(f"Summarize this email briefly:\n\n{email_text[:2000]}")
        if result:
            return result
    except Exception:
        pass

    # Just return first 200 chars
    return email_text[:200] + "..."


def check_unread_gmail(count: int = 5, skip_public: bool = True) -> str:
    """Check unread Gmail messages (synchronous for tool use)."""
    service, err = _get_gmail_service()
    if err:
        return err

    try:
        results = service.users().messages().list(userId='me', maxResults=count, q="is:unread").execute()
        messages = results.get('messages', [])
        if not messages:
            return "No unread emails."

        email_list = []
        for msg_data in messages:
            msg_id = msg_data['id']
            full = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
            headers = full['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '(no subject)')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), '(unknown)')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), '')

            if skip_public and _is_public_email(sender, headers):
                continue
            if re.match(r"^\s*(re:|fwd?:)", subject, re.IGNORECASE):
                continue

            snippet = full.get('snippet', '')[:100]
            email_list.append(f"  From: {sender}\n  Subject: {subject}\n  Date: {date}\n  Preview: {snippet}...")

        if not email_list:
            return "No personal unread emails (all filtered as public/replies)."

        return f"Unread Emails ({len(email_list)}):\n\n" + "\n\n".join(email_list)
    except Exception as e:
        return f"Gmail error: {e}"


async def read_and_summarize_gmail(count: int = 3) -> str:
    """Read and summarize unread Gmail messages."""
    service, err = _get_gmail_service()
    if err:
        return err

    try:
        results = service.users().messages().list(userId='me', maxResults=count, q="is:unread").execute()
        messages = results.get('messages', [])
        if not messages:
            return "No unread emails."

        summaries = []
        for msg_data in messages:
            msg_id = msg_data['id']
            full = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
            headers = full['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '(no subject)')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), '(unknown)')

            if _is_public_email(sender, headers):
                continue

            email_text = _extract_email_text(full['payload'])

            # Save to disk
            safe = re.sub(r'[\\/*?:"<>|@.\s]', "_", sender)[:30]
            filepath = MAIL_DIR / f"{safe}_{msg_id}.txt"
            filepath.write_text(f"From: {sender}\nSubject: {subject}\n\n{email_text}", encoding="utf-8")

            # Save attachments
            _save_attachments([full['payload']], str(MAIL_DIR / f"{safe}_{msg_id}_att"), service, msg_id)

            # Summarize
            summary = await _summarize_email(email_text)
            summaries.append(f"  From: {sender}\n  Subject: {subject}\n  Summary: {summary}")

        if not summaries:
            return "No personal unread emails found."

        return f"Email Summaries ({len(summaries)}):\n\n" + "\n\n".join(summaries)
    except Exception as e:
        return f"Gmail error: {e}"


def gmail_operation(operation: str, **kwargs) -> str:
    """Unified Gmail interface."""
    if operation == "check":
        return check_unread_gmail(int(kwargs.get("count", 5)))
    elif operation == "summarize":
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, read_and_summarize_gmail(int(kwargs.get("count", 3))))
                return future.result()
        return asyncio.run(read_and_summarize_gmail(int(kwargs.get("count", 3))))
    elif operation == "setup":
        return (
            "Gmail Setup:\n"
            "1. Go to https://console.cloud.google.com\n"
            "2. Create a project and enable Gmail API\n"
            "3. Create OAuth credentials (Desktop app)\n"
            "4. Download as credentials.json to the Jarvis root folder\n"
            "5. Run 'check gmail' and authorize in browser"
        )
    return f"Unknown gmail operation: {operation}. Available: check, summarize, setup"
