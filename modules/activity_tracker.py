"""
Activity Tracker Module — Log app usage, browser history, and daily activity
to a local SQLite database for self-awareness and productivity insights.
"""

import os
import sqlite3
import shutil
import subprocess
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from core.logger import get_logger
import config

log = get_logger("activity")

ACTIVITY_DB = config.DATA_DIR / "activity_tracker.db"


class ActivityTracker:
    """Tracks app usage, browser history, and generates activity reports."""

    def __init__(self):
        self._running = False
        self._thread = None
        self._interval = 60  # seconds
        self._init_db()

    def _init_db(self):
        """Create activity tracking tables."""
        conn = sqlite3.connect(str(ACTIVITY_DB))
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS app_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            app_name TEXT,
            window_title TEXT DEFAULT ''
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS browser_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME,
            url TEXT,
            title TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS activity_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            event_type TEXT,
            details TEXT
        )''')
        conn.commit()
        conn.close()

    def log_active_app(self) -> str:
        """Log the currently active/foreground application."""
        app_name = ""
        window_title = ""

        try:
            if config.IS_WINDOWS:
                import ctypes
                from ctypes import wintypes
                user32 = ctypes.windll.user32
                h = user32.GetForegroundWindow()
                length = user32.GetWindowTextLengthW(h)
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(h, buf, length + 1)
                window_title = buf.value

                # Get process name
                import psutil
                _, pid = ctypes.wintypes.DWORD(), ctypes.wintypes.DWORD()
                user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
                try:
                    proc = psutil.Process(pid.value)
                    app_name = proc.name()
                except Exception:
                    app_name = window_title.split(" - ")[-1] if window_title else "unknown"

            elif config.IS_MAC:
                script = 'tell application "System Events" to get name of first application process whose frontmost is true'
                app_name = subprocess.check_output(['osascript', '-e', script]).decode().strip()
            elif config.IS_LINUX:
                try:
                    result = subprocess.run(['xdotool', 'getactivewindow', 'getwindowpid'], capture_output=True, text=True, timeout=3)
                    if result.returncode == 0:
                        import psutil
                        pid = int(result.stdout.strip())
                        app_name = psutil.Process(pid).name()
                except Exception:
                    app_name = "unknown"
        except Exception as e:
            app_name = "unknown"

        if app_name:
            conn = sqlite3.connect(str(ACTIVITY_DB))
            c = conn.cursor()
            c.execute("INSERT INTO app_usage (app_name, window_title) VALUES (?, ?)",
                      (app_name, window_title[:200]))
            conn.commit()
            conn.close()

        return app_name

    def log_browser_history(self) -> int:
        """Log recent Chrome browser history."""
        if config.IS_WINDOWS:
            chrome_path = Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/User Data/Default/History"
        elif config.IS_MAC:
            chrome_path = Path.home() / "Library/Application Support/Google/Chrome/Default/History"
        elif config.IS_LINUX:
            chrome_path = Path.home() / ".config/google-chrome/Default/History"
        else:
            return 0

        if not chrome_path.exists():
            return 0

        tmp_path = config.DATA_DIR / "chrome_history_tmp"
        try:
            shutil.copy2(str(chrome_path), str(tmp_path))
            conn_hist = sqlite3.connect(str(tmp_path))
            c = conn_hist.cursor()
            c.execute("SELECT url, title, last_visit_time FROM urls ORDER BY last_visit_time DESC LIMIT 20")
            rows = c.fetchall()
            conn_hist.close()
            tmp_path.unlink(missing_ok=True)

            conn = sqlite3.connect(str(ACTIVITY_DB))
            c = conn.cursor()
            count = 0
            for url, title, visit_time in rows:
                # Chrome time: microseconds since 1601-01-01
                ts = datetime(1601, 1, 1) + timedelta(microseconds=visit_time)
                # Only log if within last hour
                if (datetime.now() - ts).total_seconds() < 3600:
                    c.execute("INSERT OR IGNORE INTO browser_history (timestamp, url, title) VALUES (?, ?, ?)",
                              (ts.isoformat(), url, title[:200]))
                    count += 1
            conn.commit()
            conn.close()
            return count
        except Exception as e:
            tmp_path.unlink(missing_ok=True)
            return 0

    def log_event(self, event_type: str, details: str = ""):
        """Log a custom activity event."""
        conn = sqlite3.connect(str(ACTIVITY_DB))
        c = conn.cursor()
        c.execute("INSERT INTO activity_events (event_type, details) VALUES (?, ?)",
                  (event_type, details[:500]))
        conn.commit()
        conn.close()

    # ─── Periodic Logging ─────────────────────────────────────
    def start_tracking(self, interval: int = 60) -> str:
        """Start periodic activity tracking."""
        if self._running:
            return "Activity tracking already running."
        self._running = True
        self._interval = max(30, interval)

        def _track_loop():
            while self._running:
                try:
                    self.log_active_app()
                    self.log_browser_history()
                except Exception as e:
                    log.error(f"Activity tracking error: {e}")
                time.sleep(self._interval)

        self._thread = threading.Thread(target=_track_loop, daemon=True, name="activity-tracker")
        self._thread.start()
        return f"Activity tracking started (every {self._interval}s)."

    def stop_tracking(self) -> str:
        if not self._running:
            return "Not tracking."
        self._running = False
        return "Activity tracking stopped."

    # ─── Reports ──────────────────────────────────────────────
    def today_summary(self) -> str:
        """What did I do today?"""
        conn = sqlite3.connect(str(ACTIVITY_DB))
        c = conn.cursor()

        # App usage
        c.execute("SELECT app_name, COUNT(*) as cnt FROM app_usage WHERE date(timestamp)=date('now') GROUP BY app_name ORDER BY cnt DESC LIMIT 15")
        apps = c.fetchall()

        # Browser history
        c.execute("SELECT title, url FROM browser_history WHERE date(timestamp)=date('now') ORDER BY timestamp DESC LIMIT 15")
        sites = c.fetchall()

        # Events
        c.execute("SELECT event_type, details FROM activity_events WHERE date(timestamp)=date('now') ORDER BY timestamp DESC LIMIT 10")
        events = c.fetchall()

        conn.close()

        result = "Today's Activity:\n\n"

        if apps:
            result += "Apps Used:\n"
            for name, cnt in apps:
                mins = cnt * (self._interval / 60)
                result += f"  {name}: ~{mins:.0f} min ({cnt} samples)\n"

        if sites:
            result += "\nRecent Sites Visited:\n"
            for title, url in sites:
                result += f"  {title[:50]} — {url[:60]}\n"

        if events:
            result += "\nEvents:\n"
            for etype, details in events:
                result += f"  [{etype}] {details[:80]}\n"

        if not apps and not sites:
            result += "No activity data recorded yet today."

        return result

    def app_usage_stats(self, days: int = 7) -> str:
        """Get app usage statistics."""
        conn = sqlite3.connect(str(ACTIVITY_DB))
        c = conn.cursor()
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        c.execute("""SELECT app_name, COUNT(*) as cnt FROM app_usage 
                     WHERE timestamp > ? GROUP BY app_name ORDER BY cnt DESC LIMIT 20""", (cutoff,))
        rows = c.fetchall()
        conn.close()

        if not rows:
            return f"No app usage data in the last {days} days."

        lines = [f"  {name}: {cnt} samples (~{cnt * self._interval / 3600:.1f} hrs)" for name, cnt in rows]
        return f"App Usage (last {days} days):\n" + "\n".join(lines)

    def activity_operation(self, operation: str, **kwargs) -> str:
        """Unified activity tracker interface."""
        ops = {
            "start": lambda: self.start_tracking(int(kwargs.get("interval", 60))),
            "stop": lambda: self.stop_tracking(),
            "today": lambda: self.today_summary(),
            "apps": lambda: self.app_usage_stats(int(kwargs.get("days", 7))),
            "log": lambda: (self.log_event(kwargs.get("event", "manual"), kwargs.get("details", "")), "Event logged.")[1],
        }
        handler = ops.get(operation)
        if handler:
            return handler()
        return f"Unknown activity operation: {operation}. Available: {', '.join(ops.keys())}"


# ─── Singleton ────────────────────────────────────────────────
activity_tracker = ActivityTracker()
