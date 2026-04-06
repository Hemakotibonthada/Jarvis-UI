"""
API Tester Module — HTTP API testing tool similar to Postman, with request
history, saved collections, and response analysis.
"""

import json
import asyncio
import time
from datetime import datetime
from pathlib import Path
import aiohttp
from core.logger import get_logger
import config

log = get_logger("api_tester")

API_COLLECTIONS_FILE = config.DATA_DIR / "api_collections.json"


class APIRequest:
    """Represents an API request."""
    def __init__(self, method: str, url: str, headers: dict = None,
                 body: str = "", params: dict = None, name: str = ""):
        self.name = name or url[:30]
        self.method = method.upper()
        self.url = url
        self.headers = headers or {}
        self.body = body
        self.params = params or {}

    def to_dict(self):
        return self.__dict__

    @staticmethod
    def from_dict(d) -> 'APIRequest':
        return APIRequest(
            method=d.get("method", "GET"), url=d.get("url", ""),
            headers=d.get("headers", {}), body=d.get("body", ""),
            params=d.get("params", {}), name=d.get("name", ""),
        )


class APIResponse:
    """Represents an API response."""
    def __init__(self, status: int, headers: dict, body: str,
                 duration_ms: float, url: str):
        self.status = status
        self.headers = headers
        self.body = body
        self.duration_ms = duration_ms
        self.url = url
        self.timestamp = datetime.now().isoformat()

    def format_display(self) -> str:
        # Status color indicator
        if self.status < 300:
            status_label = f"✓ {self.status}"
        elif self.status < 400:
            status_label = f"↪ {self.status}"
        elif self.status < 500:
            status_label = f"✗ {self.status}"
        else:
            status_label = f"💀 {self.status}"

        result = (
            f"Response: {status_label} ({self.duration_ms:.0f}ms)\n"
            f"URL: {self.url}\n"
        )

        # Headers (show key ones)
        important_headers = ["Content-Type", "Content-Length", "Server",
                           "X-Request-Id", "Cache-Control", "Set-Cookie"]
        header_lines = []
        for h in important_headers:
            if h.lower() in {k.lower(): k for k in self.headers}:
                actual_key = next(k for k in self.headers if k.lower() == h.lower())
                header_lines.append(f"  {actual_key}: {self.headers[actual_key]}")
        if header_lines:
            result += "Headers:\n" + "\n".join(header_lines) + "\n"

        # Body
        body = self.body[:5000]
        # Try to pretty-print JSON
        try:
            parsed = json.loads(body)
            body = json.dumps(parsed, indent=2)[:5000]
        except (json.JSONDecodeError, ValueError):
            pass

        result += f"\nBody ({len(self.body)} chars):\n{body}"
        return result


class APITester:
    """HTTP API testing and collection management."""

    def __init__(self):
        self.collections: dict[str, list[dict]] = {}
        self.history: list[dict] = []
        self._load()

    def _load(self):
        if API_COLLECTIONS_FILE.exists():
            try:
                data = json.loads(API_COLLECTIONS_FILE.read_text(encoding="utf-8"))
                self.collections = data.get("collections", {})
            except (json.JSONDecodeError, OSError):
                pass

    def _save(self):
        data = {"collections": self.collections}
        API_COLLECTIONS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    async def send_request(self, method: str, url: str, headers: dict = None,
                           body: str = "", params: dict = None,
                           timeout_sec: int = 30) -> str:
        """Send an HTTP request."""
        method = method.upper()
        headers = headers or {}
        params = params or {}

        if not url.startswith("http"):
            url = "https://" + url

        # Auto-set content type for JSON body
        if body and "content-type" not in {k.lower() for k in headers}:
            try:
                json.loads(body)
                headers["Content-Type"] = "application/json"
            except (json.JSONDecodeError, ValueError):
                pass

        start = time.time()

        try:
            async with aiohttp.ClientSession() as session:
                kwargs = {
                    "url": url,
                    "headers": headers,
                    "params": params,
                    "timeout": aiohttp.ClientTimeout(total=timeout_sec),
                }

                if method in ("POST", "PUT", "PATCH") and body:
                    if headers.get("Content-Type") == "application/json":
                        kwargs["json"] = json.loads(body)
                    else:
                        kwargs["data"] = body

                async with getattr(session, method.lower())(**kwargs) as resp:
                    response_body = await resp.text()
                    response_headers = dict(resp.headers)
                    duration = (time.time() - start) * 1000

                    api_resp = APIResponse(
                        status=resp.status, headers=response_headers,
                        body=response_body, duration_ms=duration, url=str(resp.url),
                    )

                    # Log to history
                    self.history.append({
                        "method": method, "url": url, "status": resp.status,
                        "duration_ms": duration, "timestamp": datetime.now().isoformat(),
                    })

                    return api_resp.format_display()
        except aiohttp.ClientError as e:
            return f"Request error: {e}"
        except json.JSONDecodeError as e:
            return f"Invalid JSON body: {e}"
        except Exception as e:
            return f"Error: {e}"

    async def get(self, url: str, headers: dict = None, params: dict = None) -> str:
        """Quick GET request."""
        return await self.send_request("GET", url, headers, params=params)

    async def post(self, url: str, body: str = "", headers: dict = None) -> str:
        """Quick POST request."""
        return await self.send_request("POST", url, headers, body)

    async def put(self, url: str, body: str = "", headers: dict = None) -> str:
        """Quick PUT request."""
        return await self.send_request("PUT", url, headers, body)

    async def delete(self, url: str, headers: dict = None) -> str:
        """Quick DELETE request."""
        return await self.send_request("DELETE", url, headers)

    # ─── Collections ──────────────────────────────────────────
    def save_request(self, collection: str, name: str, method: str,
                     url: str, headers: dict = None, body: str = "") -> str:
        """Save a request to a collection."""
        if collection not in self.collections:
            self.collections[collection] = []

        req = APIRequest(method, url, headers, body, name=name)
        self.collections[collection].append(req.to_dict())
        self._save()
        return f"Request '{name}' saved to collection '{collection}'."

    def list_collections(self) -> str:
        """List all collections."""
        if not self.collections:
            return "No API collections."
        lines = [f"  {name}: {len(reqs)} requests" for name, reqs in self.collections.items()]
        return f"API Collections ({len(self.collections)}):\n" + "\n".join(lines)

    def get_collection(self, name: str) -> str:
        """Show requests in a collection."""
        reqs = self.collections.get(name)
        if not reqs:
            return f"Collection '{name}' not found."
        lines = [f"  {i+1}. [{r.get('method', 'GET')}] {r.get('name', r.get('url', '?'))}: {r.get('url', '')[:60]}" for i, r in enumerate(reqs)]
        return f"Collection '{name}' ({len(reqs)} requests):\n" + "\n".join(lines)

    async def run_collection(self, name: str) -> str:
        """Run all requests in a collection sequentially."""
        reqs = self.collections.get(name)
        if not reqs:
            return f"Collection '{name}' not found."

        results = []
        for req_data in reqs:
            req = APIRequest.from_dict(req_data)
            result = await self.send_request(req.method, req.url, req.headers, req.body, req.params)
            results.append(f"─── {req.name} ───\n{result[:500]}")

        return f"Collection '{name}' results:\n\n" + "\n\n".join(results)

    def delete_collection(self, name: str) -> str:
        """Delete a collection."""
        if name not in self.collections:
            return f"Collection '{name}' not found."
        del self.collections[name]
        self._save()
        return f"Collection '{name}' deleted."

    def get_history(self, count: int = 20) -> str:
        """Get request history."""
        if not self.history:
            return "No request history."
        recent = self.history[-count:]
        lines = [
            f"  [{h['timestamp'][11:19]}] {h['method']} {h['url'][:50]} → {h['status']} ({h['duration_ms']:.0f}ms)"
            for h in reversed(recent)
        ]
        return f"API History ({len(recent)}):\n" + "\n".join(lines)

    # ─── Unified Interface ────────────────────────────────
    async def api_test_operation(self, operation: str, **kwargs) -> str:
        """Unified API testing interface."""
        method = kwargs.get("method", "GET")
        url = kwargs.get("url", "")
        body = kwargs.get("body", "")
        headers = kwargs.get("headers", {})
        name = kwargs.get("name", "")
        collection = kwargs.get("collection", "")

        async_ops = {
            "request": lambda: self.send_request(method, url, headers, body),
            "get": lambda: self.get(url, headers),
            "post": lambda: self.post(url, body, headers),
            "put": lambda: self.put(url, body, headers),
            "delete": lambda: self.delete(url, headers),
            "run_collection": lambda: self.run_collection(collection),
        }

        if operation in async_ops:
            return await async_ops[operation]()

        sync_ops = {
            "save": lambda: self.save_request(collection, name, method, url, headers, body),
            "collections": lambda: self.list_collections(),
            "collection": lambda: self.get_collection(collection),
            "delete_collection": lambda: self.delete_collection(collection),
            "history": lambda: self.get_history(int(kwargs.get("count", 20))),
        }

        handler = sync_ops.get(operation)
        if handler:
            return handler()
        return f"Unknown API test operation: {operation}. Available: request, get, post, put, delete, save, collections, collection, run_collection, delete_collection, history"


api_tester = APITester()
