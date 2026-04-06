"""
Snippet Manager Module — Code snippet library with syntax support, tagging,
search, and quick access for frequently used code patterns.
"""

import json
from datetime import datetime
from pathlib import Path
from core.logger import get_logger
import config

log = get_logger("snippets")

SNIPPETS_FILE = config.DATA_DIR / "snippets.json"


class CodeSnippet:
    """A stored code snippet."""
    def __init__(self, title: str, code: str, language: str = "",
                 description: str = "", tags: str = "", category: str = ""):
        self.id = 0
        self.title = title
        self.code = code
        self.language = language
        self.description = description
        self.tags = tags
        self.category = category
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        self.usage_count = 0
        self.favorite = False

    def to_dict(self):
        return self.__dict__

    @staticmethod
    def from_dict(d) -> 'CodeSnippet':
        s = CodeSnippet(d.get("title", ""), d.get("code", ""), d.get("language", ""))
        for k, v in d.items():
            if hasattr(s, k):
                setattr(s, k, v)
        return s


class SnippetManager:
    """Manage a library of code snippets."""

    def __init__(self):
        self.snippets: list[CodeSnippet] = []
        self._next_id = 1
        self._load()

    def _load(self):
        if SNIPPETS_FILE.exists():
            try:
                data = json.loads(SNIPPETS_FILE.read_text(encoding="utf-8"))
                self.snippets = [CodeSnippet.from_dict(s) for s in data.get("snippets", [])]
                self._next_id = data.get("next_id", 1)
            except (json.JSONDecodeError, OSError):
                pass

    def _save(self):
        data = {"snippets": [s.to_dict() for s in self.snippets], "next_id": self._next_id}
        SNIPPETS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def add_snippet(self, title: str, code: str, language: str = "",
                    description: str = "", tags: str = "", category: str = "") -> str:
        """Save a new code snippet."""
        snippet = CodeSnippet(title, code, language, description, tags, category)
        snippet.id = self._next_id
        self._next_id += 1
        self.snippets.append(snippet)
        self._save()
        return f"Snippet saved: #{snippet.id} '{title}' ({language or 'plain'}, {len(code)} chars)"

    def get_snippet(self, snippet_id: int) -> str:
        """Get a snippet by ID."""
        for s in self.snippets:
            if s.id == snippet_id:
                s.usage_count += 1
                self._save()
                return (
                    f"Snippet #{s.id}: {s.title}\n"
                    f"Language: {s.language or 'plain'} | Category: {s.category or '(none)'}\n"
                    f"Tags: {s.tags or '(none)'} | Used: {s.usage_count}x\n"
                    f"{'★ FAVORITE' if s.favorite else ''}\n"
                    f"{'─' * 40}\n"
                    f"{s.code}\n"
                    f"{'─' * 40}\n"
                    f"{s.description}" if s.description else ""
                )
        return f"Snippet #{snippet_id} not found."

    def search_snippets(self, query: str) -> str:
        """Search snippets by title, code, tags, or description."""
        q = query.lower()
        matches = [s for s in self.snippets if
                   q in s.title.lower() or q in s.code.lower() or
                   q in s.tags.lower() or q in s.description.lower() or
                   q in s.language.lower()]
        if not matches:
            return f"No snippets matching '{query}'."
        lines = [f"  #{s.id} [{s.language}] {s.title} ({s.tags})" for s in matches[:20]]
        return f"Snippet search ({len(matches)} matches):\n" + "\n".join(lines)

    def list_snippets(self, language: str = "", category: str = "",
                      sort_by: str = "recent") -> str:
        """List snippets with filtering."""
        filtered = self.snippets
        if language:
            filtered = [s for s in filtered if s.language.lower() == language.lower()]
        if category:
            filtered = [s for s in filtered if s.category.lower() == category.lower()]

        sort_opts = {
            "recent": lambda s: s.updated_at,
            "popular": lambda s: s.usage_count,
            "title": lambda s: s.title.lower(),
            "favorite": lambda s: (not s.favorite, s.title.lower()),
        }
        filtered.sort(key=sort_opts.get(sort_by, sort_opts["recent"]), reverse=(sort_by != "title"))

        if not filtered:
            return "No snippets found."
        lines = [
            f"  {'★' if s.favorite else ' '} #{s.id} [{s.language}] {s.title} ({s.usage_count}x used)"
            for s in filtered[:30]
        ]
        return f"Snippets ({len(filtered)}):\n" + "\n".join(lines)

    def update_snippet(self, snippet_id: int, **kwargs) -> str:
        """Update a snippet."""
        for s in self.snippets:
            if s.id == snippet_id:
                for k, v in kwargs.items():
                    if hasattr(s, k) and v:
                        setattr(s, k, v)
                s.updated_at = datetime.now().isoformat()
                self._save()
                return f"Snippet #{snippet_id} updated."
        return f"Snippet #{snippet_id} not found."

    def delete_snippet(self, snippet_id: int) -> str:
        """Delete a snippet."""
        for i, s in enumerate(self.snippets):
            if s.id == snippet_id:
                self.snippets.pop(i)
                self._save()
                return f"Snippet #{snippet_id} deleted."
        return f"Snippet #{snippet_id} not found."

    def toggle_favorite(self, snippet_id: int) -> str:
        """Toggle favorite status."""
        for s in self.snippets:
            if s.id == snippet_id:
                s.favorite = not s.favorite
                self._save()
                return f"Snippet #{snippet_id} {'favorited ★' if s.favorite else 'unfavorited'}."
        return f"Snippet #{snippet_id} not found."

    def copy_snippet(self, snippet_id: int) -> str:
        """Copy snippet code to clipboard."""
        for s in self.snippets:
            if s.id == snippet_id:
                try:
                    import pyperclip
                    pyperclip.copy(s.code)
                    s.usage_count += 1
                    self._save()
                    return f"Snippet #{snippet_id} copied to clipboard ({len(s.code)} chars)."
                except ImportError:
                    return f"pyperclip not installed. Code:\n{s.code}"
        return f"Snippet #{snippet_id} not found."

    def save_to_file(self, snippet_id: int, file_path: str = "") -> str:
        """Save a snippet to a file."""
        for s in self.snippets:
            if s.id == snippet_id:
                if not file_path:
                    ext_map = {
                        "python": ".py", "javascript": ".js", "typescript": ".ts",
                        "java": ".java", "c": ".c", "cpp": ".cpp", "csharp": ".cs",
                        "go": ".go", "rust": ".rs", "ruby": ".rb", "php": ".php",
                        "html": ".html", "css": ".css", "sql": ".sql", "bash": ".sh",
                        "powershell": ".ps1", "yaml": ".yml", "json": ".json",
                    }
                    ext = ext_map.get(s.language.lower(), ".txt")
                    safe_title = "".join(c if c.isalnum() or c in "-_ " else "" for c in s.title)[:40]
                    file_path = str(config.GENERATED_DIR / f"{safe_title}{ext}")
                p = Path(file_path)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(s.code, encoding="utf-8")
                return f"Snippet #{snippet_id} saved to: {p}"
        return f"Snippet #{snippet_id} not found."

    def list_languages(self) -> str:
        """List languages with snippet counts."""
        langs = {}
        for s in self.snippets:
            lang = s.language or "plain"
            langs[lang] = langs.get(lang, 0) + 1
        if not langs:
            return "No snippets."
        lines = [f"  {lang}: {count} snippets" for lang, count in sorted(langs.items())]
        return "Languages:\n" + "\n".join(lines)

    def export_snippets(self, file_path: str = "") -> str:
        """Export all snippets."""
        if not file_path:
            file_path = str(config.GENERATED_DIR / "snippets_export.json")
        p = Path(file_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = [s.to_dict() for s in self.snippets]
        p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return f"Exported {len(self.snippets)} snippets to {p}"

    def import_snippets(self, file_path: str) -> str:
        """Import snippets from JSON."""
        p = Path(file_path).expanduser()
        if not p.exists():
            return f"File not found: {p}"
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            imported = 0
            for item in data:
                if isinstance(item, dict) and "title" in item and "code" in item:
                    snippet = CodeSnippet.from_dict(item)
                    snippet.id = self._next_id
                    self._next_id += 1
                    self.snippets.append(snippet)
                    imported += 1
            self._save()
            return f"Imported {imported} snippets from {p}"
        except Exception as e:
            return f"Import error: {e}"

    def get_stats(self) -> str:
        """Get snippet library statistics."""
        if not self.snippets:
            return "Snippet library is empty."
        total = len(self.snippets)
        favorites = sum(1 for s in self.snippets if s.favorite)
        total_chars = sum(len(s.code) for s in self.snippets)
        most_used = max(self.snippets, key=lambda s: s.usage_count)
        languages = len(set(s.language for s in self.snippets if s.language))
        return (
            f"Snippet Library Stats:\n"
            f"  Total snippets: {total}\n"
            f"  Favorites: {favorites}\n"
            f"  Languages: {languages}\n"
            f"  Total code: {total_chars:,} chars\n"
            f"  Most used: #{most_used.id} '{most_used.title}' ({most_used.usage_count}x)"
        )

    # ─── Unified Interface ────────────────────────────────
    def snippet_operation(self, operation: str, **kwargs) -> str:
        """Unified snippet management."""
        ops = {
            "add": lambda: self.add_snippet(kwargs.get("title", ""), kwargs.get("code", ""), kwargs.get("language", ""), kwargs.get("description", ""), kwargs.get("tags", ""), kwargs.get("category", "")),
            "get": lambda: self.get_snippet(int(kwargs.get("snippet_id", 0))),
            "search": lambda: self.search_snippets(kwargs.get("query", "")),
            "list": lambda: self.list_snippets(kwargs.get("language", ""), kwargs.get("category", ""), kwargs.get("sort_by", "recent")),
            "update": lambda: self.update_snippet(int(kwargs.get("snippet_id", 0)), **{k: v for k, v in kwargs.items() if k not in ("operation", "snippet_id")}),
            "delete": lambda: self.delete_snippet(int(kwargs.get("snippet_id", 0))),
            "favorite": lambda: self.toggle_favorite(int(kwargs.get("snippet_id", 0))),
            "copy": lambda: self.copy_snippet(int(kwargs.get("snippet_id", 0))),
            "save": lambda: self.save_to_file(int(kwargs.get("snippet_id", 0)), kwargs.get("file_path", "")),
            "languages": lambda: self.list_languages(),
            "export": lambda: self.export_snippets(kwargs.get("file_path", "")),
            "import": lambda: self.import_snippets(kwargs.get("file_path", "")),
            "stats": lambda: self.get_stats(),
        }
        handler = ops.get(operation)
        if handler:
            return handler()
        return f"Unknown snippet operation: {operation}. Available: {', '.join(ops.keys())}"


snippet_manager = SnippetManager()
