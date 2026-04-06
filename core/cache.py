"""
Core Cache Module — Intelligent caching with TTL, LRU eviction, and persistence.
"""

import json
import time
import hashlib
from pathlib import Path
from collections import OrderedDict
from dataclasses import dataclass
from core.logger import get_logger
import config

log = get_logger("cache")

CACHE_DIR = config.DATA_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class CacheEntry:
    key: str
    value: str
    created_at: float
    expires_at: float
    hits: int = 0
    size_bytes: int = 0

    @property
    def is_expired(self) -> bool:
        return self.expires_at > 0 and time.time() > self.expires_at

    @property
    def ttl_remaining(self) -> float:
        if self.expires_at <= 0:
            return -1  # No expiry
        return max(0, self.expires_at - time.time())


class LRUCache:
    """In-memory LRU cache with TTL support."""

    def __init__(self, max_size: int = 500, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> str | None:
        """Get a value from cache. Returns None if not found or expired."""
        entry = self._cache.get(key)
        if entry is None:
            self._misses += 1
            return None
        if entry.is_expired:
            self._cache.pop(key, None)
            self._misses += 1
            return None
        entry.hits += 1
        self._hits += 1
        self._cache.move_to_end(key)
        return entry.value

    def set(self, key: str, value: str, ttl: int = None):
        """Set a value in cache with optional TTL (seconds)."""
        if ttl is None:
            ttl = self.default_ttl
        expires = time.time() + ttl if ttl > 0 else 0

        if key in self._cache:
            self._cache.move_to_end(key)

        self._cache[key] = CacheEntry(
            key=key, value=value, created_at=time.time(),
            expires_at=expires, size_bytes=len(value.encode()),
        )

        # Evict if over size
        while len(self._cache) > self.max_size:
            self._cache.popitem(last=False)

    def delete(self, key: str) -> bool:
        """Remove a key from cache."""
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self):
        """Clear all cache entries."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    def cleanup_expired(self) -> int:
        """Remove all expired entries. Returns count removed."""
        expired = [k for k, v in self._cache.items() if v.is_expired]
        for k in expired:
            del self._cache[k]
        return len(expired)

    @property
    def size(self) -> int:
        return len(self._cache)

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return (self._hits / total * 100) if total else 0

    def stats(self) -> str:
        """Get cache statistics."""
        total_size = sum(e.size_bytes for e in self._cache.values())
        expired = sum(1 for e in self._cache.values() if e.is_expired)
        return (
            f"Cache Statistics:\n"
            f"  Entries: {self.size}/{self.max_size}\n"
            f"  Memory: {total_size / 1024:.1f} KB\n"
            f"  Hits: {self._hits}\n"
            f"  Misses: {self._misses}\n"
            f"  Hit Rate: {self.hit_rate:.1f}%\n"
            f"  Expired: {expired}\n"
            f"  Default TTL: {self.default_ttl}s"
        )

    def list_keys(self) -> str:
        """List all cache keys."""
        if not self._cache:
            return "Cache is empty."
        lines = []
        for key, entry in self._cache.items():
            ttl = f"{entry.ttl_remaining:.0f}s" if entry.expires_at > 0 else "∞"
            lines.append(f"  {key[:50]} — {entry.size_bytes}B — TTL:{ttl} — Hits:{entry.hits}")
        return f"Cache keys ({self.size}):\n" + "\n".join(lines[:30])


class PersistentCache:
    """Disk-backed cache for larger or long-lived items."""

    def __init__(self, cache_dir: Path = None, default_ttl: int = 86400):
        self.cache_dir = cache_dir or CACHE_DIR
        self.default_ttl = default_ttl
        self._meta_file = self.cache_dir / "_meta.json"
        self._meta = self._load_meta()

    def _load_meta(self) -> dict:
        if self._meta_file.exists():
            try:
                return json.loads(self._meta_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    def _save_meta(self):
        self._meta_file.write_text(json.dumps(self._meta), encoding="utf-8")

    def _key_to_file(self, key: str) -> Path:
        safe_key = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{safe_key}.cache"

    def get(self, key: str) -> str | None:
        """Get from persistent cache."""
        meta = self._meta.get(key)
        if not meta:
            return None
        if meta.get("expires", 0) > 0 and time.time() > meta["expires"]:
            self.delete(key)
            return None
        cache_file = self._key_to_file(key)
        if cache_file.exists():
            meta["hits"] = meta.get("hits", 0) + 1
            self._save_meta()
            return cache_file.read_text(encoding="utf-8")
        return None

    def set(self, key: str, value: str, ttl: int = None):
        """Set in persistent cache."""
        if ttl is None:
            ttl = self.default_ttl
        cache_file = self._key_to_file(key)
        cache_file.write_text(value, encoding="utf-8")
        self._meta[key] = {
            "file": str(cache_file),
            "created": time.time(),
            "expires": time.time() + ttl if ttl > 0 else 0,
            "size": len(value.encode()),
            "hits": 0,
        }
        self._save_meta()

    def delete(self, key: str) -> bool:
        """Delete from persistent cache."""
        if key in self._meta:
            cache_file = self._key_to_file(key)
            if cache_file.exists():
                cache_file.unlink()
            del self._meta[key]
            self._save_meta()
            return True
        return False

    def clear(self):
        """Clear persistent cache."""
        for key in list(self._meta.keys()):
            self.delete(key)

    def cleanup(self) -> int:
        """Remove expired entries."""
        now = time.time()
        expired = [k for k, v in self._meta.items() if v.get("expires", 0) > 0 and now > v["expires"]]
        for k in expired:
            self.delete(k)
        return len(expired)

    def stats(self) -> str:
        """Get persistent cache statistics."""
        total_size = sum(v.get("size", 0) for v in self._meta.values())
        return (
            f"Persistent Cache:\n"
            f"  Entries: {len(self._meta)}\n"
            f"  Total size: {total_size / 1024:.1f} KB\n"
            f"  Directory: {self.cache_dir}"
        )


# ─── Global instances ────────────────────────────────────────
memory_cache = LRUCache(max_size=500, default_ttl=3600)
disk_cache = PersistentCache(default_ttl=86400)


def cache_operation(operation: str, **kwargs) -> str:
    """Unified cache management."""
    key = kwargs.get("key", "")
    value = kwargs.get("value", "")
    ttl = int(kwargs.get("ttl", 0))

    ops = {
        "get": lambda: memory_cache.get(key) or "(not found)",
        "set": lambda: (memory_cache.set(key, value, ttl or None), f"Cached: {key}")[1],
        "delete": lambda: f"Deleted: {key}" if memory_cache.delete(key) else f"Key '{key}' not found",
        "clear": lambda: (memory_cache.clear(), "Memory cache cleared")[1],
        "stats": lambda: memory_cache.stats(),
        "keys": lambda: memory_cache.list_keys(),
        "cleanup": lambda: f"Cleaned {memory_cache.cleanup_expired()} expired entries",
        "disk_get": lambda: disk_cache.get(key) or "(not found)",
        "disk_set": lambda: (disk_cache.set(key, value, ttl or None), f"Cached to disk: {key}")[1],
        "disk_clear": lambda: (disk_cache.clear(), "Disk cache cleared")[1],
        "disk_stats": lambda: disk_cache.stats(),
    }

    handler = ops.get(operation)
    if handler:
        return handler()
    return f"Unknown cache operation: {operation}. Available: {', '.join(ops.keys())}"
