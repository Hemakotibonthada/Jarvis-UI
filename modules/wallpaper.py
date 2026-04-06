"""
Wallpaper & Theme Module — Change desktop wallpaper, system theme settings.
"""

import os
import subprocess
import ctypes
import asyncio
import aiohttp
from pathlib import Path
from datetime import datetime
from core.logger import get_logger
import config

log = get_logger("wallpaper")


def set_wallpaper(image_path: str) -> str:
    """Set the desktop wallpaper."""
    p = Path(image_path).expanduser()
    if not p.exists():
        return f"Image not found: {p}"

    try:
        if config.IS_WINDOWS:
            # Windows API
            SPI_SETDESKWALLPAPER = 0x0014
            SPIF_UPDATEINIFILE = 0x01
            SPIF_SENDWININICHANGE = 0x02
            ctypes.windll.user32.SystemParametersInfoW(
                SPI_SETDESKWALLPAPER, 0, str(p.resolve()),
                SPIF_UPDATEINIFILE | SPIF_SENDWININICHANGE,
            )
            return f"Wallpaper set to: {p}"
        elif config.IS_LINUX:
            # GNOME
            subprocess.run(
                ["gsettings", "set", "org.gnome.desktop.background", "picture-uri", f"file://{p.resolve()}"],
                capture_output=True,
            )
            return f"Wallpaper set to: {p}"
        elif config.IS_MAC:
            subprocess.run(
                ["osascript", "-e", f'tell application "Finder" to set desktop picture to POSIX file "{p.resolve()}"'],
                capture_output=True,
            )
            return f"Wallpaper set to: {p}"
        return "Unsupported platform."
    except Exception as e:
        return f"Failed to set wallpaper: {e}"


def get_current_wallpaper() -> str:
    """Get the current wallpaper path."""
    try:
        if config.IS_WINDOWS:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop")
            wallpaper_path, _ = winreg.QueryValueEx(key, "Wallpaper")
            winreg.CloseKey(key)
            return f"Current wallpaper: {wallpaper_path}"
        elif config.IS_LINUX:
            result = subprocess.run(
                ["gsettings", "get", "org.gnome.desktop.background", "picture-uri"],
                capture_output=True, text=True,
            )
            return f"Current wallpaper: {result.stdout.strip()}"
        return "Unsupported platform."
    except Exception as e:
        return f"Could not get wallpaper: {e}"


async def download_wallpaper(query: str = "nature", resolution: str = "1920x1080") -> str:
    """Download a wallpaper from Unsplash and optionally set it."""
    try:
        url = f"https://source.unsplash.com/{resolution}/?{query}"
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = config.GENERATED_DIR / f"wallpaper_{ts}.jpg"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    save_path.write_bytes(await resp.read())
                    return f"Wallpaper downloaded: {save_path}"
                return f"Download failed: status {resp.status}"
    except Exception as e:
        return f"Wallpaper download error: {e}"


async def download_and_set_wallpaper(query: str = "nature") -> str:
    """Download a wallpaper and set it as desktop background."""
    result = await download_wallpaper(query)
    if result.startswith("Wallpaper downloaded:"):
        path = result.split(": ", 1)[1]
        set_result = set_wallpaper(path)
        return f"{result}\n{set_result}"
    return result


def set_dark_mode(enable: bool = True) -> str:
    """Toggle dark/light mode (Windows 10+)."""
    if not config.IS_WINDOWS:
        return "Dark mode toggle only supported on Windows."
    try:
        import winreg
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        value = 0 if enable else 1
        winreg.SetValueEx(key, "AppsUseLightTheme", 0, winreg.REG_DWORD, value)
        winreg.SetValueEx(key, "SystemUsesLightTheme", 0, winreg.REG_DWORD, value)
        winreg.CloseKey(key)
        return f"{'Dark' if enable else 'Light'} mode enabled."
    except Exception as e:
        return f"Failed to set theme: {e}"


def set_accent_color(color_hex: str) -> str:
    """Set Windows accent color."""
    if not config.IS_WINDOWS:
        return "Accent color only supported on Windows."
    try:
        color_hex = color_hex.lstrip("#")
        if len(color_hex) != 6:
            return "Invalid hex color. Use format: #FF5500"

        r, g, b = int(color_hex[:2], 16), int(color_hex[2:4], 16), int(color_hex[4:6], 16)
        color_value = (0xFF << 24) | (b << 16) | (g << 8) | r

        import winreg
        key_path = r"SOFTWARE\Microsoft\Windows\DWM"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "AccentColor", 0, winreg.REG_DWORD, color_value)
        winreg.CloseKey(key)
        return f"Accent color set to #{color_hex}."
    except Exception as e:
        return f"Failed to set accent color: {e}"


def wallpaper_control(action: str, **kwargs) -> str:
    """Unified wallpaper/theme control."""
    if action == "set":
        return set_wallpaper(kwargs.get("path", ""))
    elif action == "current":
        return get_current_wallpaper()
    elif action == "dark_mode":
        return set_dark_mode(kwargs.get("enable", True))
    elif action == "light_mode":
        return set_dark_mode(False)
    elif action == "accent":
        return set_accent_color(kwargs.get("color", ""))
    return f"Unknown wallpaper action: {action}. Available: set, current, dark_mode, light_mode, accent"
