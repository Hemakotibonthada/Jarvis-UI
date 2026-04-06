"""
Web Search Module — Search the web and get weather information.
"""

import asyncio
import aiohttp
import urllib.parse


async def web_search(query: str) -> str:
    """Search the web using DuckDuckGo instant answers API."""
    try:
        url = "https://api.duckduckgo.com/"
        params = {"q": query, "format": "json", "no_html": 1, "skip_disambig": 1}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    results = []

                    if data.get("AbstractText"):
                        results.append(f"Summary: {data['AbstractText']}")
                    if data.get("Answer"):
                        results.append(f"Answer: {data['Answer']}")

                    for topic in data.get("RelatedTopics", [])[:5]:
                        if isinstance(topic, dict) and "Text" in topic:
                            results.append(f"• {topic['Text'][:200]}")

                    return "\n".join(results) if results else f"No instant answers found for '{query}'. Try asking me to explain it directly."
                return f"Search returned status {resp.status}"
    except Exception as e:
        return f"Web search error: {e}"


async def get_weather(location: str) -> str:
    """Get weather from wttr.in."""
    try:
        url = f"https://wttr.in/{urllib.parse.quote(location)}?format=j1"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    current = data.get("current_condition", [{}])[0]
                    area = data.get("nearest_area", [{}])[0]
                    area_name = area.get("areaName", [{}])[0].get("value", location)
                    country = area.get("country", [{}])[0].get("value", "")

                    return (
                        f"Weather in {area_name}, {country}:\n"
                        f"  Temperature: {current.get('temp_C', '?')}°C ({current.get('temp_F', '?')}°F)\n"
                        f"  Feels like: {current.get('FeelsLikeC', '?')}°C\n"
                        f"  Humidity: {current.get('humidity', '?')}%\n"
                        f"  Wind: {current.get('windspeedKmph', '?')} km/h {current.get('winddir16Point', '')}\n"
                        f"  Condition: {current.get('weatherDesc', [{}])[0].get('value', '?')}\n"
                        f"  UV Index: {current.get('uvIndex', '?')}"
                    )
                return f"Weather API returned status {resp.status}"
    except Exception as e:
        return f"Weather error: {e}"
