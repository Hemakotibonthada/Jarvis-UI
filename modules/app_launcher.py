"""
Application Launcher Module — Smart application launching with fuzzy matching,
custom shortcuts, launch groups, and usage analytics.
Extends basic system_control.open_application with advanced capabilities.
"""

import os
import json
import subprocess
import time
from pathlib import Path
from datetime import datetime
from collections import Counter
from core.logger import get_logger
import config

log = get_logger("launcher")

LAUNCHER_FILE = config.DATA_DIR / "app_launcher.json"


class AppShortcut:
    """A custom application shortcut."""
    def __init__(self, name: str, command: str, args: str = "",
                 working_dir: str = "", description: str = "",
                 category: str = "", hotkey: str = "", icon: str = ""):
        self.name = name
        self.command = command
        self.args = args
        self.working_dir = working_dir
        self.description = description
        self.category = category
        self.hotkey = hotkey
        self.icon = icon
        self.launch_count = 0
        self.last_launched = ""
        self.created_at = datetime.now().isoformat()

    def to_dict(self):
        return self.__dict__

    @staticmethod
    def from_dict(d) -> 'AppShortcut':
        s = AppShortcut(d.get("name", ""), d.get("command", ""))
        for k, v in d.items():
            if hasattr(s, k):
                setattr(s, k, v)
        return s


class AppLaunchGroup:
    """A group of apps to launch together."""
    def __init__(self, name: str, apps: list = None, description: str = "",
                 delay_between: float = 1.0):
        self.name = name
        self.apps = apps or []  # List of app names or commands
        self.description = description
        self.delay_between = delay_between
        self.launch_count = 0

    def to_dict(self):
        return self.__dict__

    @staticmethod
    def from_dict(d) -> 'AppLaunchGroup':
        g = AppLaunchGroup(d.get("name", ""))
        for k, v in d.items():
            if hasattr(g, k):
                setattr(g, k, v)
        return g


class SmartLauncher:
    """Advanced application launcher."""

    # Built-in Windows app mappings
    BUILTIN_APPS = {
        "notepad": "notepad.exe", "calculator": "calc.exe", "calc": "calc.exe",
        "paint": "mspaint.exe", "cmd": "cmd.exe", "terminal": "wt.exe",
        "powershell": "powershell.exe", "explorer": "explorer.exe",
        "file explorer": "explorer.exe", "task manager": "taskmgr.exe",
        "control panel": "control.exe", "settings": "ms-settings:",
        "chrome": "chrome.exe", "google chrome": "chrome.exe",
        "firefox": "firefox.exe", "edge": "msedge.exe",
        "microsoft edge": "msedge.exe", "vscode": "code",
        "vs code": "code", "visual studio code": "code",
        "spotify": "spotify.exe", "discord": "discord.exe",
        "slack": "slack.exe", "word": "winword.exe",
        "excel": "excel.exe", "powerpoint": "powerpnt.exe",
        "outlook": "outlook.exe", "teams": "ms-teams.exe",
        "obs": "obs64.exe", "vlc": "vlc.exe", "steam": "steam.exe",
        "snipping tool": "snippingtool.exe", "paint 3d": "ms-paint:",
        "photos": "ms-photos:", "weather": "msnweather:",
        "maps": "bingmaps:", "clock": "ms-clock:",
        "sticky notes": "ms-stickynotes:", "voice recorder": "ms-screenclip:",
        "device manager": "devmgmt.msc", "disk management": "diskmgmt.msc",
        "event viewer": "eventvwr.msc", "services": "services.msc",
        "registry editor": "regedit.exe", "resource monitor": "resmon.exe",
        "performance monitor": "perfmon.exe", "system information": "msinfo32.exe",
        "remote desktop": "mstsc.exe", "character map": "charmap.exe",
        "windows defender": "windowsdefender:",
        "windows update": "ms-settings:windowsupdate",
        "bluetooth settings": "ms-settings:bluetooth",
        "wifi settings": "ms-settings:network-wifi",
        "display settings": "ms-settings:display",
        "sound settings": "ms-settings:sound",
        "apps settings": "ms-settings:appsfeatures",
        "storage settings": "ms-settings:storagesense",
        "mouse settings": "ms-settings:mousetouchpad",
        "keyboard settings": "ms-settings:typing",
    }

    def __init__(self):
        self.shortcuts: dict[str, AppShortcut] = {}
        self.groups: dict[str, AppLaunchGroup] = {}
        self.launch_history: list[dict] = []
        self._load()

    def _load(self):
        if LAUNCHER_FILE.exists():
            try:
                data = json.loads(LAUNCHER_FILE.read_text(encoding="utf-8"))
                for name, sdata in data.get("shortcuts", {}).items():
                    self.shortcuts[name] = AppShortcut.from_dict(sdata)
                for name, gdata in data.get("groups", {}).items():
                    self.groups[name] = AppLaunchGroup.from_dict(gdata)
                self.launch_history = data.get("history", [])[-200:]
            except (json.JSONDecodeError, OSError):
                pass

    def _save(self):
        data = {
            "shortcuts": {n: s.to_dict() for n, s in self.shortcuts.items()},
            "groups": {n: g.to_dict() for n, g in self.groups.items()},
            "history": self.launch_history[-200:],
        }
        LAUNCHER_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def launch(self, app_name: str, args: str = "") -> str:
        """Smart launch — checks shortcuts, built-in, then direct."""
        key = app_name.lower().strip()

        # Check custom shortcuts first
        if key in self.shortcuts:
            shortcut = self.shortcuts[key]
            return self._execute_launch(shortcut.command, shortcut.args or args,
                                       shortcut.working_dir, shortcut.name)

        # Fuzzy match shortcuts
        for name, shortcut in self.shortcuts.items():
            if key in name.lower() or (shortcut.description and key in shortcut.description.lower()):
                return self._execute_launch(shortcut.command, shortcut.args or args,
                                           shortcut.working_dir, shortcut.name)

        # Check built-in apps
        executable = self.BUILTIN_APPS.get(key)
        if executable:
            return self._execute_launch(executable, args, "", app_name)

        # Fuzzy match built-in
        for builtin_name, exe in self.BUILTIN_APPS.items():
            if key in builtin_name:
                return self._execute_launch(exe, args, "", builtin_name)

        # Try direct launch
        return self._execute_launch(app_name, args, "", app_name)

    def _execute_launch(self, command: str, args: str = "",
                        working_dir: str = "", display_name: str = "") -> str:
        """Execute the launch command."""
        try:
            if command.startswith("ms-") or command.endswith(":"):
                os.startfile(command)
            elif args:
                subprocess.Popen(f"{command} {args}", shell=True,
                               cwd=working_dir or None)
            else:
                subprocess.Popen(command, shell=True,
                               cwd=working_dir or None)

            # Log
            self.launch_history.append({
                "app": display_name or command,
                "command": command,
                "time": datetime.now().isoformat(),
            })

            # Update shortcut stats
            key = display_name.lower()
            if key in self.shortcuts:
                self.shortcuts[key].launch_count += 1
                self.shortcuts[key].last_launched = datetime.now().isoformat()

            self._save()
            return f"Launched: {display_name or command}"
        except Exception as e:
            return f"Failed to launch {display_name or command}: {e}"

    def add_shortcut(self, name: str, command: str, args: str = "",
                     working_dir: str = "", description: str = "",
                     category: str = "") -> str:
        """Add a custom app shortcut."""
        shortcut = AppShortcut(name, command, args, working_dir, description, category)
        self.shortcuts[name.lower()] = shortcut
        self._save()
        return f"Shortcut '{name}' → {command} added."

    def remove_shortcut(self, name: str) -> str:
        """Remove a shortcut."""
        key = name.lower()
        if key not in self.shortcuts:
            return f"Shortcut '{name}' not found."
        del self.shortcuts[key]
        self._save()
        return f"Shortcut '{name}' removed."

    def list_shortcuts(self) -> str:
        """List custom shortcuts."""
        if not self.shortcuts:
            return "No custom shortcuts. Use add_shortcut to create one."
        lines = []
        for name, s in sorted(self.shortcuts.items()):
            lines.append(f"  {name}: {s.command} ({s.description or s.category or '-'}) — used {s.launch_count}x")
        return f"Custom Shortcuts ({len(self.shortcuts)}):\n" + "\n".join(lines)

    def list_builtin(self, search: str = "") -> str:
        """List built-in app mappings."""
        apps = self.BUILTIN_APPS
        if search:
            apps = {k: v for k, v in apps.items() if search.lower() in k}
        lines = [f"  {name}: {exe}" for name, exe in sorted(apps.items())]
        return f"Built-in Apps ({len(apps)}):\n" + "\n".join(lines[:40])

    # ─── Launch Groups ────────────────────────────────────────
    def create_group(self, name: str, apps: list, description: str = "",
                     delay: float = 1.0) -> str:
        """Create a launch group."""
        self.groups[name] = AppLaunchGroup(name, apps, description, delay)
        self._save()
        return f"Launch group '{name}' created with {len(apps)} apps."

    def launch_group(self, name: str) -> str:
        """Launch all apps in a group."""
        group = self.groups.get(name)
        if not group:
            return f"Group '{name}' not found."

        results = []
        for app in group.apps:
            result = self.launch(app)
            results.append(f"  {app}: {result}")
            if group.delay_between > 0:
                time.sleep(group.delay_between)

        group.launch_count += 1
        self._save()
        return f"Launched group '{name}':\n" + "\n".join(results)

    def list_groups(self) -> str:
        """List launch groups."""
        if not self.groups:
            return "No launch groups."
        lines = [f"  {name}: {len(g.apps)} apps — {g.description or '(no description)'} (launched {g.launch_count}x)"
                 for name, g in self.groups.items()]
        return f"Launch Groups ({len(self.groups)}):\n" + "\n".join(lines)

    def delete_group(self, name: str) -> str:
        """Delete a launch group."""
        if name not in self.groups:
            return f"Group '{name}' not found."
        del self.groups[name]
        self._save()
        return f"Group '{name}' deleted."

    # ─── Analytics ────────────────────────────────────────────
    def most_launched(self, count: int = 10) -> str:
        """Get most frequently launched apps."""
        app_counts = Counter(h["app"] for h in self.launch_history)
        top = app_counts.most_common(count)
        if not top:
            return "No launch history."
        lines = [f"  {i+1}. {app}: {cnt} launches" for i, (app, cnt) in enumerate(top)]
        return f"Most Launched Apps:\n" + "\n".join(lines)

    def recent_launches(self, count: int = 15) -> str:
        """Get recent launch history."""
        if not self.launch_history:
            return "No launch history."
        recent = self.launch_history[-count:]
        lines = [f"  [{h['time'][11:19]}] {h['app']}" for h in reversed(recent)]
        return f"Recent Launches ({len(recent)}):\n" + "\n".join(lines)

    # ─── Predefined Groups ───────────────────────────────────
    def create_preset_group(self, preset: str) -> str:
        """Create a launch group from preset."""
        presets = {
            "development": {
                "apps": ["vscode", "terminal", "chrome"],
                "description": "Development environment",
            },
            "communication": {
                "apps": ["slack", "discord", "outlook", "teams"],
                "description": "Communication apps",
            },
            "productivity": {
                "apps": ["chrome", "outlook", "word", "excel"],
                "description": "Office productivity suite",
            },
            "media": {
                "apps": ["spotify", "vlc"],
                "description": "Media and entertainment",
            },
            "creative": {
                "apps": ["vscode", "paint", "photos"],
                "description": "Creative and design tools",
            },
        }
        p = presets.get(preset)
        if not p:
            return f"Unknown preset. Available: {', '.join(presets.keys())}"
        return self.create_group(preset, p["apps"], p["description"])

    # ─── Unified Interface ────────────────────────────────
    def launcher_operation(self, operation: str, **kwargs) -> str:
        """Unified launcher interface."""
        name = kwargs.get("name", kwargs.get("app", ""))

        ops = {
            "launch": lambda: self.launch(name, kwargs.get("args", "")),
            "add_shortcut": lambda: self.add_shortcut(name, kwargs.get("command", ""), kwargs.get("args", ""), kwargs.get("working_dir", ""), kwargs.get("description", ""), kwargs.get("category", "")),
            "remove_shortcut": lambda: self.remove_shortcut(name),
            "shortcuts": lambda: self.list_shortcuts(),
            "builtin": lambda: self.list_builtin(kwargs.get("search", "")),
            "create_group": lambda: self.create_group(name, kwargs.get("apps", []), kwargs.get("description", "")),
            "launch_group": lambda: self.launch_group(name),
            "groups": lambda: self.list_groups(),
            "delete_group": lambda: self.delete_group(name),
            "preset": lambda: self.create_preset_group(kwargs.get("preset", "")),
            "most_launched": lambda: self.most_launched(int(kwargs.get("count", 10))),
            "recent": lambda: self.recent_launches(int(kwargs.get("count", 15))),
        }
        handler = ops.get(operation)
        if handler:
            return handler()
        return f"Unknown launcher operation: {operation}. Available: {', '.join(ops.keys())}"


smart_launcher = SmartLauncher()
