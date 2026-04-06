"""
Journal Module — Personal daily journaling with prompts, mood tracking,
gratitude lists, tagging, and reflective analysis.
"""

import json
import random
from datetime import datetime, timedelta, date
from pathlib import Path
from collections import Counter
from core.logger import get_logger
import config

log = get_logger("journal")

JOURNAL_FILE = config.DATA_DIR / "journal.json"


class JournalEntry:
    """A single journal entry."""
    def __init__(self, content: str, mood: str = "", title: str = "",
                 tags: str = "", category: str = "daily",
                 gratitude: list = None, highlights: list = None):
        self.id = 0
        self.title = title
        self.content = content
        self.mood = mood  # happy, content, neutral, anxious, sad, angry, inspired, tired
        self.tags = tags
        self.category = category  # daily, reflection, gratitude, dream, idea, goal_review
        self.gratitude = gratitude or []
        self.highlights = highlights or []
        self.date = datetime.now().strftime("%Y-%m-%d")
        self.time = datetime.now().strftime("%H:%M")
        self.created_at = datetime.now().isoformat()
        self.word_count = len(content.split())
        self.weather = ""
        self.energy_level = 0  # 1-5

    def to_dict(self):
        return self.__dict__

    @staticmethod
    def from_dict(d) -> 'JournalEntry':
        j = JournalEntry(d.get("content", ""))
        for k, v in d.items():
            if hasattr(j, k):
                setattr(j, k, v)
        return j

    def format_display(self) -> str:
        mood_emojis = {
            "happy": "😊", "content": "🙂", "neutral": "😐", "anxious": "😰",
            "sad": "😢", "angry": "😠", "inspired": "🌟", "tired": "😴",
            "excited": "🎉", "peaceful": "🧘", "grateful": "🙏", "focused": "🎯",
        }
        emoji = mood_emojis.get(self.mood, "📝")

        lines = [f"  {emoji} #{self.id} — {self.date} {self.time}"]
        if self.title:
            lines.append(f"    📌 {self.title}")

        lines.append(f"    {self.content[:300]}")
        if len(self.content) > 300:
            lines.append(f"    ... ({self.word_count} words total)")

        if self.gratitude:
            lines.append(f"    🙏 Gratitude: {', '.join(self.gratitude[:5])}")
        if self.highlights:
            lines.append(f"    ⭐ Highlights: {', '.join(self.highlights[:5])}")
        if self.tags:
            lines.append(f"    🏷️ Tags: {self.tags}")
        if self.mood:
            lines.append(f"    Mood: {self.mood} | Energy: {'⚡' * self.energy_level if self.energy_level else 'N/A'}")

        return "\n".join(lines)


class JournalManager:
    """Personal journal management system."""

    WRITING_PROMPTS = [
        "What made you smile today?",
        "What's one thing you learned today?",
        "Describe a challenge you faced and how you handled it.",
        "What are you looking forward to tomorrow?",
        "If you could change one thing about today, what would it be?",
        "What's something you're grateful for right now?",
        "Describe your ideal day. How close was today?",
        "What conversation stood out to you today?",
        "What's a skill you'd like to develop? Why?",
        "Write about a person who inspired you recently.",
        "What's your biggest accomplishment this week?",
        "If you could give your past self one piece of advice, what would it be?",
        "What's causing you stress? How can you address it?",
        "Describe a moment of peace you experienced today.",
        "What boundaries do you need to set or maintain?",
        "What are three things going well in your life right now?",
        "What would you do if you had no fear?",
        "Write a letter to your future self.",
        "What habit would you like to build or break?",
        "How have you grown in the past month?",
        "What does success mean to you today?",
        "Describe your perfect morning routine.",
        "What book, movie, or song has been on your mind?",
        "What act of kindness did you witness or perform today?",
        "What's one thing you want to remember about this period of your life?",
    ]

    GRATITUDE_PROMPTS = [
        "Name 3 things you're grateful for today.",
        "Who is someone you appreciate and why?",
        "What simple pleasure did you enjoy today?",
        "What technology are you grateful for?",
        "What aspect of your health are you thankful for?",
        "What friendship are you most grateful for right now?",
        "What's a recent experience you're glad you had?",
        "What comfort do you have that others might not?",
    ]

    def __init__(self):
        self.entries: list[JournalEntry] = []
        self._next_id = 1
        self._load()

    def _load(self):
        if JOURNAL_FILE.exists():
            try:
                data = json.loads(JOURNAL_FILE.read_text(encoding="utf-8"))
                self.entries = [JournalEntry.from_dict(e) for e in data.get("entries", [])]
                self._next_id = data.get("next_id", 1)
            except (json.JSONDecodeError, OSError):
                pass

    def _save(self):
        data = {"entries": [e.to_dict() for e in self.entries], "next_id": self._next_id}
        JOURNAL_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def write_entry(self, content: str, mood: str = "", title: str = "",
                    tags: str = "", category: str = "daily",
                    gratitude: str = "", highlights: str = "",
                    energy_level: int = 0) -> str:
        """Write a new journal entry."""
        gratitude_list = [g.strip() for g in gratitude.split(",") if g.strip()] if gratitude else []
        highlight_list = [h.strip() for h in highlights.split(",") if h.strip()] if highlights else []

        entry = JournalEntry(content, mood, title, tags, category,
                            gratitude_list, highlight_list)
        entry.energy_level = energy_level
        entry.id = self._next_id
        self._next_id += 1
        self.entries.append(entry)
        self._save()

        result = f"Journal entry saved: #{entry.id} ({entry.word_count} words)"
        if mood:
            result += f" — Mood: {mood}"

        # Check streaks
        streak = self._get_streak()
        if streak > 1:
            result += f"\n  🔥 Writing streak: {streak} days!"

        return result

    def get_entry(self, entry_id: int) -> str:
        for e in self.entries:
            if e.id == entry_id:
                return e.format_display()
        return f"Entry #{entry_id} not found."

    def get_today(self) -> str:
        """Get today's journal entry."""
        today = datetime.now().strftime("%Y-%m-%d")
        todays = [e for e in self.entries if e.date == today]
        if not todays:
            return "No journal entry for today. Want a writing prompt? Use get_prompt."
        lines = [e.format_display() for e in todays]
        return f"Today's Journal:\n\n" + "\n\n".join(lines)

    def list_entries(self, days: int = 30, category: str = "",
                     mood: str = "") -> str:
        """List recent journal entries."""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        filtered = [e for e in self.entries if e.date >= cutoff]
        if category:
            filtered = [e for e in filtered if e.category == category]
        if mood:
            filtered = [e for e in filtered if e.mood == mood]

        if not filtered:
            return "No journal entries found."

        lines = [e.format_display() for e in reversed(filtered[-20:])]
        return f"Journal Entries ({len(filtered)}):\n\n" + "\n\n".join(lines)

    def search(self, query: str) -> str:
        q = query.lower()
        matches = [e for e in self.entries if
                   q in e.content.lower() or q in e.title.lower() or
                   q in e.tags.lower() or q in e.mood.lower()]
        if not matches:
            return f"No entries matching '{query}'."
        lines = [f"  #{e.id} {e.date} — {e.title or e.content[:50]}..." for e in matches[-15:]]
        return f"Journal search ({len(matches)} matches):\n" + "\n".join(lines)

    def delete_entry(self, entry_id: int) -> str:
        for i, e in enumerate(self.entries):
            if e.id == entry_id:
                self.entries.pop(i)
                self._save()
                return f"Entry #{entry_id} deleted."
        return f"Entry #{entry_id} not found."

    def get_prompt(self, prompt_type: str = "writing") -> str:
        """Get a random writing/gratitude prompt."""
        if prompt_type == "gratitude":
            prompt = random.choice(self.GRATITUDE_PROMPTS)
        else:
            prompt = random.choice(self.WRITING_PROMPTS)
        return f"📝 Writing Prompt:\n\n  \"{prompt}\"\n\n  Use write_entry to journal your thoughts."

    def _get_streak(self) -> int:
        """Calculate current writing streak."""
        dates = sorted(set(e.date for e in self.entries), reverse=True)
        if not dates:
            return 0

        today = datetime.now().strftime("%Y-%m-%d")
        if dates[0] != today:
            return 0

        streak = 1
        for i in range(1, len(dates)):
            prev = datetime.strptime(dates[i - 1], "%Y-%m-%d")
            curr = datetime.strptime(dates[i], "%Y-%m-%d")
            if (prev - curr).days == 1:
                streak += 1
            else:
                break
        return streak

    def mood_analysis(self, days: int = 30) -> str:
        """Analyze mood patterns."""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        recent = [e for e in self.entries if e.date >= cutoff and e.mood]
        if not recent:
            return "Not enough mood data. Log mood with your entries."

        mood_counts = Counter(e.mood for e in recent)
        total = len(recent)

        lines = [f"Mood Analysis (last {days} days, {total} entries):\n"]
        mood_emojis = {
            "happy": "😊", "content": "🙂", "neutral": "😐", "anxious": "😰",
            "sad": "😢", "angry": "😠", "inspired": "🌟", "tired": "😴",
            "excited": "🎉", "peaceful": "🧘", "grateful": "🙏", "focused": "🎯",
        }

        for mood, count in mood_counts.most_common():
            pct = count / total * 100
            emoji = mood_emojis.get(mood, "📝")
            bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
            lines.append(f"  {emoji} {mood:<12} [{bar}] {pct:.0f}% ({count})")

        # Energy analysis
        energy_entries = [e for e in recent if e.energy_level > 0]
        if energy_entries:
            avg_energy = sum(e.energy_level for e in energy_entries) / len(energy_entries)
            lines.append(f"\n  Average energy: {'⚡' * round(avg_energy)} ({avg_energy:.1f}/5)")

        return "\n".join(lines)

    def writing_stats(self) -> str:
        """Get overall journaling statistics."""
        if not self.entries:
            return "No journal entries yet."

        total = len(self.entries)
        total_words = sum(e.word_count for e in self.entries)
        avg_words = total_words / total
        days_with_entries = len(set(e.date for e in self.entries))
        streak = self._get_streak()

        categories = Counter(e.category for e in self.entries)
        moods = Counter(e.mood for e in self.entries if e.mood)

        longest = max(self.entries, key=lambda e: e.word_count)

        return (
            f"Journal Statistics:\n"
            f"  Total entries: {total}\n"
            f"  Total words: {total_words:,}\n"
            f"  Average length: {avg_words:.0f} words/entry\n"
            f"  Days journaled: {days_with_entries}\n"
            f"  Current streak: {streak} days {'🔥' if streak > 3 else ''}\n"
            f"  Longest entry: #{longest.id} ({longest.word_count} words)\n"
            f"\n  Categories: {', '.join(f'{k}({v})' for k, v in categories.most_common(5))}\n"
            f"  Top moods: {', '.join(f'{k}({v})' for k, v in moods.most_common(5))}"
        )

    def export_markdown(self, file_path: str = "", days: int = 365) -> str:
        """Export journal entries as markdown."""
        if not file_path:
            file_path = str(config.GENERATED_DIR / "journal_export.md")
        p = Path(file_path)

        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        entries = [e for e in self.entries if e.date >= cutoff]

        lines = [f"# Journal Export\n\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n---\n"]
        for e in entries:
            lines.append(f"## {e.date} {e.time}" + (f" — {e.title}" if e.title else ""))
            if e.mood:
                lines.append(f"**Mood:** {e.mood}" + (f" | **Energy:** {'⚡' * e.energy_level}" if e.energy_level else ""))
            lines.append(f"\n{e.content}\n")
            if e.gratitude:
                lines.append("**Gratitude:** " + ", ".join(e.gratitude))
            if e.highlights:
                lines.append("**Highlights:** " + ", ".join(e.highlights))
            lines.append("\n---\n")

        p.write_text("\n".join(lines), encoding="utf-8")
        return f"Exported {len(entries)} entries to {p}"

    def on_this_day(self) -> str:
        """Show entries from this day in previous years."""
        today_md = datetime.now().strftime("%m-%d")
        matches = [e for e in self.entries if e.date[5:] == today_md and e.date < datetime.now().strftime("%Y-%m-%d")]

        if not matches:
            return "No entries from this day in previous years."

        lines = ["📅 On This Day:\n"]
        for e in matches:
            lines.append(f"  {e.date}: {e.content[:100]}...")
        return "\n".join(lines)

    # ─── Unified Interface ────────────────────────────────
    def journal_operation(self, operation: str, **kwargs) -> str:
        ops = {
            "write": lambda: self.write_entry(kwargs.get("content", ""), kwargs.get("mood", ""), kwargs.get("title", ""), kwargs.get("tags", ""), kwargs.get("category", "daily"), kwargs.get("gratitude", ""), kwargs.get("highlights", ""), int(kwargs.get("energy_level", 0))),
            "get": lambda: self.get_entry(int(kwargs.get("entry_id", 0))),
            "today": lambda: self.get_today(),
            "list": lambda: self.list_entries(int(kwargs.get("days", 30)), kwargs.get("category", ""), kwargs.get("mood", "")),
            "search": lambda: self.search(kwargs.get("query", "")),
            "delete": lambda: self.delete_entry(int(kwargs.get("entry_id", 0))),
            "prompt": lambda: self.get_prompt(kwargs.get("type", "writing")),
            "mood": lambda: self.mood_analysis(int(kwargs.get("days", 30))),
            "stats": lambda: self.writing_stats(),
            "export": lambda: self.export_markdown(kwargs.get("file_path", "")),
            "on_this_day": lambda: self.on_this_day(),
        }
        handler = ops.get(operation)
        if handler:
            return handler()
        return f"Unknown journal operation: {operation}. Available: {', '.join(ops.keys())}"


journal_manager = JournalManager()
