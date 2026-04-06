"""
Scheduler Module — Advanced task scheduling with cron-like capabilities.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Callable, Optional
from core.logger import get_logger

log = get_logger("scheduler")


class ScheduledTask:
    """Represents a scheduled task."""

    def __init__(self, name: str, callback: Callable, interval_seconds: int = 0,
                 run_at: str = "", repeat: bool = False, data: dict = None):
        self.name = name
        self.callback = callback
        self.interval_seconds = interval_seconds
        self.run_at = run_at  # HH:MM format
        self.repeat = repeat
        self.data = data or {}
        self.created_at = datetime.now().isoformat()
        self.last_run = ""
        self.run_count = 0
        self.enabled = True
        self._task: Optional[asyncio.Task] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "interval": self.interval_seconds,
            "run_at": self.run_at,
            "repeat": self.repeat,
            "created": self.created_at,
            "last_run": self.last_run,
            "run_count": self.run_count,
            "enabled": self.enabled,
        }


class AdvancedScheduler:
    """Advanced task scheduler with interval and time-based scheduling."""

    def __init__(self):
        self.tasks: dict[str, ScheduledTask] = {}
        self.reminders: list[dict] = []
        self._running = False
        self._check_task = None
        self.on_reminder: Optional[Callable] = None

    async def start(self):
        """Start the scheduler."""
        self._running = True
        self._check_task = asyncio.create_task(self._time_check_loop())
        log.info("Advanced scheduler started")

    async def stop(self):
        """Stop the scheduler."""
        self._running = False
        if self._check_task:
            self._check_task.cancel()
        for task in self.tasks.values():
            if task._task:
                task._task.cancel()

    async def _time_check_loop(self):
        """Check for time-based tasks every minute."""
        while self._running:
            now = datetime.now()
            current_time = now.strftime("%H:%M")

            for name, task in self.tasks.items():
                if not task.enabled:
                    continue
                if task.run_at == current_time:
                    # Only run once per minute
                    if task.last_run != now.strftime("%Y-%m-%d %H:%M"):
                        task.last_run = now.strftime("%Y-%m-%d %H:%M")
                        task.run_count += 1
                        try:
                            result = task.callback(**task.data)
                            if asyncio.iscoroutine(result):
                                await result
                        except Exception as e:
                            log.error(f"Scheduled task '{name}' error: {e}")

            await asyncio.sleep(30)  # Check every 30 seconds

    # ─── Reminders (backward compatible) ──────────────────────
    async def set_reminder(self, message: str, seconds: int) -> str:
        """Set a reminder that triggers after given seconds."""
        trigger_time = datetime.now().timestamp() + seconds

        reminder = {
            "message": message,
            "seconds": seconds,
            "trigger_time": trigger_time,
            "created": datetime.now().isoformat(),
        }
        self.reminders.append(reminder)

        asyncio.create_task(self._reminder_worker(reminder))

        if seconds < 60:
            when = f"{seconds} seconds"
        elif seconds < 3600:
            when = f"{seconds // 60} minutes"
        else:
            when = f"{seconds // 3600} hours and {(seconds % 3600) // 60} minutes"

        return f"Reminder set: '{message}' in {when}."

    async def _reminder_worker(self, reminder: dict):
        await asyncio.sleep(reminder["seconds"])
        if self.on_reminder:
            await self.on_reminder(reminder["message"])
        reminder["triggered"] = True

    def list_reminders(self) -> str:
        """List all reminders."""
        active = [r for r in self.reminders if not r.get("triggered")]
        if not active:
            return "No active reminders."
        lines = []
        for i, r in enumerate(active, 1):
            remaining = r["trigger_time"] - datetime.now().timestamp()
            if remaining > 0:
                mins = remaining / 60
                lines.append(f"  {i}. {r['message']} (in {mins:.0f} min)")
        return "Active reminders:\n" + "\n".join(lines) if lines else "No active reminders."

    # ─── Scheduled Tasks ─────────────────────────────────────
    def schedule_interval(self, name: str, callback: Callable,
                          interval_seconds: int, data: dict = None) -> str:
        """Schedule a task to run at regular intervals."""
        task = ScheduledTask(name, callback, interval_seconds=interval_seconds,
                            repeat=True, data=data)
        self.tasks[name] = task

        async def interval_runner():
            while task.enabled:
                await asyncio.sleep(interval_seconds)
                if not task.enabled:
                    break
                task.last_run = datetime.now().isoformat()
                task.run_count += 1
                try:
                    result = callback(**(data or {}))
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    log.error(f"Interval task '{name}' error: {e}")

        task._task = asyncio.create_task(interval_runner())
        return f"Scheduled '{name}' every {interval_seconds}s."

    def schedule_daily(self, name: str, callback: Callable,
                       time_str: str, data: dict = None) -> str:
        """Schedule a task to run daily at a specific time (HH:MM)."""
        task = ScheduledTask(name, callback, run_at=time_str, repeat=True, data=data)
        self.tasks[name] = task
        return f"Scheduled '{name}' daily at {time_str}."

    def cancel_task(self, name: str) -> str:
        """Cancel a scheduled task."""
        if name not in self.tasks:
            return f"Task '{name}' not found."
        task = self.tasks[name]
        task.enabled = False
        if task._task:
            task._task.cancel()
        del self.tasks[name]
        return f"Cancelled task '{name}'."

    def list_tasks(self) -> str:
        """List all scheduled tasks."""
        if not self.tasks:
            return "No scheduled tasks."
        lines = []
        for name, task in self.tasks.items():
            status = "✓" if task.enabled else "✗"
            schedule = f"every {task.interval_seconds}s" if task.interval_seconds else f"at {task.run_at}"
            lines.append(f"  {status} {name}: {schedule} (ran {task.run_count}x)")
        return "Scheduled tasks:\n" + "\n".join(lines)

    def pause_task(self, name: str) -> str:
        """Pause a scheduled task."""
        if name not in self.tasks:
            return f"Task '{name}' not found."
        self.tasks[name].enabled = False
        return f"Paused task '{name}'."

    def resume_task(self, name: str) -> str:
        """Resume a paused task."""
        if name not in self.tasks:
            return f"Task '{name}' not found."
        self.tasks[name].enabled = True
        return f"Resumed task '{name}'."


# ─── Replace simple scheduler with advanced one ───────────────
scheduler = AdvancedScheduler()
