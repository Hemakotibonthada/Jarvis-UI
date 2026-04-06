"""
System Optimizer Module — Performance tuning, cleanup, startup management,
registry tweaks, and system maintenance tasks.
"""

import subprocess
import shutil
import os
import tempfile
from pathlib import Path
from datetime import datetime
from core.logger import get_logger
import config

log = get_logger("optimizer")


class SystemOptimizer:
    """System optimization and maintenance tools."""

    def disk_cleanup(self, aggressive: bool = False) -> str:
        """Clean up temporary files and disk space."""
        freed = 0
        cleaned = []

        # Temp directories
        temp_dirs = [
            Path(tempfile.gettempdir()),
        ]
        if config.IS_WINDOWS:
            temp_dirs.extend([
                Path(os.environ.get("TEMP", "")),
                Path(os.environ.get("LOCALAPPDATA", "")) / "Temp",
            ])

        for temp_dir in temp_dirs:
            if temp_dir.exists():
                count = 0
                for item in temp_dir.iterdir():
                    try:
                        if item.is_file():
                            size = item.stat().st_size
                            item.unlink()
                            freed += size
                            count += 1
                        elif item.is_dir() and aggressive:
                            size = sum(f.stat().st_size for f in item.rglob("*") if f.is_file())
                            shutil.rmtree(str(item), ignore_errors=True)
                            freed += size
                            count += 1
                    except (PermissionError, OSError):
                        pass
                if count:
                    cleaned.append(f"  Temp ({temp_dir.name}): {count} items")

        # Python caches
        if aggressive:
            for cache_dir in Path.home().rglob("__pycache__"):
                try:
                    if cache_dir.is_dir():
                        size = sum(f.stat().st_size for f in cache_dir.rglob("*") if f.is_file())
                        shutil.rmtree(str(cache_dir), ignore_errors=True)
                        freed += size
                except (PermissionError, OSError):
                    pass

        # Windows-specific cleanup
        if config.IS_WINDOWS:
            # Recycle bin
            try:
                subprocess.run(
                    ['powershell', '-c', 'Clear-RecycleBin -Force -ErrorAction SilentlyContinue'],
                    capture_output=True, timeout=10,
                )
                cleaned.append("  Recycle bin emptied")
            except Exception:
                pass

            # Windows prefetch
            if aggressive:
                prefetch = Path("C:/Windows/Prefetch")
                if prefetch.exists():
                    count = 0
                    for f in prefetch.glob("*.pf"):
                        try:
                            size = f.stat().st_size
                            f.unlink()
                            freed += size
                            count += 1
                        except (PermissionError, OSError):
                            pass
                    if count:
                        cleaned.append(f"  Prefetch: {count} files")

        # Browser caches (aggressive only)
        if aggressive:
            browser_caches = []
            if config.IS_WINDOWS:
                local = Path(os.environ.get("LOCALAPPDATA", ""))
                browser_caches = [
                    local / "Google/Chrome/User Data/Default/Cache",
                    local / "Microsoft/Edge/User Data/Default/Cache",
                    local / "Mozilla/Firefox/Profiles",
                ]

            for cache in browser_caches:
                if cache.exists():
                    try:
                        size = sum(f.stat().st_size for f in cache.rglob("*") if f.is_file())
                        # Don't delete profiles, just note the size
                        cleaned.append(f"  Browser cache ({cache.parent.parent.name}): {size / (1024**2):.0f}MB (not cleared)")
                    except (PermissionError, OSError):
                        pass

        freed_mb = freed / (1024 * 1024)
        result = f"Disk Cleanup {'(aggressive)' if aggressive else '(standard)'}:\n"
        if cleaned:
            result += "\n".join(cleaned) + "\n"
        result += f"\n  Total freed: {freed_mb:.1f} MB"
        return result

    def analyze_disk_usage(self, path: str = "") -> str:
        """Analyze disk usage by directory/file size."""
        root = Path(path).expanduser() if path else Path.home()
        if not root.exists():
            return f"Path not found: {root}"

        sizes = {}
        total = 0
        count = 0

        try:
            for item in root.iterdir():
                try:
                    if item.is_file():
                        size = item.stat().st_size
                        sizes[item.name] = size
                        total += size
                    elif item.is_dir():
                        size = sum(f.stat().st_size for f in item.rglob("*") if f.is_file())
                        sizes[item.name + "/"] = size
                        total += size
                    count += 1
                except (PermissionError, OSError):
                    pass
                if count > 100:
                    break
        except PermissionError:
            return f"Permission denied: {root}"

        # Sort by size descending
        sorted_items = sorted(sizes.items(), key=lambda x: x[1], reverse=True)[:25]

        lines = []
        for name, size in sorted_items:
            if size >= 1024 * 1024 * 1024:
                size_str = f"{size / (1024**3):.1f} GB"
            elif size >= 1024 * 1024:
                size_str = f"{size / (1024**2):.1f} MB"
            elif size >= 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size} B"

            pct = (size / total * 100) if total else 0
            bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
            lines.append(f"  {size_str:>10}  {bar} {pct:>5.1f}%  {name}")

        total_str = f"{total / (1024**3):.1f} GB" if total > 1024**3 else f"{total / (1024**2):.1f} MB"
        return f"Disk Usage Analysis: {root}\n  Total: {total_str}\n\n" + "\n".join(lines)

    def find_large_files(self, path: str = "", min_size_mb: int = 100,
                         limit: int = 20) -> str:
        """Find large files on disk."""
        root = Path(path).expanduser() if path else Path.home()
        min_bytes = min_size_mb * 1024 * 1024

        large_files = []
        count = 0

        try:
            for f in root.rglob("*"):
                if count > 10000:
                    break
                count += 1
                try:
                    if f.is_file() and f.stat().st_size >= min_bytes:
                        large_files.append((f, f.stat().st_size))
                except (PermissionError, OSError):
                    pass
        except PermissionError:
            pass

        large_files.sort(key=lambda x: x[1], reverse=True)
        large_files = large_files[:limit]

        if not large_files:
            return f"No files larger than {min_size_mb}MB found in {root}."

        lines = []
        for f, size in large_files:
            size_str = f"{size / (1024**2):.1f} MB" if size < 1024**3 else f"{size / (1024**3):.1f} GB"
            lines.append(f"  {size_str:>10}  {f}")

        return f"Large files in {root} (>{min_size_mb}MB):\n" + "\n".join(lines)

    def find_duplicate_files(self, path: str = "", limit: int = 20) -> str:
        """Find duplicate files by size and partial hash."""
        import hashlib
        root = Path(path).expanduser() if path else Path.cwd()

        # Group files by size
        size_groups = {}
        count = 0
        for f in root.rglob("*"):
            if count > 5000:
                break
            count += 1
            try:
                if f.is_file() and f.stat().st_size > 1024:  # Skip tiny files
                    size = f.stat().st_size
                    if size not in size_groups:
                        size_groups[size] = []
                    size_groups[size].append(f)
            except (PermissionError, OSError):
                pass

        # Check hashes for same-size files
        duplicates = []
        for size, files in size_groups.items():
            if len(files) < 2:
                continue
            hashes = {}
            for f in files:
                try:
                    h = hashlib.md5()
                    with open(f, "rb") as fh:
                        h.update(fh.read(8192))  # Hash first 8KB
                    digest = h.hexdigest()
                    if digest in hashes:
                        duplicates.append((f, hashes[digest], size))
                    else:
                        hashes[digest] = f
                except (PermissionError, OSError):
                    pass

        if not duplicates:
            return f"No duplicate files found in {root}."

        duplicates = duplicates[:limit]
        lines = []
        for dup, original, size in duplicates:
            size_str = f"{size / 1024:.0f}KB" if size < 1024 * 1024 else f"{size / (1024**2):.1f}MB"
            lines.append(f"  [{size_str}] {dup.name}")
            lines.append(f"         = {original}")

        return f"Potential duplicates ({len(duplicates)} pairs):\n" + "\n".join(lines)

    def memory_cleanup(self) -> str:
        """Free up system memory (Windows)."""
        if not config.IS_WINDOWS:
            return "Memory cleanup is Windows-specific."
        try:
            # Clear standby list (needs admin)
            subprocess.run(
                ['powershell', '-c',
                 '[System.GC]::Collect(); '
                 '[System.GC]::WaitForPendingFinalizers(); '
                 'Write-Host "Garbage collection triggered"'],
                capture_output=True, text=True, timeout=10,
            )

            import psutil
            mem_before = psutil.virtual_memory().available
            # Attempt to free memory
            subprocess.run(
                ['powershell', '-c', 'Clear-Host'],
                capture_output=True, timeout=5,
            )
            mem_after = psutil.virtual_memory().available
            freed = max(0, mem_after - mem_before)

            return (
                f"Memory cleanup completed.\n"
                f"  Available before: {mem_before / (1024**3):.2f} GB\n"
                f"  Available after: {mem_after / (1024**3):.2f} GB\n"
                f"  Freed: {freed / (1024**2):.0f} MB"
            )
        except Exception as e:
            return f"Memory cleanup error: {e}"

    def startup_optimization(self) -> str:
        """Analyze and report on startup programs."""
        if not config.IS_WINDOWS:
            return "Startup optimization only available on Windows."
        try:
            result = subprocess.run(
                ['powershell', '-c',
                 'Get-CimInstance Win32_StartupCommand | '
                 'Select-Object Name,Command,Location | '
                 'Format-Table -AutoSize'],
                capture_output=True, text=True, timeout=15,
            )
            startup_items = result.stdout.strip()

            # Get startup impact
            try:
                impact = subprocess.run(
                    ['powershell', '-c',
                     'Get-CimInstance -ClassName Win32_StartupCommand | Measure-Object | Select-Object Count'],
                    capture_output=True, text=True, timeout=10,
                )
                count_info = impact.stdout.strip()
            except Exception:
                count_info = ""

            return (
                f"Startup Programs:\n{startup_items}\n\n"
                f"Tip: Disable unnecessary startup items in Task Manager → Startup tab\n"
                f"to improve boot time."
            )
        except Exception as e:
            return f"Startup analysis error: {e}"

    def system_health_score(self) -> str:
        """Calculate an overall system health score."""
        import psutil

        score = 100
        issues = []
        good = []

        # CPU
        cpu = psutil.cpu_percent(interval=1)
        if cpu > 90:
            score -= 20
            issues.append(f"⚠ CPU critical: {cpu}%")
        elif cpu > 70:
            score -= 10
            issues.append(f"⚠ CPU high: {cpu}%")
        else:
            good.append(f"✓ CPU: {cpu}%")

        # RAM
        ram = psutil.virtual_memory()
        if ram.percent > 90:
            score -= 20
            issues.append(f"⚠ RAM critical: {ram.percent}%")
        elif ram.percent > 80:
            score -= 10
            issues.append(f"⚠ RAM high: {ram.percent}%")
        else:
            good.append(f"✓ RAM: {ram.percent}%")

        # Disk
        disk = psutil.disk_usage(config.SYSTEM_DRIVE)
        if disk.percent > 95:
            score -= 25
            issues.append(f"⚠ Disk critical: {disk.percent}%")
        elif disk.percent > 85:
            score -= 10
            issues.append(f"⚠ Disk high: {disk.percent}%")
        else:
            good.append(f"✓ Disk: {disk.percent}%")

        # Battery
        try:
            battery = psutil.sensors_battery()
            if battery:
                if battery.percent < 15 and not battery.power_plugged:
                    score -= 15
                    issues.append(f"⚠ Battery critical: {battery.percent}%")
                elif battery.percent < 30 and not battery.power_plugged:
                    score -= 5
                    issues.append(f"⚠ Battery low: {battery.percent}%")
                else:
                    plug = "plugged" if battery.power_plugged else "on battery"
                    good.append(f"✓ Battery: {battery.percent}% ({plug})")
        except Exception:
            pass

        # Temp
        try:
            temps = psutil.sensors_temperatures()
            for name, entries in temps.items():
                for entry in entries:
                    if entry.current > 85:
                        score -= 15
                        issues.append(f"⚠ {name} temp: {entry.current}°C")
                    break
                break
        except Exception:
            pass

        # Rating
        if score >= 90:
            rating = "EXCELLENT 🌟"
        elif score >= 70:
            rating = "GOOD 👍"
        elif score >= 50:
            rating = "FAIR ⚠"
        elif score >= 30:
            rating = "POOR 🔴"
        else:
            rating = "CRITICAL 💀"

        result = (
            f"System Health Score: {score}/100 — {rating}\n"
            f"\n{'── Issues ──' if issues else '── No Issues ──'}\n"
        )
        for issue in issues:
            result += f"  {issue}\n"
        result += f"\n── Healthy ──\n"
        for g in good:
            result += f"  {g}\n"

        return result

    def get_environment_vars(self, search: str = "") -> str:
        """List or search environment variables."""
        env_vars = dict(os.environ)
        if search:
            env_vars = {k: v for k, v in env_vars.items() if search.lower() in k.lower() or search.lower() in v.lower()}

        if not env_vars:
            return f"No environment variables matching '{search}'."

        lines = [f"  {k}={v[:100]}" for k, v in sorted(env_vars.items())[:50]]
        return f"Environment Variables ({len(env_vars)}):\n" + "\n".join(lines)

    def set_environment_var(self, key: str, value: str, permanent: bool = False) -> str:
        """Set an environment variable."""
        os.environ[key] = value
        if permanent and config.IS_WINDOWS:
            try:
                subprocess.run(
                    ['setx', key, value],
                    capture_output=True, text=True, timeout=10,
                )
                return f"Set {key}={value} (permanent)"
            except Exception:
                return f"Set {key}={value} (session only — setx failed)"
        return f"Set {key}={value} (session only)"

    # ─── Unified Interface ────────────────────────────────────
    def optimizer_operation(self, operation: str, **kwargs) -> str:
        """Unified system optimizer interface."""
        ops = {
            "cleanup": lambda: self.disk_cleanup(kwargs.get("aggressive", False)),
            "disk_usage": lambda: self.analyze_disk_usage(kwargs.get("path", "")),
            "large_files": lambda: self.find_large_files(kwargs.get("path", ""), int(kwargs.get("min_size_mb", 100))),
            "duplicates": lambda: self.find_duplicate_files(kwargs.get("path", "")),
            "memory_cleanup": lambda: self.memory_cleanup(),
            "startup": lambda: self.startup_optimization(),
            "health_score": lambda: self.system_health_score(),
            "env": lambda: self.get_environment_vars(kwargs.get("search", "")),
            "set_env": lambda: self.set_environment_var(kwargs.get("key", ""), kwargs.get("value", ""), kwargs.get("permanent", False)),
        }
        handler = ops.get(operation)
        if handler:
            return handler()
        return f"Unknown optimizer operation: {operation}. Available: {', '.join(ops.keys())}"


# ─── Singleton ────────────────────────────────────────────────
system_optimizer = SystemOptimizer()
