"""
Calendar & Event Manager — Full calendar system with recurring events,
reminders, iCal export, and time zone support.
"""

import json
import re
from datetime import datetime, timedelta, date
from pathlib import Path
from core.logger import get_logger
import config

log = get_logger("calendar")

CALENDAR_FILE = config.DATA_DIR / "calendar.json"


class CalendarEvent:
    """Represents a calendar event."""

    def __init__(self, title: str, start: str, end: str = "", description: str = "",
                 location: str = "", category: str = "", recurrence: str = "",
                 reminder_minutes: int = 0, all_day: bool = False,
                 attendees: list = None, color: str = ""):
        self.id = 0  # Set when saved
        self.title = title
        self.start = start  # ISO format: 2025-01-15T09:00
        self.end = end
        self.description = description
        self.location = location
        self.category = category
        self.recurrence = recurrence  # none, daily, weekly, monthly, yearly
        self.reminder_minutes = reminder_minutes
        self.all_day = all_day
        self.attendees = attendees or []
        self.color = color
        self.created_at = datetime.now().isoformat()
        self.cancelled = False

    def to_dict(self) -> dict:
        return {
            "id": self.id, "title": self.title, "start": self.start,
            "end": self.end, "description": self.description,
            "location": self.location, "category": self.category,
            "recurrence": self.recurrence, "reminder_minutes": self.reminder_minutes,
            "all_day": self.all_day, "attendees": self.attendees,
            "color": self.color, "created_at": self.created_at,
            "cancelled": self.cancelled,
        }

    @staticmethod
    def from_dict(data: dict) -> 'CalendarEvent':
        event = CalendarEvent(
            title=data.get("title", ""),
            start=data.get("start", ""),
            end=data.get("end", ""),
            description=data.get("description", ""),
            location=data.get("location", ""),
            category=data.get("category", ""),
            recurrence=data.get("recurrence", ""),
            reminder_minutes=data.get("reminder_minutes", 0),
            all_day=data.get("all_day", False),
            attendees=data.get("attendees", []),
            color=data.get("color", ""),
        )
        event.id = data.get("id", 0)
        event.created_at = data.get("created_at", "")
        event.cancelled = data.get("cancelled", False)
        return event

    def format_display(self) -> str:
        """Format event for display."""
        try:
            start_dt = datetime.fromisoformat(self.start)
            start_str = start_dt.strftime("%b %d, %Y %I:%M %p")
        except (ValueError, TypeError):
            start_str = self.start

        parts = [f"  #{self.id} {self.title}"]
        parts.append(f"    When: {start_str}")
        if self.end:
            try:
                end_dt = datetime.fromisoformat(self.end)
                parts.append(f"    Until: {end_dt.strftime('%I:%M %p')}")
            except (ValueError, TypeError):
                parts.append(f"    Until: {self.end}")
        if self.location:
            parts.append(f"    Where: {self.location}")
        if self.description:
            parts.append(f"    Notes: {self.description[:100]}")
        if self.recurrence and self.recurrence != "none":
            parts.append(f"    Repeats: {self.recurrence}")
        if self.attendees:
            parts.append(f"    Attendees: {', '.join(self.attendees[:5])}")
        if self.category:
            parts.append(f"    Category: {self.category}")
        if self.cancelled:
            parts.append("    [CANCELLED]")
        return "\n".join(parts)


class CalendarManager:
    """Full-featured calendar management."""

    def __init__(self):
        self.events: list[CalendarEvent] = []
        self._next_id = 1
        self._load()

    def _load(self):
        """Load events from disk."""
        if CALENDAR_FILE.exists():
            try:
                data = json.loads(CALENDAR_FILE.read_text(encoding="utf-8"))
                self.events = [CalendarEvent.from_dict(e) for e in data.get("events", [])]
                self._next_id = data.get("next_id", 1)
            except (json.JSONDecodeError, OSError):
                pass

    def _save(self):
        """Save events to disk."""
        data = {
            "events": [e.to_dict() for e in self.events],
            "next_id": self._next_id,
        }
        CALENDAR_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def add_event(self, title: str, start: str, end: str = "",
                  description: str = "", location: str = "",
                  category: str = "", recurrence: str = "none",
                  reminder_minutes: int = 0, all_day: bool = False,
                  attendees: str = "") -> str:
        """Add a new calendar event."""
        # Parse start date/time
        start = self._parse_datetime(start)
        if end:
            end = self._parse_datetime(end)

        attendee_list = [a.strip() for a in attendees.split(",") if a.strip()] if attendees else []

        event = CalendarEvent(
            title=title, start=start, end=end,
            description=description, location=location,
            category=category, recurrence=recurrence,
            reminder_minutes=reminder_minutes,
            all_day=all_day, attendees=attendee_list,
        )
        event.id = self._next_id
        self._next_id += 1
        self.events.append(event)
        self._save()

        result = f"Event created: #{event.id} '{title}'\n"
        result += f"  Date: {start}"
        if end:
            result += f" to {end}"
        if location:
            result += f"\n  Location: {location}"
        if recurrence != "none":
            result += f"\n  Repeats: {recurrence}"
        return result

    def _parse_datetime(self, dt_str: str) -> str:
        """Parse a flexible datetime string to ISO format."""
        dt_str = dt_str.strip()

        # If already ISO-like, return as-is
        if re.match(r'\d{4}-\d{2}-\d{2}', dt_str):
            return dt_str

        # Try natural-ish formats
        formats = [
            "%m/%d/%Y %I:%M %p", "%m/%d/%Y %H:%M",
            "%m/%d/%Y", "%d/%m/%Y",
            "%B %d, %Y %I:%M %p", "%B %d, %Y",
            "%b %d, %Y %I:%M %p", "%b %d, %Y",
            "%Y-%m-%d %H:%M", "%Y-%m-%d %I:%M %p",
        ]
        for fmt in formats:
            try:
                parsed = datetime.strptime(dt_str, fmt)
                return parsed.isoformat()
            except ValueError:
                continue

        # Relative dates
        lower = dt_str.lower()
        now = datetime.now()
        if lower == "today":
            return now.strftime("%Y-%m-%dT09:00")
        elif lower == "tomorrow":
            return (now + timedelta(days=1)).strftime("%Y-%m-%dT09:00")
        elif lower == "next week":
            return (now + timedelta(weeks=1)).strftime("%Y-%m-%dT09:00")
        elif lower.startswith("in "):
            parts = lower[3:].split()
            if len(parts) >= 2:
                try:
                    num = int(parts[0])
                    unit = parts[1]
                    if "hour" in unit:
                        return (now + timedelta(hours=num)).isoformat()[:16]
                    elif "day" in unit:
                        return (now + timedelta(days=num)).isoformat()[:16]
                    elif "week" in unit:
                        return (now + timedelta(weeks=num)).isoformat()[:16]
                    elif "month" in unit:
                        return (now + timedelta(days=num * 30)).isoformat()[:16]
                except ValueError:
                    pass

        return dt_str  # Return as-is if can't parse

    def get_event(self, event_id: int) -> str:
        """Get details of an event."""
        for event in self.events:
            if event.id == event_id:
                return event.format_display()
        return f"Event #{event_id} not found."

    def update_event(self, event_id: int, **kwargs) -> str:
        """Update an event's properties."""
        for event in self.events:
            if event.id == event_id:
                for key, value in kwargs.items():
                    if hasattr(event, key) and value:
                        if key == "start" or key == "end":
                            value = self._parse_datetime(value)
                        setattr(event, key, value)
                self._save()
                return f"Event #{event_id} updated."
        return f"Event #{event_id} not found."

    def cancel_event(self, event_id: int) -> str:
        """Cancel an event (mark as cancelled, don't delete)."""
        for event in self.events:
            if event.id == event_id:
                event.cancelled = True
                self._save()
                return f"Event #{event_id} '{event.title}' cancelled."
        return f"Event #{event_id} not found."

    def delete_event(self, event_id: int) -> str:
        """Permanently delete an event."""
        for i, event in enumerate(self.events):
            if event.id == event_id:
                title = event.title
                self.events.pop(i)
                self._save()
                return f"Event #{event_id} '{title}' deleted."
        return f"Event #{event_id} not found."

    def list_events(self, days: int = 30, category: str = "",
                    include_cancelled: bool = False) -> str:
        """List upcoming events."""
        now = datetime.now()
        cutoff = now + timedelta(days=days)

        filtered = []
        for event in self.events:
            if event.cancelled and not include_cancelled:
                continue
            if category and event.category != category:
                continue
            try:
                event_dt = datetime.fromisoformat(event.start)
                if now - timedelta(hours=1) <= event_dt <= cutoff:
                    filtered.append((event_dt, event))
            except (ValueError, TypeError):
                filtered.append((now, event))

        # Include recurring events
        for event in self.events:
            if event.cancelled or (category and event.category != category):
                continue
            if event.recurrence and event.recurrence != "none":
                try:
                    start_dt = datetime.fromisoformat(event.start)
                    occurrences = self._generate_recurrences(start_dt, event.recurrence, now, cutoff)
                    for occ in occurrences:
                        if (occ, event) not in filtered:
                            # Create a display copy with the occurrence date
                            display_event = CalendarEvent.from_dict(event.to_dict())
                            display_event.start = occ.isoformat()
                            filtered.append((occ, display_event))
                except (ValueError, TypeError):
                    pass

        filtered.sort(key=lambda x: x[0])

        if not filtered:
            return f"No upcoming events in the next {days} days."

        lines = [event.format_display() for _, event in filtered[:30]]

        return f"Upcoming Events (next {days} days, {len(filtered)} found):\n\n" + "\n\n".join(lines)

    def _generate_recurrences(self, start: datetime, recurrence: str,
                               range_start: datetime, range_end: datetime) -> list[datetime]:
        """Generate recurring event dates within a range."""
        deltas = {
            "daily": timedelta(days=1),
            "weekly": timedelta(weeks=1),
            "biweekly": timedelta(weeks=2),
            "monthly": timedelta(days=30),
            "yearly": timedelta(days=365),
        }
        delta = deltas.get(recurrence)
        if not delta:
            return []

        occurrences = []
        current = start
        while current <= range_end:
            if current >= range_start:
                occurrences.append(current)
            current += delta
            if len(occurrences) > 50:
                break

        return occurrences

    def today(self) -> str:
        """Get today's events."""
        today_str = datetime.now().strftime("%Y-%m-%d")
        todays = []
        for event in self.events:
            if not event.cancelled and event.start.startswith(today_str):
                todays.append(event)

        if not todays:
            return "No events today."

        lines = [event.format_display() for event in todays]
        return f"Today's Events ({len(todays)}):\n\n" + "\n\n".join(lines)

    def this_week(self) -> str:
        """Get this week's events."""
        return self.list_events(days=7)

    def search_events(self, query: str) -> str:
        """Search events by title, description, or location."""
        query_lower = query.lower()
        matches = [
            e for e in self.events
            if not e.cancelled and (
                query_lower in e.title.lower() or
                query_lower in e.description.lower() or
                query_lower in e.location.lower()
            )
        ]

        if not matches:
            return f"No events matching '{query}'."

        lines = [e.format_display() for e in matches[:20]]
        return f"Events matching '{query}' ({len(matches)}):\n\n" + "\n\n".join(lines)

    def categories(self) -> str:
        """List event categories."""
        cats = {}
        for e in self.events:
            if e.category and not e.cancelled:
                cats[e.category] = cats.get(e.category, 0) + 1

        if not cats:
            return "No event categories."

        lines = [f"  {cat}: {count} events" for cat, count in sorted(cats.items())]
        return "Event Categories:\n" + "\n".join(lines)

    def export_ical(self, file_path: str = "") -> str:
        """Export events to iCal format (.ics)."""
        if not file_path:
            file_path = str(config.GENERATED_DIR / "jarvis_calendar.ics")

        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//JARVIS//Calendar//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
        ]

        for event in self.events:
            if event.cancelled:
                continue
            try:
                start_dt = datetime.fromisoformat(event.start)
                start_ical = start_dt.strftime("%Y%m%dT%H%M%S")
            except (ValueError, TypeError):
                continue

            lines.append("BEGIN:VEVENT")
            lines.append(f"UID:{event.id}@jarvis")
            lines.append(f"DTSTART:{start_ical}")
            if event.end:
                try:
                    end_dt = datetime.fromisoformat(event.end)
                    lines.append(f"DTEND:{end_dt.strftime('%Y%m%dT%H%M%S')}")
                except (ValueError, TypeError):
                    pass
            lines.append(f"SUMMARY:{event.title}")
            if event.description:
                lines.append(f"DESCRIPTION:{event.description[:200]}")
            if event.location:
                lines.append(f"LOCATION:{event.location}")
            if event.category:
                lines.append(f"CATEGORIES:{event.category}")
            lines.append("END:VEVENT")

        lines.append("END:VCALENDAR")

        p = Path(file_path)
        p.write_text("\r\n".join(lines), encoding="utf-8")
        return f"Calendar exported to: {p} ({len(self.events)} events)"

    def get_free_slots(self, date_str: str = "", duration_hours: int = 1) -> str:
        """Find free time slots on a given date."""
        if not date_str:
            target = datetime.now().date()
        else:
            try:
                target = datetime.fromisoformat(self._parse_datetime(date_str)).date()
            except (ValueError, TypeError):
                target = datetime.now().date()

        # Collect busy times
        busy = []
        for event in self.events:
            if event.cancelled:
                continue
            try:
                start = datetime.fromisoformat(event.start)
                if start.date() == target:
                    end_str = event.end or (start + timedelta(hours=1)).isoformat()
                    end = datetime.fromisoformat(end_str)
                    busy.append((start.hour * 60 + start.minute, end.hour * 60 + end.minute))
            except (ValueError, TypeError):
                continue

        busy.sort()

        # Find free slots between 8:00 and 20:00
        work_start = 8 * 60  # 8:00 AM
        work_end = 20 * 60   # 8:00 PM
        duration_min = duration_hours * 60

        free_slots = []
        current = work_start

        for busy_start, busy_end in busy:
            if current + duration_min <= busy_start:
                free_slots.append((current, busy_start))
            current = max(current, busy_end)

        if current + duration_min <= work_end:
            free_slots.append((current, work_end))

        if not free_slots:
            return f"No free slots of {duration_hours}h on {target}."

        lines = []
        for start, end in free_slots:
            s = f"{start // 60:02d}:{start % 60:02d}"
            e = f"{end // 60:02d}:{end % 60:02d}"
            lines.append(f"  {s} - {e}")

        return f"Free slots on {target} ({duration_hours}h minimum):\n" + "\n".join(lines)

    def get_summary(self) -> str:
        """Calendar summary/stats."""
        total = len(self.events)
        active = sum(1 for e in self.events if not e.cancelled)
        cancelled = total - active
        recurring = sum(1 for e in self.events if e.recurrence and e.recurrence != "none")

        now = datetime.now()
        today_count = sum(1 for e in self.events if not e.cancelled and e.start.startswith(now.strftime("%Y-%m-%d")))
        this_week = sum(1 for e in self.events if not e.cancelled and self._is_this_week(e.start))

        return (
            f"Calendar Summary:\n"
            f"  Total events: {total}\n"
            f"  Active: {active}\n"
            f"  Cancelled: {cancelled}\n"
            f"  Recurring: {recurring}\n"
            f"  Today: {today_count}\n"
            f"  This week: {this_week}"
        )

    def _is_this_week(self, dt_str: str) -> bool:
        try:
            dt = datetime.fromisoformat(dt_str)
            now = datetime.now()
            start_of_week = now - timedelta(days=now.weekday())
            end_of_week = start_of_week + timedelta(days=7)
            return start_of_week <= dt <= end_of_week
        except (ValueError, TypeError):
            return False

    # ─── Unified Interface ────────────────────────────────────
    def calendar_operation(self, operation: str, **kwargs) -> str:
        """Unified calendar management."""
        ops = {
            "add": lambda: self.add_event(
                kwargs.get("title", ""), kwargs.get("start", ""),
                kwargs.get("end", ""), kwargs.get("description", ""),
                kwargs.get("location", ""), kwargs.get("category", ""),
                kwargs.get("recurrence", "none"),
                int(kwargs.get("reminder_minutes", 0)),
                kwargs.get("all_day", False),
                kwargs.get("attendees", ""),
            ),
            "get": lambda: self.get_event(int(kwargs.get("event_id", 0))),
            "update": lambda: self.update_event(int(kwargs.get("event_id", 0)), **{k: v for k, v in kwargs.items() if k != "operation" and k != "event_id"}),
            "cancel": lambda: self.cancel_event(int(kwargs.get("event_id", 0))),
            "delete": lambda: self.delete_event(int(kwargs.get("event_id", 0))),
            "list": lambda: self.list_events(int(kwargs.get("days", 30)), kwargs.get("category", "")),
            "today": lambda: self.today(),
            "week": lambda: self.this_week(),
            "search": lambda: self.search_events(kwargs.get("query", "")),
            "categories": lambda: self.categories(),
            "export": lambda: self.export_ical(kwargs.get("file_path", "")),
            "free_slots": lambda: self.get_free_slots(kwargs.get("date", ""), int(kwargs.get("duration_hours", 1))),
            "summary": lambda: self.get_summary(),
        }
        handler = ops.get(operation)
        if handler:
            return handler()
        return f"Unknown calendar operation: {operation}. Available: {', '.join(ops.keys())}"


# ─── Singleton ────────────────────────────────────────────────
calendar_manager = CalendarManager()
