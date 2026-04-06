"""
Pomodoro & Focus Timer Module — Full Pomodoro technique implementation with
focus sessions, break management, statistics, and distraction blocking.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Callable
from core.logger import get_logger
import config

log = get_logger("pomodoro")

POMODORO_FILE = config.DATA_DIR / "pomodoro_history.json"


class PomodoroSession:
    """Represents a single Pomodoro focus session."""
    def __init__(self, task: str = "", work_min: int = 25, break_min: int = 5):
        self.task = task
        self.work_min = work_min
        self.break_min = break_min
        self.started_at = ""
        self.ended_at = ""
        self.completed = False
        self.interrupted = False
        self.actual_work_min = 0
        self.notes = ""
        self.distractions = 0

    def to_dict(self):
        return self.__dict__

    @staticmethod
    def from_dict(d) -> 'PomodoroSession':
        s = PomodoroSession()
        for k, v in d.items():
            if hasattr(s, k):
                setattr(s, k, v)
        return s


class PomodoroTimer:
    """Full Pomodoro timer with statistics and history."""

    def __init__(self):
        self._active = False
        self._paused = False
        self._current_session: Optional[PomodoroSession] = None
        self._session_task: Optional[asyncio.Task] = None
        self._start_time: float = 0
        self._elapsed: float = 0
        self._phase = "idle"  # idle, work, short_break, long_break
        self._cycle = 0
        self._total_cycles = 4
        self._on_notify: Optional[Callable] = None
        self.history: list[dict] = []
        self.daily_stats: dict[str, dict] = {}

        # Default durations
        self.work_duration = 25
        self.short_break = 5
        self.long_break = 15
        self.cycles_before_long = 4

        self._load_history()

    def _load_history(self):
        if POMODORO_FILE.exists():
            try:
                data = json.loads(POMODORO_FILE.read_text(encoding="utf-8"))
                self.history = data.get("history", [])[-500:]
                self.daily_stats = data.get("daily_stats", {})
            except (json.JSONDecodeError, OSError):
                pass

    def _save_history(self):
        data = {"history": self.history[-500:], "daily_stats": self.daily_stats}
        POMODORO_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _update_daily_stats(self, session: PomodoroSession):
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in self.daily_stats:
            self.daily_stats[today] = {"sessions": 0, "total_min": 0, "completed": 0, "interrupted": 0}
        stats = self.daily_stats[today]
        stats["sessions"] += 1
        stats["total_min"] += session.actual_work_min
        if session.completed:
            stats["completed"] += 1
        if session.interrupted:
            stats["interrupted"] += 1

    async def start(self, task: str = "", work_min: int = 0,
                    break_min: int = 0, cycles: int = 0) -> str:
        """Start a Pomodoro session."""
        if self._active:
            return f"Timer already running ({self._phase}). Stop first."

        work = work_min or self.work_duration
        brk = break_min or self.short_break
        total_cycles = cycles or self._total_cycles

        self._active = True
        self._cycle = 0
        self._total_cycles = total_cycles
        self._phase = "work"

        session = PomodoroSession(task, work, brk)
        session.started_at = datetime.now().isoformat()
        self._current_session = session
        self._start_time = time.time()

        # Start the timer task
        self._session_task = asyncio.create_task(self._run_pomodoro(work, brk, total_cycles, task))

        total_time = total_cycles * (work + brk)
        return (
            f"🍅 Pomodoro started!\n"
            f"  Task: {task or '(general focus)'}\n"
            f"  Work: {work} min | Break: {brk} min\n"
            f"  Cycles: {total_cycles} ({total_time} min total)\n"
            f"  Focus now! First work session begins."
        )

    async def _run_pomodoro(self, work_min: int, break_min: int,
                             cycles: int, task: str):
        """Internal Pomodoro loop."""
        try:
            for cycle in range(1, cycles + 1):
                if not self._active:
                    break

                self._cycle = cycle
                self._phase = "work"
                self._start_time = time.time()

                if self._on_notify:
                    await self._on_notify(
                        f"🍅 Pomodoro {cycle}/{cycles}: Work time! Focus for {work_min} minutes."
                        + (f" Task: {task}" if task else "")
                    )

                # Work phase
                await self._wait_minutes(work_min)
                if not self._active:
                    break

                # Record completed work session
                session = PomodoroSession(task, work_min, break_min)
                session.started_at = datetime.now().isoformat()
                session.completed = True
                session.actual_work_min = work_min
                self.history.append(session.to_dict())
                self._update_daily_stats(session)
                self._save_history()

                # Break phase
                if cycle < cycles:
                    is_long = (cycle % self.cycles_before_long == 0)
                    brk = self.long_break if is_long else break_min
                    self._phase = "long_break" if is_long else "short_break"
                    self._start_time = time.time()

                    if self._on_notify:
                        break_type = "Long break" if is_long else "Short break"
                        await self._on_notify(
                            f"☕ {break_type}! Rest for {brk} minutes. ({cycle}/{cycles} done)"
                        )

                    await self._wait_minutes(brk)
                else:
                    if self._on_notify:
                        await self._on_notify(
                            f"🎉 Pomodoro complete! All {cycles} cycles done. Great work! "
                            f"Total: {cycles * work_min} minutes of focused work."
                        )
        except asyncio.CancelledError:
            pass
        finally:
            self._active = False
            self._phase = "idle"
            self._current_session = None

    async def _wait_minutes(self, minutes: int):
        """Wait for specified minutes, checking for pause/stop."""
        seconds = minutes * 60
        waited = 0
        while waited < seconds and self._active:
            if not self._paused:
                await asyncio.sleep(1)
                waited += 1
            else:
                await asyncio.sleep(0.5)

    def stop(self) -> str:
        """Stop the current Pomodoro."""
        if not self._active:
            return "No timer running."

        elapsed = (time.time() - self._start_time) / 60
        self._active = False
        if self._session_task:
            self._session_task.cancel()

        if self._current_session:
            self._current_session.interrupted = True
            self._current_session.actual_work_min = round(elapsed, 1)
            self._current_session.ended_at = datetime.now().isoformat()
            self.history.append(self._current_session.to_dict())
            self._update_daily_stats(self._current_session)
            self._save_history()

        task = self._current_session.task if self._current_session else ""
        self._phase = "idle"
        self._current_session = None

        return (
            f"Pomodoro stopped after {elapsed:.1f} minutes.\n"
            f"  Phase: {self._phase} | Cycle: {self._cycle}/{self._total_cycles}\n"
            f"  Task: {task or '(general)'}"
        )

    def pause(self) -> str:
        """Pause the timer."""
        if not self._active:
            return "No timer running."
        if self._paused:
            return "Timer already paused."
        self._paused = True
        self._elapsed = time.time() - self._start_time
        return f"Timer paused at {self._elapsed / 60:.1f} minutes."

    def resume(self) -> str:
        """Resume the timer."""
        if not self._paused:
            return "Timer not paused."
        self._paused = False
        self._start_time = time.time() - self._elapsed
        return "Timer resumed."

    def log_distraction(self) -> str:
        """Log a distraction during focus time."""
        if self._current_session:
            self._current_session.distractions += 1
            return f"Distraction logged ({self._current_session.distractions} total). Stay focused! 💪"
        return "No active session."

    def status(self) -> str:
        """Get current timer status."""
        if not self._active:
            return "No Pomodoro active. Start one with start()."

        elapsed = (time.time() - self._start_time) / 60
        phase_duration = {
            "work": self.work_duration,
            "short_break": self.short_break,
            "long_break": self.long_break,
        }.get(self._phase, self.work_duration)
        remaining = max(0, phase_duration - elapsed)

        task = self._current_session.task if self._current_session else ""
        paused = " (PAUSED)" if self._paused else ""

        return (
            f"Pomodoro Status{paused}:\n"
            f"  Phase: {self._phase.replace('_', ' ').title()}\n"
            f"  Cycle: {self._cycle}/{self._total_cycles}\n"
            f"  Elapsed: {elapsed:.1f} min\n"
            f"  Remaining: {remaining:.1f} min\n"
            f"  Task: {task or '(general)'}"
        )

    def set_durations(self, work: int = 0, short_break: int = 0,
                      long_break: int = 0, cycles: int = 0) -> str:
        """Configure default durations."""
        if work:
            self.work_duration = work
        if short_break:
            self.short_break = short_break
        if long_break:
            self.long_break = long_break
        if cycles:
            self.cycles_before_long = cycles

        return (
            f"Pomodoro settings updated:\n"
            f"  Work: {self.work_duration} min\n"
            f"  Short break: {self.short_break} min\n"
            f"  Long break: {self.long_break} min\n"
            f"  Cycles before long break: {self.cycles_before_long}"
        )

    # ─── Statistics ───────────────────────────────────────────
    def today_stats(self) -> str:
        """Get today's Pomodoro stats."""
        today = datetime.now().strftime("%Y-%m-%d")
        stats = self.daily_stats.get(today, {"sessions": 0, "total_min": 0, "completed": 0, "interrupted": 0})

        return (
            f"Today's Pomodoro Stats:\n"
            f"  Sessions: {stats['sessions']}\n"
            f"  Completed: {stats['completed']}\n"
            f"  Interrupted: {stats['interrupted']}\n"
            f"  Total focus time: {stats['total_min']} min ({stats['total_min'] / 60:.1f} hrs)"
        )

    def weekly_stats(self) -> str:
        """Get weekly Pomodoro statistics."""
        lines = ["Weekly Pomodoro Report:\n"]
        total_sessions = 0
        total_min = 0

        for i in range(6, -1, -1):
            day = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            day_name = (datetime.now() - timedelta(days=i)).strftime("%a")
            stats = self.daily_stats.get(day, {"sessions": 0, "total_min": 0, "completed": 0})
            bar = "█" * min(stats["sessions"], 20) + "░" * max(0, 20 - stats["sessions"])
            lines.append(f"  {day_name} {day}: [{bar}] {stats['sessions']} ({stats['total_min']}min)")
            total_sessions += stats["sessions"]
            total_min += stats["total_min"]

        lines.append(f"\n  Total: {total_sessions} sessions, {total_min} min ({total_min / 60:.1f} hrs)")
        return "\n".join(lines)

    def all_time_stats(self) -> str:
        """Get all-time Pomodoro statistics."""
        if not self.history:
            return "No Pomodoro history."

        total = len(self.history)
        completed = sum(1 for h in self.history if h.get("completed"))
        interrupted = sum(1 for h in self.history if h.get("interrupted"))
        total_min = sum(h.get("actual_work_min", 0) for h in self.history)
        total_distractions = sum(h.get("distractions", 0) for h in self.history)

        # Tasks
        from collections import Counter
        tasks = Counter(h.get("task", "(general)") for h in self.history if h.get("task"))
        top_tasks = tasks.most_common(5)

        result = (
            f"All-Time Pomodoro Stats:\n"
            f"  Total sessions: {total}\n"
            f"  Completed: {completed} ({completed / max(total, 1) * 100:.0f}%)\n"
            f"  Interrupted: {interrupted}\n"
            f"  Total focus time: {total_min:.0f} min ({total_min / 60:.1f} hrs)\n"
            f"  Total distractions: {total_distractions}\n"
            f"  Days tracked: {len(self.daily_stats)}\n"
        )

        if top_tasks:
            result += "\n  Top tasks:\n"
            for task, count in top_tasks:
                result += f"    {task}: {count} sessions\n"

        return result

    # ─── Unified Interface ────────────────────────────────
    async def pomodoro_operation(self, operation: str, **kwargs) -> str:
        """Unified Pomodoro interface."""
        if operation == "start":
            return await self.start(
                kwargs.get("task", ""),
                int(kwargs.get("work_min", 0)),
                int(kwargs.get("break_min", 0)),
                int(kwargs.get("cycles", 0)),
            )

        ops = {
            "stop": lambda: self.stop(),
            "pause": lambda: self.pause(),
            "resume": lambda: self.resume(),
            "status": lambda: self.status(),
            "distraction": lambda: self.log_distraction(),
            "settings": lambda: self.set_durations(
                int(kwargs.get("work", 0)), int(kwargs.get("short_break", 0)),
                int(kwargs.get("long_break", 0)), int(kwargs.get("cycles", 0)),
            ),
            "today": lambda: self.today_stats(),
            "weekly": lambda: self.weekly_stats(),
            "stats": lambda: self.all_time_stats(),
        }
        handler = ops.get(operation)
        if handler:
            return handler()
        return f"Unknown Pomodoro operation: {operation}. Available: start, stop, pause, resume, status, distraction, settings, today, weekly, stats"


# ─── Singleton ────────────────────────────────────────────────
pomodoro_timer = PomodoroTimer()
