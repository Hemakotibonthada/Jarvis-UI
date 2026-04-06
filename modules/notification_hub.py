"""
Notification Hub — Centralized notification system for desktop, email, and webhook alerts.
Supports desktop toasts (Windows/Linux/Mac), email notifications,
webhook integrations (Slack, Discord, Telegram), and notification history.
"""

import asyncio
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable
import aiohttp
from core.logger import get_logger
import config

log = get_logger("notifications")

NOTIFICATION_LOG = config.DATA_DIR / "notifications.jsonl"


class NotificationChannel:
    """Base class for notification channels."""
    name: str = "base"
    enabled: bool = True

    async def send(self, title: str, message: str, **kwargs) -> str:
        raise NotImplementedError


class DesktopNotification(NotificationChannel):
    """Desktop toast notifications."""
    name = "desktop"

    async def send(self, title: str, message: str, **kwargs) -> str:
        try:
            if config.IS_WINDOWS:
                # PowerShell balloon notification
                ps_script = f'''
                [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
                $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
                $textNodes = $template.GetElementsByTagName("text")
                $textNodes.Item(0).AppendChild($template.CreateTextNode("{title}")) > $null
                $textNodes.Item(1).AppendChild($template.CreateTextNode("{message[:200]}")) > $null
                $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
                [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("JARVIS").Show($toast)
                '''
                subprocess.Popen(
                    ["powershell", "-c", ps_script],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                )
                return "Desktop notification sent."
            elif config.IS_LINUX:
                subprocess.Popen(["notify-send", title, message[:200]])
                return "Desktop notification sent."
            elif config.IS_MAC:
                subprocess.Popen([
                    "osascript", "-e",
                    f'display notification "{message[:200]}" with title "{title}"'
                ])
                return "Desktop notification sent."
            return "Unsupported platform."
        except Exception as e:
            return f"Desktop notification error: {e}"


class EmailNotification(NotificationChannel):
    """Email notifications."""
    name = "email"

    def __init__(self, to_address: str = ""):
        self.to_address = to_address or config.EMAIL_ADDRESS

    async def send(self, title: str, message: str, **kwargs) -> str:
        if not config.EMAIL_ADDRESS or not config.EMAIL_PASSWORD:
            return "Email not configured."
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart()
            msg["From"] = config.EMAIL_ADDRESS
            msg["To"] = kwargs.get("to", self.to_address)
            msg["Subject"] = f"[JARVIS] {title}"

            body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; background: #1a1a2e; color: #eee; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: #16213e; padding: 20px; border-radius: 10px; border: 1px solid #0f3460;">
            <h2 style="color: #00d4ff; margin-top: 0;">J.A.R.V.I.S. Notification</h2>
            <h3 style="color: #e0f0ff;">{title}</h3>
            <p style="color: #c0d8f0; line-height: 1.6;">{message}</p>
            <hr style="border: 1px solid #0f3460;">
            <p style="color: #666; font-size: 12px;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            </body>
            </html>
            """
            msg.attach(MIMEText(body, "html"))

            with smtplib.SMTP(config.EMAIL_SMTP_SERVER, config.EMAIL_SMTP_PORT) as server:
                server.starttls()
                server.login(config.EMAIL_ADDRESS, config.EMAIL_PASSWORD)
                server.send_message(msg)

            return f"Email notification sent to {msg['To']}."
        except Exception as e:
            return f"Email notification error: {e}"


class SlackNotification(NotificationChannel):
    """Slack webhook notifications."""
    name = "slack"

    def __init__(self, webhook_url: str = ""):
        self.webhook_url = webhook_url

    async def send(self, title: str, message: str, **kwargs) -> str:
        if not self.webhook_url:
            return "Slack webhook URL not configured."
        try:
            payload = {
                "blocks": [
                    {"type": "header", "text": {"type": "plain_text", "text": f"🤖 {title}"}},
                    {"type": "section", "text": {"type": "mrkdwn", "text": message[:3000]}},
                    {"type": "context", "elements": [
                        {"type": "mrkdwn", "text": f"_JARVIS • {datetime.now().strftime('%H:%M:%S')}_"}
                    ]},
                ]
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        return "Slack notification sent."
                    return f"Slack error: {resp.status}"
        except Exception as e:
            return f"Slack notification error: {e}"


class DiscordNotification(NotificationChannel):
    """Discord webhook notifications."""
    name = "discord"

    def __init__(self, webhook_url: str = ""):
        self.webhook_url = webhook_url

    async def send(self, title: str, message: str, **kwargs) -> str:
        if not self.webhook_url:
            return "Discord webhook URL not configured."
        try:
            payload = {
                "embeds": [{
                    "title": f"🤖 {title}",
                    "description": message[:4000],
                    "color": 0x00D4FF,
                    "footer": {"text": f"JARVIS • {datetime.now().strftime('%H:%M:%S')}"},
                }]
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status in (200, 204):
                        return "Discord notification sent."
                    return f"Discord error: {resp.status}"
        except Exception as e:
            return f"Discord notification error: {e}"


class TelegramNotification(NotificationChannel):
    """Telegram bot notifications."""
    name = "telegram"

    def __init__(self, bot_token: str = "", chat_id: str = ""):
        self.bot_token = bot_token
        self.chat_id = chat_id

    async def send(self, title: str, message: str, **kwargs) -> str:
        if not self.bot_token or not self.chat_id:
            return "Telegram bot token and chat ID required."
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": f"*{title}*\n\n{message}",
                "parse_mode": "Markdown",
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        return "Telegram notification sent."
                    return f"Telegram error: {resp.status}"
        except Exception as e:
            return f"Telegram notification error: {e}"


class WebhookNotification(NotificationChannel):
    """Generic webhook (POST JSON)."""
    name = "webhook"

    def __init__(self, url: str = ""):
        self.url = url

    async def send(self, title: str, message: str, **kwargs) -> str:
        if not self.url:
            return "Webhook URL not configured."
        try:
            payload = {
                "source": "jarvis",
                "title": title,
                "message": message,
                "timestamp": datetime.now().isoformat(),
                **kwargs,
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(self.url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    return f"Webhook sent: HTTP {resp.status}"
        except Exception as e:
            return f"Webhook error: {e}"


# ─── Notification Hub ─────────────────────────────────────────
class NotificationHub:
    """Central notification manager with multiple channels and history."""

    def __init__(self):
        self.channels: dict[str, NotificationChannel] = {
            "desktop": DesktopNotification(),
        }
        self.history: list[dict] = []
        self.rules: list[dict] = []  # Notification rules/filters
        self._load_history()

    def _load_history(self):
        """Load notification history from disk."""
        if NOTIFICATION_LOG.exists():
            try:
                entries = NOTIFICATION_LOG.read_text(encoding="utf-8").strip().split("\n")
                for line in entries[-100:]:
                    try:
                        self.history.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
            except OSError:
                pass

    def _log(self, title: str, message: str, channels: list, results: list):
        """Log a notification."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "title": title,
            "message": message[:200],
            "channels": channels,
            "results": results,
        }
        self.history.append(entry)
        try:
            with open(NOTIFICATION_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            pass

    def add_channel(self, channel_type: str, **kwargs) -> str:
        """Add a notification channel."""
        channel_map = {
            "desktop": lambda: DesktopNotification(),
            "email": lambda: EmailNotification(kwargs.get("to", "")),
            "slack": lambda: SlackNotification(kwargs.get("webhook_url", "")),
            "discord": lambda: DiscordNotification(kwargs.get("webhook_url", "")),
            "telegram": lambda: TelegramNotification(kwargs.get("bot_token", ""), kwargs.get("chat_id", "")),
            "webhook": lambda: WebhookNotification(kwargs.get("url", "")),
        }
        factory = channel_map.get(channel_type)
        if not factory:
            return f"Unknown channel type: {channel_type}. Available: {', '.join(channel_map.keys())}"

        name = kwargs.get("name", channel_type)
        self.channels[name] = factory()
        return f"Notification channel '{name}' ({channel_type}) added."

    def remove_channel(self, name: str) -> str:
        """Remove a notification channel."""
        if name not in self.channels:
            return f"Channel '{name}' not found."
        del self.channels[name]
        return f"Channel '{name}' removed."

    def list_channels(self) -> str:
        """List configured notification channels."""
        if not self.channels:
            return "No notification channels configured."
        lines = [f"  {'✓' if ch.enabled else '✗'} {name} ({ch.name})" for name, ch in self.channels.items()]
        return f"Notification Channels ({len(self.channels)}):\n" + "\n".join(lines)

    async def notify(self, title: str, message: str, channels: list = None,
                     priority: str = "normal") -> str:
        """Send a notification through specified or all channels."""
        target_channels = channels or list(self.channels.keys())
        results = []

        for ch_name in target_channels:
            channel = self.channels.get(ch_name)
            if channel and channel.enabled:
                result = await channel.send(title, message)
                results.append(f"  {ch_name}: {result}")

        self._log(title, message, target_channels, results)

        if not results:
            return "No enabled channels to send to."

        return f"Notification '{title}' sent:\n" + "\n".join(results)

    async def notify_desktop(self, title: str, message: str) -> str:
        """Quick desktop notification."""
        return await self.channels.get("desktop", DesktopNotification()).send(title, message)

    def get_history(self, count: int = 20) -> str:
        """Get notification history."""
        if not self.history:
            return "No notification history."
        recent = self.history[-count:]
        lines = []
        for entry in reversed(recent):
            ts = entry.get("timestamp", "")[:19]
            title = entry.get("title", "")
            channels = ", ".join(entry.get("channels", []))
            lines.append(f"  [{ts}] {title} → {channels}")
        return f"Notification History ({len(recent)}):\n" + "\n".join(lines)

    def clear_history(self) -> str:
        """Clear notification history."""
        count = len(self.history)
        self.history.clear()
        if NOTIFICATION_LOG.exists():
            NOTIFICATION_LOG.unlink()
        return f"Cleared {count} notification entries."

    def add_rule(self, trigger: str, condition: str, channel: str,
                 title_template: str = "", message_template: str = "") -> str:
        """Add a notification rule (trigger-based)."""
        rule = {
            "trigger": trigger,  # e.g., "cpu_high", "task_due", "sensor_alert"
            "condition": condition,
            "channel": channel,
            "title_template": title_template or trigger,
            "message_template": message_template or "Alert triggered: {trigger}",
            "enabled": True,
            "created": datetime.now().isoformat(),
        }
        self.rules.append(rule)
        return f"Notification rule added: '{trigger}' → {channel}"

    def list_rules(self) -> str:
        """List notification rules."""
        if not self.rules:
            return "No notification rules configured."
        lines = [
            f"  {'✓' if r['enabled'] else '✗'} {r['trigger']} → {r['channel']} ({r.get('condition', 'always')})"
            for r in self.rules
        ]
        return f"Notification Rules ({len(self.rules)}):\n" + "\n".join(lines)

    # ─── Unified Interface ────────────────────────────────────
    async def notification_operation(self, operation: str, **kwargs) -> str:
        """Unified notification management."""
        title = kwargs.get("title", "JARVIS Notification")
        message = kwargs.get("message", "")

        if operation == "send":
            channels = kwargs.get("channels", "").split(",") if kwargs.get("channels") else None
            return await self.notify(title, message, channels)
        elif operation == "desktop":
            return await self.notify_desktop(title, message)

        ops = {
            "add_channel": lambda: self.add_channel(kwargs.get("channel_type", ""), **kwargs),
            "remove_channel": lambda: self.remove_channel(kwargs.get("name", "")),
            "list_channels": lambda: self.list_channels(),
            "history": lambda: self.get_history(int(kwargs.get("count", 20))),
            "clear": lambda: self.clear_history(),
            "add_rule": lambda: self.add_rule(kwargs.get("trigger", ""), kwargs.get("condition", ""), kwargs.get("channel", "")),
            "list_rules": lambda: self.list_rules(),
        }

        handler = ops.get(operation)
        if handler:
            return handler()
        return f"Unknown notification operation: {operation}. Available: send, desktop, add_channel, remove_channel, list_channels, history, clear, add_rule, list_rules"


# ─── Singleton ────────────────────────────────────────────────
notification_hub = NotificationHub()
