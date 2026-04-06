"""
Docker & Container Module — Manage Docker containers, images, and compose.
"""

import subprocess
import json
from core.logger import get_logger

log = get_logger("docker")


def _run_docker(args: list[str]) -> str:
    """Run a docker command."""
    try:
        result = subprocess.run(
            ["docker"] + args,
            capture_output=True, text=True, timeout=30,
        )
        output = result.stdout.strip()
        error = result.stderr.strip()
        if result.returncode != 0:
            return f"Docker error: {error or output}"
        return output or "(no output)"
    except FileNotFoundError:
        return "Docker is not installed or not in PATH."
    except subprocess.TimeoutExpired:
        return "Docker command timed out."
    except Exception as e:
        return f"Docker error: {e}"


def docker_ps(all_containers: bool = False) -> str:
    """List running containers."""
    args = ["ps", "--format", "table {{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"]
    if all_containers:
        args.insert(1, "-a")
    return _run_docker(args)


def docker_images() -> str:
    """List Docker images."""
    return _run_docker(["images", "--format", "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedSince}}"])


def docker_start(container: str) -> str:
    """Start a container."""
    return _run_docker(["start", container])


def docker_stop(container: str) -> str:
    """Stop a container."""
    return _run_docker(["stop", container])


def docker_restart(container: str) -> str:
    """Restart a container."""
    return _run_docker(["restart", container])


def docker_remove(container: str) -> str:
    """Remove a container."""
    return _run_docker(["rm", container])


def docker_logs(container: str, tail: int = 50) -> str:
    """Get container logs."""
    return _run_docker(["logs", "--tail", str(tail), container])


def docker_inspect(container: str) -> str:
    """Inspect a container."""
    result = _run_docker(["inspect", container])
    try:
        data = json.loads(result)
        if isinstance(data, list) and data:
            info = data[0]
            return (
                f"Container: {info.get('Name', '?')}\n"
                f"Image: {info.get('Config', {}).get('Image', '?')}\n"
                f"Status: {info.get('State', {}).get('Status', '?')}\n"
                f"Created: {info.get('Created', '?')[:19]}\n"
                f"IP: {info.get('NetworkSettings', {}).get('IPAddress', '?')}\n"
                f"Ports: {json.dumps(info.get('NetworkSettings', {}).get('Ports', {}), indent=2)}"
            )
    except json.JSONDecodeError:
        pass
    return result[:2000]


def docker_stats() -> str:
    """Get container resource usage."""
    return _run_docker(["stats", "--no-stream", "--format", "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"])


def docker_exec(container: str, command: str) -> str:
    """Execute a command in a running container."""
    return _run_docker(["exec", container] + command.split())


def docker_pull(image: str) -> str:
    """Pull a Docker image."""
    return _run_docker(["pull", image])


def docker_build(path: str = ".", tag: str = "") -> str:
    """Build a Docker image."""
    args = ["build", path]
    if tag:
        args = ["build", "-t", tag, path]
    return _run_docker(args)


def docker_compose_up(path: str = ".") -> str:
    """Run docker-compose up."""
    try:
        result = subprocess.run(
            ["docker", "compose", "up", "-d"],
            capture_output=True, text=True, timeout=60, cwd=path,
        )
        return result.stdout + result.stderr
    except Exception as e:
        return f"Docker Compose error: {e}"


def docker_compose_down(path: str = ".") -> str:
    """Run docker-compose down."""
    try:
        result = subprocess.run(
            ["docker", "compose", "down"],
            capture_output=True, text=True, timeout=30, cwd=path,
        )
        return result.stdout + result.stderr
    except Exception as e:
        return f"Docker Compose error: {e}"


def docker_system_info() -> str:
    """Get Docker system information."""
    info = _run_docker(["info", "--format", "{{json .}}"])
    try:
        data = json.loads(info)
        return (
            f"Docker System Info:\n"
            f"  Version: {data.get('ServerVersion', '?')}\n"
            f"  Containers: {data.get('Containers', 0)} (Running: {data.get('ContainersRunning', 0)})\n"
            f"  Images: {data.get('Images', 0)}\n"
            f"  OS: {data.get('OperatingSystem', '?')}\n"
            f"  Architecture: {data.get('Architecture', '?')}\n"
            f"  CPUs: {data.get('NCPU', '?')}\n"
            f"  Memory: {data.get('MemTotal', 0) / (1024**3):.1f} GB\n"
            f"  Storage Driver: {data.get('Driver', '?')}"
        )
    except (json.JSONDecodeError, TypeError):
        return info[:2000]


def docker_prune() -> str:
    """Clean up unused Docker resources."""
    return _run_docker(["system", "prune", "-f"])


def docker_volume_ls() -> str:
    """List Docker volumes."""
    return _run_docker(["volume", "ls"])


def docker_network_ls() -> str:
    """List Docker networks."""
    return _run_docker(["network", "ls"])


# ─── Unified interface ───────────────────────────────────────
def docker_operation(operation: str, **kwargs) -> str:
    """Unified Docker operations interface."""
    container = kwargs.get("container", "")
    image = kwargs.get("image", "")
    path = kwargs.get("path", ".")

    ops = {
        "ps": lambda: docker_ps(kwargs.get("all", False)),
        "images": lambda: docker_images(),
        "start": lambda: docker_start(container),
        "stop": lambda: docker_stop(container),
        "restart": lambda: docker_restart(container),
        "remove": lambda: docker_remove(container),
        "logs": lambda: docker_logs(container, int(kwargs.get("tail", 50))),
        "inspect": lambda: docker_inspect(container),
        "stats": lambda: docker_stats(),
        "exec": lambda: docker_exec(container, kwargs.get("command", "ls")),
        "pull": lambda: docker_pull(image),
        "build": lambda: docker_build(path, kwargs.get("tag", "")),
        "compose_up": lambda: docker_compose_up(path),
        "compose_down": lambda: docker_compose_down(path),
        "info": lambda: docker_system_info(),
        "prune": lambda: docker_prune(),
        "volumes": lambda: docker_volume_ls(),
        "networks": lambda: docker_network_ls(),
    }

    handler = ops.get(operation)
    if handler:
        return handler()
    return f"Unknown docker operation: {operation}. Available: {', '.join(ops.keys())}"
