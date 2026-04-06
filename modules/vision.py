"""
Vision & PDF Module — Image analysis, OCR, PDF reading, QR codes.
"""

import asyncio
import base64
from pathlib import Path
from datetime import datetime
from openai import AsyncOpenAI
import config

client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)


async def analyze_image(image_path: str, question: str = "Describe this image in detail.") -> str:
    """Analyze an image using GPT-4o Vision."""
    p = Path(image_path).expanduser()
    if not p.exists():
        return f"Image not found: {p}"

    try:
        with open(p, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()

        ext = p.suffix.lower().lstrip(".")
        mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "gif": "gif", "webp": "webp"}.get(ext, "png")

        response = await client.chat.completions.create(
            model=config.OPENAI_VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question},
                        {"type": "image_url", "image_url": {"url": f"data:image/{mime};base64,{b64}"}},
                    ],
                }
            ],
            max_tokens=1000,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Image analysis failed: {e}"


async def analyze_screenshot(question: str = "What's on this screen?") -> str:
    """Take a screenshot and analyze it with vision AI."""
    try:
        import pyautogui
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = config.GENERATED_DIR / f"screen_{ts}.png"
        img = pyautogui.screenshot()
        img.save(str(path))
        result = await analyze_image(str(path), question)
        return f"Screenshot analyzed ({path}):\n{result}"
    except ImportError:
        return "pyautogui not installed — cannot take screenshot."
    except Exception as e:
        return f"Screenshot analysis failed: {e}"


def read_pdf(file_path: str, max_pages: int = 20) -> str:
    """Read text content from a PDF file."""
    p = Path(file_path).expanduser()
    if not p.exists():
        return f"PDF not found: {p}"

    try:
        import PyPDF2
        text_parts = []
        with open(p, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            total = len(reader.pages)
            pages_to_read = min(total, max_pages)
            for i in range(pages_to_read):
                page_text = reader.pages[i].extract_text()
                if page_text:
                    text_parts.append(f"--- Page {i + 1} ---\n{page_text}")

        if not text_parts:
            return "PDF has no extractable text (might be scanned/image-based)."

        full = "\n\n".join(text_parts)
        if len(full) > 8000:
            full = full[:8000] + "\n\n... (truncated)"
        return f"PDF: {p.name} ({total} pages, read {pages_to_read})\n\n{full}"
    except ImportError:
        return "PyPDF2 not installed. Run: pip install PyPDF2"
    except Exception as e:
        return f"PDF read error: {e}"


async def summarize_pdf(file_path: str) -> str:
    """Read a PDF and generate an AI summary."""
    content = read_pdf(file_path)
    if content.startswith("PDF not found") or content.startswith("PyPDF2") or content.startswith("PDF read error"):
        return content

    try:
        response = await client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "Summarize the following PDF content concisely. Highlight key points."},
                {"role": "user", "content": content[:6000]},
            ],
            max_tokens=1000,
        )
        return f"PDF Summary:\n{response.choices[0].message.content}"
    except Exception as e:
        return f"Summary failed: {e}"


def generate_qr_code(data: str, file_name: str = "") -> str:
    """Generate a QR code image."""
    try:
        import qrcode
        img = qrcode.make(data)
        if not file_name:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"qr_{ts}.png"
        path = config.GENERATED_DIR / file_name
        img.save(str(path))
        return f"QR code generated: {path}"
    except ImportError:
        return "qrcode not installed. Run: pip install qrcode[pil]"
    except Exception as e:
        return f"QR code error: {e}"


def ocr_image(image_path: str) -> str:
    """Extract text from an image using OCR."""
    p = Path(image_path).expanduser()
    if not p.exists():
        return f"Image not found: {p}"
    try:
        from PIL import Image
        import pytesseract
        img = Image.open(str(p))
        text = pytesseract.image_to_string(img)
        return text.strip() if text.strip() else "No text detected in image."
    except ImportError:
        return "pytesseract not installed. Run: pip install pytesseract (also need Tesseract OCR installed)."
    except Exception as e:
        return f"OCR error: {e}"
