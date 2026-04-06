"""
Automation Module — Reminders, scheduled tasks, routine automation, and macros.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Callable, Optional


class MacroRecorder:
    """Records and replays sequences of actions."""

    def __init__(self):
        self.macros: dict[str, list[dict]] = {}
        self._recording = False
        self._current_macro: str = ""
        self._current_steps: list[dict] = []

    def start_recording(self, name: str) -> str:
        """Start recording a macro."""
        if self._recording:
            return f"Already recording macro '{self._current_macro}'. Stop it first."
        self._recording = True
        self._current_macro = name
        self._current_steps = []
        return f"Recording macro '{name}'. Perform actions, then stop recording."

    def stop_recording(self) -> str:
        """Stop recording and save the macro."""
        if not self._recording:
            return "Not recording any macro."
        self._recording = False
        self.macros[self._current_macro] = self._current_steps
        count = len(self._current_steps)
        name = self._current_macro
        self._current_macro = ""
        self._current_steps = []
        return f"Macro '{name}' saved with {count} steps."

    def add_step(self, action: str, params: dict = None):
        """Add a step to the current recording."""
        if self._recording:
            self._current_steps.append({
                "action": action,
                "params": params or {},
                "timestamp": datetime.now().isoformat(),
            })

    def list_macros(self) -> str:
        """List all saved macros."""
        if not self.macros:
            return "No macros saved."
        lines = [f"  {name}: {len(steps)} steps" for name, steps in self.macros.items()]
        return "Saved macros:\n" + "\n".join(lines)

    def get_macro(self, name: str) -> list[dict]:
        """Get macro steps."""
        return self.macros.get(name, [])

    def delete_macro(self, name: str) -> str:
        """Delete a macro."""
        if name in self.macros:
            del self.macros[name]
            return f"Macro '{name}' deleted."
        return f"Macro '{name}' not found."


class TaskScheduler:
    """Simple in-memory task scheduler with reminders and macros."""

    def __init__(self):
        self.reminders: list[dict] = []
        self._tasks: list[asyncio.Task] = []
        self.on_reminder: Optional[Callable] = None
        self.macro_recorder = MacroRecorder()
        self._pomodoro_active = False
        self._pomodoro_task = None

    async def set_reminder(self, message: str, seconds: int) -> str:
        """Set a reminder that triggers after given seconds."""
        trigger_time = datetime.now().timestamp() + seconds

        reminder = {
            "message": message,
            "seconds": seconds,
            "trigger_time": trigger_time,
            "created": datetime.now().isoformat(),
            "triggered": False,
        }
        self.reminders.append(reminder)

        task = asyncio.create_task(self._reminder_worker(reminder))
        self._tasks.append(task)

        if seconds < 60:
            when = f"{seconds} seconds"
        elif seconds < 3600:
            when = f"{seconds // 60} minutes"
        else:
            when = f"{seconds // 3600} hours and {(seconds % 3600) // 60} minutes"

        return f"Reminder set: '{message}' in {when}."

    async def _reminder_worker(self, reminder: dict):
        await asyncio.sleep(reminder["seconds"])
        reminder["triggered"] = True
        if self.on_reminder:
            await self.on_reminder(reminder["message"])

    def list_reminders(self) -> str:
        """List all active (not triggered) reminders."""
        active = [r for r in self.reminders if not r.get("triggered")]
        if not active:
            return "No active reminders."
        lines = []
        now = datetime.now().timestamp()
        for i, r in enumerate(active, 1):
            remaining = r["trigger_time"] - now
            if remaining > 0:
                if remaining < 60:
                    time_str = f"{remaining:.0f}s"
                elif remaining < 3600:
                    time_str = f"{remaining / 60:.0f}m"
                else:
                    time_str = f"{remaining / 3600:.1f}h"
                lines.append(f"  {i}. {r['message']} (in {time_str})")
        return "Active reminders:\n" + "\n".join(lines) if lines else "No active reminders."

    def clear_reminders(self) -> str:
        """Clear all reminders."""
        count = len(self.reminders)
        self.reminders.clear()
        for task in self._tasks:
            task.cancel()
        self._tasks.clear()
        return f"Cleared {count} reminder(s)."

    async def start_pomodoro(self, work_minutes: int = 25, break_minutes: int = 5, 
                              cycles: int = 4) -> str:
        """Start a Pomodoro timer session."""
        if self._pomodoro_active:
            return "Pomodoro already active. Stop it first."

        self._pomodoro_active = True

        async def pomodoro_loop():
            for cycle in range(1, cycles + 1):
                if not self._pomodoro_active:
                    break

                # Work phase
                if self.on_reminder:
                    await self.on_reminder(
                        f"🍅 Pomodoro {cycle}/{cycles}: Work time! Focus for {work_minutes} minutes."
                    )
                await asyncio.sleep(work_minutes * 60)

                if not self._pomodoro_active:
                    break

                # Break phase
                if cycle < cycles:
                    if self.on_reminder:
                        await self.on_reminder(
                            f"☕ Break time! Rest for {break_minutes} minutes. ({cycle}/{cycles} done)"
                        )
                    await asyncio.sleep(break_minutes * 60)
                else:
                    if self.on_reminder:
                        await self.on_reminder(
                            f"🎉 Pomodoro complete! All {cycles} cycles done. Great work!"
                        )
            self._pomodoro_active = False

        self._pomodoro_task = asyncio.create_task(pomodoro_loop())
        return (
            f"Pomodoro started: {cycles} cycles of {work_minutes}min work / {break_minutes}min break. "
            f"Total: {cycles * (work_minutes + break_minutes)} minutes."
        )

    def stop_pomodoro(self) -> str:
        """Stop active Pomodoro timer."""
        if not self._pomodoro_active:
            return "No Pomodoro session active."
        self._pomodoro_active = False
        if self._pomodoro_task:
            self._pomodoro_task.cancel()
        return "Pomodoro session stopped."


scheduler = TaskScheduler()
