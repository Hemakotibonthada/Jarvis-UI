"""
Utilities Module — Translation, math, news, conversions, networking.
"""

import asyncio
import socket
import subprocess
import urllib.parse
import math
import aiohttp
import config


async def translate_text(text: str, to_lang: str = "en", from_lang: str = "auto") -> str:
    """Translate text using MyMemory free API."""
    try:
        langpair = f"{from_lang}|{to_lang}"
        url = "https://api.mymemory.translated.net/get"
        params = {"q": text[:500], "langpair": langpair}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    translated = data.get("responseData", {}).get("translatedText", "")
                    return f"Translation ({from_lang} → {to_lang}):\n{translated}"
                return f"Translation API returned status {resp.status}"
    except Exception as e:
        return f"Translation error: {e}"


def calculate(expression: str) -> str:
    """Safely evaluate a math expression."""
    allowed_names = {
        "abs": abs, "round": round, "min": min, "max": max,
        "pow": pow, "sum": sum, "len": len,
        "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos,
        "tan": math.tan, "log": math.log, "log10": math.log10,
        "pi": math.pi, "e": math.e, "inf": math.inf,
        "ceil": math.ceil, "floor": math.floor,
        "radians": math.radians, "degrees": math.degrees,
        "factorial": math.factorial, "gcd": math.gcd,
    }
    try:
        # Only allow safe math operations
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return f"{expression} = {result}"
    except Exception as e:
        return f"Calculation error: {e}"


async def get_news(topic: str = "technology", count: int = 5) -> str:
    """Get news headlines."""
    # Use free RSS/API approach
    try:
        url = f"https://news.google.com/rss/search?q={urllib.parse.quote(topic)}&hl=en-US&gl=US&ceid=US:en"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    import xml.etree.ElementTree as ET
                    text = await resp.text()
                    root = ET.fromstring(text)
                    items = root.findall(".//item")[:count]
                    if not items:
                        return f"No news found for '{topic}'."
                    lines = []
                    for item in items:
                        title = item.find("title")
                        pub_date = item.find("pubDate")
                        t = title.text if title is not None else "No title"
                        d = pub_date.text[:22] if pub_date is not None else ""
                        lines.append(f"  • {t} ({d})")
                    return f"News on '{topic}':\n" + "\n".join(lines)
                return f"News fetch returned status {resp.status}"
    except Exception as e:
        return f"News error: {e}"


def convert_units(value: float, from_unit: str, to_unit: str) -> str:
    """Convert between common units."""
    conversions = {
        # Length
        ("km", "miles"): lambda v: v * 0.621371,
        ("miles", "km"): lambda v: v * 1.60934,
        ("m", "ft"): lambda v: v * 3.28084,
        ("ft", "m"): lambda v: v * 0.3048,
        ("cm", "inches"): lambda v: v * 0.393701,
        ("inches", "cm"): lambda v: v * 2.54,
        # Weight
        ("kg", "lbs"): lambda v: v * 2.20462,
        ("lbs", "kg"): lambda v: v * 0.453592,
        ("g", "oz"): lambda v: v * 0.035274,
        ("oz", "g"): lambda v: v * 28.3495,
        # Temperature
        ("c", "f"): lambda v: v * 9 / 5 + 32,
        ("f", "c"): lambda v: (v - 32) * 5 / 9,
        ("c", "k"): lambda v: v + 273.15,
        ("k", "c"): lambda v: v - 273.15,
        # Speed
        ("mph", "kmh"): lambda v: v * 1.60934,
        ("kmh", "mph"): lambda v: v * 0.621371,
        # Data
        ("gb", "mb"): lambda v: v * 1024,
        ("mb", "gb"): lambda v: v / 1024,
        ("tb", "gb"): lambda v: v * 1024,
        ("gb", "tb"): lambda v: v / 1024,
    }

    key = (from_unit.lower(), to_unit.lower())
    converter = conversions.get(key)
    if converter:
        result = converter(value)
        return f"{value} {from_unit} = {result:.4f} {to_unit}"
    return f"Unknown conversion: {from_unit} to {to_unit}. Supported: {', '.join(f'{a}→{b}' for a, b in conversions.keys())}"


def network_scan() -> str:
    """Basic network info and connected devices scan."""
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)

        info = [
            f"  Hostname: {hostname}",
            f"  Local IP: {local_ip}",
        ]

        # Get network interfaces
        import psutil
        addrs = psutil.net_if_addrs()
        for iface, addr_list in addrs.items():
            for addr in addr_list:
                if addr.family == socket.AF_INET:
                    info.append(f"  Interface {iface}: {addr.address}")

        # Quick ping sweep of local subnet  
        info.append(f"\n  Gateway check:")
        try:
            result = subprocess.run(
                ["ipconfig"] if config.IS_WINDOWS else ["ip", "route"],
                capture_output=True, text=True, timeout=5,
            )
            for line in result.stdout.split("\n"):
                if "gateway" in line.lower() or "default" in line.lower():
                    info.append(f"  {line.strip()}")
        except Exception:
            pass

        return "Network Info:\n" + "\n".join(info)
    except Exception as e:
        return f"Network scan error: {e}"


def ping_host(host: str) -> str:
    """Ping a host and return result."""
    try:
        flag = "-n" if config.IS_WINDOWS else "-c"
        result = subprocess.run(
            ["ping", flag, "4", host],
            capture_output=True, text=True, timeout=15,
        )
        return result.stdout or result.stderr
    except subprocess.TimeoutExpired:
        return f"Ping to {host} timed out."
    except Exception as e:
        return f"Ping error: {e}"


def get_datetime_info() -> str:
    """Get current date, time, day, timezone info."""
    from datetime import datetime, timezone
    import time
    now = datetime.now()
    utc_now = datetime.now(timezone.utc)
    return (
        f"Date: {now.strftime('%A, %B %d, %Y')}\n"
        f"Time: {now.strftime('%I:%M:%S %p')}\n"
        f"24h:  {now.strftime('%H:%M:%S')}\n"
        f"UTC:  {utc_now.strftime('%H:%M:%S')}\n"
        f"Timezone: {time.tzname[0]}\n"
        f"Day of year: {now.timetuple().tm_yday}\n"
        f"Week number: {now.isocalendar()[1]}"
    )


async def fetch_url_content(url: str) -> str:
    """Fetch and extract text content from a URL."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15),
                                   headers={"User-Agent": "Mozilla/5.0"}) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    # Basic HTML stripping
                    import re
                    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
                    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
                    text = re.sub(r'<[^>]+>', ' ', text)
                    text = re.sub(r'\s+', ' ', text).strip()
                    return text[:5000]
                return f"URL returned status {resp.status}"
    except Exception as e:
        return f"URL fetch error: {e}"


def create_zip(paths: list[str], output_path: str) -> str:
    """Create a zip archive from files/folders."""
    import zipfile
    from pathlib import Path
    try:
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for p in paths:
                path = Path(p).expanduser()
                if path.is_file():
                    zf.write(path, path.name)
                elif path.is_dir():
                    for f in path.rglob("*"):
                        if f.is_file():
                            zf.write(f, f.relative_to(path.parent))
        return f"Zip archive created: {output_path}"
    except Exception as e:
        return f"Zip error: {e}"


def extract_zip(zip_path: str, dest: str = "") -> str:
    """Extract a zip archive."""
    import zipfile
    from pathlib import Path
    try:
        zp = Path(zip_path).expanduser()
        if not zp.exists():
            return f"Zip file not found: {zp}"
        dest_path = Path(dest).expanduser() if dest else zp.parent / zp.stem
        with zipfile.ZipFile(str(zp), 'r') as zf:
            zf.extractall(str(dest_path))
        return f"Extracted to: {dest_path}"
    except Exception as e:
        return f"Extract error: {e}"


def find_files(directory: str, pattern: str) -> str:
    """Search for files matching a pattern."""
    from pathlib import Path
    p = Path(directory).expanduser()
    if not p.exists():
        return f"Directory not found: {p}"
    matches = list(p.rglob(pattern))[:50]
    if not matches:
        return f"No files matching '{pattern}' in {p}"
    lines = [f"  {m.relative_to(p)} ({m.stat().st_size:,} bytes)" for m in matches if m.is_file()]
    return f"Found {len(matches)} files matching '{pattern}':\n" + "\n".join(lines)
