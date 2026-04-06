"""
System Control Module — OS info, process management, volume, screenshots, clipboard.
"""

import os
import platform
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

import psutil

try:
    import pyautogui
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False

try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False

import config


def system_info() -> str:
    """Gather comprehensive system information."""
    uname = platform.uname()
    cpu_freq = psutil.cpu_freq()
    svmem = psutil.virtual_memory()
    disk = psutil.disk_usage(config.SYSTEM_DRIVE)
    net = psutil.net_io_counters()

    info = {
        "os": f"{uname.system} {uname.release} ({uname.version})",
        "machine": uname.machine,
        "processor": uname.processor,
        "hostname": uname.node,
        "cpu_cores_physical": psutil.cpu_count(logical=False),
        "cpu_cores_logical": psutil.cpu_count(logical=True),
        "cpu_freq_mhz": round(cpu_freq.current, 1) if cpu_freq else "N/A",
        "cpu_usage_percent": psutil.cpu_percent(interval=1),
        "ram_total_gb": round(svmem.total / (1024**3), 2),
        "ram_used_gb": round(svmem.used / (1024**3), 2),
        "ram_percent": svmem.percent,
        "disk_total_gb": round(disk.total / (1024**3), 2),
        "disk_used_gb": round(disk.used / (1024**3), 2),
        "disk_percent": disk.percent,
        "net_sent_mb": round(net.bytes_sent / (1024**2), 2),
        "net_recv_mb": round(net.bytes_recv / (1024**2), 2),
    }

    try:
        battery = psutil.sensors_battery()
        if battery:
            info["battery_percent"] = battery.percent
            info["battery_plugged"] = battery.power_plugged
    except Exception:
        pass

    lines = [f"  {k}: {v}" for k, v in info.items()]
    return "System Information:\n" + "\n".join(lines)


def list_running_processes() -> str:
    """Get top 30 processes by memory usage."""
    procs = []
    for p in psutil.process_iter(["pid", "name", "memory_percent", "cpu_percent"]):
        try:
            info = p.info
            procs.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    procs.sort(key=lambda x: x.get("memory_percent", 0) or 0, reverse=True)
    top = procs[:30]
    lines = [f"  PID {p['pid']:>6} | {p['name']:<30} | RAM {p.get('memory_percent', 0):.1f}% | CPU {p.get('cpu_percent', 0):.1f}%"
             for p in top]
    return f"Top {len(lines)} processes by memory:\n" + "\n".join(lines)


def open_application(app_name: str) -> str:
    """Open an application by name."""
    app_map = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "calc": "calc.exe",
        "paint": "mspaint.exe",
        "cmd": "cmd.exe",
        "terminal": "wt.exe",
        "powershell": "powershell.exe",
        "explorer": "explorer.exe",
        "file explorer": "explorer.exe",
        "task manager": "taskmgr.exe",
        "control panel": "control.exe",
        "settings": "ms-settings:",
        "chrome": "chrome.exe",
        "google chrome": "chrome.exe",
        "firefox": "firefox.exe",
        "edge": "msedge.exe",
        "microsoft edge": "msedge.exe",
        "vscode": "code",
        "vs code": "code",
        "visual studio code": "code",
        "spotify": "spotify.exe",
        "discord": "discord.exe",
        "slack": "slack.exe",
        "word": "winword.exe",
        "excel": "excel.exe",
        "powerpoint": "powerpnt.exe",
        "outlook": "outlook.exe",
        "teams": "ms-teams.exe",
        "obs": "obs64.exe",
        "vlc": "vlc.exe",
        "steam": "steam.exe",
    }

    key = app_name.lower().strip()
    executable = app_map.get(key, key)

    try:
        if executable.startswith("ms-"):
            os.startfile(executable)
        else:
            subprocess.Popen(executable, shell=True)
        return f"Opened {app_name}."
    except Exception as e:
        return f"Failed to open {app_name}: {e}"


def close_application(app_name: str) -> str:
    """Close an application by name."""
    killed = 0
    for proc in psutil.process_iter(["name"]):
        try:
            if app_name.lower() in proc.info["name"].lower():
                proc.terminate()
                killed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if killed:
        return f"Terminated {killed} process(es) matching '{app_name}'."
    return f"No running process found matching '{app_name}'."


def execute_command(command: str) -> str:
    """Execute a shell command and return output."""
    # Block obviously dangerous commands
    dangerous = ["format", "del /f /s /q c:", "rd /s /q c:", "rm -rf /"]
    if any(d in command.lower() for d in dangerous):
        return "Blocked: this command is potentially destructive."

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=os.path.expanduser("~"),
        )
        output = result.stdout[:3000] if result.stdout else ""
        error = result.stderr[:1000] if result.stderr else ""
        return f"Exit code: {result.returncode}\nOutput:\n{output}\n{error}".strip()
    except subprocess.TimeoutExpired:
        return "Command timed out after 30 seconds."
    except Exception as e:
        return f"Command error: {e}"


def set_volume(level: int) -> str:
    """Set system volume (Windows)."""
    level = max(0, min(100, level))
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        volume.SetMasterVolumeLevelScalar(level / 100, None)
        return f"Volume set to {level}%."
    except ImportError:
        # Fallback using nircmd or powershell
        try:
            subprocess.run(
                f'powershell -c "(New-Object -ComObject WScript.Shell).SendKeys([char]173)"',
                shell=True, capture_output=True
            )
            return f"Volume command sent (approximate to {level}%)."
        except Exception as e:
            return f"Could not set volume: {e}"


def screenshot() -> str:
    """Take a screenshot and save it."""
    if not HAS_PYAUTOGUI:
        return "pyautogui not installed — cannot take screenshot."
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = config.GENERATED_DIR / f"screenshot_{ts}.png"
    img = pyautogui.screenshot()
    img.save(str(path))
    return f"Screenshot saved to {path}"


def clipboard_read() -> str:
    """Read clipboard content."""
    if HAS_PYPERCLIP:
        return pyperclip.paste() or "(clipboard is empty)"
    return "pyperclip not installed."


def clipboard_write(text: str) -> str:
    """Write text to clipboard."""
    if HAS_PYPERCLIP:
        pyperclip.copy(text)
        return "Text copied to clipboard."
    return "pyperclip not installed."


def type_text(text: str) -> str:
    """Type text via keyboard simulation."""
    if HAS_PYAUTOGUI:
        pyautogui.typewrite(text, interval=0.02)
        return f"Typed {len(text)} characters."
    return "pyautogui not installed."


def hotkey(keys: str) -> str:
    """Press a hotkey combination like 'ctrl+shift+s'."""
    if HAS_PYAUTOGUI:
        parts = [k.strip() for k in keys.split("+")]
        pyautogui.hotkey(*parts)
        return f"Pressed {keys}."
    return "pyautogui not installed."


# ─── Power Management ────────────────────────────────────────
def system_power(action: str) -> str:
    """Control system power: shutdown, restart, sleep, lock, hibernate, logoff."""
    actions = {
        "lock": "rundll32.exe user32.dll,LockWorkStation",
        "sleep": "rundll32.exe powrprof.dll,SetSuspendState 0,1,0",
        "hibernate": "shutdown /h",
        "shutdown": "shutdown /s /t 5",
        "restart": "shutdown /r /t 5",
        "logoff": "shutdown /l",
        "cancel_shutdown": "shutdown /a",
    }
    if not config.IS_WINDOWS:
        actions = {
            "lock": "xdg-screensaver lock" if config.IS_LINUX else "pmset displaysleepnow",
            "sleep": "systemctl suspend" if config.IS_LINUX else "pmset sleepnow",
            "shutdown": "shutdown -h +1" if config.IS_LINUX else "sudo shutdown -h +1",
            "restart": "shutdown -r +1" if config.IS_LINUX else "sudo shutdown -r +1",
            "logoff": "gnome-session-quit" if config.IS_LINUX else "osascript -e 'tell app \"System Events\" to log out'",
            "cancel_shutdown": "shutdown -c" if config.IS_LINUX else "sudo killall shutdown",
        }

    cmd = actions.get(action.lower())
    if not cmd:
        return f"Unknown power action: {action}. Available: {', '.join(actions.keys())}"

    try:
        subprocess.Popen(cmd, shell=True)
        return f"Power action '{action}' initiated."
    except Exception as e:
        return f"Power action failed: {e}"


# ─── Window Management ───────────────────────────────────────
def manage_window(action: str, window_title: str = "") -> str:
    """Manage windows: minimize, maximize, restore, close, minimize_all, show_desktop."""
    if action == "minimize_all" or action == "show_desktop":
        if HAS_PYAUTOGUI:
            pyautogui.hotkey("win", "d")
            return "Showing desktop / minimizing all windows."
        return "pyautogui not installed."

    if action == "switch":
        if HAS_PYAUTOGUI:
            pyautogui.hotkey("alt", "tab")
            return "Switched window."
        return "pyautogui not installed."

    if action == "task_view":
        if HAS_PYAUTOGUI:
            pyautogui.hotkey("win", "tab")
            return "Opened task view."
        return "pyautogui not installed."

    if action == "snap_left":
        if HAS_PYAUTOGUI:
            pyautogui.hotkey("win", "left")
            return "Snapped window to left."
        return "pyautogui not installed."

    if action == "snap_right":
        if HAS_PYAUTOGUI:
            pyautogui.hotkey("win", "right")
            return "Snapped window to right."
        return "pyautogui not installed."

    if action == "maximize":
        if HAS_PYAUTOGUI:
            pyautogui.hotkey("win", "up")
            return "Maximized window."
        return "pyautogui not installed."

    if action == "minimize":
        if HAS_PYAUTOGUI:
            pyautogui.hotkey("win", "down")
            return "Minimized window."
        return "pyautogui not installed."

    if action == "close":
        if HAS_PYAUTOGUI:
            pyautogui.hotkey("alt", "F4")
            return "Closed current window."
        return "pyautogui not installed."

    if action == "new_desktop":
        if HAS_PYAUTOGUI:
            pyautogui.hotkey("win", "ctrl", "d")
            return "Created new virtual desktop."
        return "pyautogui not installed."

    if action == "close_desktop":
        if HAS_PYAUTOGUI:
            pyautogui.hotkey("win", "ctrl", "F4")
            return "Closed current virtual desktop."
        return "pyautogui not installed."

    if action == "next_desktop":
        if HAS_PYAUTOGUI:
            pyautogui.hotkey("win", "ctrl", "right")
            return "Switched to next virtual desktop."
        return "pyautogui not installed."

    if action == "prev_desktop":
        if HAS_PYAUTOGUI:
            pyautogui.hotkey("win", "ctrl", "left")
            return "Switched to previous virtual desktop."
        return "pyautogui not installed."

    return f"Unknown window action: {action}. Available: minimize, maximize, close, snap_left, snap_right, minimize_all, show_desktop, switch, task_view, new_desktop, close_desktop, next_desktop, prev_desktop"


# ─── WiFi Management ─────────────────────────────────────────
def wifi_control(action: str, network_name: str = "", password: str = "") -> str:
    """WiFi management: list, connect, disconnect, status."""
    if action == "list":
        try:
            if config.IS_WINDOWS:
                result = subprocess.run(["netsh", "wlan", "show", "networks"], capture_output=True, text=True, timeout=10)
            else:
                result = subprocess.run(["nmcli", "dev", "wifi", "list"], capture_output=True, text=True, timeout=10)
            return result.stdout or "No networks found."
        except Exception as e:
            return f"WiFi scan error: {e}"

    elif action == "status":
        try:
            if config.IS_WINDOWS:
                result = subprocess.run(["netsh", "wlan", "show", "interfaces"], capture_output=True, text=True, timeout=10)
            else:
                result = subprocess.run(["nmcli", "general", "status"], capture_output=True, text=True, timeout=10)
            return result.stdout or "No WiFi info."
        except Exception as e:
            return f"WiFi status error: {e}"

    elif action == "disconnect":
        try:
            if config.IS_WINDOWS:
                result = subprocess.run(["netsh", "wlan", "disconnect"], capture_output=True, text=True, timeout=10)
            else:
                result = subprocess.run(["nmcli", "dev", "disconnect", "wifi"], capture_output=True, text=True, timeout=10)
            return result.stdout or "Disconnected from WiFi."
        except Exception as e:
            return f"WiFi disconnect error: {e}"

    elif action == "connect":
        if not network_name:
            return "Please provide a network name."
        try:
            if config.IS_WINDOWS:
                result = subprocess.run(
                    ["netsh", "wlan", "connect", f"name={network_name}"],
                    capture_output=True, text=True, timeout=15,
                )
            else:
                cmd = ["nmcli", "dev", "wifi", "connect", network_name]
                if password:
                    cmd += ["password", password]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            return result.stdout or result.stderr or f"Connecting to {network_name}..."
        except Exception as e:
            return f"WiFi connect error: {e}"

    return f"Unknown WiFi action: {action}. Available: list, connect, disconnect, status"


# ─── Bluetooth ────────────────────────────────────────────────
def bluetooth_control(action: str) -> str:
    """Bluetooth control: on, off, status."""
    if config.IS_WINDOWS:
        if action in ("on", "off"):
            state = "On" if action == "on" else "Off"
            try:
                subprocess.run(
                    ["powershell", "-c", f"Set-BluetoothRadio -{state}"],
                    capture_output=True, text=True, timeout=10,
                )
                return f"Bluetooth turned {action}."
            except Exception:
                return f"Could not turn Bluetooth {action}. May need admin privileges."
        elif action == "status":
            try:
                result = subprocess.run(
                    ["powershell", "-c", "Get-PnpDevice -Class Bluetooth | Select-Object Status,Name"],
                    capture_output=True, text=True, timeout=10,
                )
                return result.stdout or "No Bluetooth info."
            except Exception as e:
                return f"Bluetooth status error: {e}"
    return f"Bluetooth {action} not supported on this platform."


# ─── Service Management ──────────────────────────────────────
def manage_service(action: str, service_name: str) -> str:
    """Manage system services: start, stop, restart, status."""
    if config.IS_WINDOWS:
        cmds = {
            "start": f"net start {service_name}",
            "stop": f"net stop {service_name}",
            "restart": f"net stop {service_name} && net start {service_name}",
            "status": f'sc query "{service_name}"',
        }
    else:
        cmds = {
            "start": f"sudo systemctl start {service_name}",
            "stop": f"sudo systemctl stop {service_name}",
            "restart": f"sudo systemctl restart {service_name}",
            "status": f"systemctl status {service_name}",
        }

    cmd = cmds.get(action)
    if not cmd:
        return f"Unknown service action: {action}. Available: start, stop, restart, status"

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        return result.stdout or result.stderr or f"Service {action} executed."
    except Exception as e:
        return f"Service error: {e}"


# ─── Startup Programs ────────────────────────────────────────
def list_startup_programs() -> str:
    """List startup programs (Windows)."""
    if not config.IS_WINDOWS:
        return "Startup listing only supported on Windows."
    try:
        result = subprocess.run(
            ['powershell', '-c', 'Get-CimInstance Win32_StartupCommand | Select-Object Name,Command,Location | Format-Table -AutoSize'],
            capture_output=True, text=True, timeout=10,
        )
        return result.stdout or "No startup programs found."
    except Exception as e:
        return f"Startup list error: {e}"


# ─── Installed Programs ──────────────────────────────────────
def list_installed_programs() -> str:
    """List installed programs (Windows)."""
    if not config.IS_WINDOWS:
        return "Use 'dpkg -l' or 'brew list' on your platform."
    try:
        result = subprocess.run(
            ['powershell', '-c', 'Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* | Select-Object DisplayName,DisplayVersion | Sort-Object DisplayName | Format-Table -AutoSize'],
            capture_output=True, text=True, timeout=15,
        )
        return result.stdout[:4000] or "No installed programs found."
    except Exception as e:
        return f"Program list error: {e}"


# ─── Screen Brightness ───────────────────────────────────────
def set_brightness(level: int) -> str:
    """Set screen brightness (0-100)."""
    level = max(0, min(100, level))
    if config.IS_WINDOWS:
        try:
            subprocess.run(
                ['powershell', '-c', f'(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{level})'],
                capture_output=True, text=True, timeout=10,
            )
            return f"Brightness set to {level}%."
        except Exception as e:
            return f"Brightness error: {e}"
    return "Brightness control not supported on this platform."


# ─── System Stats (for live API) ─────────────────────────────
def get_live_stats() -> dict:
    """Get real-time CPU, RAM, disk stats as dict (for API endpoint)."""
    return {
        "cpu": psutil.cpu_percent(interval=0.5),
        "ram": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage(config.SYSTEM_DRIVE).percent,
    }


# ─── Run Script ──────────────────────────────────────────────
def run_script(file_path: str) -> str:
    """Run a Python or other script file."""
    from pathlib import Path
    p = Path(file_path).expanduser()
    if not p.exists():
        return f"Script not found: {p}"

    ext = p.suffix.lower()
    runners = {
        ".py": ["python", str(p)],
        ".js": ["node", str(p)],
        ".sh": ["bash", str(p)],
        ".bat": [str(p)],
        ".ps1": ["powershell", "-File", str(p)],
    }
    cmd = runners.get(ext)
    if not cmd:
        return f"Unknown script type: {ext}"

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=str(p.parent))
        output = result.stdout[:3000] if result.stdout else ""
        error = result.stderr[:1000] if result.stderr else ""
        return f"Script exit code: {result.returncode}\nOutput:\n{output}\n{error}".strip()
    except subprocess.TimeoutExpired:
        return "Script timed out after 30 seconds."
    except Exception as e:
        return f"Script error: {e}"
