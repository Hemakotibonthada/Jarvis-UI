"""
Example Plugin — Demonstrates the J.A.R.V.I.S. plugin system.
Shows how to register tools, subscribe to events, and extend functionality.
"""

__version__ = "1.0.0"
__author__ = "Jarvis"
__description__ = "Example plugin with custom tools"


def get_uptime() -> str:
    """Get system uptime."""
    import psutil
    from datetime import datetime
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime = datetime.now() - boot_time
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"System uptime: {days}d {hours}h {minutes}m {seconds}s (since {boot_time.strftime('%Y-%m-%d %H:%M')})"


def system_health_check() -> str:
    """Run a comprehensive system health check."""
    import psutil
    import shutil

    issues = []
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    disk = shutil.disk_usage("/")

    if cpu > 90:
        issues.append(f"⚠ CPU usage critical: {cpu}%")
    if ram.percent > 90:
        issues.append(f"⚠ RAM usage critical: {ram.percent}%")
    if (disk.used / disk.total * 100) > 90:
        issues.append(f"⚠ Disk usage critical: {disk.used / disk.total * 100:.1f}%")

    # Check if battery is low
    try:
        battery = psutil.sensors_battery()
        if battery and battery.percent < 20 and not battery.power_plugged:
            issues.append(f"⚠ Battery low: {battery.percent}%")
    except Exception:
        pass

    if issues:
        return "Health Check — Issues Found:\n" + "\n".join(issues)
    return f"Health Check — All systems nominal. CPU: {cpu}%, RAM: {ram.percent}%, Disk: {disk.used / disk.total * 100:.1f}%"


def register(manager):
    """Register this plugin's tools and event handlers."""
    manager.register_tool(
        name="system_uptime",
        handler=get_uptime,
        description="Get system uptime since last boot",
        plugin_name="example_plugin",
    )

    manager.register_tool(
        name="health_check",
        handler=system_health_check,
        description="Run a comprehensive system health check",
        plugin_name="example_plugin",
    )


def cleanup():
    """Called when plugin is unloaded."""
    pass
