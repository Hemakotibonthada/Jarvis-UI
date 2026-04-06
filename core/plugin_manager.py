"""
J.A.R.V.I.S. Plugin Manager — Dynamic plugin loading and management.
Plugins are Python files in the plugins/ directory with a register() function.
"""

import os
import sys
import importlib
import importlib.util
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Any, Callable
from core.logger import get_logger
from core.event_system import event_bus, Events

log = get_logger("plugins")


@dataclass
class PluginInfo:
    """Metadata about a loaded plugin."""
    name: str
    version: str = "1.0.0"
    author: str = "Unknown"
    description: str = ""
    enabled: bool = True
    loaded_at: str = field(default_factory=lambda: datetime.now().isoformat())
    tools: list = field(default_factory=list)
    module: Any = None
    file_path: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "enabled": self.enabled,
            "loaded_at": self.loaded_at,
            "tools": self.tools,
            "file_path": self.file_path,
        }


class PluginManager:
    """
    Manages plugin loading, unloading, and lifecycle.
    
    Plugins are Python files with a register(manager) function.
    The register function receives the PluginManager and can:
    - Register new tools via manager.register_tool()
    - Subscribe to events via manager.event_bus
    - Access configuration via manager.config
    """

    def __init__(self, plugins_dir: str = None):
        import config
        self.config = config
        self.plugins_dir = Path(plugins_dir) if plugins_dir else config.BASE_DIR / "plugins"
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        self.plugins: dict[str, PluginInfo] = {}
        self.event_bus = event_bus
        self._tool_registry: dict[str, Callable] = {}
        self._tool_definitions: list[dict] = []

    def discover_plugins(self) -> list[str]:
        """Find all plugin files in the plugins directory."""
        plugin_files = []
        for f in self.plugins_dir.glob("*.py"):
            if f.name.startswith("_"):
                continue
            plugin_files.append(f.stem)
        return sorted(plugin_files)

    def load_plugin(self, plugin_name: str) -> str:
        """Load a single plugin by name."""
        plugin_file = self.plugins_dir / f"{plugin_name}.py"
        if not plugin_file.exists():
            return f"Plugin file not found: {plugin_file}"

        if plugin_name in self.plugins:
            return f"Plugin '{plugin_name}' is already loaded."

        try:
            # Load module dynamically
            spec = importlib.util.spec_from_file_location(
                f"jarvis_plugin_{plugin_name}", str(plugin_file)
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Get plugin metadata
            info = PluginInfo(
                name=plugin_name,
                version=getattr(module, "__version__", "1.0.0"),
                author=getattr(module, "__author__", "Unknown"),
                description=getattr(module, "__description__", ""),
                module=module,
                file_path=str(plugin_file),
            )

            # Call register function
            if hasattr(module, "register"):
                module.register(self)
            else:
                return f"Plugin '{plugin_name}' has no register() function."

            self.plugins[plugin_name] = info
            log.info(f"Loaded plugin: {plugin_name} v{info.version}")

            event_bus.emit_sync("plugin.loaded", {"name": plugin_name})
            return f"Plugin '{plugin_name}' loaded successfully."

        except Exception as e:
            log.error(f"Failed to load plugin '{plugin_name}': {e}")
            return f"Failed to load plugin '{plugin_name}': {e}"

    def unload_plugin(self, plugin_name: str) -> str:
        """Unload a plugin."""
        if plugin_name not in self.plugins:
            return f"Plugin '{plugin_name}' is not loaded."

        info = self.plugins[plugin_name]

        # Call cleanup if available
        if info.module and hasattr(info.module, "cleanup"):
            try:
                info.module.cleanup()
            except Exception:
                pass

        # Remove registered tools
        for tool_name in info.tools:
            self._tool_registry.pop(tool_name, None)
            self._tool_definitions = [
                t for t in self._tool_definitions
                if t["function"]["name"] != tool_name
            ]

        del self.plugins[plugin_name]
        log.info(f"Unloaded plugin: {plugin_name}")
        return f"Plugin '{plugin_name}' unloaded."

    def reload_plugin(self, plugin_name: str) -> str:
        """Reload a plugin."""
        self.unload_plugin(plugin_name)
        return self.load_plugin(plugin_name)

    def load_all(self) -> str:
        """Load all discovered plugins."""
        discovered = self.discover_plugins()
        if not discovered:
            return "No plugins found."

        results = []
        for name in discovered:
            result = self.load_plugin(name)
            results.append(f"  {name}: {result}")

        return f"Loaded {len(discovered)} plugins:\n" + "\n".join(results)

    def register_tool(self, name: str, handler: Callable, description: str = "",
                      parameters: dict = None, required: list = None,
                      plugin_name: str = ""):
        """Register a tool from a plugin."""
        self._tool_registry[name] = handler

        tool_def = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": parameters or {},
                    "required": required or [],
                },
            },
        }
        self._tool_definitions.append(tool_def)

        # Track which plugin owns this tool
        if plugin_name and plugin_name in self.plugins:
            self.plugins[plugin_name].tools.append(name)

    def get_tools(self) -> dict[str, Callable]:
        """Get all registered plugin tools."""
        return dict(self._tool_registry)

    def get_tool_definitions(self) -> list[dict]:
        """Get OpenAI-format tool definitions from plugins."""
        return list(self._tool_definitions)

    def list_plugins(self) -> str:
        """List all loaded plugins."""
        if not self.plugins:
            return "No plugins loaded."
        lines = []
        for name, info in self.plugins.items():
            status = "✓" if info.enabled else "✗"
            lines.append(
                f"  {status} {name} v{info.version} — {info.description} "
                f"({len(info.tools)} tools)"
            )
        return "Loaded plugins:\n" + "\n".join(lines)

    def get_plugin_info(self, plugin_name: str) -> str:
        """Get detailed info about a plugin."""
        info = self.plugins.get(plugin_name)
        if not info:
            return f"Plugin '{plugin_name}' not found."
        return (
            f"Plugin: {info.name}\n"
            f"Version: {info.version}\n"
            f"Author: {info.author}\n"
            f"Description: {info.description}\n"
            f"Enabled: {info.enabled}\n"
            f"Loaded: {info.loaded_at}\n"
            f"Tools: {', '.join(info.tools) if info.tools else 'none'}\n"
            f"File: {info.file_path}"
        )

    def enable_plugin(self, plugin_name: str) -> str:
        """Enable a disabled plugin."""
        if plugin_name not in self.plugins:
            return f"Plugin '{plugin_name}' not found."
        self.plugins[plugin_name].enabled = True
        return f"Plugin '{plugin_name}' enabled."

    def disable_plugin(self, plugin_name: str) -> str:
        """Disable a plugin (tools remain but are skipped)."""
        if plugin_name not in self.plugins:
            return f"Plugin '{plugin_name}' not found."
        self.plugins[plugin_name].enabled = False
        return f"Plugin '{plugin_name}' disabled."


# ─── Singleton ────────────────────────────────────────────────
plugin_manager = PluginManager()
