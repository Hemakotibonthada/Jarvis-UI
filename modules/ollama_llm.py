"""
Ollama Local LLM Module — Fallback to local AI models (llama3, mistral, etc.)
when OpenAI is unavailable. Uses Ollama running on localhost.
"""

import asyncio
import aiohttp
from core.logger import get_logger

log = get_logger("ollama")

OLLAMA_URL = "http://localhost:11434"


async def ask_ollama(prompt: str, model: str = "llama3",
                     system_prompt: str = "", temperature: float = 0.7,
                     max_tokens: int = 500) -> str:
    """Send a prompt to locally running Ollama and get a response."""
    try:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{OLLAMA_URL}/api/chat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("message", {}).get("content", "No response from local model.")
                else:
                    return f"Ollama returned status {resp.status}"
    except aiohttp.ClientConnectorError:
        return ""  # Ollama not running — return empty to signal unavailable
    except Exception as e:
        return f"Ollama error: {e}"


async def is_ollama_available() -> bool:
    """Check if Ollama is running locally."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{OLLAMA_URL}/api/tags",
                timeout=aiohttp.ClientTimeout(total=3),
            ) as resp:
                return resp.status == 200
    except Exception:
        return False


async def list_ollama_models() -> str:
    """List available Ollama models."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{OLLAMA_URL}/api/tags",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    models = data.get("models", [])
                    if not models:
                        return "No Ollama models installed. Run: ollama pull llama3"
                    lines = [f"  {m['name']} ({m.get('size', 0) // (1024**3):.1f}GB)" for m in models]
                    return "Ollama models:\n" + "\n".join(lines)
                return "Could not list models."
    except Exception:
        return "Ollama not running. Install from https://ollama.ai and run: ollama serve"


async def generate_with_ollama(prompt: str, model: str = "llama3") -> str:
    """Simple generation endpoint (non-chat)."""
    try:
        payload = {"model": model, "prompt": prompt, "stream": False}
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{OLLAMA_URL}/api/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("response", "")
                return f"Ollama error: {resp.status}"
    except Exception as e:
        return f"Ollama error: {e}"
