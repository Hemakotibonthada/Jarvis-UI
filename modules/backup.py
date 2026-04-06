"""
Backup & Sync Module — Automated file backups, folder watching, and sync.
"""

import os
import shutil
import hashlib
import json
import zipfile
from datetime import datetime
from pathlib import Path
from core.logger import get_logger
import config

log = get_logger("backup")


class BackupManager:
    """Manages file/folder backups with versioning."""

    def __init__(self):
        self.backup_dir = config.DATA_DIR / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_file = self.backup_dir / "manifest.json"
        self._manifest = self._load_manifest()

    def _load_manifest(self) -> dict:
        if self.manifest_file.exists():
            try:
                return json.loads(self.manifest_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {"backups": [], "total_size": 0}

    def _save_manifest(self):
        self.manifest_file.write_text(
            json.dumps(self._manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def create_backup(self, source_path: str, name: str = "", compress: bool = True) -> str:
        """Create a backup of a file or directory."""
        src = Path(source_path).expanduser()
        if not src.exists():
            return f"Source not found: {src}"

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = name or src.name.replace(" ", "_")[:30]
        backup_name = f"{safe_name}_{ts}"

        if compress:
            backup_path = self.backup_dir / f"{backup_name}.zip"
            try:
                with zipfile.ZipFile(str(backup_path), 'w', zipfile.ZIP_DEFLATED) as zf:
                    if src.is_file():
                        zf.write(src, src.name)
                    elif src.is_dir():
                        for f in src.rglob("*"):
                            if f.is_file():
                                zf.write(f, f.relative_to(src.parent))
                backup_size = backup_path.stat().st_size
            except Exception as e:
                return f"Backup compression failed: {e}"
        else:
            backup_path = self.backup_dir / backup_name
            try:
                if src.is_file():
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(src), str(backup_path))
                elif src.is_dir():
                    shutil.copytree(str(src), str(backup_path))
                backup_size = sum(
                    f.stat().st_size for f in backup_path.rglob("*") if f.is_file()
                ) if backup_path.is_dir() else backup_path.stat().st_size
            except Exception as e:
                return f"Backup copy failed: {e}"

        # Update manifest
        entry = {
            "name": safe_name,
            "source": str(src),
            "backup_path": str(backup_path),
            "timestamp": ts,
            "size_bytes": backup_size,
            "compressed": compress,
            "type": "file" if src.is_file() else "directory",
        }
        self._manifest["backups"].append(entry)
        self._manifest["total_size"] += backup_size
        self._save_manifest()

        size_mb = backup_size / (1024 * 1024)
        return f"Backup created:\n  Name: {safe_name}\n  Path: {backup_path}\n  Size: {size_mb:.2f} MB\n  Source: {src}"

    def list_backups(self) -> str:
        """List all backups."""
        backups = self._manifest.get("backups", [])
        if not backups:
            return "No backups found."

        lines = []
        for i, b in enumerate(reversed(backups[:30]), 1):
            size_mb = b["size_bytes"] / (1024 * 1024)
            lines.append(
                f"  {i}. {b['name']} ({b['timestamp']}) — {size_mb:.1f}MB "
                f"{'[ZIP]' if b.get('compressed') else '[DIR]'} — {b['source'][:50]}"
            )

        total_mb = self._manifest.get("total_size", 0) / (1024 * 1024)
        return f"Backups ({len(backups)} total, {total_mb:.1f}MB):\n" + "\n".join(lines)

    def restore_backup(self, index: int, dest: str = "") -> str:
        """Restore a backup by index (1-based from most recent)."""
        backups = self._manifest.get("backups", [])
        if not backups:
            return "No backups available."

        reversed_backups = list(reversed(backups))
        if index < 1 or index > len(reversed_backups):
            return f"Invalid index. Available: 1-{len(reversed_backups)}"

        entry = reversed_backups[index - 1]
        backup_path = Path(entry["backup_path"])

        if not backup_path.exists():
            return f"Backup file not found: {backup_path}"

        dest_path = Path(dest).expanduser() if dest else Path(entry["source"]).expanduser()

        try:
            if entry.get("compressed") and backup_path.suffix == ".zip":
                with zipfile.ZipFile(str(backup_path), 'r') as zf:
                    zf.extractall(str(dest_path.parent))
                return f"Restored backup '{entry['name']}' to {dest_path.parent}"
            else:
                if backup_path.is_dir():
                    if dest_path.exists():
                        shutil.rmtree(str(dest_path))
                    shutil.copytree(str(backup_path), str(dest_path))
                else:
                    shutil.copy2(str(backup_path), str(dest_path))
                return f"Restored backup '{entry['name']}' to {dest_path}"
        except Exception as e:
            return f"Restore failed: {e}"

    def delete_backup(self, index: int) -> str:
        """Delete a backup by index."""
        backups = self._manifest.get("backups", [])
        if not backups:
            return "No backups available."

        reversed_idx = len(backups) - index
        if reversed_idx < 0 or reversed_idx >= len(backups):
            return "Invalid index."

        entry = backups[reversed_idx]
        backup_path = Path(entry["backup_path"])

        try:
            if backup_path.exists():
                if backup_path.is_dir():
                    shutil.rmtree(str(backup_path))
                else:
                    backup_path.unlink()
        except Exception as e:
            return f"Failed to delete backup file: {e}"

        self._manifest["total_size"] -= entry.get("size_bytes", 0)
        backups.pop(reversed_idx)
        self._save_manifest()

        return f"Deleted backup: {entry['name']} ({entry['timestamp']})"

    def cleanup_old(self, keep: int = 10) -> str:
        """Remove old backups, keeping the most recent ones."""
        backups = self._manifest.get("backups", [])
        if len(backups) <= keep:
            return f"Only {len(backups)} backups exist (keeping {keep}). Nothing to clean."

        to_remove = backups[:-keep]
        removed = 0
        freed = 0

        for entry in to_remove:
            path = Path(entry["backup_path"])
            try:
                if path.exists():
                    if path.is_dir():
                        shutil.rmtree(str(path))
                    else:
                        path.unlink()
                freed += entry.get("size_bytes", 0)
                removed += 1
            except Exception:
                pass

        self._manifest["backups"] = backups[-keep:]
        self._manifest["total_size"] -= freed
        self._save_manifest()

        freed_mb = freed / (1024 * 1024)
        return f"Cleaned up {removed} old backups. Freed {freed_mb:.1f}MB."

    def get_checksum(self, file_path: str, algorithm: str = "sha256") -> str:
        """Calculate file checksum."""
        p = Path(file_path).expanduser()
        if not p.exists():
            return f"File not found: {p}"
        if not p.is_file():
            return "Can only checksum files, not directories."

        hash_func = getattr(hashlib, algorithm, None)
        if not hash_func:
            return f"Unknown algorithm: {algorithm}. Use: md5, sha1, sha256, sha512"

        h = hash_func()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)

        return f"{algorithm.upper()}: {h.hexdigest()}\nFile: {p}\nSize: {p.stat().st_size:,} bytes"

    def compare_directories(self, dir1: str, dir2: str) -> str:
        """Compare two directories and list differences."""
        p1, p2 = Path(dir1).expanduser(), Path(dir2).expanduser()

        if not p1.exists() or not p2.exists():
            return "One or both directories don't exist."

        files1 = {f.relative_to(p1): f for f in p1.rglob("*") if f.is_file()}
        files2 = {f.relative_to(p2): f for f in p2.rglob("*") if f.is_file()}

        only_in_1 = files1.keys() - files2.keys()
        only_in_2 = files2.keys() - files1.keys()
        common = files1.keys() & files2.keys()

        # Check for modified files
        modified = []
        for path in common:
            if files1[path].stat().st_size != files2[path].stat().st_size:
                modified.append(path)

        result = [f"Directory comparison:\n  {p1}\n  {p2}\n"]

        if only_in_1:
            result.append(f"Only in {p1.name} ({len(only_in_1)}):")
            for f in list(only_in_1)[:20]:
                result.append(f"  + {f}")

        if only_in_2:
            result.append(f"Only in {p2.name} ({len(only_in_2)}):")
            for f in list(only_in_2)[:20]:
                result.append(f"  + {f}")

        if modified:
            result.append(f"Modified ({len(modified)}):")
            for f in modified[:20]:
                result.append(f"  ~ {f}")

        if not only_in_1 and not only_in_2 and not modified:
            result.append("Directories are identical!")

        return "\n".join(result)

    def backup_operation(self, operation: str, **kwargs) -> str:
        """Unified backup interface."""
        ops = {
            "create": lambda: self.create_backup(kwargs.get("source", ""), kwargs.get("name", ""), kwargs.get("compress", True)),
            "list": lambda: self.list_backups(),
            "restore": lambda: self.restore_backup(int(kwargs.get("index", 1)), kwargs.get("dest", "")),
            "delete": lambda: self.delete_backup(int(kwargs.get("index", 1))),
            "cleanup": lambda: self.cleanup_old(int(kwargs.get("keep", 10))),
            "checksum": lambda: self.get_checksum(kwargs.get("path", ""), kwargs.get("algorithm", "sha256")),
            "compare": lambda: self.compare_directories(kwargs.get("dir1", ""), kwargs.get("dir2", "")),
        }
        handler = ops.get(operation)
        if handler:
            return handler()
        return f"Unknown backup operation: {operation}. Available: {', '.join(ops.keys())}"


backup_manager = BackupManager()
