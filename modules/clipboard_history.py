"""
Clipboard History Module — Tracks clipboard history and provides search/recall.
"""

import threading
import time
from datetime import datetime
from dataclasses import dataclass, field
from core.logger import get_logger

log = get_logger("clipboard")

try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False


@dataclass
class ClipboardEntry:
    content: str
    timestamp: str
    source: str = ""
    content_type: str = "text"


class ClipboardHistory:
    """Maintains a history of clipboard contents."""

    def __init__(self, max_entries: int = 100):
        self.max_entries = max_entries
        self._history: list[ClipboardEntry] = []
        self._monitoring = False
        self._thread = None
        self._last_content = ""

    def start_monitoring(self) -> str:
        """Start monitoring clipboard changes."""
        if not HAS_PYPERCLIP:
            return "pyperclip not installed."
        if self._monitoring:
            return "Already monitoring clipboard."

        self._monitoring = True
        self._last_content = pyperclip.paste() or ""

        def monitor_thread():
            while self._monitoring:
                try:
                    current = pyperclip.paste() or ""
                    if current != self._last_content and current.strip():
                        entry = ClipboardEntry(
                            content=current,
                            timestamp=datetime.now().isoformat(),
                        )
                        self._history.append(entry)
                        if len(self._history) > self.max_entries:
                            self._history = self._history[-self.max_entries:]
                        self._last_content = current
                        log.debug(f"Clipboard updated: {current[:50]}...")
                except Exception:
                    pass
                time.sleep(1)

        self._thread = threading.Thread(target=monitor_thread, daemon=True)
        self._thread.start()
        return "Clipboard monitoring started."

    def stop_monitoring(self) -> str:
        """Stop monitoring clipboard."""
        self._monitoring = False
        if self._thread:
            self._thread.join(timeout=3)
        return "Clipboard monitoring stopped."

    def get_history(self, count: int = 20) -> str:
        """Get clipboard history."""
        if not self._history:
            return "Clipboard history is empty."
        entries = self._history[-count:]
        lines = []
        for i, entry in enumerate(reversed(entries), 1):
            preview = entry.content[:80].replace("\n", " ")
            lines.append(f"  {i}. [{entry.timestamp[11:19]}] {preview}...")
        return f"Clipboard history ({len(self._history)} total):\n" + "\n".join(lines)

    def search_history(self, query: str) -> str:
        """Search clipboard history."""
        query_lower = query.lower()
        matches = [e for e in self._history if query_lower in e.content.lower()]
        if not matches:
            return f"No clipboard entries matching '{query}'."
        lines = [f"  [{e.timestamp[11:19]}] {e.content[:80]}..." for e in matches[-10:]]
        return f"Clipboard search results ({len(matches)}):\n" + "\n".join(lines)

    def get_entry(self, index: int) -> str:
        """Get a specific clipboard entry (1-indexed from most recent)."""
        if index < 1 or index > len(self._history):
            return f"Invalid index. History has {len(self._history)} entries."
        entry = self._history[-index]
        return entry.content

    def paste_entry(self, index: int) -> str:
        """Paste a historical clipboard entry back to clipboard."""
        content = self.get_entry(index)
        if content.startswith("Invalid"):
            return content
        if HAS_PYPERCLIP:
            pyperclip.copy(content)
            self._last_content = content
            return f"Restored clipboard entry #{index} ({len(content)} chars)."
        return "pyperclip not installed."

    def clear_history(self) -> str:
        """Clear clipboard history."""
        count = len(self._history)
        self._history.clear()
        return f"Cleared {count} clipboard entries."

    def clipboard_operation(self, operation: str, **kwargs) -> str:
        """Unified clipboard history interface."""
        ops = {
            "history": lambda: self.get_history(int(kwargs.get("count", 20))),
            "search": lambda: self.search_history(kwargs.get("query", "")),
            "get": lambda: self.get_entry(int(kwargs.get("index", 1))),
            "paste": lambda: self.paste_entry(int(kwargs.get("index", 1))),
            "clear": lambda: self.clear_history(),
            "start": lambda: self.start_monitoring(),
            "stop": lambda: self.stop_monitoring(),
        }
        handler = ops.get(operation)
        if handler:
            return handler()
        return f"Unknown clipboard operation: {operation}. Available: {', '.join(ops.keys())}"


clipboard_history = ClipboardHistory()
