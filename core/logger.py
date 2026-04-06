"""
J.A.R.V.I.S. Logger — Structured logging with file rotation and colored console output.
"""

import os
import sys
import logging
import json
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler
import config


# ─── Color codes for console output ──────────────────────────
class Colors:
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    HEADER = BOLD + CYAN
    INFO = GREEN
    WARNING = YELLOW
    ERROR = RED
    DEBUG = DIM + WHITE
    CRITICAL = BOLD + RED


# ─── Custom Formatter ────────────────────────────────────────
class JarvisConsoleFormatter(logging.Formatter):
    """Color-coded console formatter with icons."""

    LEVEL_COLORS = {
        logging.DEBUG: Colors.DEBUG,
        logging.INFO: Colors.INFO,
        logging.WARNING: Colors.WARNING,
        logging.ERROR: Colors.ERROR,
        logging.CRITICAL: Colors.CRITICAL,
    }

    LEVEL_ICONS = {
        logging.DEBUG: "🔍",
        logging.INFO: "✦",
        logging.WARNING: "⚠",
        logging.ERROR: "✖",
        logging.CRITICAL: "💀",
    }

    def format(self, record):
        color = self.LEVEL_COLORS.get(record.levelno, Colors.RESET)
        icon = self.LEVEL_ICONS.get(record.levelno, "•")
        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")

        module = record.name.split(".")[-1][:15]
        msg = record.getMessage()

        formatted = (
            f"{Colors.DIM}{timestamp}{Colors.RESET} "
            f"{color}{icon} {record.levelname:<8}{Colors.RESET} "
            f"{Colors.CYAN}[{module:<15}]{Colors.RESET} "
            f"{msg}"
        )

        if record.exc_info and record.exc_info[0]:
            formatted += f"\n{Colors.RED}{self.formatException(record.exc_info)}{Colors.RESET}"

        return formatted


class JarvisFileFormatter(logging.Formatter):
    """JSON-structured file formatter for machine-readable logs."""

    def format(self, record):
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "extra_data"):
            log_entry["data"] = record.extra_data

        return json.dumps(log_entry, ensure_ascii=False)


# ─── Logger Factory ──────────────────────────────────────────
class LoggerFactory:
    """Creates and manages loggers for different modules."""

    _loggers: dict = {}
    _initialized = False

    @classmethod
    def initialize(cls, log_level: str = "INFO", log_to_file: bool = True):
        """Initialize the logging system."""
        if cls._initialized:
            return

        # Create log directory
        config.LOGS_DIR.mkdir(parents=True, exist_ok=True)

        # Set root logger level
        root_logger = logging.getLogger("jarvis")
        root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(JarvisConsoleFormatter())
        root_logger.addHandler(console_handler)

        # File handler (rotating)
        if log_to_file:
            log_file = config.LOGS_DIR / "jarvis.log"
            file_handler = RotatingFileHandler(
                str(log_file),
                maxBytes=5 * 1024 * 1024,  # 5MB
                backupCount=5,
                encoding="utf-8",
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(JarvisFileFormatter())
            root_logger.addHandler(file_handler)

            # Error-only log
            error_file = config.LOGS_DIR / "errors.log"
            error_handler = RotatingFileHandler(
                str(error_file),
                maxBytes=2 * 1024 * 1024,
                backupCount=3,
                encoding="utf-8",
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(JarvisFileFormatter())
            root_logger.addHandler(error_handler)

        cls._initialized = True

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Get or create a logger for a module."""
        if not cls._initialized:
            cls.initialize()

        full_name = f"jarvis.{name}"
        if full_name not in cls._loggers:
            cls._loggers[full_name] = logging.getLogger(full_name)
        return cls._loggers[full_name]


# ─── Convenience function ────────────────────────────────────
def get_logger(name: str) -> logging.Logger:
    """Get a logger for a module. Usage: log = get_logger('brain')"""
    return LoggerFactory.get_logger(name)


# ─── Activity Logger ─────────────────────────────────────────
class ActivityLog:
    """Tracks tool usage, commands, and system events for analytics."""

    def __init__(self):
        self.log_file = config.LOGS_DIR / "activity.jsonl"
        self._entries: list = []

    def log_tool_call(self, tool_name: str, args: dict, result: str, duration_ms: float = 0):
        """Log a tool invocation."""
        entry = {
            "type": "tool_call",
            "timestamp": datetime.now().isoformat(),
            "tool": tool_name,
            "args": {k: str(v)[:200] for k, v in args.items()},
            "result_length": len(result),
            "success": not result.startswith("Error") and not result.startswith("Failed"),
            "duration_ms": round(duration_ms, 2),
        }
        self._write(entry)

    def log_voice_command(self, text: str, confidence: float = 0):
        """Log a voice command."""
        entry = {
            "type": "voice_command",
            "timestamp": datetime.now().isoformat(),
            "text": text,
            "confidence": confidence,
        }
        self._write(entry)

    def log_conversation(self, user_msg: str, assistant_msg: str, tools_used: list = None):
        """Log a conversation exchange."""
        entry = {
            "type": "conversation",
            "timestamp": datetime.now().isoformat(),
            "user": user_msg[:500],
            "assistant": assistant_msg[:500],
            "tools_used": tools_used or [],
        }
        self._write(entry)

    def log_system_event(self, event: str, details: dict = None):
        """Log a system event (startup, shutdown, error, etc.)."""
        entry = {
            "type": "system_event",
            "timestamp": datetime.now().isoformat(),
            "event": event,
            "details": details or {},
        }
        self._write(entry)

    def _write(self, entry: dict):
        self._entries.append(entry)
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            pass

    def get_stats(self) -> dict:
        """Get usage statistics."""
        if not self.log_file.exists():
            return {"total_entries": 0}

        tool_counts = {}
        total = 0
        errors = 0

        for line in self.log_file.read_text(encoding="utf-8").strip().split("\n"):
            try:
                entry = json.loads(line)
                total += 1
                if entry.get("type") == "tool_call":
                    tool = entry.get("tool", "unknown")
                    tool_counts[tool] = tool_counts.get(tool, 0) + 1
                    if not entry.get("success", True):
                        errors += 1
            except (json.JSONDecodeError, KeyError):
                continue

        top_tools = sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "total_entries": total,
            "total_errors": errors,
            "top_tools": dict(top_tools),
        }

    def get_recent(self, count: int = 20) -> list:
        """Get recent activity entries."""
        if not self.log_file.exists():
            return []
        lines = self.log_file.read_text(encoding="utf-8").strip().split("\n")
        entries = []
        for line in lines[-count:]:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return entries


# ─── Singleton activity logger ────────────────────────────────
activity_log = ActivityLog()
