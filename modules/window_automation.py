"""
Window Automation Module — Advanced window management using Win32 on Windows.
Find windows, resize, reposition, arrange, and interact with app windows.
"""

import subprocess
import time
from core.logger import get_logger
import config

log = get_logger("window_automation")

try:
    import pyautogui
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False

if config.IS_WINDOWS:
    try:
        import ctypes
        from ctypes import wintypes
        import win32gui
        import win32con
        import win32process
        HAS_WIN32 = True
    except ImportError:
        HAS_WIN32 = False
else:
    HAS_WIN32 = False


def list_windows() -> str:
    """List all visible windows with titles."""
    if not config.IS_WINDOWS:
        try:
            result = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True, timeout=5)
            return result.stdout or "No windows found."
        except Exception:
            return "wmctrl not available."

    if not HAS_WIN32:
        return "win32gui not installed. Run: pip install pywin32"

    windows = []

    def enum_callback(hwnd, results):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                rect = win32gui.GetWindowRect(hwnd)
                w, h = rect[2] - rect[0], rect[3] - rect[1]
                results.append({
                    "hwnd": hwnd,
                    "title": title[:60],
                    "pid": pid,
                    "x": rect[0],
                    "y": rect[1],
                    "width": w,
                    "height": h,
                })

    win32gui.EnumWindows(enum_callback, windows)

    if not windows:
        return "No visible windows found."

    lines = [f"  [{w['hwnd']:>8}] {w['title']:<40} PID:{w['pid']:>6} ({w['width']}x{w['height']} at {w['x']},{w['y']})"
             for w in windows]
    return f"Visible windows ({len(windows)}):\n" + "\n".join(lines)


def find_window(title_search: str) -> str:
    """Find windows matching a title."""
    if not HAS_WIN32:
        return "win32gui not available."

    matches = []

    def enum_callback(hwnd, results):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title and title_search.lower() in title.lower():
                results.append({"hwnd": hwnd, "title": title})

    win32gui.EnumWindows(enum_callback, matches)

    if not matches:
        return f"No windows matching '{title_search}'."

    lines = [f"  [{m['hwnd']}] {m['title']}" for m in matches]
    return f"Matching windows ({len(matches)}):\n" + "\n".join(lines)


def focus_window(title_search: str) -> str:
    """Bring a window to foreground by title."""
    if not HAS_WIN32:
        return "win32gui not available."

    def enum_callback(hwnd, results):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title and title_search.lower() in title.lower():
                results.append(hwnd)

    matches = []
    win32gui.EnumWindows(enum_callback, matches)

    if not matches:
        return f"No window matching '{title_search}'."

    hwnd = matches[0]
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        return f"Focused window: {win32gui.GetWindowText(hwnd)}"
    except Exception as e:
        return f"Failed to focus window: {e}"


def move_window(title_search: str, x: int, y: int, width: int = 0, height: int = 0) -> str:
    """Move and optionally resize a window."""
    if not HAS_WIN32:
        return "win32gui not available."

    matches = []

    def enum_callback(hwnd, results):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title and title_search.lower() in title.lower():
                results.append(hwnd)

    win32gui.EnumWindows(enum_callback, matches)

    if not matches:
        return f"No window matching '{title_search}'."

    hwnd = matches[0]
    try:
        if width and height:
            win32gui.MoveWindow(hwnd, x, y, width, height, True)
            return f"Moved and resized window to ({x},{y}) {width}x{height}"
        else:
            rect = win32gui.GetWindowRect(hwnd)
            w, h = rect[2] - rect[0], rect[3] - rect[1]
            win32gui.MoveWindow(hwnd, x, y, w, h, True)
            return f"Moved window to ({x},{y})"
    except Exception as e:
        return f"Failed to move window: {e}"


def minimize_window(title_search: str) -> str:
    """Minimize a window by title."""
    if not HAS_WIN32:
        return "win32gui not available."

    matches = []

    def enum_callback(hwnd, results):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title and title_search.lower() in title.lower():
                results.append(hwnd)

    win32gui.EnumWindows(enum_callback, matches)

    if not matches:
        return f"No window matching '{title_search}'."

    try:
        win32gui.ShowWindow(matches[0], win32con.SW_MINIMIZE)
        return f"Minimized window: {win32gui.GetWindowText(matches[0])}"
    except Exception as e:
        return f"Failed: {e}"


def maximize_window(title_search: str) -> str:
    """Maximize a window by title."""
    if not HAS_WIN32:
        return "win32gui not available."

    matches = []

    def enum_callback(hwnd, results):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title and title_search.lower() in title.lower():
                results.append(hwnd)

    win32gui.EnumWindows(enum_callback, matches)

    if not matches:
        return f"No window matching '{title_search}'."

    try:
        win32gui.ShowWindow(matches[0], win32con.SW_MAXIMIZE)
        return f"Maximized window: {win32gui.GetWindowText(matches[0])}"
    except Exception as e:
        return f"Failed: {e}"


def close_window(title_search: str) -> str:
    """Close a window by title."""
    if not HAS_WIN32:
        return "win32gui not available."

    matches = []

    def enum_callback(hwnd, results):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title and title_search.lower() in title.lower():
                results.append(hwnd)

    win32gui.EnumWindows(enum_callback, matches)

    if not matches:
        return f"No window matching '{title_search}'."

    try:
        win32gui.PostMessage(matches[0], win32con.WM_CLOSE, 0, 0)
        return f"Sent close to: {win32gui.GetWindowText(matches[0])}"
    except Exception as e:
        return f"Failed: {e}"


def arrange_windows(layout: str = "tile") -> str:
    """Arrange windows in a layout: tile, cascade, stack, side_by_side."""
    if not HAS_PYAUTOGUI:
        return "pyautogui not available."

    if layout == "show_desktop":
        pyautogui.hotkey("win", "d")
        return "Showing desktop."

    if layout == "cascade":
        if config.IS_WINDOWS:
            try:
                # Win+Shift+M to restore all, then cascade manually
                subprocess.run(
                    ['powershell', '-c', '(New-Object -ComObject Shell.Application).CascadeWindows()'],
                    capture_output=True, timeout=5,
                )
                return "Windows cascaded."
            except Exception:
                return "Failed to cascade windows."

    if layout == "side_by_side":
        if config.IS_WINDOWS:
            try:
                subprocess.run(
                    ['powershell', '-c', '(New-Object -ComObject Shell.Application).TileVertically()'],
                    capture_output=True, timeout=5,
                )
                return "Windows tiled side by side."
            except Exception:
                return "Failed to tile windows."

    if layout == "stack":
        if config.IS_WINDOWS:
            try:
                subprocess.run(
                    ['powershell', '-c', '(New-Object -ComObject Shell.Application).TileHorizontally()'],
                    capture_output=True, timeout=5,
                )
                return "Windows stacked horizontally."
            except Exception:
                return "Failed to stack windows."

    return f"Unknown layout: {layout}. Available: tile, cascade, side_by_side, stack, show_desktop"


def get_screen_info() -> str:
    """Get screen/monitor information."""
    if HAS_PYAUTOGUI:
        w, h = pyautogui.size()
        info = f"Primary screen: {w}x{h}"
    else:
        info = "Screen size: unknown (pyautogui not installed)"

    if config.IS_WINDOWS:
        try:
            user32 = ctypes.windll.user32
            monitors = user32.GetSystemMetrics(80)  # SM_CMONITORS
            vw = user32.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
            vh = user32.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN
            info += f"\n  Monitors: {monitors}"
            info += f"\n  Virtual screen: {vw}x{vh}"
        except Exception:
            pass

    return f"Screen Info:\n  {info}"


def set_window_opacity(title_search: str, opacity: int = 200) -> str:
    """Set window transparency (Windows only). Opacity: 0-255."""
    if not HAS_WIN32:
        return "win32gui not available."

    matches = []

    def enum_callback(hwnd, results):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title and title_search.lower() in title.lower():
                results.append(hwnd)

    win32gui.EnumWindows(enum_callback, matches)

    if not matches:
        return f"No window matching '{title_search}'."

    hwnd = matches[0]
    try:
        # Add layered window style
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style | win32con.WS_EX_LAYERED)
        # Set opacity
        ctypes.windll.user32.SetLayeredWindowAttributes(
            hwnd, 0, max(30, min(255, opacity)), 0x02  # LWA_ALPHA
        )
        return f"Set opacity to {opacity}/255 for: {win32gui.GetWindowText(hwnd)}"
    except Exception as e:
        return f"Failed: {e}"


def set_always_on_top(title_search: str, enable: bool = True) -> str:
    """Set a window to always stay on top."""
    if not HAS_WIN32:
        return "win32gui not available."

    matches = []

    def enum_callback(hwnd, results):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title and title_search.lower() in title.lower():
                results.append(hwnd)

    win32gui.EnumWindows(enum_callback, matches)

    if not matches:
        return f"No window matching '{title_search}'."

    hwnd = matches[0]
    try:
        topmost = win32con.HWND_TOPMOST if enable else win32con.HWND_NOTOPMOST
        win32gui.SetWindowPos(
            hwnd, topmost, 0, 0, 0, 0,
            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE
        )
        return f"{'Pinned' if enable else 'Unpinned'} window: {win32gui.GetWindowText(hwnd)}"
    except Exception as e:
        return f"Failed: {e}"


# ─── Unified interface ───────────────────────────────────────
def window_operation(operation: str, **kwargs) -> str:
    """Unified window operations interface."""
    title = kwargs.get("title", "")

    ops = {
        "list": lambda: list_windows(),
        "find": lambda: find_window(title),
        "focus": lambda: focus_window(title),
        "move": lambda: move_window(title, int(kwargs.get("x", 0)), int(kwargs.get("y", 0)), int(kwargs.get("width", 0)), int(kwargs.get("height", 0))),
        "minimize": lambda: minimize_window(title),
        "maximize": lambda: maximize_window(title),
        "close": lambda: close_window(title),
        "arrange": lambda: arrange_windows(kwargs.get("layout", "tile")),
        "screen_info": lambda: get_screen_info(),
        "opacity": lambda: set_window_opacity(title, int(kwargs.get("opacity", 200))),
        "always_on_top": lambda: set_always_on_top(title, kwargs.get("enable", True)),
    }

    handler = ops.get(operation)
    if handler:
        return handler()
    return f"Unknown window operation: {operation}. Available: {', '.join(ops.keys())}"
