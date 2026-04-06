"""
Bookmark & Reading List Module — Save URLs, organize bookmarks, 
reading queue management, and link health checking.
"""

import json
import asyncio
from datetime import datetime
from pathlib import Path
import aiohttp
from core.logger import get_logger
import config

log = get_logger("bookmarks")

BOOKMARKS_FILE = config.DATA_DIR / "bookmarks_v2.json"


class Bookmark:
    """A saved bookmark."""
    def __init__(self, url: str, title: str = "", description: str = "",
                 category: str = "", tags: str = "", notes: str = ""):
        self.id = 0
        self.url = url
        self.title = title or url[:50]
        self.description = description
        self.category = category
        self.tags = tags
        self.notes = notes
        self.created_at = datetime.now().isoformat()
        self.last_visited = ""
        self.visit_count = 0
        self.favorite = False
        self.read_later = False
        self.archived = False
        self.status = "active"  # active, broken, archived

    def to_dict(self):
        return self.__dict__

    @staticmethod
    def from_dict(d) -> 'Bookmark':
        b = Bookmark(d.get("url", ""))
        for k, v in d.items():
            if hasattr(b, k):
                setattr(b, k, v)
        return b


class BookmarkManager:
    """Comprehensive bookmark and reading list management."""

    def __init__(self):
        self.bookmarks: list[Bookmark] = []
        self._next_id = 1
        self._load()

    def _load(self):
        if BOOKMARKS_FILE.exists():
            try:
                data = json.loads(BOOKMARKS_FILE.read_text(encoding="utf-8"))
                self.bookmarks = [Bookmark.from_dict(b) for b in data.get("bookmarks", [])]
                self._next_id = data.get("next_id", 1)
            except (json.JSONDecodeError, OSError):
                pass

    def _save(self):
        data = {"bookmarks": [b.to_dict() for b in self.bookmarks], "next_id": self._next_id}
        BOOKMARKS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def add_bookmark(self, url: str, title: str = "", category: str = "",
                     tags: str = "", notes: str = "", read_later: bool = False) -> str:
        """Add a new bookmark."""
        # Check for duplicates
        for existing in self.bookmarks:
            if existing.url == url and not existing.archived:
                return f"Bookmark already exists: #{existing.id} '{existing.title}'"

        bookmark = Bookmark(url, title, "", category, tags, notes)
        bookmark.read_later = read_later
        bookmark.id = self._next_id
        self._next_id += 1
        self.bookmarks.append(bookmark)
        self._save()

        rl = " (added to reading list)" if read_later else ""
        return f"Bookmark added: #{bookmark.id} '{bookmark.title}'{rl}"

    def get_bookmark(self, bookmark_id: int) -> str:
        for b in self.bookmarks:
            if b.id == bookmark_id:
                lines = [
                    f"Bookmark #{b.id}: {b.title}",
                    f"  URL: {b.url}",
                    f"  Category: {b.category or '(none)'}",
                    f"  Tags: {b.tags or '(none)'}",
                    f"  Visits: {b.visit_count}",
                    f"  {'★ Favorite' if b.favorite else ''}",
                    f"  {'📖 Read Later' if b.read_later else ''}",
                    f"  Created: {b.created_at[:19]}",
                ]
                if b.notes:
                    lines.append(f"  Notes: {b.notes[:200]}")
                return "\n".join(lines)
        return f"Bookmark #{bookmark_id} not found."

    def delete_bookmark(self, bookmark_id: int) -> str:
        for i, b in enumerate(self.bookmarks):
            if b.id == bookmark_id:
                self.bookmarks.pop(i)
                self._save()
                return f"Bookmark #{bookmark_id} deleted."
        return f"Bookmark #{bookmark_id} not found."

    def search(self, query: str) -> str:
        q = query.lower()
        matches = [b for b in self.bookmarks if not b.archived and (
            q in b.title.lower() or q in b.url.lower() or
            q in b.tags.lower() or q in b.notes.lower() or
            q in b.category.lower()
        )]
        if not matches:
            return f"No bookmarks matching '{query}'."
        lines = [f"  {'★' if b.favorite else ' '} #{b.id} [{b.category}] {b.title[:50]} — {b.url[:40]}..."
                 for b in matches[:20]]
        return f"Bookmarks matching '{query}' ({len(matches)}):\n" + "\n".join(lines)

    def list_bookmarks(self, category: str = "", sort_by: str = "recent",
                       show_read_later: bool = False) -> str:
        filtered = [b for b in self.bookmarks if not b.archived]
        if category:
            filtered = [b for b in filtered if b.category.lower() == category.lower()]
        if show_read_later:
            filtered = [b for b in filtered if b.read_later]

        sort_opts = {
            "recent": lambda b: b.created_at,
            "visits": lambda b: b.visit_count,
            "title": lambda b: b.title.lower(),
            "favorite": lambda b: (not b.favorite, b.title.lower()),
        }
        filtered.sort(key=sort_opts.get(sort_by, sort_opts["recent"]),
                      reverse=(sort_by in ("recent", "visits")))

        if not filtered:
            return "No bookmarks."
        lines = []
        for b in filtered[:30]:
            prefix = "★" if b.favorite else " "
            rl = "📖" if b.read_later else " "
            lines.append(f"  {prefix}{rl} #{b.id} [{b.category or '-'}] {b.title[:45]} ({b.visit_count}x)")

        return f"Bookmarks ({len(filtered)}):\n" + "\n".join(lines)

    def list_categories(self) -> str:
        cats = {}
        for b in self.bookmarks:
            if not b.archived:
                cat = b.category or "Uncategorized"
                cats[cat] = cats.get(cat, 0) + 1
        if not cats:
            return "No categories."
        lines = [f"  {cat}: {count}" for cat, count in sorted(cats.items())]
        return "Bookmark Categories:\n" + "\n".join(lines)

    def toggle_favorite(self, bookmark_id: int) -> str:
        for b in self.bookmarks:
            if b.id == bookmark_id:
                b.favorite = not b.favorite
                self._save()
                return f"Bookmark #{bookmark_id} {'favorited ★' if b.favorite else 'unfavorited'}."
        return f"Bookmark #{bookmark_id} not found."

    def toggle_read_later(self, bookmark_id: int) -> str:
        for b in self.bookmarks:
            if b.id == bookmark_id:
                b.read_later = not b.read_later
                self._save()
                return f"Bookmark #{bookmark_id} {'added to' if b.read_later else 'removed from'} reading list."
        return f"Bookmark #{bookmark_id} not found."

    def reading_list(self) -> str:
        """Show the reading list (bookmarks marked as read later)."""
        return self.list_bookmarks(show_read_later=True)

    def mark_read(self, bookmark_id: int) -> str:
        for b in self.bookmarks:
            if b.id == bookmark_id:
                b.read_later = False
                b.visit_count += 1
                b.last_visited = datetime.now().isoformat()
                self._save()
                return f"Bookmark #{bookmark_id} marked as read."
        return f"Bookmark #{bookmark_id} not found."

    def archive_bookmark(self, bookmark_id: int) -> str:
        for b in self.bookmarks:
            if b.id == bookmark_id:
                b.archived = True
                b.status = "archived"
                self._save()
                return f"Bookmark #{bookmark_id} archived."
        return f"Bookmark #{bookmark_id} not found."

    async def check_links(self, limit: int = 20) -> str:
        """Check if bookmarked URLs are still alive."""
        active = [b for b in self.bookmarks if not b.archived][:limit]
        results = []

        async with aiohttp.ClientSession() as session:
            for b in active:
                try:
                    async with session.head(b.url, timeout=aiohttp.ClientTimeout(total=10),
                                           allow_redirects=True) as resp:
                        if resp.status < 400:
                            results.append(f"  ✓ #{b.id} {b.title[:40]} — {resp.status}")
                        else:
                            results.append(f"  ✗ #{b.id} {b.title[:40]} — {resp.status}")
                            b.status = "broken"
                except Exception as e:
                    results.append(f"  ✗ #{b.id} {b.title[:40]} — Error: {str(e)[:30]}")
                    b.status = "broken"

        self._save()
        broken = sum(1 for r in results if "✗" in r)
        return (
            f"Link Check ({len(results)} checked, {broken} broken):\n"
            + "\n".join(results)
        )

    def open_bookmark(self, bookmark_id: int) -> str:
        """Open a bookmark in browser."""
        import webbrowser
        for b in self.bookmarks:
            if b.id == bookmark_id:
                b.visit_count += 1
                b.last_visited = datetime.now().isoformat()
                self._save()
                webbrowser.open(b.url)
                return f"Opened: {b.title}"
        return f"Bookmark #{bookmark_id} not found."

    def export_html(self, file_path: str = "") -> str:
        """Export bookmarks as HTML (Netscape format, importable by browsers)."""
        if not file_path:
            file_path = str(config.GENERATED_DIR / "bookmarks_export.html")
        p = Path(file_path)
        
        lines = [
            '<!DOCTYPE NETSCAPE-Bookmark-file-1>',
            '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
            '<TITLE>Bookmarks</TITLE>',
            '<H1>JARVIS Bookmarks</H1>',
            '<DL><p>',
        ]

        # Group by category
        categories = {}
        for b in self.bookmarks:
            if not b.archived:
                cat = b.category or "Uncategorized"
                categories.setdefault(cat, []).append(b)

        for cat, bmarks in sorted(categories.items()):
            lines.append(f'    <DT><H3>{cat}</H3>')
            lines.append('    <DL><p>')
            for b in bmarks:
                ts = int(datetime.fromisoformat(b.created_at).timestamp())
                lines.append(f'        <DT><A HREF="{b.url}" ADD_DATE="{ts}">{b.title}</A>')
            lines.append('    </DL><p>')

        lines.append('</DL><p>')
        p.write_text("\n".join(lines), encoding="utf-8")
        return f"Exported {sum(len(bl) for bl in categories.values())} bookmarks to {p}"

    def import_json(self, file_path: str) -> str:
        p = Path(file_path).expanduser()
        if not p.exists():
            return f"File not found: {p}"
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            imported = 0
            for item in data:
                if isinstance(item, dict) and "url" in item:
                    b = Bookmark.from_dict(item)
                    b.id = self._next_id
                    self._next_id += 1
                    self.bookmarks.append(b)
                    imported += 1
            self._save()
            return f"Imported {imported} bookmarks."
        except Exception as e:
            return f"Import error: {e}"

    def get_stats(self) -> str:
        total = len(self.bookmarks)
        active = sum(1 for b in self.bookmarks if not b.archived)
        favorites = sum(1 for b in self.bookmarks if b.favorite)
        read_later = sum(1 for b in self.bookmarks if b.read_later)
        broken = sum(1 for b in self.bookmarks if b.status == "broken")
        cats = len(set(b.category for b in self.bookmarks if b.category))
        return (
            f"Bookmark Stats:\n"
            f"  Total: {total} (active: {active})\n"
            f"  Favorites: {favorites}\n"
            f"  Reading list: {read_later}\n"
            f"  Broken links: {broken}\n"
            f"  Categories: {cats}"
        )

    async def bookmark_operation(self, operation: str, **kwargs) -> str:
        if operation == "check_links":
            return await self.check_links(int(kwargs.get("limit", 20)))

        ops = {
            "add": lambda: self.add_bookmark(kwargs.get("url", ""), kwargs.get("title", ""), kwargs.get("category", ""), kwargs.get("tags", ""), kwargs.get("notes", ""), kwargs.get("read_later", False)),
            "get": lambda: self.get_bookmark(int(kwargs.get("bookmark_id", 0))),
            "delete": lambda: self.delete_bookmark(int(kwargs.get("bookmark_id", 0))),
            "search": lambda: self.search(kwargs.get("query", "")),
            "list": lambda: self.list_bookmarks(kwargs.get("category", ""), kwargs.get("sort_by", "recent")),
            "categories": lambda: self.list_categories(),
            "favorite": lambda: self.toggle_favorite(int(kwargs.get("bookmark_id", 0))),
            "read_later": lambda: self.toggle_read_later(int(kwargs.get("bookmark_id", 0))),
            "reading_list": lambda: self.reading_list(),
            "mark_read": lambda: self.mark_read(int(kwargs.get("bookmark_id", 0))),
            "archive": lambda: self.archive_bookmark(int(kwargs.get("bookmark_id", 0))),
            "open": lambda: self.open_bookmark(int(kwargs.get("bookmark_id", 0))),
            "export": lambda: self.export_html(kwargs.get("file_path", "")),
            "import": lambda: self.import_json(kwargs.get("file_path", "")),
            "stats": lambda: self.get_stats(),
        }
        handler = ops.get(operation)
        if handler:
            return handler()
        return f"Unknown bookmark operation: {operation}. Available: add, get, delete, search, list, categories, favorite, read_later, reading_list, mark_read, archive, open, check_links, export, import, stats"


bookmark_manager = BookmarkManager()
