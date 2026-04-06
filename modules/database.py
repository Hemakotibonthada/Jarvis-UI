"""
Database Module — SQLite-based local data management, key-value store, and structured data.
"""

import sqlite3
import json
import csv
import io
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager
from core.logger import get_logger
import config

log = get_logger("database")

DB_PATH = config.DATA_DIR / "jarvis.db"


# ─── Database Manager ────────────────────────────────────────
class DatabaseManager:
    """SQLite database manager for structured data storage."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_PATH)
        self._init_db()

    def _init_db(self):
        """Initialize database with core tables."""
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS key_value (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    category TEXT DEFAULT '',
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    phone TEXT DEFAULT '',
                    email TEXT DEFAULT '',
                    notes TEXT DEFAULT '',
                    created_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS bookmarks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    category TEXT DEFAULT '',
                    tags TEXT DEFAULT '',
                    created_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    category TEXT DEFAULT '',
                    tags TEXT DEFAULT '',
                    pinned INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    status TEXT DEFAULT 'todo',
                    priority INTEGER DEFAULT 0,
                    due_date TEXT DEFAULT '',
                    project TEXT DEFAULT '',
                    tags TEXT DEFAULT '',
                    created_at TEXT DEFAULT (datetime('now')),
                    completed_at TEXT DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS command_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    command TEXT NOT NULL,
                    result TEXT DEFAULT '',
                    timestamp TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS sensor_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sensor TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT DEFAULT '',
                    timestamp TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS custom_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    table_name TEXT NOT NULL,
                    data TEXT NOT NULL,
                    created_at TEXT DEFAULT (datetime('now'))
                );

                CREATE INDEX IF NOT EXISTS idx_kv_category ON key_value(category);
                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
                CREATE INDEX IF NOT EXISTS idx_notes_category ON notes(category);
                CREATE INDEX IF NOT EXISTS idx_sensor_timestamp ON sensor_data(timestamp);
            """)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ─── Key-Value Store ──────────────────────────────────────
    def kv_set(self, key: str, value: str, category: str = "") -> str:
        """Set a key-value pair."""
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO key_value (key, value, category, updated_at)
                   VALUES (?, ?, ?, datetime('now'))
                   ON CONFLICT(key) DO UPDATE SET value=?, category=?, updated_at=datetime('now')""",
                (key, value, category, value, category),
            )
        return f"Stored: {key} = {value}"

    def kv_get(self, key: str) -> str:
        """Get a value by key."""
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM key_value WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else f"Key '{key}' not found."

    def kv_delete(self, key: str) -> str:
        """Delete a key-value pair."""
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM key_value WHERE key = ?", (key,))
            if cursor.rowcount:
                return f"Deleted key: {key}"
            return f"Key '{key}' not found."

    def kv_list(self, category: str = "") -> str:
        """List all key-value pairs."""
        with self._connect() as conn:
            if category:
                rows = conn.execute("SELECT key, value, category FROM key_value WHERE category = ? ORDER BY key", (category,)).fetchall()
            else:
                rows = conn.execute("SELECT key, value, category FROM key_value ORDER BY category, key").fetchall()
            if not rows:
                return "No stored data."
            lines = [f"  [{r['category']}] {r['key']}: {r['value']}" for r in rows]
            return f"Stored data ({len(rows)} entries):\n" + "\n".join(lines)

    def kv_search(self, query: str) -> str:
        """Search key-value pairs."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT key, value, category FROM key_value WHERE key LIKE ? OR value LIKE ?",
                (f"%{query}%", f"%{query}%"),
            ).fetchall()
            if not rows:
                return f"No results for '{query}'."
            lines = [f"  [{r['category']}] {r['key']}: {r['value']}" for r in rows]
            return f"Search results ({len(rows)}):\n" + "\n".join(lines)

    # ─── Contacts ─────────────────────────────────────────────
    def add_contact(self, name: str, phone: str = "", email: str = "", notes: str = "") -> str:
        """Add a contact."""
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO contacts (name, phone, email, notes) VALUES (?, ?, ?, ?)",
                (name, phone, email, notes),
            )
        return f"Contact added: {name}"

    def find_contact(self, search: str) -> str:
        """Search contacts."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM contacts WHERE name LIKE ? OR phone LIKE ? OR email LIKE ?",
                (f"%{search}%", f"%{search}%", f"%{search}%"),
            ).fetchall()
            if not rows:
                return f"No contacts matching '{search}'."
            lines = [f"  {r['name']} | Phone: {r['phone']} | Email: {r['email']} | Notes: {r['notes']}" for r in rows]
            return f"Contacts ({len(rows)}):\n" + "\n".join(lines)

    def list_contacts(self) -> str:
        """List all contacts."""
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM contacts ORDER BY name").fetchall()
            if not rows:
                return "No contacts saved."
            lines = [f"  {r['id']}. {r['name']} — {r['phone']} — {r['email']}" for r in rows]
            return f"All contacts ({len(rows)}):\n" + "\n".join(lines)

    def delete_contact(self, name: str) -> str:
        """Delete a contact."""
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM contacts WHERE name LIKE ?", (f"%{name}%",))
            if cursor.rowcount:
                return f"Deleted {cursor.rowcount} contact(s) matching '{name}'."
            return f"No contacts matching '{name}'."

    # ─── Bookmarks ────────────────────────────────────────────
    def add_bookmark(self, title: str, url: str, category: str = "", tags: str = "") -> str:
        """Add a bookmark."""
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO bookmarks (title, url, category, tags) VALUES (?, ?, ?, ?)",
                (title, url, category, tags),
            )
        return f"Bookmark added: {title}"

    def find_bookmarks(self, search: str) -> str:
        """Search bookmarks."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM bookmarks WHERE title LIKE ? OR url LIKE ? OR category LIKE ? OR tags LIKE ?",
                (f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"),
            ).fetchall()
            if not rows:
                return f"No bookmarks matching '{search}'."
            lines = [f"  {r['title']}: {r['url']} [{r['category']}]" for r in rows]
            return f"Bookmarks ({len(rows)}):\n" + "\n".join(lines)

    def list_bookmarks(self, category: str = "") -> str:
        """List bookmarks."""
        with self._connect() as conn:
            if category:
                rows = conn.execute("SELECT * FROM bookmarks WHERE category = ? ORDER BY title", (category,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM bookmarks ORDER BY category, title").fetchall()
            if not rows:
                return "No bookmarks saved."
            lines = [f"  [{r['category']}] {r['title']}: {r['url']}" for r in rows]
            return f"Bookmarks ({len(rows)}):\n" + "\n".join(lines)

    # ─── Sensor Data ──────────────────────────────────────────
    def log_sensor(self, sensor: str, value: float, unit: str = "") -> str:
        """Log a sensor reading."""
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO sensor_data (sensor, value, unit) VALUES (?, ?, ?)",
                (sensor, value, unit),
            )
        return f"Logged {sensor}: {value} {unit}"

    def get_sensor_history(self, sensor: str, limit: int = 50) -> str:
        """Get sensor history."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM sensor_data WHERE sensor = ? ORDER BY timestamp DESC LIMIT ?",
                (sensor, limit),
            ).fetchall()
            if not rows:
                return f"No data for sensor '{sensor}'."
            lines = [f"  {r['timestamp']}: {r['value']} {r['unit']}" for r in rows]
            return f"Sensor '{sensor}' history ({len(rows)} readings):\n" + "\n".join(lines)

    def get_sensor_stats(self, sensor: str) -> str:
        """Get sensor statistics."""
        with self._connect() as conn:
            row = conn.execute(
                """SELECT MIN(value) as min_val, MAX(value) as max_val, 
                   AVG(value) as avg_val, COUNT(*) as count,
                   MIN(timestamp) as first_reading, MAX(timestamp) as last_reading
                   FROM sensor_data WHERE sensor = ?""",
                (sensor,),
            ).fetchone()
            if not row or row["count"] == 0:
                return f"No data for sensor '{sensor}'."
            return (
                f"Sensor '{sensor}' statistics:\n"
                f"  Min: {row['min_val']:.2f}\n"
                f"  Max: {row['max_val']:.2f}\n"
                f"  Average: {row['avg_val']:.2f}\n"
                f"  Total readings: {row['count']}\n"
                f"  First: {row['first_reading']}\n"
                f"  Last: {row['last_reading']}"
            )

    # ─── Command History ──────────────────────────────────────
    def log_command(self, command: str, result: str = ""):
        """Log a command execution."""
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO command_history (command, result) VALUES (?, ?)",
                (command, result[:1000]),
            )

    def search_command_history(self, query: str, limit: int = 20) -> str:
        """Search command history."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM command_history WHERE command LIKE ? ORDER BY timestamp DESC LIMIT ?",
                (f"%{query}%", limit),
            ).fetchall()
            if not rows:
                return f"No commands matching '{query}'."
            lines = [f"  [{r['timestamp'][:19]}] {r['command']}" for r in rows]
            return f"Command history ({len(rows)}):\n" + "\n".join(lines)

    # ─── Custom SQL ───────────────────────────────────────────
    def execute_query(self, query: str) -> str:
        """Execute a read-only SQL query."""
        # Only allow SELECT queries for safety
        query_stripped = query.strip().upper()
        if not query_stripped.startswith("SELECT"):
            return "Only SELECT queries are allowed for safety."
        try:
            with self._connect() as conn:
                rows = conn.execute(query).fetchall()
                if not rows:
                    return "Query returned no results."
                # Convert to readable format
                headers = rows[0].keys()
                lines = [" | ".join(str(r[h]) for h in headers) for r in rows[:100]]
                header_line = " | ".join(headers)
                return f"{header_line}\n{'─' * len(header_line)}\n" + "\n".join(lines)
        except Exception as e:
            return f"Query error: {e}"

    def get_db_info(self) -> str:
        """Get database info and table sizes."""
        with self._connect() as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            lines = []
            for t in tables:
                name = t["name"]
                count = conn.execute(f"SELECT COUNT(*) as c FROM {name}").fetchone()["c"]
                lines.append(f"  {name}: {count} rows")
            db_size = Path(self.db_path).stat().st_size if Path(self.db_path).exists() else 0
            return (
                f"Database: {self.db_path}\n"
                f"Size: {db_size / 1024:.1f} KB\n"
                f"Tables:\n" + "\n".join(lines)
            )

    def export_to_csv(self, table: str, output_path: str) -> str:
        """Export a table to CSV."""
        try:
            with self._connect() as conn:
                rows = conn.execute(f"SELECT * FROM {table}").fetchall()
                if not rows:
                    return f"Table '{table}' is empty."
                p = Path(output_path).expanduser()
                p.parent.mkdir(parents=True, exist_ok=True)
                with open(p, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(rows[0].keys())
                    for row in rows:
                        writer.writerow(list(row))
                return f"Exported {len(rows)} rows from '{table}' to {p}"
        except Exception as e:
            return f"Export error: {e}"


# ─── Top-level functions for tool registration ────────────────
_db = DatabaseManager()


def database_query(operation: str, **kwargs) -> str:
    """Unified database operation handler."""
    ops = {
        "set": lambda: _db.kv_set(kwargs.get("key", ""), kwargs.get("value", ""), kwargs.get("category", "")),
        "get": lambda: _db.kv_get(kwargs.get("key", "")),
        "delete": lambda: _db.kv_delete(kwargs.get("key", "")),
        "list": lambda: _db.kv_list(kwargs.get("category", "")),
        "search": lambda: _db.kv_search(kwargs.get("query", "")),
        "info": lambda: _db.get_db_info(),
        "sql": lambda: _db.execute_query(kwargs.get("query", "")),
        "export": lambda: _db.export_to_csv(kwargs.get("table", ""), kwargs.get("path", "")),
        "add_contact": lambda: _db.add_contact(kwargs.get("name", ""), kwargs.get("phone", ""), kwargs.get("email", ""), kwargs.get("notes", "")),
        "find_contact": lambda: _db.find_contact(kwargs.get("name", "")),
        "list_contacts": lambda: _db.list_contacts(),
        "add_bookmark": lambda: _db.add_bookmark(kwargs.get("title", ""), kwargs.get("url", ""), kwargs.get("category", "")),
        "find_bookmarks": lambda: _db.find_bookmarks(kwargs.get("query", "")),
        "list_bookmarks": lambda: _db.list_bookmarks(kwargs.get("category", "")),
        "log_sensor": lambda: _db.log_sensor(kwargs.get("sensor", ""), float(kwargs.get("value", 0)), kwargs.get("unit", "")),
        "sensor_history": lambda: _db.get_sensor_history(kwargs.get("sensor", "")),
        "sensor_stats": lambda: _db.get_sensor_stats(kwargs.get("sensor", "")),
    }
    handler = ops.get(operation)
    if handler:
        return handler()
    return f"Unknown database operation: {operation}. Available: {', '.join(ops.keys())}"


db_manager = _db
