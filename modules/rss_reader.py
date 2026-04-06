"""
RSS Feed Reader Module — Subscribe to, fetch, and manage RSS/Atom feeds.
"""

import json
import asyncio
import re
from datetime import datetime
from pathlib import Path
import aiohttp
import xml.etree.ElementTree as ET
from core.logger import get_logger
import config

log = get_logger("rss")

FEEDS_FILE = config.DATA_DIR / "rss_feeds.json"


class RSSFeed:
    """An RSS feed subscription."""
    def __init__(self, name: str, url: str, category: str = ""):
        self.name = name
        self.url = url
        self.category = category
        self.last_fetched = ""
        self.item_count = 0
        self.enabled = True

    def to_dict(self):
        return self.__dict__

    @staticmethod
    def from_dict(d) -> 'RSSFeed':
        f = RSSFeed(d.get("name", ""), d.get("url", ""), d.get("category", ""))
        f.last_fetched = d.get("last_fetched", "")
        f.item_count = d.get("item_count", 0)
        f.enabled = d.get("enabled", True)
        return f


class RSSReader:
    """RSS/Atom feed reader and manager."""

    def __init__(self):
        self.feeds: dict[str, RSSFeed] = {}
        self._articles_cache: dict[str, list] = {}
        self._load()

    def _load(self):
        if FEEDS_FILE.exists():
            try:
                data = json.loads(FEEDS_FILE.read_text(encoding="utf-8"))
                for name, fdata in data.items():
                    self.feeds[name] = RSSFeed.from_dict(fdata)
            except (json.JSONDecodeError, OSError):
                pass

    def _save(self):
        data = {name: f.to_dict() for name, f in self.feeds.items()}
        FEEDS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def add_feed(self, name: str, url: str, category: str = "") -> str:
        """Subscribe to an RSS feed."""
        self.feeds[name] = RSSFeed(name, url, category)
        self._save()
        return f"Feed '{name}' added: {url}"

    def remove_feed(self, name: str) -> str:
        """Unsubscribe from a feed."""
        if name not in self.feeds:
            return f"Feed '{name}' not found."
        del self.feeds[name]
        self._save()
        return f"Feed '{name}' removed."

    def list_feeds(self) -> str:
        """List all subscribed feeds."""
        if not self.feeds:
            return "No RSS feeds subscribed. Use add_feed to subscribe."
        lines = []
        for name, feed in self.feeds.items():
            status = "✓" if feed.enabled else "✗"
            last = feed.last_fetched[:10] if feed.last_fetched else "never"
            lines.append(f"  {status} {name} [{feed.category}]: {feed.url[:50]}... (last: {last})")
        return f"RSS Feeds ({len(self.feeds)}):\n" + "\n".join(lines)

    async def fetch_feed(self, name: str = "", url: str = "", count: int = 10) -> str:
        """Fetch and display a feed's latest articles."""
        if name and name in self.feeds:
            feed = self.feeds[name]
            url = feed.url
        elif not url:
            return "Provide a feed name or URL."

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15),
                                       headers={"User-Agent": "JARVIS/2.0"}) as resp:
                    if resp.status != 200:
                        return f"Feed returned HTTP {resp.status}"
                    text = await resp.text()
        except Exception as e:
            return f"Feed fetch error: {e}"

        try:
            root = ET.fromstring(text)
        except ET.ParseError as e:
            return f"Feed parse error: {e}"

        articles = []

        # RSS 2.0
        for item in root.findall(".//item")[:count]:
            title = item.findtext("title", "No title")
            link = item.findtext("link", "")
            desc = item.findtext("description", "")
            pub_date = item.findtext("pubDate", "")
            # Strip HTML from description
            desc = re.sub(r'<[^>]+>', '', desc)[:200]
            articles.append({"title": title, "link": link, "description": desc, "date": pub_date})

        # Atom
        if not articles:
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            for entry in root.findall(".//atom:entry", ns)[:count]:
                title = entry.findtext("atom:title", "No title", ns)
                link_elem = entry.find("atom:link", ns)
                link = link_elem.get("href", "") if link_elem is not None else ""
                summary = entry.findtext("atom:summary", "", ns)
                summary = re.sub(r'<[^>]+>', '', summary)[:200]
                updated = entry.findtext("atom:updated", "", ns)
                articles.append({"title": title, "link": link, "description": summary, "date": updated})

        if not articles:
            return "No articles found in feed."

        # Update feed metadata
        if name and name in self.feeds:
            self.feeds[name].last_fetched = datetime.now().isoformat()
            self.feeds[name].item_count = len(articles)
            self._save()
            self._articles_cache[name] = articles

        lines = []
        for i, a in enumerate(articles, 1):
            date_str = f" ({a['date'][:22]})" if a['date'] else ""
            lines.append(f"  {i}. {a['title']}{date_str}")
            if a['description']:
                lines.append(f"     {a['description'][:150]}...")
            if a['link']:
                lines.append(f"     🔗 {a['link'][:80]}")
            lines.append("")

        feed_title = name or url[:40]
        return f"Feed: {feed_title} ({len(articles)} articles):\n\n" + "\n".join(lines)

    async def fetch_all_feeds(self, count: int = 5) -> str:
        """Fetch all subscribed feeds."""
        if not self.feeds:
            return "No feeds subscribed."

        results = []
        for name, feed in self.feeds.items():
            if not feed.enabled:
                continue
            result = await self.fetch_feed(name, count=count)
            results.append(f"─── {name} ───\n{result}")

        return "\n\n".join(results)

    def add_popular_feeds(self) -> str:
        """Add popular default feeds."""
        popular = {
            "TechCrunch": ("https://techcrunch.com/feed/", "tech"),
            "Hacker News": ("https://hnrss.org/newest", "tech"),
            "ArsTechnica": ("https://feeds.arstechnica.com/arstechnica/index", "tech"),
            "BBC News": ("http://feeds.bbci.co.uk/news/rss.xml", "news"),
            "Reuters": ("https://www.reutersagency.com/feed/", "news"),
            "NASA": ("https://www.nasa.gov/rss/dyn/breaking_news.rss", "science"),
            "xkcd": ("https://xkcd.com/rss.xml", "fun"),
        }
        added = 0
        for name, (url, cat) in popular.items():
            if name not in self.feeds:
                self.feeds[name] = RSSFeed(name, url, cat)
                added += 1
        self._save()
        return f"Added {added} popular feeds. Total: {len(self.feeds)}."

    async def search_articles(self, query: str) -> str:
        """Search cached articles."""
        query_lower = query.lower()
        matches = []
        for name, articles in self._articles_cache.items():
            for a in articles:
                if (query_lower in a.get("title", "").lower() or
                    query_lower in a.get("description", "").lower()):
                    matches.append((name, a))

        if not matches:
            return f"No cached articles matching '{query}'. Fetch feeds first."

        lines = [f"  [{name}] {a['title'][:60]}" for name, a in matches[:15]]
        return f"Article search ({len(matches)} matches):\n" + "\n".join(lines)

    async def rss_operation(self, operation: str, **kwargs) -> str:
        """Unified RSS interface."""
        name = kwargs.get("name", "")

        if operation == "fetch":
            return await self.fetch_feed(name, kwargs.get("url", ""), int(kwargs.get("count", 10)))
        elif operation == "fetch_all":
            return await self.fetch_all_feeds(int(kwargs.get("count", 5)))
        elif operation == "search":
            return await self.search_articles(kwargs.get("query", ""))

        sync_ops = {
            "add": lambda: self.add_feed(name, kwargs.get("url", ""), kwargs.get("category", "")),
            "remove": lambda: self.remove_feed(name),
            "list": lambda: self.list_feeds(),
            "popular": lambda: self.add_popular_feeds(),
        }
        handler = sync_ops.get(operation)
        if handler:
            return handler()
        return f"Unknown RSS operation: {operation}. Available: add, remove, list, fetch, fetch_all, search, popular"


rss_reader = RSSReader()
