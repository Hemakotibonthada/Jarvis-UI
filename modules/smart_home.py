"""
Smart Home Module — Integration with Home Assistant, smart devices, and IR control.
Supports Philips Hue, smart plugs, and generic HTTP-based smart home devices.
"""

import asyncio
import json
import aiohttp
from datetime import datetime
from typing import Optional
from core.logger import get_logger

log = get_logger("smart_home")


# ─── Home Assistant Integration ──────────────────────────────
class HomeAssistantClient:
    """Client for Home Assistant REST API."""

    def __init__(self, url: str = "", token: str = ""):
        self.base_url = url.rstrip("/")
        self.token = token
        self._connected = False

    @property
    def headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    async def connect(self, url: str = "", token: str = "") -> str:
        """Connect to Home Assistant instance."""
        if url:
            self.base_url = url.rstrip("/")
        if token:
            self.token = token

        if not self.base_url or not self.token:
            return "Home Assistant URL and token are required. Set HA_URL and HA_TOKEN env vars."

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/",
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self._connected = True
                        return f"Connected to Home Assistant: {data.get('message', 'OK')}"
                    elif resp.status == 401:
                        return "Authentication failed. Check your Home Assistant token."
                    else:
                        return f"Connection failed with status {resp.status}"
        except aiohttp.ClientError as e:
            return f"Connection error: {e}"

    async def get_states(self) -> str:
        """Get all entity states."""
        if not self._connected:
            return "Not connected to Home Assistant."
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/states",
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        states = await resp.json()
                        lines = []
                        for entity in states[:50]:
                            eid = entity.get("entity_id", "")
                            state = entity.get("state", "")
                            name = entity.get("attributes", {}).get("friendly_name", eid)
                            lines.append(f"  {name}: {state}")
                        return f"Home Assistant entities ({len(states)} total):\n" + "\n".join(lines)
                    return f"Failed to get states: {resp.status}"
        except Exception as e:
            return f"Error: {e}"

    async def get_entity_state(self, entity_id: str) -> str:
        """Get state of a specific entity."""
        if not self._connected:
            return "Not connected to Home Assistant."
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/states/{entity_id}",
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        name = data.get("attributes", {}).get("friendly_name", entity_id)
                        state = data.get("state", "unknown")
                        attrs = data.get("attributes", {})
                        attr_lines = [f"  {k}: {v}" for k, v in list(attrs.items())[:10]]
                        return f"{name}: {state}\nAttributes:\n" + "\n".join(attr_lines)
                    elif resp.status == 404:
                        return f"Entity '{entity_id}' not found."
                    return f"Error: {resp.status}"
        except Exception as e:
            return f"Error: {e}"

    async def call_service(self, domain: str, service: str, entity_id: str = "",
                           data: dict = None) -> str:
        """Call a Home Assistant service."""
        if not self._connected:
            return "Not connected to Home Assistant."
        try:
            payload = data or {}
            if entity_id:
                payload["entity_id"] = entity_id

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/services/{domain}/{service}",
                    headers=self.headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        return f"Service {domain}.{service} called successfully for {entity_id or 'all'}."
                    return f"Service call failed: {resp.status}"
        except Exception as e:
            return f"Service error: {e}"

    async def turn_on(self, entity_id: str) -> str:
        """Turn on a device."""
        domain = entity_id.split(".")[0] if "." in entity_id else "homeassistant"
        return await self.call_service(domain, "turn_on", entity_id)

    async def turn_off(self, entity_id: str) -> str:
        """Turn off a device."""
        domain = entity_id.split(".")[0] if "." in entity_id else "homeassistant"
        return await self.call_service(domain, "turn_off", entity_id)

    async def toggle(self, entity_id: str) -> str:
        """Toggle a device."""
        domain = entity_id.split(".")[0] if "." in entity_id else "homeassistant"
        return await self.call_service(domain, "toggle", entity_id)

    async def set_light(self, entity_id: str, brightness: int = 255,
                        color: str = "", temperature: int = 0) -> str:
        """Set light attributes."""
        data = {}
        if brightness is not None:
            data["brightness"] = max(0, min(255, brightness))
        if color:
            # Parse color string like "red", "blue", or "#FF0000"
            color_map = {
                "red": [255, 0, 0], "green": [0, 255, 0], "blue": [0, 0, 255],
                "white": [255, 255, 255], "yellow": [255, 255, 0],
                "purple": [128, 0, 128], "orange": [255, 165, 0],
                "pink": [255, 192, 203], "cyan": [0, 255, 255],
                "warm": None, "cool": None,
            }
            rgb = color_map.get(color.lower())
            if rgb:
                data["rgb_color"] = rgb
        if temperature:
            data["color_temp"] = temperature

        return await self.call_service("light", "turn_on", entity_id, data)

    async def set_thermostat(self, entity_id: str, temperature: float,
                              hvac_mode: str = "") -> str:
        """Set thermostat temperature and mode."""
        data = {"temperature": temperature}
        if hvac_mode:
            data["hvac_mode"] = hvac_mode
        return await self.call_service("climate", "set_temperature", entity_id, data)

    async def lock(self, entity_id: str) -> str:
        """Lock a smart lock."""
        return await self.call_service("lock", "lock", entity_id)

    async def unlock(self, entity_id: str) -> str:
        """Unlock a smart lock."""
        return await self.call_service("lock", "unlock", entity_id)

    async def media_play(self, entity_id: str) -> str:
        """Play media on a media player."""
        return await self.call_service("media_player", "media_play", entity_id)

    async def media_pause(self, entity_id: str) -> str:
        """Pause media on a media player."""
        return await self.call_service("media_player", "media_pause", entity_id)

    async def get_history(self, entity_id: str, hours: int = 24) -> str:
        """Get entity history."""
        if not self._connected:
            return "Not connected to Home Assistant."
        try:
            from datetime import timedelta
            start = (datetime.now() - timedelta(hours=hours)).isoformat()
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/history/period/{start}?filter_entity_id={entity_id}",
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if not data or not data[0]:
                            return f"No history for {entity_id}"
                        entries = data[0][-20:]
                        lines = [
                            f"  {e.get('last_changed', '')[:19]}: {e.get('state', '')}"
                            for e in entries
                        ]
                        return f"History for {entity_id} (last {hours}h):\n" + "\n".join(lines)
                    return f"History error: {resp.status}"
        except Exception as e:
            return f"History error: {e}"

    async def find_entities(self, search: str) -> str:
        """Search for entities by name or ID."""
        if not self._connected:
            return "Not connected to Home Assistant."
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/states",
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        states = await resp.json()
                        search_lower = search.lower()
                        matches = []
                        for entity in states:
                            eid = entity.get("entity_id", "")
                            name = entity.get("attributes", {}).get("friendly_name", "")
                            if search_lower in eid.lower() or search_lower in name.lower():
                                matches.append(f"  {eid}: {name} = {entity.get('state', '?')}")
                        if not matches:
                            return f"No entities matching '{search}'."
                        return f"Found {len(matches)} entities:\n" + "\n".join(matches[:30])
                    return f"Search error: {resp.status}"
        except Exception as e:
            return f"Search error: {e}"


# ─── Generic Device Control ──────────────────────────────────
class SmartDevice:
    """Represents a generic smart device controllable via HTTP."""

    def __init__(self, name: str, ip: str, device_type: str = "switch"):
        self.name = name
        self.ip = ip
        self.device_type = device_type
        self.state = "unknown"
        self.last_updated = None

    async def send_command(self, endpoint: str, data: dict = None) -> str:
        """Send HTTP command to device."""
        try:
            url = f"http://{self.ip}/{endpoint}"
            async with aiohttp.ClientSession() as session:
                if data:
                    async with session.post(url, json=data, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        result = await resp.text()
                else:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        result = await resp.text()
                self.last_updated = datetime.now().isoformat()
                return result
        except Exception as e:
            return f"Device {self.name} error: {e}"


class SmartHomeManager:
    """Manages all smart home integrations."""

    def __init__(self):
        self.ha_client = HomeAssistantClient()
        self.devices: dict[str, SmartDevice] = {}
        self.scenes: dict[str, list[dict]] = {}

    def add_device(self, name: str, ip: str, device_type: str = "switch") -> str:
        """Register a smart device."""
        self.devices[name] = SmartDevice(name, ip, device_type)
        return f"Device '{name}' registered at {ip}."

    def remove_device(self, name: str) -> str:
        """Remove a registered device."""
        if name in self.devices:
            del self.devices[name]
            return f"Device '{name}' removed."
        return f"Device '{name}' not found."

    def list_devices(self) -> str:
        """List registered devices."""
        if not self.devices:
            return "No smart devices registered."
        lines = [f"  {d.name}: {d.ip} ({d.device_type}) — {d.state}" for d in self.devices.values()]
        return "Smart devices:\n" + "\n".join(lines)

    def create_scene(self, scene_name: str, actions: list[dict]) -> str:
        """Create a scene (group of device actions)."""
        self.scenes[scene_name] = actions
        return f"Scene '{scene_name}' created with {len(actions)} actions."

    async def activate_scene(self, scene_name: str) -> str:
        """Activate a scene."""
        actions = self.scenes.get(scene_name)
        if not actions:
            return f"Scene '{scene_name}' not found."

        results = []
        for action in actions:
            entity = action.get("entity_id", "")
            service = action.get("service", "turn_on")
            domain = entity.split(".")[0] if "." in entity else "homeassistant"
            result = await self.ha_client.call_service(domain, service, entity, action.get("data"))
            results.append(f"  {entity}: {result}")

        return f"Scene '{scene_name}' activated:\n" + "\n".join(results)

    def list_scenes(self) -> str:
        """List available scenes."""
        if not self.scenes:
            return "No scenes configured."
        lines = [f"  {name}: {len(actions)} actions" for name, actions in self.scenes.items()]
        return "Scenes:\n" + "\n".join(lines)

    # ─── High-level Functions ─────────────────────────────────
    async def smart_home_control(self, action: str, device: str = "",
                                  value: str = "", **kwargs) -> str:
        """Unified smart home control interface."""
        if action == "status":
            return await self.ha_client.get_states()
        elif action == "turn_on":
            return await self.ha_client.turn_on(device)
        elif action == "turn_off":
            return await self.ha_client.turn_off(device)
        elif action == "toggle":
            return await self.ha_client.toggle(device)
        elif action == "set_light":
            brightness = int(kwargs.get("brightness", 255))
            color = kwargs.get("color", "")
            return await self.ha_client.set_light(device, brightness, color)
        elif action == "thermostat":
            temp = float(value) if value else 22.0
            return await self.ha_client.set_thermostat(device, temp)
        elif action == "lock":
            return await self.ha_client.lock(device)
        elif action == "unlock":
            return await self.ha_client.unlock(device)
        elif action == "find":
            return await self.ha_client.find_entities(device)
        elif action == "scene":
            return await self.activate_scene(device)
        elif action == "devices":
            return self.list_devices()
        elif action == "history":
            return await self.ha_client.get_history(device)

        return (
            f"Unknown smart home action: {action}. "
            f"Available: status, turn_on, turn_off, toggle, set_light, thermostat, "
            f"lock, unlock, find, scene, devices, history"
        )


# ─── Singleton ────────────────────────────────────────────────
smart_home = SmartHomeManager()
