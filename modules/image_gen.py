"""
Image Generation Module — Generate images using OpenAI DALL-E.
"""

import asyncio
from pathlib import Path
from datetime import datetime
from openai import AsyncOpenAI
import config

client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)


async def generate_image(prompt: str, size: str = "1024x1024") -> str:
    """Generate an image from a text description."""
    try:
        response = await client.images.generate(
            model=config.OPENAI_IMAGE_MODEL,
            prompt=prompt,
            size=size,
            quality="hd",
            n=1,
        )
        image_url = response.data[0].url
        revised_prompt = response.data[0].revised_prompt

        # Download and save locally
        import aiohttp
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = config.GENERATED_DIR / f"image_{ts}.png"

        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as resp:
                if resp.status == 200:
                    save_path.write_bytes(await resp.read())

        return (
            f"Image generated and saved to {save_path}\n"
            f"Revised prompt: {revised_prompt}\n"
            f"URL: {image_url}"
        )
    except Exception as e:
        return f"Image generation failed: {e}"
