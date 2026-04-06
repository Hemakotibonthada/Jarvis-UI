"""
Habit & Routine Engine — Automated daily routines, habit chains,
morning/evening routines, and behavioral tracking.
"""

import json
import asyncio
from datetime import datetime, timedelta, date
from pathlib import Path
from core.logger import get_logger
import config

log = get_logger("routines")

ROUTINES_FILE = config.DATA_DIR / "routines.json"


class RoutineStep:
    """A single step in a routine."""
    def __init__(self, name: str, action: str = "", duration_min: int = 5,
                 tool: str = "", tool_params: dict = None, prompt: str = ""):
        self.name = name
        self.action = action  # Description of what to do
        self.duration_min = duration_min
        self.tool = tool  # Optional Jarvis tool to execute
        self.tool_params = tool_params or {}
        self.prompt = prompt  # Motivational prompt or instruction

    def to_dict(self):
        return self.__dict__

    @staticmethod
    def from_dict(d) -> 'RoutineStep':
        return RoutineStep(**{k: v for k, v in d.items() if k in RoutineStep.__init__.__code__.co_varnames})


class Routine:
    """A sequence of steps that form a routine."""
    def __init__(self, name: str, description: str = "", time: str = "",
                 steps: list = None, days: str = "daily", enabled: bool = True):
        self.name = name
        self.description = description
        self.time = time  # HH:MM trigger time
        self.steps = steps or []
        self.days = days  # daily, weekdays, weekends, mon,tue,wed,...
        self.enabled = enabled
        self.created_at = datetime.now().isoformat()
        self.last_run = ""
        self.run_count = 0
        self.completion_rate = 0.0

    def to_dict(self):
        d = dict(self.__dict__)
        d['steps'] = [s.to_dict() if isinstance(s, RoutineStep) else s for s in self.steps]
        return d

    @staticmethod
    def from_dict(d) -> 'Routine':
        r = Routine(name=d.get("name", ""), description=d.get("description", ""),
                    time=d.get("time", ""), days=d.get("days", "daily"),
                    enabled=d.get("enabled", True))
        r.steps = [RoutineStep.from_dict(s) if isinstance(s, dict) else s for s in d.get("steps", [])]
        r.created_at = d.get("created_at", "")
        r.last_run = d.get("last_run", "")
        r.run_count = d.get("run_count", 0)
        r.completion_rate = d.get("completion_rate", 0.0)
        return r

    def should_run_today(self) -> bool:
        today = datetime.now()
        day_name = today.strftime("%a").lower()
        if self.days == "daily":
            return True
        elif self.days == "weekdays":
            return today.weekday() < 5
        elif self.days == "weekends":
            return today.weekday() >= 5
        else:
            return day_name in self.days.lower()

    def total_time(self) -> int:
        return sum(s.duration_min if isinstance(s, RoutineStep) else s.get("duration_min", 5) for s in self.steps)


class RoutineManager:
    """Manage daily routines and automated habits."""

    def __init__(self):
        self.routines: dict[str, Routine] = {}
        self._load()

    def _load(self):
        if ROUTINES_FILE.exists():
            try:
                data = json.loads(ROUTINES_FILE.read_text(encoding="utf-8"))
                for name, rdata in data.items():
                    self.routines[name] = Routine.from_dict(rdata)
            except (json.JSONDecodeError, OSError):
                pass

    def _save(self):
        data = {name: r.to_dict() for name, r in self.routines.items()}
        ROUTINES_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def create_routine(self, name: str, description: str = "", time: str = "",
                       days: str = "daily") -> str:
        """Create a new empty routine."""
        if name in self.routines:
            return f"Routine '{name}' already exists."
        self.routines[name] = Routine(name, description, time, [], days)
        self._save()
        return f"Routine '{name}' created. Add steps with add_step."

    def add_step(self, routine_name: str, step_name: str, action: str = "",
                 duration_min: int = 5, tool: str = "", prompt: str = "",
                 tool_params: dict = None) -> str:
        """Add a step to a routine."""
        r = self.routines.get(routine_name)
        if not r:
            return f"Routine '{routine_name}' not found."
        step = RoutineStep(step_name, action, duration_min, tool, tool_params or {}, prompt)
        r.steps.append(step)
        self._save()
        return f"Step '{step_name}' added to '{routine_name}' (total: {len(r.steps)} steps, {r.total_time()} min)."

    def remove_step(self, routine_name: str, step_index: int) -> str:
        """Remove a step from a routine."""
        r = self.routines.get(routine_name)
        if not r:
            return f"Routine '{routine_name}' not found."
        if step_index < 0 or step_index >= len(r.steps):
            return f"Invalid step index."
        removed = r.steps.pop(step_index)
        name = removed.name if isinstance(removed, RoutineStep) else removed.get("name", "?")
        self._save()
        return f"Removed step '{name}' from '{routine_name}'."

    def delete_routine(self, name: str) -> str:
        """Delete a routine."""
        if name not in self.routines:
            return f"Routine '{name}' not found."
        del self.routines[name]
        self._save()
        return f"Routine '{name}' deleted."

    def get_routine(self, name: str) -> str:
        """Get routine details."""
        r = self.routines.get(name)
        if not r:
            return f"Routine '{name}' not found."

        lines = [
            f"Routine: {r.name}",
            f"  Description: {r.description or '(none)'}",
            f"  Schedule: {r.days} at {r.time or 'any time'}",
            f"  Total time: {r.total_time()} minutes",
            f"  Steps: {len(r.steps)}",
            f"  Run count: {r.run_count}",
            f"  Last run: {r.last_run[:10] if r.last_run else 'never'}",
            f"  Enabled: {r.enabled}",
            "",
            "  Steps:",
        ]
        for i, step in enumerate(r.steps):
            if isinstance(step, RoutineStep):
                lines.append(f"    {i}. {step.name} ({step.duration_min}min) — {step.action or step.tool or 'manual'}")
                if step.prompt:
                    lines.append(f"       💡 {step.prompt}")
            else:
                lines.append(f"    {i}. {step.get('name', '?')} ({step.get('duration_min', '?')}min)")

        return "\n".join(lines)

    def list_routines(self) -> str:
        """List all routines."""
        if not self.routines:
            return "No routines defined."
        lines = []
        for name, r in self.routines.items():
            status = "✓" if r.enabled else "✗"
            today = "📅" if r.should_run_today() else "  "
            lines.append(
                f"  {status} {today} {name}: {len(r.steps)} steps, {r.total_time()}min "
                f"({r.days} at {r.time or 'any time'}) — ran {r.run_count}x"
            )
        return f"Routines ({len(self.routines)}):\n" + "\n".join(lines)

    def today_routines(self) -> str:
        """Get routines scheduled for today."""
        todays = [r for r in self.routines.values() if r.enabled and r.should_run_today()]
        if not todays:
            return "No routines scheduled for today."
        lines = [
            f"  • {r.name}: {len(r.steps)} steps, {r.total_time()}min (at {r.time or 'any time'})"
            for r in todays
        ]
        return f"Today's Routines ({len(todays)}):\n" + "\n".join(lines)

    def start_routine(self, name: str) -> str:
        """Start/display a routine for execution."""
        r = self.routines.get(name)
        if not r:
            return f"Routine '{name}' not found."

        r.last_run = datetime.now().isoformat()
        r.run_count += 1
        self._save()

        lines = [f"🚀 Starting routine: {r.name}", f"   Total time: {r.total_time()} minutes", ""]
        for i, step in enumerate(r.steps, 1):
            if isinstance(step, RoutineStep):
                lines.append(f"  Step {i}/{len(r.steps)}: {step.name} ({step.duration_min} min)")
                if step.action:
                    lines.append(f"    → {step.action}")
                if step.prompt:
                    lines.append(f"    💡 {step.prompt}")
            else:
                lines.append(f"  Step {i}: {step.get('name', '?')} ({step.get('duration_min', '?')} min)")
            lines.append("")

        return "\n".join(lines)

    def create_from_template(self, template_name: str, routine_name: str = "") -> str:
        """Create routine from template."""
        templates = {
            "morning": {
                "description": "Morning wake-up routine",
                "time": "07:00",
                "days": "daily",
                "steps": [
                    {"name": "Hydrate", "action": "Drink a glass of water", "duration_min": 2, "prompt": "Start the day hydrated!"},
                    {"name": "Stretch", "action": "5-minute morning stretch", "duration_min": 5, "prompt": "Loosen those muscles!"},
                    {"name": "Briefing", "action": "Daily briefing from Jarvis", "duration_min": 3, "tool": "get_daily_briefing"},
                    {"name": "Weather", "action": "Check the weather", "duration_min": 1, "tool": "get_weather", "tool_params": {"location": "auto"}},
                    {"name": "Tasks", "action": "Review today's tasks", "duration_min": 3, "tool": "task_operation", "tool_params": {"operation": "today"}},
                    {"name": "Emails", "action": "Check emails", "duration_min": 5, "tool": "count_unread_emails"},
                ],
            },
            "evening": {
                "description": "Evening wind-down routine",
                "time": "21:00",
                "days": "daily",
                "steps": [
                    {"name": "Day Review", "action": "Review completed tasks", "duration_min": 5, "tool": "task_operation", "tool_params": {"operation": "summary"}},
                    {"name": "Plan Tomorrow", "action": "Review tomorrow's schedule", "duration_min": 5, "tool": "calendar_operation", "tool_params": {"operation": "list", "days": "2"}},
                    {"name": "Health Log", "action": "Log water and exercise", "duration_min": 2, "prompt": "Did you stay hydrated and active today?"},
                    {"name": "Mood Check", "action": "Log mood for the day", "duration_min": 1, "prompt": "How are you feeling?"},
                    {"name": "Wind Down", "action": "Prepare for sleep", "duration_min": 10, "prompt": "No screens for 30 minutes before bed."},
                ],
            },
            "work_start": {
                "description": "Start of work day routine",
                "time": "09:00",
                "days": "weekdays",
                "steps": [
                    {"name": "System Check", "action": "Check system health", "duration_min": 1, "tool": "system_info"},
                    {"name": "Emails", "action": "Process emails", "duration_min": 10, "tool": "read_emails", "tool_params": {"count": 5}},
                    {"name": "Tasks", "action": "Plan the day", "duration_min": 5, "tool": "task_operation", "tool_params": {"operation": "today"}},
                    {"name": "Start Timer", "action": "Begin work tracking", "duration_min": 1, "tool": "task_operation", "tool_params": {"operation": "start_timer"}},
                ],
            },
            "weekly_review": {
                "description": "Weekly review and planning",
                "time": "10:00",
                "days": "sun",
                "steps": [
                    {"name": "Task Review", "action": "Review all tasks", "duration_min": 10, "tool": "task_operation", "tool_params": {"operation": "summary"}},
                    {"name": "Health Review", "action": "Weekly health report", "duration_min": 5, "tool": "health_operation", "tool_params": {"operation": "weekly"}},
                    {"name": "Backup", "action": "Run system backup", "duration_min": 5, "tool": "backup_operation", "tool_params": {"operation": "create", "source": "."}},
                    {"name": "Cleanup", "action": "Clean up disk", "duration_min": 5, "tool": "optimizer_operation", "tool_params": {"operation": "cleanup"}},
                    {"name": "Plan Week", "action": "Plan next week", "duration_min": 15, "prompt": "What are your top priorities for next week?"},
                ],
            },
            "fitness": {
                "description": "Workout routine",
                "time": "06:30",
                "days": "weekdays",
                "steps": [
                    {"name": "Warm Up", "action": "Light cardio warm up", "duration_min": 5, "prompt": "Get the blood flowing!"},
                    {"name": "Strength", "action": "Strength training exercises", "duration_min": 20, "prompt": "Push yourself, but maintain form!"},
                    {"name": "Cardio", "action": "High-intensity cardio", "duration_min": 15, "prompt": "Keep your heart rate up!"},
                    {"name": "Cool Down", "action": "Stretching and cool down", "duration_min": 5, "prompt": "Great work! Don't skip the stretch."},
                    {"name": "Log", "action": "Log exercise", "duration_min": 1, "tool": "health_operation", "tool_params": {"operation": "exercise", "type": "workout", "duration": "45"}},
                    {"name": "Hydrate", "action": "Drink water", "duration_min": 1, "tool": "health_operation", "tool_params": {"operation": "water", "glasses": "2"}},
                ],
            },
        }

        template = templates.get(template_name)
        if not template:
            return f"Unknown template. Available: {', '.join(templates.keys())}"

        name = routine_name or template_name
        if name in self.routines:
            return f"Routine '{name}' already exists."

        routine = Routine(
            name=name, description=template["description"],
            time=template["time"], days=template["days"],
        )
        routine.steps = [RoutineStep.from_dict(s) for s in template["steps"]]
        self.routines[name] = routine
        self._save()

        return f"Routine '{name}' created from template '{template_name}' ({len(routine.steps)} steps, {routine.total_time()}min)."

    def toggle_routine(self, name: str) -> str:
        """Enable/disable a routine."""
        r = self.routines.get(name)
        if not r:
            return f"Routine '{name}' not found."
        r.enabled = not r.enabled
        self._save()
        return f"Routine '{name}' {'enabled' if r.enabled else 'disabled'}."

    # ─── Unified Interface ────────────────────────────────────
    def routine_operation(self, operation: str, **kwargs) -> str:
        """Unified routine management."""
        name = kwargs.get("name", "")
        ops = {
            "create": lambda: self.create_routine(name, kwargs.get("description", ""), kwargs.get("time", ""), kwargs.get("days", "daily")),
            "add_step": lambda: self.add_step(name, kwargs.get("step_name", ""), kwargs.get("action", ""), int(kwargs.get("duration_min", 5)), kwargs.get("tool", ""), kwargs.get("prompt", "")),
            "remove_step": lambda: self.remove_step(name, int(kwargs.get("step_index", 0))),
            "delete": lambda: self.delete_routine(name),
            "get": lambda: self.get_routine(name),
            "list": lambda: self.list_routines(),
            "today": lambda: self.today_routines(),
            "start": lambda: self.start_routine(name),
            "template": lambda: self.create_from_template(kwargs.get("template", ""), name),
            "toggle": lambda: self.toggle_routine(name),
            "templates": lambda: "Available templates: morning, evening, work_start, weekly_review, fitness",
        }
        handler = ops.get(operation)
        if handler:
            return handler()
        return f"Unknown routine operation: {operation}. Available: {', '.join(ops.keys())}"


# ─── Singleton ────────────────────────────────────────────────
routine_manager = RoutineManager()
