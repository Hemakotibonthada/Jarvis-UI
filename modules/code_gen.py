"""
Code Generation Module — Generate code using AI and save to files.
"""

from openai import AsyncOpenAI
from pathlib import Path
import config

client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)


async def generate_code(description: str, language: str, file_path: str) -> str:
    """Generate code based on description, save to file."""
    try:
        response = await client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You are an expert {language} programmer. "
                        "Generate clean, well-commented, production-ready code. "
                        "Return ONLY the code, no markdown fences or explanations."
                    ),
                },
                {"role": "user", "content": description},
            ],
            temperature=0.3,
            max_tokens=4096,
        )

        code = response.choices[0].message.content.strip()

        # Remove markdown code fences if present
        if code.startswith("```"):
            lines = code.split("\n")
            code = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        p = Path(file_path).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(code, encoding="utf-8")

        return f"Generated {language} code ({len(code)} chars) saved to {p}"
    except Exception as e:
        return f"Code generation failed: {e}"
