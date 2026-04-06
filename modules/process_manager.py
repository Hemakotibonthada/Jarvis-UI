"""
Process Manager Module — Advanced process management, monitoring, and control.
Kill processes by name/PID, analyze resource hogs, set process priorities.
"""

import subprocess
import os
import signal
from datetime import datetime
from core.logger import get_logger
import config

log = get_logger("process_mgr")

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


def kill_process(name_or_pid: str, force: bool = False) -> str:
    """Kill a process by name or PID."""
    if not HAS_PSUTIL:
        return "psutil not installed."

    killed = 0

    # Try as PID first
    try:
        pid = int(name_or_pid)
        proc = psutil.Process(pid)
        proc_name = proc.name()
        if force:
            proc.kill()
        else:
            proc.terminate()
        killed = 1
        return f"{'Killed' if force else 'Terminated'} process: {proc_name} (PID {pid})"
    except (ValueError, psutil.NoSuchProcess, psutil.AccessDenied):
        pass

    # Try as name
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            if name_or_pid.lower() in proc.info["name"].lower():
                if force:
                    proc.kill()
                else:
                    proc.terminate()
                killed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if killed:
        return f"{'Killed' if force else 'Terminated'} {killed} process(es) matching '{name_or_pid}'."
    return f"No processes matching '{name_or_pid}'."


def get_process_details(name_or_pid: str) -> str:
    """Get detailed information about a process."""
    if not HAS_PSUTIL:
        return "psutil not installed."

    target = None

    # Try PID
    try:
        pid = int(name_or_pid)
        target = psutil.Process(pid)
    except (ValueError, psutil.NoSuchProcess):
        pass

    # Try name
    if not target:
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if name_or_pid.lower() in proc.info["name"].lower():
                    target = psutil.Process(proc.info["pid"])
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    if not target:
        return f"Process '{name_or_pid}' not found."

    try:
        with target.oneshot():
            info = {
                "PID": target.pid,
                "Name": target.name(),
                "Status": target.status(),
                "CPU %": f"{target.cpu_percent():.1f}",
                "Memory %": f"{target.memory_percent():.1f}",
                "Memory (MB)": f"{target.memory_info().rss / (1024**2):.1f}",
                "Threads": target.num_threads(),
                "Created": datetime.fromtimestamp(target.create_time()).strftime("%Y-%m-%d %H:%M:%S"),
                "Executable": target.exe(),
                "CWD": target.cwd(),
                "Username": target.username(),
            }

            try:
                connections = target.connections()
                if connections:
                    info["Connections"] = len(connections)
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass

            try:
                info["Command"] = " ".join(target.cmdline()[:5])
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass

            try:
                children = target.children(recursive=True)
                if children:
                    info["Child processes"] = len(children)
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass

        lines = [f"  {k}: {v}" for k, v in info.items()]
        return f"Process Details:\n" + "\n".join(lines)
    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
        return f"Cannot access process: {e}"


def resource_hogs(sort_by: str = "memory", top: int = 15) -> str:
    """Find top resource-consuming processes."""
    if not HAS_PSUTIL:
        return "psutil not installed."

    procs = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "memory_info"]):
        try:
            info = proc.info
            info["memory_mb"] = info["memory_info"].rss / (1024**2) if info.get("memory_info") else 0
            procs.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if sort_by == "cpu":
        procs.sort(key=lambda x: x.get("cpu_percent", 0) or 0, reverse=True)
    else:
        procs.sort(key=lambda x: x.get("memory_percent", 0) or 0, reverse=True)

    top_procs = procs[:top]
    header = f"Top {len(top_procs)} processes by {'CPU' if sort_by == 'cpu' else 'Memory'}:"
    lines = [
        f"  PID {p['pid']:>6} | {p['name']:<28} | CPU {p.get('cpu_percent', 0):>5.1f}% "
        f"| RAM {p.get('memory_percent', 0):>5.1f}% ({p.get('memory_mb', 0):>7.1f}MB)"
        for p in top_procs
    ]
    return header + "\n" + "\n".join(lines)


def set_process_priority(name_or_pid: str, priority: str = "normal") -> str:
    """Set process priority: low, below_normal, normal, above_normal, high, realtime."""
    if not HAS_PSUTIL:
        return "psutil not installed."

    priority_map = {
        "low": psutil.IDLE_PRIORITY_CLASS if config.IS_WINDOWS else 19,
        "below_normal": psutil.BELOW_NORMAL_PRIORITY_CLASS if config.IS_WINDOWS else 10,
        "normal": psutil.NORMAL_PRIORITY_CLASS if config.IS_WINDOWS else 0,
        "above_normal": psutil.ABOVE_NORMAL_PRIORITY_CLASS if config.IS_WINDOWS else -5,
        "high": psutil.HIGH_PRIORITY_CLASS if config.IS_WINDOWS else -10,
        "realtime": psutil.REALTIME_PRIORITY_CLASS if config.IS_WINDOWS else -20,
    }

    nice_value = priority_map.get(priority.lower())
    if nice_value is None:
        return f"Invalid priority. Available: {', '.join(priority_map.keys())}"

    target = None
    try:
        pid = int(name_or_pid)
        target = psutil.Process(pid)
    except (ValueError, psutil.NoSuchProcess):
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if name_or_pid.lower() in proc.info["name"].lower():
                    target = psutil.Process(proc.info["pid"])
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    if not target:
        return f"Process '{name_or_pid}' not found."

    try:
        target.nice(nice_value)
        return f"Set priority of {target.name()} (PID {target.pid}) to '{priority}'."
    except (psutil.AccessDenied, PermissionError):
        return f"Permission denied. Run as administrator to change process priority."
    except Exception as e:
        return f"Failed to set priority: {e}"


def find_process_by_port(port: int) -> str:
    """Find which process is using a specific port."""
    if not HAS_PSUTIL:
        return "psutil not installed."

    for conn in psutil.net_connections(kind="inet"):
        if conn.laddr and conn.laddr.port == port:
            try:
                proc = psutil.Process(conn.pid) if conn.pid else None
                if proc:
                    return (
                        f"Port {port} is used by:\n"
                        f"  Process: {proc.name()}\n"
                        f"  PID: {proc.pid}\n"
                        f"  Status: {conn.status}\n"
                        f"  Address: {conn.laddr.ip}:{conn.laddr.port}"
                    )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return f"Port {port} is in use but process access denied."

    return f"Port {port} is not in use."


def process_tree(pid: int = 0) -> str:
    """Show process tree from a parent PID or all top-level."""
    if not HAS_PSUTIL:
        return "psutil not installed."

    if pid:
        try:
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
            lines = [f"  {parent.pid} {parent.name()} (root)"]
            for child in children:
                try:
                    lines.append(f"    └── {child.pid} {child.name()}")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            return f"Process tree for PID {pid}:\n" + "\n".join(lines)
        except psutil.NoSuchProcess:
            return f"Process {pid} not found."
    else:
        # Show system process tree summary
        parent_counts = {}
        for proc in psutil.process_iter(["pid", "name", "ppid"]):
            try:
                ppid = proc.info.get("ppid", 0)
                if ppid not in parent_counts:
                    parent_counts[ppid] = {"count": 0, "children": []}
                parent_counts[ppid]["count"] += 1
                if len(parent_counts[ppid]["children"]) < 3:
                    parent_counts[ppid]["children"].append(proc.info["name"])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Find top parents
        top = sorted(parent_counts.items(), key=lambda x: x[1]["count"], reverse=True)[:10]
        lines = []
        for ppid, data in top:
            try:
                parent_name = psutil.Process(ppid).name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                parent_name = "unknown"
            children_str = ", ".join(data["children"][:3])
            lines.append(f"  PID {ppid} ({parent_name}): {data['count']} children [{children_str}...]")

        return "Process tree (top parents):\n" + "\n".join(lines)


def suspend_process(name_or_pid: str) -> str:
    """Suspend (pause) a process."""
    if not HAS_PSUTIL:
        return "psutil not installed."

    target = None
    try:
        pid = int(name_or_pid)
        target = psutil.Process(pid)
    except (ValueError, psutil.NoSuchProcess):
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if name_or_pid.lower() in proc.info["name"].lower():
                    target = psutil.Process(proc.info["pid"])
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    if not target:
        return f"Process '{name_or_pid}' not found."

    try:
        target.suspend()
        return f"Suspended: {target.name()} (PID {target.pid})"
    except Exception as e:
        return f"Failed to suspend: {e}"


def resume_process(name_or_pid: str) -> str:
    """Resume a suspended process."""
    if not HAS_PSUTIL:
        return "psutil not installed."

    target = None
    try:
        pid = int(name_or_pid)
        target = psutil.Process(pid)
    except (ValueError, psutil.NoSuchProcess):
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if name_or_pid.lower() in proc.info["name"].lower():
                    target = psutil.Process(proc.info["pid"])
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    if not target:
        return f"Process '{name_or_pid}' not found."

    try:
        target.resume()
        return f"Resumed: {target.name()} (PID {target.pid})"
    except Exception as e:
        return f"Failed to resume: {e}"


# ─── Unified interface ───────────────────────────────────────
def process_operation(operation: str, **kwargs) -> str:
    """Unified process management interface."""
    target = kwargs.get("target", kwargs.get("name", ""))

    ops = {
        "kill": lambda: kill_process(target, kwargs.get("force", False)),
        "details": lambda: get_process_details(target),
        "hogs": lambda: resource_hogs(kwargs.get("sort_by", "memory"), int(kwargs.get("top", 15))),
        "priority": lambda: set_process_priority(target, kwargs.get("priority", "normal")),
        "port": lambda: find_process_by_port(int(kwargs.get("port", 0))),
        "tree": lambda: process_tree(int(kwargs.get("pid", 0))),
        "suspend": lambda: suspend_process(target),
        "resume": lambda: resume_process(target),
    }

    handler = ops.get(operation)
    if handler:
        return handler()
    return f"Unknown process operation: {operation}. Available: {', '.join(ops.keys())}"
