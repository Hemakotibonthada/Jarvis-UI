"""
Notes Module — Persistent note-taking system with categories, tags, and search.
"""

from datetime import datetime
from modules.database import db_manager
from core.logger import get_logger

log = get_logger("notes")


class NotesManager:
    """Full-featured note-taking system backed by SQLite."""

    def __init__(self):
        self.db = db_manager

    def create_note(self, title: str, content: str, category: str = "",
                    tags: str = "", pinned: bool = False) -> str:
        """Create a new note."""
        with self.db._connect() as conn:
            conn.execute(
                """INSERT INTO notes (title, content, category, tags, pinned)
                   VALUES (?, ?, ?, ?, ?)""",
                (title, content, category, tags, 1 if pinned else 0),
            )
        msg = f"Note created: '{title}'"
        if category:
            msg += f" [{category}]"
        return msg

    def get_note(self, note_id: int) -> str:
        """Get a note by ID."""
        with self.db._connect() as conn:
            row = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
        if not row:
            return f"Note #{note_id} not found."
        return (
            f"╔══ Note #{row['id']}: {row['title']} ══╗\n"
            f"Category: {row['category'] or '(none)'} | Tags: {row['tags'] or '(none)'}\n"
            f"Created: {row['created_at']} | Updated: {row['updated_at']}\n"
            f"{'📌 PINNED' if row['pinned'] else ''}\n"
            f"{'─' * 40}\n"
            f"{row['content']}"
        )

    def update_note(self, note_id: int, content: str = "", title: str = "") -> str:
        """Update a note's content or title."""
        updates = []
        params = []
        if content:
            updates.append("content = ?")
            params.append(content)
        if title:
            updates.append("title = ?")
            params.append(title)
        if not updates:
            return "Nothing to update."

        updates.append("updated_at = datetime('now')")
        params.append(note_id)

        with self.db._connect() as conn:
            cursor = conn.execute(
                f"UPDATE notes SET {', '.join(updates)} WHERE id = ?", params
            )
            if cursor.rowcount:
                return f"Note #{note_id} updated."
            return f"Note #{note_id} not found."

    def append_to_note(self, note_id: int, text: str) -> str:
        """Append text to an existing note."""
        with self.db._connect() as conn:
            row = conn.execute("SELECT content FROM notes WHERE id = ?", (note_id,)).fetchone()
            if not row:
                return f"Note #{note_id} not found."
            new_content = row["content"] + "\n" + text
            conn.execute(
                "UPDATE notes SET content = ?, updated_at = datetime('now') WHERE id = ?",
                (new_content, note_id),
            )
        return f"Appended to note #{note_id}."

    def delete_note(self, note_id: int) -> str:
        """Delete a note."""
        with self.db._connect() as conn:
            cursor = conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            if cursor.rowcount:
                return f"Note #{note_id} deleted."
            return f"Note #{note_id} not found."

    def list_notes(self, category: str = "", limit: int = 30) -> str:
        """List notes, optionally filtered by category."""
        query = "SELECT id, title, category, tags, pinned, created_at FROM notes"
        params = []
        if category:
            query += " WHERE category = ?"
            params.append(category)
        query += " ORDER BY pinned DESC, updated_at DESC LIMIT ?"
        params.append(limit)

        with self.db._connect() as conn:
            rows = conn.execute(query, params).fetchall()

        if not rows:
            return "No notes found."

        lines = []
        for r in rows:
            pin = "📌 " if r["pinned"] else "   "
            cat = f"[{r['category']}] " if r["category"] else ""
            lines.append(f"  {pin}#{r['id']} {cat}{r['title']} ({r['created_at'][:10]})")

        return f"Notes ({len(rows)}):\n" + "\n".join(lines)

    def search_notes(self, query: str) -> str:
        """Search notes by title, content, or tags."""
        with self.db._connect() as conn:
            rows = conn.execute(
                """SELECT id, title, category, tags, created_at FROM notes 
                   WHERE title LIKE ? OR content LIKE ? OR tags LIKE ?
                   ORDER BY updated_at DESC LIMIT 20""",
                (f"%{query}%", f"%{query}%", f"%{query}%"),
            ).fetchall()

        if not rows:
            return f"No notes matching '{query}'."

        lines = [f"  #{r['id']} [{r['category']}] {r['title']}" for r in rows]
        return f"Search results ({len(rows)}):\n" + "\n".join(lines)

    def pin_note(self, note_id: int) -> str:
        """Pin/unpin a note."""
        with self.db._connect() as conn:
            row = conn.execute("SELECT pinned FROM notes WHERE id = ?", (note_id,)).fetchone()
            if not row:
                return f"Note #{note_id} not found."
            new_pin = 0 if row["pinned"] else 1
            conn.execute("UPDATE notes SET pinned = ? WHERE id = ?", (new_pin, note_id))
        return f"Note #{note_id} {'pinned' if new_pin else 'unpinned'}."

    def list_categories(self) -> str:
        """List all note categories."""
        with self.db._connect() as conn:
            rows = conn.execute(
                "SELECT category, COUNT(*) as c FROM notes WHERE category != '' GROUP BY category ORDER BY c DESC"
            ).fetchall()
        if not rows:
            return "No categories."
        lines = [f"  {r['category']}: {r['c']} notes" for r in rows]
        return "Note categories:\n" + "\n".join(lines)

    def export_note(self, note_id: int, file_path: str = "") -> str:
        """Export a note to a text file."""
        from pathlib import Path
        with self.db._connect() as conn:
            row = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
        if not row:
            return f"Note #{note_id} not found."

        if not file_path:
            safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in row["title"])[:50]
            import config
            file_path = str(config.GENERATED_DIR / f"note_{safe_title}.md")

        p = Path(file_path).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        content = f"# {row['title']}\n\n{row['content']}\n\n---\nCategory: {row['category']}\nTags: {row['tags']}\nCreated: {row['created_at']}"
        p.write_text(content, encoding="utf-8")
        return f"Note exported to: {p}"

    def note_operation(self, operation: str, **kwargs) -> str:
        """Unified notes interface."""
        ops = {
            "create": lambda: self.create_note(kwargs.get("title", ""), kwargs.get("content", ""), kwargs.get("category", ""), kwargs.get("tags", ""), kwargs.get("pinned", False)),
            "get": lambda: self.get_note(int(kwargs.get("note_id", 0))),
            "update": lambda: self.update_note(int(kwargs.get("note_id", 0)), kwargs.get("content", ""), kwargs.get("title", "")),
            "append": lambda: self.append_to_note(int(kwargs.get("note_id", 0)), kwargs.get("text", "")),
            "delete": lambda: self.delete_note(int(kwargs.get("note_id", 0))),
            "list": lambda: self.list_notes(kwargs.get("category", "")),
            "search": lambda: self.search_notes(kwargs.get("query", "")),
            "pin": lambda: self.pin_note(int(kwargs.get("note_id", 0))),
            "categories": lambda: self.list_categories(),
            "export": lambda: self.export_note(int(kwargs.get("note_id", 0)), kwargs.get("file_path", "")),
        }
        handler = ops.get(operation)
        if handler:
            return handler()
        return f"Unknown notes operation: {operation}. Available: {', '.join(ops.keys())}"


notes_manager = NotesManager()
