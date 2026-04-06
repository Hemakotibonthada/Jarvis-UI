"""
System Monitor Module — Real-time system monitoring with history tracking.
"""

import asyncio
import time
import json
from datetime import datetime, timedelta
from collections import deque
from core.logger import get_logger
import config

log = get_logger("monitor")

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


class SystemMonitor:
    """Continuous system monitoring with history and alerts."""

    def __init__(self, history_size: int = 300):
        self.history_size = history_size
        self._cpu_history: deque = deque(maxlen=history_size)
        self._ram_history: deque = deque(maxlen=history_size)
        self._net_history: deque = deque(maxlen=history_size)
        self._disk_io_history: deque = deque(maxlen=history_size)
        self._temp_history: deque = deque(maxlen=history_size)
        self._alerts: list = []
        self._monitoring = False
        self._task = None
        self._last_net_io = None
        self._last_disk_io = None
        self._alert_callbacks: list = []

        # Alert thresholds
        self.cpu_threshold = 90
        self.ram_threshold = 90
        self.disk_threshold = 95
        self.temp_threshold = 85

    async def start(self, interval: float = 2.0):
        """Start monitoring in background."""
        if self._monitoring:
            return
        self._monitoring = True
        self._task = asyncio.create_task(self._monitor_loop(interval))
        log.info("System monitor started")

    async def stop(self):
        """Stop monitoring."""
        self._monitoring = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        log.info("System monitor stopped")

    async def _monitor_loop(self, interval: float):
        """Main monitoring loop."""
        while self._monitoring:
            try:
                snapshot = self._take_snapshot()
                self._check_alerts(snapshot)
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Monitor error: {e}")
                await asyncio.sleep(interval)

    def _take_snapshot(self) -> dict:
        """Take a system snapshot."""
        if not HAS_PSUTIL:
            return {}

        now = datetime.now().isoformat()

        # CPU
        cpu_percent = psutil.cpu_percent(interval=0)
        cpu_per_core = psutil.cpu_percent(percpu=True)
        self._cpu_history.append({"time": now, "total": cpu_percent, "cores": cpu_per_core})

        # RAM
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        self._ram_history.append({
            "time": now,
            "percent": mem.percent,
            "used_gb": round(mem.used / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2),
            "swap_percent": swap.percent,
        })

        # Network I/O rate
        net_io = psutil.net_io_counters()
        if self._last_net_io:
            sent_rate = (net_io.bytes_sent - self._last_net_io.bytes_sent) / 2
            recv_rate = (net_io.bytes_recv - self._last_net_io.bytes_recv) / 2
            self._net_history.append({
                "time": now,
                "sent_kbps": round(sent_rate / 1024, 1),
                "recv_kbps": round(recv_rate / 1024, 1),
            })
        self._last_net_io = net_io

        # Disk I/O rate
        try:
            disk_io = psutil.disk_io_counters()
            if self._last_disk_io and disk_io:
                read_rate = (disk_io.read_bytes - self._last_disk_io.read_bytes) / 2
                write_rate = (disk_io.write_bytes - self._last_disk_io.write_bytes) / 2
                self._disk_io_history.append({
                    "time": now,
                    "read_kbps": round(read_rate / 1024, 1),
                    "write_kbps": round(write_rate / 1024, 1),
                })
            self._last_disk_io = disk_io
        except Exception:
            pass

        # Temperature (if available)
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    for entry in entries:
                        self._temp_history.append({
                            "time": now,
                            "sensor": f"{name}/{entry.label}",
                            "temp": entry.current,
                        })
                        break
                    break
        except Exception:
            pass

        return {
            "cpu": cpu_percent,
            "ram": mem.percent,
            "disk": psutil.disk_usage(config.SYSTEM_DRIVE).percent,
        }

    def _check_alerts(self, snapshot: dict):
        """Check thresholds and trigger alerts."""
        if not snapshot:
            return

        cpu = snapshot.get("cpu", 0)
        ram = snapshot.get("ram", 0)
        disk = snapshot.get("disk", 0)

        if cpu > self.cpu_threshold:
            self._add_alert("cpu_high", f"CPU usage critical: {cpu:.1f}%")
        if ram > self.ram_threshold:
            self._add_alert("ram_high", f"RAM usage critical: {ram:.1f}%")
        if disk > self.disk_threshold:
            self._add_alert("disk_high", f"Disk usage critical: {disk:.1f}%")

    def _add_alert(self, alert_type: str, message: str):
        """Add an alert, avoiding duplicates within 5 minutes."""
        now = datetime.now()
        # Check for recent duplicate
        for alert in self._alerts[-10:]:
            if (alert["type"] == alert_type and
                (now - datetime.fromisoformat(alert["time"])).total_seconds() < 300):
                return

        alert = {"type": alert_type, "message": message, "time": now.isoformat()}
        self._alerts.append(alert)
        log.warning(f"System alert: {message}")

        # Notify callbacks
        for cb in self._alert_callbacks:
            try:
                cb(alert)
            except Exception:
                pass

    def on_alert(self, callback):
        """Register alert callback."""
        self._alert_callbacks.append(callback)

    # ─── Data Access ──────────────────────────────────────────
    def get_current(self) -> dict:
        """Get current system stats."""
        if not HAS_PSUTIL:
            return {"error": "psutil not available"}

        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage(config.SYSTEM_DRIVE)

        result = {
            "cpu": cpu,
            "cpu_cores": psutil.cpu_percent(percpu=True),
            "ram": mem.percent,
            "ram_used_gb": round(mem.used / (1024**3), 2),
            "ram_total_gb": round(mem.total / (1024**3), 2),
            "disk": disk.percent,
            "disk_used_gb": round(disk.used / (1024**3), 2),
            "disk_total_gb": round(disk.total / (1024**3), 2),
        }

        try:
            battery = psutil.sensors_battery()
            if battery:
                result["battery"] = battery.percent
                result["plugged"] = battery.power_plugged
        except Exception:
            pass

        net = psutil.net_io_counters()
        result["net_sent_mb"] = round(net.bytes_sent / (1024**2), 1)
        result["net_recv_mb"] = round(net.bytes_recv / (1024**2), 1)

        return result

    def get_cpu_history(self, count: int = 60) -> list:
        """Get CPU history."""
        return list(self._cpu_history)[-count:]

    def get_ram_history(self, count: int = 60) -> list:
        """Get RAM history."""
        return list(self._ram_history)[-count:]

    def get_net_history(self, count: int = 60) -> list:
        """Get network I/O history."""
        return list(self._net_history)[-count:]

    def get_alerts(self, count: int = 20) -> list:
        """Get recent alerts."""
        return self._alerts[-count:]

    def get_process_tree(self, top: int = 15) -> str:
        """Get top processes with details."""
        if not HAS_PSUTIL:
            return "psutil not available."

        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent",
                                       "memory_info", "status", "create_time"]):
            try:
                info = p.info
                info["memory_mb"] = round(info.get("memory_info", {}).rss / (1024**2), 1) if info.get("memory_info") else 0
                procs.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        procs.sort(key=lambda x: x.get("memory_percent", 0) or 0, reverse=True)
        top_procs = procs[:top]

        lines = [
            f"  PID {p['pid']:>6} | {p['name']:<25} | CPU {p.get('cpu_percent', 0):>5.1f}% | "
            f"RAM {p.get('memory_percent', 0):>5.1f}% ({p.get('memory_mb', 0):>7.1f}MB) | {p.get('status', '')}"
            for p in top_procs
        ]
        return f"Top {len(lines)} processes:\n" + "\n".join(lines)

    def get_disk_details(self) -> str:
        """Get detailed disk information."""
        if not HAS_PSUTIL:
            return "psutil not available."

        lines = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                lines.append(
                    f"  {partition.device} ({partition.mountpoint}) [{partition.fstype}]\n"
                    f"    Total: {usage.total / (1024**3):.1f}GB | "
                    f"Used: {usage.used / (1024**3):.1f}GB | "
                    f"Free: {usage.free / (1024**3):.1f}GB | "
                    f"{usage.percent}%"
                )
            except (PermissionError, OSError):
                lines.append(f"  {partition.device} ({partition.mountpoint}) — access denied")

        return "Disk Partitions:\n" + "\n".join(lines)

    def get_boot_info(self) -> str:
        """Get boot time and uptime info."""
        if not HAS_PSUTIL:
            return "psutil not available."

        boot = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, _ = divmod(remainder, 60)

        return (
            f"Boot time: {boot.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Uptime: {days}d {hours}h {minutes}m\n"
            f"Users: {len(psutil.users())}"
        )

    def get_full_report(self) -> str:
        """Comprehensive system report."""
        parts = [
            "═══ J.A.R.V.I.S. System Report ═══",
            "",
            self.get_boot_info(),
            "",
            "── Resource Usage ──",
        ]

        current = self.get_current()
        parts.extend([
            f"  CPU: {current.get('cpu', 0):.1f}% ({len(current.get('cpu_cores', []))} cores)",
            f"  RAM: {current.get('ram', 0):.1f}% ({current.get('ram_used_gb', 0):.1f}/{current.get('ram_total_gb', 0):.1f} GB)",
            f"  Disk: {current.get('disk', 0):.1f}% ({current.get('disk_used_gb', 0):.1f}/{current.get('disk_total_gb', 0):.1f} GB)",
        ])

        if "battery" in current:
            plug = "plugged" if current.get("plugged") else "on battery"
            parts.append(f"  Battery: {current['battery']}% ({plug})")

        parts.append(f"  Network: ↑{current.get('net_sent_mb', 0)}MB ↓{current.get('net_recv_mb', 0)}MB")

        parts.extend(["", "── Disk Details ──", self.get_disk_details()])
        parts.extend(["", "── Top Processes ──", self.get_process_tree(10)])

        alerts = self.get_alerts(5)
        if alerts:
            parts.extend(["", "── Recent Alerts ──"])
            for a in alerts:
                parts.append(f"  [{a['time'][11:19]}] {a['message']}")

        return "\n".join(parts)


# ─── Singleton ────────────────────────────────────────────────
system_monitor = SystemMonitor()
