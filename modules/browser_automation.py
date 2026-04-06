"""
Browser Automation Module — Web scraping, form filling, browser control, 
and web testing via Selenium or HTTP.
"""

import asyncio
import json
import re
import urllib.parse
from datetime import datetime
from pathlib import Path
import aiohttp
from core.logger import get_logger
import config

log = get_logger("browser")

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False


class WebScraper:
    """HTTP-based web scraping without browser."""

    @staticmethod
    async def fetch_page(url: str, headers: dict = None) -> dict:
        """Fetch a web page and return content."""
        default_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        if headers:
            default_headers.update(headers)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=default_headers,
                                       timeout=aiohttp.ClientTimeout(total=30),
                                       allow_redirects=True) as resp:
                    content_type = resp.headers.get("Content-Type", "")
                    status = resp.status
                    final_url = str(resp.url)
                    
                    if "text" in content_type or "html" in content_type or "json" in content_type:
                        text = await resp.text()
                    else:
                        text = f"(Binary content: {content_type}, {resp.content_length or 0} bytes)"

                    return {
                        "status": status,
                        "url": final_url,
                        "content_type": content_type,
                        "text": text[:50000],
                    }
        except Exception as e:
            return {"status": 0, "url": url, "error": str(e)}

    @staticmethod
    def extract_text(html: str) -> str:
        """Extract readable text from HTML."""
        # Remove scripts and styles
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.I)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.I)
        text = re.sub(r'<head[^>]*>.*?</head>', '', text, flags=re.DOTALL | re.I)
        # Remove tags
        text = re.sub(r'<[^>]+>', ' ', text)
        # Clean whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        # Decode common entities
        text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        text = text.replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
        return text

    @staticmethod
    def extract_links(html: str, base_url: str = "") -> list[dict]:
        """Extract links from HTML."""
        links = []
        for match in re.finditer(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.I | re.DOTALL):
            href = match.group(1).strip()
            text = re.sub(r'<[^>]+>', '', match.group(2)).strip()
            if href.startswith("http") or href.startswith("/"):
                if href.startswith("/") and base_url:
                    parsed = urllib.parse.urlparse(base_url)
                    href = f"{parsed.scheme}://{parsed.netloc}{href}"
                links.append({"url": href, "text": text[:100]})
        return links

    @staticmethod
    def extract_images(html: str, base_url: str = "") -> list[dict]:
        """Extract image URLs from HTML."""
        images = []
        for match in re.finditer(r'<img\s+[^>]*src=["\']([^"\']+)["\'][^>]*>', html, re.I):
            src = match.group(1).strip()
            alt = ""
            alt_match = re.search(r'alt=["\']([^"\']*)["\']', match.group(0))
            if alt_match:
                alt = alt_match.group(1)
            if src.startswith("/") and base_url:
                parsed = urllib.parse.urlparse(base_url)
                src = f"{parsed.scheme}://{parsed.netloc}{src}"
            images.append({"url": src, "alt": alt})
        return images

    @staticmethod
    def extract_metadata(html: str) -> dict:
        """Extract page metadata (title, description, OG tags)."""
        meta = {}
        
        title_match = re.search(r'<title>(.*?)</title>', html, re.I | re.DOTALL)
        if title_match:
            meta["title"] = title_match.group(1).strip()

        for match in re.finditer(r'<meta\s+[^>]*>', html, re.I):
            tag = match.group(0)
            name = ""
            content = ""
            name_match = re.search(r'(?:name|property)=["\']([^"\']+)["\']', tag)
            content_match = re.search(r'content=["\']([^"\']+)["\']', tag)
            if name_match:
                name = name_match.group(1)
            if content_match:
                content = content_match.group(1)
            if name and content:
                meta[name] = content

        return meta

    @staticmethod
    def extract_tables(html: str) -> list[list[list[str]]]:
        """Extract tables from HTML."""
        tables = []
        for table_match in re.finditer(r'<table[^>]*>(.*?)</table>', html, re.I | re.DOTALL):
            table_html = table_match.group(1)
            rows = []
            for row_match in re.finditer(r'<tr[^>]*>(.*?)</tr>', table_html, re.I | re.DOTALL):
                cells = []
                for cell_match in re.finditer(r'<t[dh][^>]*>(.*?)</t[dh]>', row_match.group(1), re.I | re.DOTALL):
                    cell_text = re.sub(r'<[^>]+>', '', cell_match.group(1)).strip()
                    cells.append(cell_text)
                if cells:
                    rows.append(cells)
            if rows:
                tables.append(rows)
        return tables


class BrowserController:
    """Selenium-based browser automation."""

    def __init__(self):
        self.driver = None

    def start_browser(self, headless: bool = True) -> str:
        """Start a browser instance."""
        if not HAS_SELENIUM:
            return "Selenium not installed. Run: pip install selenium"

        try:
            options = Options()
            if headless:
                options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")

            self.driver = webdriver.Chrome(options=options)
            return f"Browser started ({'headless' if headless else 'visible'} mode)."
        except Exception as e:
            return f"Failed to start browser: {e}"

    def stop_browser(self) -> str:
        """Close the browser."""
        if self.driver:
            self.driver.quit()
            self.driver = None
            return "Browser closed."
        return "No browser running."

    def navigate(self, url: str) -> str:
        """Navigate to a URL."""
        if not self.driver:
            return "Browser not started."
        try:
            self.driver.get(url)
            return f"Navigated to: {self.driver.title} ({url})"
        except Exception as e:
            return f"Navigation error: {e}"

    def get_page_text(self) -> str:
        """Get the visible text of the current page."""
        if not self.driver:
            return "Browser not started."
        try:
            text = self.driver.find_element(By.TAG_NAME, "body").text
            return text[:5000]
        except Exception as e:
            return f"Error: {e}"

    def take_screenshot(self, file_name: str = "") -> str:
        """Take a browser screenshot."""
        if not self.driver:
            return "Browser not started."
        try:
            if not file_name:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_name = f"browser_{ts}.png"
            path = config.GENERATED_DIR / file_name
            self.driver.save_screenshot(str(path))
            return f"Browser screenshot saved: {path}"
        except Exception as e:
            return f"Screenshot error: {e}"

    def click_element(self, selector: str, by: str = "css") -> str:
        """Click an element by selector."""
        if not self.driver:
            return "Browser not started."
        try:
            by_map = {"css": By.CSS_SELECTOR, "xpath": By.XPATH, "id": By.ID, "name": By.NAME, "class": By.CLASS_NAME}
            sel = by_map.get(by, By.CSS_SELECTOR)
            element = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((sel, selector)))
            element.click()
            return f"Clicked element: {selector}"
        except Exception as e:
            return f"Click error: {e}"

    def type_in_element(self, selector: str, text: str, by: str = "css") -> str:
        """Type text into an input element."""
        if not self.driver:
            return "Browser not started."
        try:
            by_map = {"css": By.CSS_SELECTOR, "xpath": By.XPATH, "id": By.ID, "name": By.NAME}
            sel = by_map.get(by, By.CSS_SELECTOR)
            element = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((sel, selector)))
            element.clear()
            element.send_keys(text)
            return f"Typed into {selector}"
        except Exception as e:
            return f"Type error: {e}"

    def get_page_source(self) -> str:
        """Get current page HTML source."""
        if not self.driver:
            return "Browser not started."
        return self.driver.page_source[:10000]

    def execute_js(self, script: str) -> str:
        """Execute JavaScript in the browser."""
        if not self.driver:
            return "Browser not started."
        try:
            result = self.driver.execute_script(script)
            return str(result) if result else "Script executed (no return value)."
        except Exception as e:
            return f"JS error: {e}"

    def get_cookies(self) -> str:
        """Get browser cookies."""
        if not self.driver:
            return "Browser not started."
        cookies = self.driver.get_cookies()
        lines = [f"  {c['name']}: {c['value'][:50]}..." for c in cookies[:20]]
        return f"Cookies ({len(cookies)}):\n" + "\n".join(lines)

    def current_url(self) -> str:
        if not self.driver:
            return "Browser not started."
        return f"Current URL: {self.driver.current_url}\nTitle: {self.driver.title}"


# ─── High-level scraping functions ────────────────────────────
scraper = WebScraper()
browser = BrowserController()


async def scrape_page(url: str, extract: str = "text") -> str:
    """Scrape a web page and extract content."""
    result = await scraper.fetch_page(url)
    if result.get("error"):
        return f"Fetch error: {result['error']}"
    if result["status"] != 200:
        return f"HTTP {result['status']} for {url}"

    html = result["text"]
    
    if extract == "text":
        text = scraper.extract_text(html)
        return f"Page text from {result['url']}:\n\n{text[:5000]}"
    elif extract == "links":
        links = scraper.extract_links(html, url)
        lines = [f"  [{l['text'][:40]}] {l['url']}" for l in links[:30]]
        return f"Links ({len(links)}):\n" + "\n".join(lines)
    elif extract == "images":
        images = scraper.extract_images(html, url)
        lines = [f"  [{i['alt'][:30]}] {i['url']}" for i in images[:20]]
        return f"Images ({len(images)}):\n" + "\n".join(lines)
    elif extract == "metadata":
        meta = scraper.extract_metadata(html)
        lines = [f"  {k}: {v[:100]}" for k, v in meta.items()]
        return f"Page Metadata:\n" + "\n".join(lines)
    elif extract == "tables":
        tables = scraper.extract_tables(html)
        if not tables:
            return "No tables found."
        result_str = f"Found {len(tables)} table(s):\n"
        for i, table in enumerate(tables[:3]):
            result_str += f"\n  Table {i+1} ({len(table)} rows):\n"
            for row in table[:10]:
                result_str += f"    {' | '.join(c[:20] for c in row)}\n"
        return result_str
    elif extract == "all":
        meta = scraper.extract_metadata(html)
        text = scraper.extract_text(html)
        links = scraper.extract_links(html, url)
        images = scraper.extract_images(html, url)
        return (
            f"Page: {meta.get('title', url)}\n"
            f"URL: {result['url']}\n"
            f"Status: {result['status']}\n\n"
            f"Text ({len(text)} chars):\n{text[:2000]}\n\n"
            f"Links: {len(links)} | Images: {len(images)}\n"
            f"Meta: {json.dumps(meta, indent=2)[:500]}"
        )

    return f"Unknown extract mode: {extract}. Use: text, links, images, metadata, tables, all"


async def monitor_webpage(url: str, css_selector: str = "",
                          check_text: str = "") -> str:
    """Check a webpage for specific content or changes."""
    result = await scraper.fetch_page(url)
    if result.get("error"):
        return f"Monitor error: {result['error']}"

    html = result["text"]
    text = scraper.extract_text(html)

    if check_text:
        found = check_text.lower() in text.lower()
        return (
            f"Webpage Monitor: {url}\n"
            f"  Looking for: '{check_text}'\n"
            f"  Status: {'FOUND ✓' if found else 'NOT FOUND ✗'}\n"
            f"  Page title: {scraper.extract_metadata(html).get('title', '?')}"
        )

    if css_selector:
        # Try to find CSS selector in HTML (basic)
        pattern = re.compile(rf'class=["\'][^"\']*{re.escape(css_selector)}[^"\']*["\']', re.I)
        matches = pattern.findall(html)
        return f"Selector '{css_selector}': {len(matches)} matches found."

    return f"Page status: HTTP {result['status']} — {len(text)} chars of text content."


async def compare_pages(url1: str, url2: str) -> str:
    """Compare text content of two web pages."""
    r1 = await scraper.fetch_page(url1)
    r2 = await scraper.fetch_page(url2)

    if r1.get("error") or r2.get("error"):
        return f"Fetch error: {r1.get('error', '')} {r2.get('error', '')}"

    text1 = scraper.extract_text(r1["text"])
    text2 = scraper.extract_text(r2["text"])

    # Compare word sets
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    common = words1 & words2
    only1 = words1 - words2
    only2 = words2 - words1

    similarity = len(common) / max(len(words1 | words2), 1) * 100

    return (
        f"Page Comparison:\n"
        f"  Page 1: {url1[:60]} ({len(text1)} chars)\n"
        f"  Page 2: {url2[:60]} ({len(text2)} chars)\n"
        f"  Similarity: {similarity:.1f}%\n"
        f"  Common words: {len(common)}\n"
        f"  Unique to page 1: {len(only1)}\n"
        f"  Unique to page 2: {len(only2)}"
    )


async def download_file(url: str, save_path: str = "") -> str:
    """Download a file from URL."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status != 200:
                    return f"Download failed: HTTP {resp.status}"
                
                content = await resp.read()
                
                if not save_path:
                    filename = url.split("/")[-1].split("?")[0] or "download"
                    save_path = str(config.GENERATED_DIR / filename)
                
                p = Path(save_path)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(content)
                
                size_mb = len(content) / (1024 * 1024)
                return f"Downloaded: {p} ({size_mb:.2f} MB)"
    except Exception as e:
        return f"Download error: {e}"


# ─── Unified Interface ───────────────────────────────────────
async def browser_operation(operation: str, **kwargs) -> str:
    """Unified browser/scraping interface."""
    url = kwargs.get("url", "")
    
    async_ops = {
        "scrape": lambda: scrape_page(url, kwargs.get("extract", "text")),
        "monitor": lambda: monitor_webpage(url, kwargs.get("selector", ""), kwargs.get("check_text", "")),
        "compare": lambda: compare_pages(url, kwargs.get("url2", "")),
        "download": lambda: download_file(url, kwargs.get("save_path", "")),
    }
    
    sync_ops = {
        "start": lambda: browser.start_browser(kwargs.get("headless", True)),
        "stop": lambda: browser.stop_browser(),
        "navigate": lambda: browser.navigate(url),
        "text": lambda: browser.get_page_text(),
        "screenshot": lambda: browser.take_screenshot(kwargs.get("filename", "")),
        "click": lambda: browser.click_element(kwargs.get("selector", ""), kwargs.get("by", "css")),
        "type": lambda: browser.type_in_element(kwargs.get("selector", ""), kwargs.get("text", "")),
        "js": lambda: browser.execute_js(kwargs.get("script", "")),
        "cookies": lambda: browser.get_cookies(),
        "current": lambda: browser.current_url(),
    }

    if operation in async_ops:
        return await async_ops[operation]()
    if operation in sync_ops:
        return sync_ops[operation]()
    
    all_ops = list(async_ops.keys()) + list(sync_ops.keys())
    return f"Unknown browser operation: {operation}. Available: {', '.join(all_ops)}"
