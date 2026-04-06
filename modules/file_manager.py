"""
File Manager Module — Create, read, modify, delete files and directories.
"""

import os
import shutil
from pathlib import Path


def create_file(file_path: str, content: str) -> str:
    """Create a file with content. Creates parent directories if needed."""
    p = Path(file_path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"File created: {p} ({len(content)} chars)"


def read_file(file_path: str) -> str:
    """Read a file's content."""
    p = Path(file_path).expanduser()
    if not p.exists():
        return f"File not found: {p}"
    if not p.is_file():
        return f"Not a file: {p}"
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"Binary file ({p.stat().st_size} bytes) — cannot display as text."


def list_directory(dir_path: str, recursive: bool = False) -> str:
    """List directory contents."""
    p = Path(dir_path).expanduser()
    if not p.exists():
        return f"Directory not found: {p}"
    if not p.is_dir():
        return f"Not a directory: {p}"

    entries = []
    if recursive:
        for item in sorted(p.rglob("*")):
            rel = item.relative_to(p)
            kind = "DIR " if item.is_dir() else "FILE"
            size = item.stat().st_size if item.is_file() else 0
            entries.append(f"  {kind} {rel} ({size:,} bytes)" if item.is_file() else f"  {kind} {rel}/")
            if len(entries) > 200:
                entries.append("  ... (truncated)")
                break
    else:
        for item in sorted(p.iterdir()):
            kind = "DIR " if item.is_dir() else "FILE"
            size = item.stat().st_size if item.is_file() else 0
            entries.append(f"  {kind} {item.name} ({size:,} bytes)" if item.is_file() else f"  {kind} {item.name}/")

    return f"Contents of {p}:\n" + "\n".join(entries)


def delete_file(path: str) -> str:
    """Delete a file or directory."""
    p = Path(path).expanduser()
    if not p.exists():
        return f"Path not found: {p}"
    if p.is_file():
        p.unlink()
        return f"Deleted file: {p}"
    elif p.is_dir():
        shutil.rmtree(p)
        return f"Deleted directory: {p}"
    return f"Unknown path type: {p}"


def move_file(src: str, dst: str) -> str:
    """Move/rename a file or directory."""
    s, d = Path(src).expanduser(), Path(dst).expanduser()
    if not s.exists():
        return f"Source not found: {s}"
    d.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(s), str(d))
    return f"Moved {s} → {d}"


def copy_file(src: str, dst: str) -> str:
    """Copy a file or directory."""
    s, d = Path(src).expanduser(), Path(dst).expanduser()
    if not s.exists():
        return f"Source not found: {s}"
    d.parent.mkdir(parents=True, exist_ok=True)
    if s.is_dir():
        shutil.copytree(str(s), str(d))
    else:
        shutil.copy2(str(s), str(d))
    return f"Copied {s} → {d}"
