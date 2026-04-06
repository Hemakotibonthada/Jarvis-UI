"""
Task & Project Manager Module — Advanced task tracking, projects, and time management.
Uses the SQLite database for persistence.
"""

from datetime import datetime, timedelta
from modules.database import db_manager
from core.logger import get_logger

log = get_logger("tasks")


class TaskManager:
    """Full-featured task and project management system."""

    def __init__(self):
        self.db = db_manager
        self._ensure_tables()

    def _ensure_tables(self):
        """Ensure task tables exist."""
        with self.db._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT DEFAULT '',
                    status TEXT DEFAULT 'active',
                    created_at TEXT DEFAULT (datetime('now')),
                    deadline TEXT DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS time_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER,
                    description TEXT DEFAULT '',
                    start_time TEXT NOT NULL,
                    end_time TEXT DEFAULT '',
                    duration_minutes REAL DEFAULT 0,
                    FOREIGN KEY (task_id) REFERENCES tasks(id)
                );

                CREATE TABLE IF NOT EXISTS habits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    frequency TEXT DEFAULT 'daily',
                    streak INTEGER DEFAULT 0,
                    last_completed TEXT DEFAULT '',
                    created_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS habit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    habit_id INTEGER,
                    completed_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (habit_id) REFERENCES habits(id)
                );
            """)

    # ─── Task CRUD ────────────────────────────────────────────
    def add_task(self, title: str, description: str = "", priority: int = 0,
                 due_date: str = "", project: str = "", tags: str = "") -> str:
        """Create a new task."""
        with self.db._connect() as conn:
            conn.execute(
                """INSERT INTO tasks (title, description, priority, due_date, project, tags)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (title, description, priority, due_date, project, tags),
            )
        priority_labels = {0: "Normal", 1: "High", 2: "Urgent", 3: "Critical"}
        p_label = priority_labels.get(priority, "Normal")
        result = f"Task created: {title} [{p_label}]"
        if due_date:
            result += f" — Due: {due_date}"
        if project:
            result += f" — Project: {project}"
        return result

    def list_tasks(self, status: str = "", project: str = "", sort_by: str = "priority") -> str:
        """List tasks with filtering and sorting."""
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []

        if status:
            query += " AND status = ?"
            params.append(status)
        else:
            query += " AND status != 'archived'"
        if project:
            query += " AND project = ?"
            params.append(project)

        sort_columns = {
            "priority": "priority DESC, due_date ASC",
            "due_date": "due_date ASC, priority DESC",
            "created": "created_at DESC",
            "title": "title ASC",
        }
        query += f" ORDER BY {sort_columns.get(sort_by, 'priority DESC')}"

        with self.db._connect() as conn:
            rows = conn.execute(query, params).fetchall()

        if not rows:
            return "No tasks found."

        status_icons = {"todo": "○", "in_progress": "◐", "done": "●", "blocked": "✗"}
        priority_colors = {0: "", 1: "!", 2: "!!", 3: "!!!"}

        lines = []
        for r in rows:
            icon = status_icons.get(r["status"], "○")
            pri = priority_colors.get(r["priority"], "")
            due = f" [Due: {r['due_date']}]" if r["due_date"] else ""
            proj = f" ({r['project']})" if r["project"] else ""
            lines.append(f"  {icon} #{r['id']} {pri} {r['title']}{due}{proj}")

        return f"Tasks ({len(rows)}):\n" + "\n".join(lines)

    def update_task_status(self, task_id: int, status: str) -> str:
        """Update task status: todo, in_progress, done, blocked, archived."""
        valid = ["todo", "in_progress", "done", "blocked", "archived"]
        if status not in valid:
            return f"Invalid status. Use: {', '.join(valid)}"

        completed_at = datetime.now().isoformat() if status == "done" else ""

        with self.db._connect() as conn:
            cursor = conn.execute(
                "UPDATE tasks SET status = ?, completed_at = ? WHERE id = ?",
                (status, completed_at, task_id),
            )
            if cursor.rowcount:
                return f"Task #{task_id} updated to '{status}'."
            return f"Task #{task_id} not found."

    def delete_task(self, task_id: int) -> str:
        """Delete a task."""
        with self.db._connect() as conn:
            cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            if cursor.rowcount:
                return f"Task #{task_id} deleted."
            return f"Task #{task_id} not found."

    def get_task(self, task_id: int) -> str:
        """Get detailed task info."""
        with self.db._connect() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            if not row:
                return f"Task #{task_id} not found."
            return (
                f"Task #{row['id']}: {row['title']}\n"
                f"  Status: {row['status']}\n"
                f"  Priority: {row['priority']}\n"
                f"  Description: {row['description'] or '(none)'}\n"
                f"  Project: {row['project'] or '(none)'}\n"
                f"  Due: {row['due_date'] or '(none)'}\n"
                f"  Tags: {row['tags'] or '(none)'}\n"
                f"  Created: {row['created_at']}\n"
                f"  Completed: {row['completed_at'] or '(not yet)'}"
            )

    def search_tasks(self, query: str) -> str:
        """Search tasks by title or description."""
        with self.db._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE title LIKE ? OR description LIKE ? ORDER BY priority DESC",
                (f"%{query}%", f"%{query}%"),
            ).fetchall()
        if not rows:
            return f"No tasks matching '{query}'."
        lines = [f"  #{r['id']} [{r['status']}] {r['title']}" for r in rows]
        return f"Search results ({len(rows)}):\n" + "\n".join(lines)

    def get_overdue(self) -> str:
        """Get overdue tasks."""
        today = datetime.now().strftime("%Y-%m-%d")
        with self.db._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE due_date != '' AND due_date < ? AND status NOT IN ('done', 'archived') ORDER BY due_date",
                (today,),
            ).fetchall()
        if not rows:
            return "No overdue tasks."
        lines = [f"  #{r['id']} {r['title']} — Due: {r['due_date']}" for r in rows]
        return f"Overdue tasks ({len(rows)}):\n" + "\n".join(lines)

    def get_today(self) -> str:
        """Get tasks due today."""
        today = datetime.now().strftime("%Y-%m-%d")
        with self.db._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE due_date = ? AND status NOT IN ('done', 'archived') ORDER BY priority DESC",
                (today,),
            ).fetchall()
        if not rows:
            return "No tasks due today."
        lines = [f"  #{r['id']} [P{r['priority']}] {r['title']}" for r in rows]
        return f"Today's tasks ({len(rows)}):\n" + "\n".join(lines)

    def get_summary(self) -> str:
        """Get task summary/dashboard."""
        with self.db._connect() as conn:
            total = conn.execute("SELECT COUNT(*) as c FROM tasks WHERE status != 'archived'").fetchone()["c"]
            todo = conn.execute("SELECT COUNT(*) as c FROM tasks WHERE status = 'todo'").fetchone()["c"]
            in_progress = conn.execute("SELECT COUNT(*) as c FROM tasks WHERE status = 'in_progress'").fetchone()["c"]
            done = conn.execute("SELECT COUNT(*) as c FROM tasks WHERE status = 'done'").fetchone()["c"]
            blocked = conn.execute("SELECT COUNT(*) as c FROM tasks WHERE status = 'blocked'").fetchone()["c"]

            today = datetime.now().strftime("%Y-%m-%d")
            overdue = conn.execute(
                "SELECT COUNT(*) as c FROM tasks WHERE due_date != '' AND due_date < ? AND status NOT IN ('done', 'archived')",
                (today,),
            ).fetchone()["c"]

            today_count = conn.execute(
                "SELECT COUNT(*) as c FROM tasks WHERE due_date = ? AND status NOT IN ('done', 'archived')",
                (today,),
            ).fetchone()["c"]

        return (
            f"Task Dashboard:\n"
            f"  Total Active: {total}\n"
            f"  ○ To Do: {todo}\n"
            f"  ◐ In Progress: {in_progress}\n"
            f"  ● Done: {done}\n"
            f"  ✗ Blocked: {blocked}\n"
            f"  ⚠ Overdue: {overdue}\n"
            f"  📅 Due Today: {today_count}"
        )

    # ─── Projects ─────────────────────────────────────────────
    def create_project(self, name: str, description: str = "", deadline: str = "") -> str:
        """Create a new project."""
        with self.db._connect() as conn:
            try:
                conn.execute(
                    "INSERT INTO projects (name, description, deadline) VALUES (?, ?, ?)",
                    (name, description, deadline),
                )
                return f"Project '{name}' created."
            except Exception as e:
                return f"Error creating project: {e}"

    def list_projects(self) -> str:
        """List all projects with task counts."""
        with self.db._connect() as conn:
            projects = conn.execute("SELECT * FROM projects WHERE status = 'active' ORDER BY name").fetchall()
            if not projects:
                return "No active projects."
            lines = []
            for p in projects:
                task_count = conn.execute(
                    "SELECT COUNT(*) as c FROM tasks WHERE project = ? AND status != 'archived'",
                    (p["name"],),
                ).fetchone()["c"]
                done_count = conn.execute(
                    "SELECT COUNT(*) as c FROM tasks WHERE project = ? AND status = 'done'",
                    (p["name"],),
                ).fetchone()["c"]
                progress = f"{done_count}/{task_count}" if task_count else "0/0"
                due = f" — Deadline: {p['deadline']}" if p["deadline"] else ""
                lines.append(f"  {p['name']}: {progress} tasks done{due}")
            return f"Projects ({len(projects)}):\n" + "\n".join(lines)

    # ─── Habits ───────────────────────────────────────────────
    def add_habit(self, name: str, frequency: str = "daily") -> str:
        """Add a habit to track."""
        with self.db._connect() as conn:
            conn.execute("INSERT INTO habits (name, frequency) VALUES (?, ?)", (name, frequency))
        return f"Habit '{name}' added ({frequency})."

    def complete_habit(self, habit_name: str) -> str:
        """Mark a habit as completed for today."""
        with self.db._connect() as conn:
            habit = conn.execute("SELECT * FROM habits WHERE name LIKE ?", (f"%{habit_name}%",)).fetchone()
            if not habit:
                return f"Habit '{habit_name}' not found."

            today = datetime.now().strftime("%Y-%m-%d")
            last = habit["last_completed"][:10] if habit["last_completed"] else ""

            if last == today:
                return f"Habit '{habit['name']}' already completed today!"

            # Check if streak continues
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            new_streak = habit["streak"] + 1 if last == yesterday else 1

            conn.execute(
                "UPDATE habits SET streak = ?, last_completed = datetime('now') WHERE id = ?",
                (new_streak, habit["id"]),
            )
            conn.execute("INSERT INTO habit_log (habit_id) VALUES (?)", (habit["id"],))

            return f"Habit '{habit['name']}' completed! Streak: {new_streak} days 🔥"

    def list_habits(self) -> str:
        """List all habits with streaks."""
        with self.db._connect() as conn:
            habits = conn.execute("SELECT * FROM habits ORDER BY name").fetchall()
            if not habits:
                return "No habits tracked."
            today = datetime.now().strftime("%Y-%m-%d")
            lines = []
            for h in habits:
                last = h["last_completed"][:10] if h["last_completed"] else ""
                done_today = "✓" if last == today else "○"
                lines.append(f"  {done_today} {h['name']} — {h['streak']} day streak ({h['frequency']})")
            return f"Habits:\n" + "\n".join(lines)

    # ─── Time Tracking ────────────────────────────────────────
    def start_timer(self, task_id: int = 0, description: str = "") -> str:
        """Start a time tracking session."""
        with self.db._connect() as conn:
            conn.execute(
                "INSERT INTO time_entries (task_id, description, start_time) VALUES (?, ?, datetime('now'))",
                (task_id, description),
            )
        msg = "Timer started"
        if task_id:
            msg += f" for task #{task_id}"
        if description:
            msg += f": {description}"
        return msg

    def stop_timer(self) -> str:
        """Stop the active timer."""
        with self.db._connect() as conn:
            active = conn.execute(
                "SELECT * FROM time_entries WHERE end_time = '' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if not active:
                return "No active timer."

            conn.execute(
                """UPDATE time_entries 
                   SET end_time = datetime('now'), 
                       duration_minutes = (julianday(datetime('now')) - julianday(start_time)) * 24 * 60
                   WHERE id = ?""",
                (active["id"],),
            )

            updated = conn.execute("SELECT * FROM time_entries WHERE id = ?", (active["id"],)).fetchone()
            return f"Timer stopped. Duration: {updated['duration_minutes']:.1f} minutes. Task: {active['description'] or active['task_id'] or 'general'}"

    def get_time_summary(self, days: int = 7) -> str:
        """Get time tracking summary."""
        with self.db._connect() as conn:
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            rows = conn.execute(
                "SELECT * FROM time_entries WHERE start_time > ? AND end_time != '' ORDER BY start_time DESC",
                (cutoff,),
            ).fetchall()
            if not rows:
                return f"No time entries in the last {days} days."

            total_minutes = sum(r["duration_minutes"] for r in rows)
            lines = []
            for r in rows[:20]:
                desc = r['description'] or f"Task #{r['task_id']}"
                lines.append(f"  {r['start_time'][:16]} -- {r['duration_minutes']:.0f}min -- {desc}")
            return (
                f"Time tracking (last {days} days):\n"
                f"  Total: {total_minutes:.0f} minutes ({total_minutes / 60:.1f} hours)\n"
                f"  Entries: {len(rows)}\n\n"
                + "\n".join(lines)
            )

    # ─── Unified Interface ────────────────────────────────────
    def task_operation(self, operation: str, **kwargs) -> str:
        """Unified task management interface."""
        ops = {
            "add": lambda: self.add_task(kwargs.get("title", ""), kwargs.get("description", ""), int(kwargs.get("priority", 0)), kwargs.get("due_date", ""), kwargs.get("project", ""), kwargs.get("tags", "")),
            "list": lambda: self.list_tasks(kwargs.get("status", ""), kwargs.get("project", ""), kwargs.get("sort_by", "priority")),
            "done": lambda: self.update_task_status(int(kwargs.get("task_id", 0)), "done"),
            "start": lambda: self.update_task_status(int(kwargs.get("task_id", 0)), "in_progress"),
            "block": lambda: self.update_task_status(int(kwargs.get("task_id", 0)), "blocked"),
            "delete": lambda: self.delete_task(int(kwargs.get("task_id", 0))),
            "get": lambda: self.get_task(int(kwargs.get("task_id", 0))),
            "search": lambda: self.search_tasks(kwargs.get("query", "")),
            "overdue": lambda: self.get_overdue(),
            "today": lambda: self.get_today(),
            "summary": lambda: self.get_summary(),
            "projects": lambda: self.list_projects(),
            "create_project": lambda: self.create_project(kwargs.get("name", ""), kwargs.get("description", ""), kwargs.get("deadline", "")),
            "habits": lambda: self.list_habits(),
            "add_habit": lambda: self.add_habit(kwargs.get("name", ""), kwargs.get("frequency", "daily")),
            "complete_habit": lambda: self.complete_habit(kwargs.get("name", "")),
            "start_timer": lambda: self.start_timer(int(kwargs.get("task_id", 0)), kwargs.get("description", "")),
            "stop_timer": lambda: self.stop_timer(),
            "time_summary": lambda: self.get_time_summary(int(kwargs.get("days", 7))),
        }
        handler = ops.get(operation)
        if handler:
            return handler()
        return f"Unknown task operation: {operation}. Available: {', '.join(ops.keys())}"


# ─── Singleton ────────────────────────────────────────────────
task_manager = TaskManager()
