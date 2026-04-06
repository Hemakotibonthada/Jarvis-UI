"""
Text Processing Module — Summarize, rephrase, extract, format text.
Advanced NLP utilities powered by OpenAI.
"""

import re
import asyncio
import hashlib
import json
from datetime import datetime
from pathlib import Path
from openai import AsyncOpenAI
import config
from core.logger import get_logger

log = get_logger("text_processing")
client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)


async def summarize_text(text: str, style: str = "concise") -> str:
    """Summarize a long text. Styles: concise, detailed, bullet_points, eli5."""
    if len(text) < 50:
        return "Text too short to summarize."

    style_prompts = {
        "concise": "Provide a brief, concise summary in 2-3 sentences.",
        "detailed": "Provide a detailed summary covering all main points.",
        "bullet_points": "Summarize as a bullet-point list of key takeaways.",
        "eli5": "Explain this like I'm 5 years old — simple and fun.",
        "executive": "Write an executive summary suitable for leadership review.",
        "academic": "Provide an academic-style abstract.",
    }

    prompt = style_prompts.get(style, style_prompts["concise"])
    try:
        response = await client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text[:8000]},
            ],
            temperature=0.3,
            max_tokens=1500,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Summarization failed: {e}"


async def rephrase_text(text: str, tone: str = "professional") -> str:
    """Rephrase text in a different tone.
    Tones: professional, casual, formal, friendly, academic, humorous, persuasive
    """
    try:
        response = await client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": f"Rephrase the following text in a {tone} tone. Keep the same meaning but change the style."},
                {"role": "user", "content": text[:4000]},
            ],
            temperature=0.7,
            max_tokens=2000,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Rephrasing failed: {e}"


async def extract_entities(text: str) -> str:
    """Extract named entities (people, places, organizations, dates, etc.)."""
    try:
        response = await client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "Extract all named entities from the text. Categorize them as: People, Places, Organizations, Dates, Products, Technologies. Return as structured list."},
                {"role": "user", "content": text[:4000]},
            ],
            temperature=0.1,
            max_tokens=1000,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Entity extraction failed: {e}"


async def proofread_text(text: str) -> str:
    """Proofread and correct grammar, spelling, punctuation."""
    try:
        response = await client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "Proofread the following text. Fix grammar, spelling, and punctuation errors. Then list the changes you made."},
                {"role": "user", "content": text[:4000]},
            ],
            temperature=0.1,
            max_tokens=2000,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Proofreading failed: {e}"


async def explain_code(code: str, language: str = "") -> str:
    """Explain what a piece of code does."""
    lang_hint = f"This is {language} code. " if language else ""
    try:
        response = await client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": f"You are a code explainer. {lang_hint}Explain what this code does in plain English. Cover the purpose, how it works step by step, and any notable patterns or issues."},
                {"role": "user", "content": code[:6000]},
            ],
            temperature=0.3,
            max_tokens=2000,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Code explanation failed: {e}"


async def generate_tests(code: str, language: str = "python", framework: str = "pytest") -> str:
    """Generate unit tests for a piece of code."""
    try:
        response = await client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": f"Generate comprehensive unit tests for the following {language} code using {framework}. Include edge cases, error cases, and happy path tests. Return only the test code."},
                {"role": "user", "content": code[:6000]},
            ],
            temperature=0.3,
            max_tokens=3000,
        )
        result = response.choices[0].message.content
        # Strip markdown fences
        if result.startswith("```"):
            lines = result.split("\n")
            result = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        return result
    except Exception as e:
        return f"Test generation failed: {e}"


async def review_code(code: str, language: str = "") -> str:
    """Review code for bugs, performance, and best practices."""
    lang_hint = f"This is {language} code. " if language else ""
    try:
        response = await client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": f"You are a senior code reviewer. {lang_hint}Review this code for: 1) Bugs and potential issues, 2) Performance problems, 3) Security concerns, 4) Code style and best practices, 5) Suggestions for improvement. Be specific and actionable."},
                {"role": "user", "content": code[:6000]},
            ],
            temperature=0.3,
            max_tokens=2000,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Code review failed: {e}"


# ─── Text Statistics ──────────────────────────────────────────
def text_stats(text: str) -> str:
    """Get statistics about a text."""
    words = text.split()
    sentences = re.split(r'[.!?]+', text)
    paragraphs = [p for p in text.split('\n\n') if p.strip()]
    chars = len(text)
    chars_no_space = len(text.replace(' ', '').replace('\n', ''))

    # Unique words
    word_list = [w.lower().strip('.,!?;:()[]{}"\'-') for w in words]
    unique_words = len(set(word_list))

    # Average word length
    avg_word_len = sum(len(w) for w in word_list) / max(len(word_list), 1)

    # Reading time (250 wpm avg)
    reading_time = len(words) / 250

    # Flesch reading ease (simplified)
    sentences_count = max(len([s for s in sentences if s.strip()]), 1)
    syllable_count = sum(max(1, len(re.findall(r'[aeiouy]+', w, re.I))) for w in word_list)
    if len(words) > 0:
        flesch = 206.835 - 1.015 * (len(words) / sentences_count) - 84.6 * (syllable_count / len(words))
    else:
        flesch = 0

    # Most common words
    from collections import Counter
    word_freq = Counter(w for w in word_list if len(w) > 3)
    top_words = word_freq.most_common(10)

    return (
        f"Text Statistics:\n"
        f"  Characters: {chars:,} ({chars_no_space:,} without spaces)\n"
        f"  Words: {len(words):,}\n"
        f"  Unique words: {unique_words:,}\n"
        f"  Sentences: {sentences_count}\n"
        f"  Paragraphs: {len(paragraphs)}\n"
        f"  Avg word length: {avg_word_len:.1f} chars\n"
        f"  Reading time: {reading_time:.1f} min\n"
        f"  Flesch readability: {flesch:.1f} ({'Easy' if flesch > 60 else 'Medium' if flesch > 30 else 'Difficult'})\n"
        f"  Top words: {', '.join(f'{w}({c})' for w, c in top_words)}"
    )


# ─── Text Transformations ────────────────────────────────────
def transform_text(text: str, operation: str) -> str:
    """Transform text: uppercase, lowercase, title, reverse, sort_lines, unique_lines, number_lines, remove_blank_lines, encode_base64, decode_base64, hash_md5, hash_sha256, word_count_per_line, remove_duplicates."""
    import base64

    ops = {
        "uppercase": lambda t: t.upper(),
        "lowercase": lambda t: t.lower(),
        "title": lambda t: t.title(),
        "reverse": lambda t: t[::-1],
        "reverse_words": lambda t: " ".join(t.split()[::-1]),
        "reverse_lines": lambda t: "\n".join(t.split("\n")[::-1]),
        "sort_lines": lambda t: "\n".join(sorted(t.split("\n"))),
        "unique_lines": lambda t: "\n".join(dict.fromkeys(t.split("\n"))),
        "number_lines": lambda t: "\n".join(f"{i+1}: {line}" for i, line in enumerate(t.split("\n"))),
        "remove_blank_lines": lambda t: "\n".join(line for line in t.split("\n") if line.strip()),
        "strip_lines": lambda t: "\n".join(line.strip() for line in t.split("\n")),
        "encode_base64": lambda t: base64.b64encode(t.encode()).decode(),
        "decode_base64": lambda t: base64.b64decode(t.encode()).decode(),
        "hash_md5": lambda t: hashlib.md5(t.encode()).hexdigest(),
        "hash_sha256": lambda t: hashlib.sha256(t.encode()).hexdigest(),
        "count_words": lambda t: f"Word count: {len(t.split())}",
        "remove_html": lambda t: re.sub(r'<[^>]+>', '', t),
        "slug": lambda t: re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-'),
        "camel_case": lambda t: ''.join(w.capitalize() for w in t.split()),
        "snake_case": lambda t: '_'.join(t.lower().split()),
        "kebab_case": lambda t: '-'.join(t.lower().split()),
    }

    handler = ops.get(operation)
    if handler:
        try:
            return handler(text)
        except Exception as e:
            return f"Transform error: {e}"
    return f"Unknown operation: {operation}. Available: {', '.join(ops.keys())}"


# ─── JSON/CSV/YAML Formatting ────────────────────────────────
def format_json(text: str) -> str:
    """Pretty-print JSON."""
    try:
        data = json.loads(text)
        return json.dumps(data, indent=2, ensure_ascii=False)
    except json.JSONDecodeError as e:
        return f"Invalid JSON: {e}"


def json_to_csv(text: str) -> str:
    """Convert JSON array to CSV."""
    try:
        data = json.loads(text)
        if not isinstance(data, list) or not data:
            return "JSON must be an array of objects."

        import csv
        import io
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()
    except Exception as e:
        return f"Conversion error: {e}"


def csv_to_json(text: str) -> str:
    """Convert CSV to JSON array."""
    try:
        import csv
        import io
        reader = csv.DictReader(io.StringIO(text))
        return json.dumps(list(reader), indent=2, ensure_ascii=False)
    except Exception as e:
        return f"Conversion error: {e}"


# ─── Regex Tools ──────────────────────────────────────────────
def regex_extract(text: str, pattern: str) -> str:
    """Extract all matches of a regex pattern from text."""
    try:
        matches = re.findall(pattern, text)
        if not matches:
            return f"No matches found for pattern: {pattern}"
        return f"Found {len(matches)} matches:\n" + "\n".join(f"  {m}" for m in matches[:100])
    except re.error as e:
        return f"Invalid regex: {e}"


def regex_replace(text: str, pattern: str, replacement: str) -> str:
    """Replace all matches of a regex pattern."""
    try:
        result = re.sub(pattern, replacement, text)
        count = len(re.findall(pattern, text))
        return f"Replaced {count} matches.\n\n{result}"
    except re.error as e:
        return f"Invalid regex: {e}"


# ─── Diff Tool ────────────────────────────────────────────────
def text_diff(text1: str, text2: str) -> str:
    """Show differences between two texts."""
    import difflib
    lines1 = text1.splitlines(keepends=True)
    lines2 = text2.splitlines(keepends=True)
    diff = difflib.unified_diff(lines1, lines2, fromfile="Text 1", tofile="Text 2", lineterm="")
    result = "\n".join(diff)
    return result if result else "No differences found."


# ─── Unified text processing interface ────────────────────────
async def text_process(operation: str, text: str = "", **kwargs) -> str:
    """Unified text processing interface."""
    async_ops = {
        "summarize": lambda: summarize_text(text, kwargs.get("style", "concise")),
        "rephrase": lambda: rephrase_text(text, kwargs.get("tone", "professional")),
        "extract_entities": lambda: extract_entities(text),
        "proofread": lambda: proofread_text(text),
        "explain_code": lambda: explain_code(text, kwargs.get("language", "")),
        "generate_tests": lambda: generate_tests(text, kwargs.get("language", "python"), kwargs.get("framework", "pytest")),
        "review_code": lambda: review_code(text, kwargs.get("language", "")),
    }

    sync_ops = {
        "stats": lambda: text_stats(text),
        "transform": lambda: transform_text(text, kwargs.get("transform_type", "uppercase")),
        "format_json": lambda: format_json(text),
        "json_to_csv": lambda: json_to_csv(text),
        "csv_to_json": lambda: csv_to_json(text),
        "regex_extract": lambda: regex_extract(text, kwargs.get("pattern", "")),
        "regex_replace": lambda: regex_replace(text, kwargs.get("pattern", ""), kwargs.get("replacement", "")),
        "diff": lambda: text_diff(text, kwargs.get("text2", "")),
    }

    if operation in async_ops:
        return await async_ops[operation]()
    if operation in sync_ops:
        return sync_ops[operation]()

    all_ops = list(async_ops.keys()) + list(sync_ops.keys())
    return f"Unknown text operation: {operation}. Available: {', '.join(all_ops)}"
