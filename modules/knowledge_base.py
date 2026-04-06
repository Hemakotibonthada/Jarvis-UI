"""
Knowledge Base Module — A persistent Q&A knowledge base that Jarvis can learn from,
query, and use to provide better responses over time. Supports categories,
tagging, fuzzy search, and import/export.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from core.logger import get_logger
import config

log = get_logger("knowledge")

KB_FILE = config.DATA_DIR / "knowledge_base.json"


class KnowledgeEntry:
    """A single knowledge base entry."""

    def __init__(self, question: str, answer: str, category: str = "",
                 tags: str = "", source: str = "", confidence: float = 1.0):
        self.id = 0
        self.question = question
        self.answer = answer
        self.category = category
        self.tags = tags
        self.source = source
        self.confidence = confidence
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        self.access_count = 0
        self.upvotes = 0
        self.downvotes = 0

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}

    @staticmethod
    def from_dict(data: dict) -> 'KnowledgeEntry':
        entry = KnowledgeEntry(
            question=data.get("question", ""),
            answer=data.get("answer", ""),
            category=data.get("category", ""),
            tags=data.get("tags", ""),
            source=data.get("source", ""),
            confidence=data.get("confidence", 1.0),
        )
        for k, v in data.items():
            if hasattr(entry, k):
                setattr(entry, k, v)
        return entry

    def relevance_score(self, query: str) -> float:
        """Calculate relevance score for a query."""
        query_words = set(re.findall(r'\w+', query.lower()))
        question_words = set(re.findall(r'\w+', self.question.lower()))
        answer_words = set(re.findall(r'\w+', self.answer.lower()))
        tag_words = set(re.findall(r'\w+', self.tags.lower()))

        # Exact match boost
        if query.lower().strip() == self.question.lower().strip():
            return 100.0

        # Word overlap scoring
        q_overlap = len(query_words & question_words) / max(len(query_words), 1)
        a_overlap = len(query_words & answer_words) / max(len(query_words), 1)
        t_overlap = len(query_words & tag_words) / max(len(query_words), 1)

        score = (q_overlap * 3 + a_overlap * 1 + t_overlap * 2) * self.confidence
        score += self.upvotes * 0.1 - self.downvotes * 0.2

        return score


class KnowledgeBase:
    """Persistent knowledge base with fuzzy search."""

    def __init__(self):
        self.entries: list[KnowledgeEntry] = []
        self._next_id = 1
        self._load()

    def _load(self):
        if KB_FILE.exists():
            try:
                data = json.loads(KB_FILE.read_text(encoding="utf-8"))
                self.entries = [KnowledgeEntry.from_dict(e) for e in data.get("entries", [])]
                self._next_id = data.get("next_id", 1)
            except (json.JSONDecodeError, OSError):
                pass

    def _save(self):
        data = {
            "entries": [e.to_dict() for e in self.entries],
            "next_id": self._next_id,
        }
        KB_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def add_entry(self, question: str, answer: str, category: str = "",
                  tags: str = "", source: str = "", confidence: float = 1.0) -> str:
        """Add a knowledge base entry."""
        # Check for duplicates
        for existing in self.entries:
            if self._similarity(question, existing.question) > 0.85:
                return f"Similar entry already exists: #{existing.id} '{existing.question[:50]}...'"

        entry = KnowledgeEntry(question, answer, category, tags, source, confidence)
        entry.id = self._next_id
        self._next_id += 1
        self.entries.append(entry)
        self._save()

        return f"Knowledge added: #{entry.id} '{question[:50]}...'"

    def query(self, question: str, top_k: int = 5) -> str:
        """Query the knowledge base for relevant answers."""
        if not self.entries:
            return "Knowledge base is empty."

        scored = [(e, e.relevance_score(question)) for e in self.entries]
        scored.sort(key=lambda x: -x[1])
        top = [(e, s) for e, s in scored[:top_k] if s > 0.1]

        if not top:
            return f"No relevant knowledge found for: '{question}'"

        # Update access counts
        for entry, _ in top:
            entry.access_count += 1
        self._save()

        lines = []
        for entry, score in top:
            lines.append(
                f"  #{entry.id} [{entry.category}] (relevance: {score:.1f})\n"
                f"    Q: {entry.question[:100]}\n"
                f"    A: {entry.answer[:200]}\n"
                f"    Tags: {entry.tags} | Source: {entry.source or 'manual'}"
            )

        return f"Knowledge Base Results ({len(top)} matches):\n\n" + "\n\n".join(lines)

    def get_entry(self, entry_id: int) -> str:
        """Get full entry details."""
        for e in self.entries:
            if e.id == entry_id:
                e.access_count += 1
                self._save()
                return (
                    f"Knowledge Entry #{e.id}:\n"
                    f"  Question: {e.question}\n"
                    f"  Answer: {e.answer}\n"
                    f"  Category: {e.category or '(none)'}\n"
                    f"  Tags: {e.tags or '(none)'}\n"
                    f"  Source: {e.source or '(manual)'}\n"
                    f"  Confidence: {e.confidence:.0%}\n"
                    f"  Accessed: {e.access_count} times\n"
                    f"  Votes: +{e.upvotes} / -{e.downvotes}\n"
                    f"  Created: {e.created_at[:19]}\n"
                    f"  Updated: {e.updated_at[:19]}"
                )
        return f"Entry #{entry_id} not found."

    def update_entry(self, entry_id: int, **kwargs) -> str:
        """Update an entry."""
        for e in self.entries:
            if e.id == entry_id:
                for k, v in kwargs.items():
                    if hasattr(e, k) and v:
                        setattr(e, k, v)
                e.updated_at = datetime.now().isoformat()
                self._save()
                return f"Entry #{entry_id} updated."
        return f"Entry #{entry_id} not found."

    def delete_entry(self, entry_id: int) -> str:
        """Delete an entry."""
        for i, e in enumerate(self.entries):
            if e.id == entry_id:
                self.entries.pop(i)
                self._save()
                return f"Entry #{entry_id} deleted."
        return f"Entry #{entry_id} not found."

    def upvote(self, entry_id: int) -> str:
        """Upvote an entry (mark as helpful)."""
        for e in self.entries:
            if e.id == entry_id:
                e.upvotes += 1
                self._save()
                return f"Entry #{entry_id} upvoted (total: +{e.upvotes})"
        return f"Entry #{entry_id} not found."

    def downvote(self, entry_id: int) -> str:
        """Downvote an entry (mark as unhelpful)."""
        for e in self.entries:
            if e.id == entry_id:
                e.downvotes += 1
                self._save()
                return f"Entry #{entry_id} downvoted (total: -{e.downvotes})"
        return f"Entry #{entry_id} not found."

    def list_entries(self, category: str = "", sort_by: str = "recent",
                     limit: int = 20) -> str:
        """List knowledge base entries."""
        filtered = self.entries
        if category:
            filtered = [e for e in filtered if e.category.lower() == category.lower()]

        sort_opts = {
            "recent": lambda e: e.updated_at,
            "popular": lambda e: e.access_count,
            "votes": lambda e: e.upvotes - e.downvotes,
            "confidence": lambda e: e.confidence,
            "alphabetical": lambda e: e.question.lower(),
        }
        key_fn = sort_opts.get(sort_by, sort_opts["recent"])
        filtered.sort(key=key_fn, reverse=(sort_by != "alphabetical"))

        if not filtered:
            return "No knowledge base entries." if not category else f"No entries in category '{category}'."

        lines = []
        for e in filtered[:limit]:
            lines.append(f"  #{e.id} [{e.category}] {e.question[:60]}... (accessed {e.access_count}x, +{e.upvotes}/-{e.downvotes})")

        return f"Knowledge Base ({len(filtered)} entries):\n" + "\n".join(lines)

    def list_categories(self) -> str:
        """List categories with counts."""
        cats = {}
        for e in self.entries:
            cat = e.category or "Uncategorized"
            cats[cat] = cats.get(cat, 0) + 1

        if not cats:
            return "No categories."
        lines = [f"  {cat}: {count} entries" for cat, count in sorted(cats.items())]
        return "Knowledge Categories:\n" + "\n".join(lines)

    def search(self, query: str) -> str:
        """Full-text search across all entries."""
        q = query.lower()
        matches = [
            e for e in self.entries
            if q in e.question.lower() or q in e.answer.lower() or
               q in e.tags.lower() or q in e.category.lower()
        ]
        if not matches:
            return f"No entries matching '{query}'."
        lines = [f"  #{e.id} [{e.category}] {e.question[:60]}..." for e in matches[:20]]
        return f"Search results ({len(matches)}):\n" + "\n".join(lines)

    def get_stats(self) -> str:
        """Knowledge base statistics."""
        total = len(self.entries)
        if not total:
            return "Knowledge base is empty."

        categories = len(set(e.category for e in self.entries if e.category))
        total_access = sum(e.access_count for e in self.entries)
        avg_confidence = sum(e.confidence for e in self.entries) / total
        most_accessed = max(self.entries, key=lambda e: e.access_count)

        return (
            f"Knowledge Base Statistics:\n"
            f"  Total entries: {total}\n"
            f"  Categories: {categories}\n"
            f"  Total accesses: {total_access}\n"
            f"  Avg confidence: {avg_confidence:.0%}\n"
            f"  Most accessed: #{most_accessed.id} '{most_accessed.question[:40]}...' ({most_accessed.access_count}x)"
        )

    def export_json(self, file_path: str = "") -> str:
        """Export knowledge base."""
        if not file_path:
            file_path = str(config.GENERATED_DIR / "knowledge_export.json")
        p = Path(file_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = [e.to_dict() for e in self.entries]
        p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return f"Exported {len(self.entries)} entries to {p}"

    def import_json(self, file_path: str) -> str:
        """Import knowledge base entries from JSON."""
        p = Path(file_path).expanduser()
        if not p.exists():
            return f"File not found: {p}"
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            imported = 0
            for item in data:
                if isinstance(item, dict) and "question" in item and "answer" in item:
                    entry = KnowledgeEntry.from_dict(item)
                    entry.id = self._next_id
                    self._next_id += 1
                    self.entries.append(entry)
                    imported += 1
            self._save()
            return f"Imported {imported} entries from {p}"
        except Exception as e:
            return f"Import error: {e}"

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        """Simple string similarity (Jaccard)."""
        a_words = set(re.findall(r'\w+', a.lower()))
        b_words = set(re.findall(r'\w+', b.lower()))
        if not a_words or not b_words:
            return 0
        return len(a_words & b_words) / len(a_words | b_words)

    # ─── Unified Interface ────────────────────────────────────
    def knowledge_operation(self, operation: str, **kwargs) -> str:
        """Unified knowledge base management."""
        ops = {
            "add": lambda: self.add_entry(kwargs.get("question", ""), kwargs.get("answer", ""), kwargs.get("category", ""), kwargs.get("tags", ""), kwargs.get("source", "")),
            "query": lambda: self.query(kwargs.get("question", ""), int(kwargs.get("top_k", 5))),
            "get": lambda: self.get_entry(int(kwargs.get("entry_id", 0))),
            "update": lambda: self.update_entry(int(kwargs.get("entry_id", 0)), **{k: v for k, v in kwargs.items() if k not in ("operation", "entry_id")}),
            "delete": lambda: self.delete_entry(int(kwargs.get("entry_id", 0))),
            "upvote": lambda: self.upvote(int(kwargs.get("entry_id", 0))),
            "downvote": lambda: self.downvote(int(kwargs.get("entry_id", 0))),
            "list": lambda: self.list_entries(kwargs.get("category", ""), kwargs.get("sort_by", "recent")),
            "categories": lambda: self.list_categories(),
            "search": lambda: self.search(kwargs.get("query", "")),
            "stats": lambda: self.get_stats(),
            "export": lambda: self.export_json(kwargs.get("file_path", "")),
            "import": lambda: self.import_json(kwargs.get("file_path", "")),
        }
        handler = ops.get(operation)
        if handler:
            return handler()
        return f"Unknown knowledge operation: {operation}. Available: {', '.join(ops.keys())}"


# ─── Singleton ────────────────────────────────────────────────
knowledge_base = KnowledgeBase()
