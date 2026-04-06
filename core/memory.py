"""
Conversation memory with persistence, long-term facts, and user preferences.
"""

import json
import time
from collections import deque
from datetime import datetime
from pathlib import Path


class ConversationMemory:
    """Short-term conversation memory with sliding window."""

    def __init__(self, max_messages: int = 50):
        self.max_messages = max_messages
        self._messages: deque = deque(maxlen=max_messages)

    def add(self, role: str, content: str):
        self._messages.append({"role": role, "content": content})

    def get_messages(self) -> list[dict]:
        return list(self._messages)

    def clear(self):
        self._messages.clear()

    def get_last(self, n: int = 5) -> list[dict]:
        return list(self._messages)[-n:]

    def to_dict(self) -> list[dict]:
        return list(self._messages)


class PersistentMemory:
    """Long-term memory stored on disk — survives restarts."""

    def __init__(self, memory_dir: Path):
        self.memory_dir = memory_dir
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.facts_file = self.memory_dir / "facts.json"
        self.prefs_file = self.memory_dir / "user_preferences.json"
        self.history_file = self.memory_dir / "conversation_history.jsonl"
        self._facts: dict = self._load_json(self.facts_file, {})
        self._prefs: dict = self._load_json(self.prefs_file, {})

    def _load_json(self, path: Path, default):
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return default

    def _save_json(self, path: Path, data):
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    # ─── Facts (things Jarvis learns) ─────────────────────────
    def store_fact(self, key: str, value: str) -> str:
        self._facts[key] = {"value": value, "stored": datetime.now().isoformat()}
        self._save_json(self.facts_file, self._facts)
        return f"Remembered: {key} = {value}"

    def recall_fact(self, key: str) -> str:
        fact = self._facts.get(key)
        if fact:
            return fact["value"]
        return f"I don't have any memory about '{key}'."

    def list_facts(self) -> str:
        if not self._facts:
            return "No stored facts."
        lines = [f"  {k}: {v['value']}" for k, v in self._facts.items()]
        return "Stored facts:\n" + "\n".join(lines)

    def forget_fact(self, key: str) -> str:
        if key in self._facts:
            del self._facts[key]
            self._save_json(self.facts_file, self._facts)
            return f"Forgot: {key}"
        return f"No fact found for '{key}'."

    # ─── User Preferences ────────────────────────────────────
    def set_preference(self, key: str, value: str) -> str:
        self._prefs[key] = value
        self._save_json(self.prefs_file, self._prefs)
        return f"Preference set: {key} = {value}"

    def get_preference(self, key: str, default: str = "") -> str:
        return self._prefs.get(key, default)

    def list_preferences(self) -> str:
        if not self._prefs:
            return "No preferences set."
        lines = [f"  {k}: {v}" for k, v in self._prefs.items()]
        return "User preferences:\n" + "\n".join(lines)

    # ─── Conversation History ─────────────────────────────────
    def log_exchange(self, user_msg: str, assistant_msg: str):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "user": user_msg,
            "assistant": assistant_msg,
        }
        with open(self.history_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def get_history(self, n: int = 20) -> list[dict]:
        if not self.history_file.exists():
            return []
        lines = self.history_file.read_text(encoding="utf-8").strip().split("\n")
        entries = []
        for line in lines[-n:]:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return entries

    def search_history(self, query: str, limit: int = 10) -> str:
        if not self.history_file.exists():
            return "No conversation history."
        results = []
        query_lower = query.lower()
        for line in self.history_file.read_text(encoding="utf-8").strip().split("\n"):
            try:
                entry = json.loads(line)
                if query_lower in entry.get("user", "").lower() or query_lower in entry.get("assistant", "").lower():
                    results.append(entry)
            except json.JSONDecodeError:
                continue
        if not results:
            return f"No history matching '{query}'."
        results = results[-limit:]
        lines = [f"[{e['timestamp'][:16]}] User: {e['user'][:60]}..." for e in results]
        return f"Found {len(results)} matches:\n" + "\n".join(lines)

    def get_context_summary(self) -> str:
        """Get a summary of stored knowledge for the system prompt."""
        parts = []
        if self._facts:
            top_facts = list(self._facts.items())[:15]
            parts.append("Known facts: " + "; ".join(f"{k}={v['value']}" for k, v in top_facts))
        if self._prefs:
            parts.append("User preferences: " + "; ".join(f"{k}={v}" for k, v in self._prefs.items()))
        return "\n".join(parts) if parts else ""
