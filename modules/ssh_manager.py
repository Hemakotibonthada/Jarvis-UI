"""
SSH Manager Module — SSH connection management, remote command execution,
and SCP file transfers.
"""

import subprocess
import json
from pathlib import Path
from datetime import datetime
from core.logger import get_logger
import config

log = get_logger("ssh")

SSH_CONFIG_FILE = config.DATA_DIR / "ssh_hosts.json"


class SSHHost:
    """Represents an SSH host configuration."""

    def __init__(self, name: str, hostname: str, username: str = "",
                 port: int = 22, key_file: str = "", description: str = ""):
        self.name = name
        self.hostname = hostname
        self.username = username or os.getlogin() if hasattr(os, 'getlogin') else "user"
        self.port = port
        self.key_file = key_file
        self.description = description
        self.last_connected = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name, "hostname": self.hostname,
            "username": self.username, "port": self.port,
            "key_file": self.key_file, "description": self.description,
            "last_connected": self.last_connected,
        }

    @staticmethod
    def from_dict(data: dict) -> 'SSHHost':
        host = SSHHost(
            name=data.get("name", ""),
            hostname=data.get("hostname", ""),
            username=data.get("username", ""),
            port=data.get("port", 22),
            key_file=data.get("key_file", ""),
            description=data.get("description", ""),
        )
        host.last_connected = data.get("last_connected", "")
        return host

    def ssh_command(self) -> list:
        """Build SSH command args."""
        cmd = ["ssh"]
        if self.port != 22:
            cmd.extend(["-p", str(self.port)])
        if self.key_file:
            cmd.extend(["-i", self.key_file])
        cmd.append(f"{self.username}@{self.hostname}")
        return cmd


import os


class SSHManager:
    """Manage SSH connections and remote operations."""

    def __init__(self):
        self.hosts: dict[str, SSHHost] = {}
        self._load()

    def _load(self):
        if SSH_CONFIG_FILE.exists():
            try:
                data = json.loads(SSH_CONFIG_FILE.read_text(encoding="utf-8"))
                for name, host_data in data.items():
                    self.hosts[name] = SSHHost.from_dict(host_data)
            except (json.JSONDecodeError, OSError):
                pass

    def _save(self):
        data = {name: host.to_dict() for name, host in self.hosts.items()}
        SSH_CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def add_host(self, name: str, hostname: str, username: str = "",
                 port: int = 22, key_file: str = "", description: str = "") -> str:
        """Register an SSH host."""
        host = SSHHost(name, hostname, username, port, key_file, description)
        self.hosts[name] = host
        self._save()
        return f"SSH host '{name}' added: {username}@{hostname}:{port}"

    def remove_host(self, name: str) -> str:
        """Remove an SSH host."""
        if name not in self.hosts:
            return f"SSH host '{name}' not found."
        del self.hosts[name]
        self._save()
        return f"SSH host '{name}' removed."

    def list_hosts(self) -> str:
        """List registered SSH hosts."""
        if not self.hosts:
            return "No SSH hosts registered."
        lines = []
        for name, host in self.hosts.items():
            last = host.last_connected[:10] if host.last_connected else "never"
            lines.append(
                f"  {name}: {host.username}@{host.hostname}:{host.port} "
                f"(last: {last}) — {host.description}"
            )
        return f"SSH Hosts ({len(self.hosts)}):\n" + "\n".join(lines)

    def execute_remote(self, host_name: str, command: str, timeout: int = 30) -> str:
        """Execute a command on a remote host via SSH."""
        host = self.hosts.get(host_name)
        if not host:
            # Try direct hostname
            host = SSHHost("direct", host_name)

        ssh_cmd = host.ssh_command() + [command]

        try:
            result = subprocess.run(
                ssh_cmd,
                capture_output=True, text=True, timeout=timeout,
            )
            host.last_connected = datetime.now().isoformat()
            if host_name in self.hosts:
                self._save()

            output = result.stdout[:3000] if result.stdout else ""
            error = result.stderr[:1000] if result.stderr else ""
            return f"SSH {host.hostname} — Exit: {result.returncode}\n{output}\n{error}".strip()
        except subprocess.TimeoutExpired:
            return f"SSH command timed out after {timeout}s."
        except FileNotFoundError:
            return "SSH client not found. Install OpenSSH."
        except Exception as e:
            return f"SSH error: {e}"

    def copy_to_remote(self, host_name: str, local_path: str,
                       remote_path: str) -> str:
        """Copy a file to a remote host via SCP."""
        host = self.hosts.get(host_name)
        if not host:
            return f"SSH host '{host_name}' not found."

        p = Path(local_path).expanduser()
        if not p.exists():
            return f"Local file not found: {p}"

        scp_cmd = ["scp"]
        if host.port != 22:
            scp_cmd.extend(["-P", str(host.port)])
        if host.key_file:
            scp_cmd.extend(["-i", host.key_file])
        if p.is_dir():
            scp_cmd.append("-r")
        scp_cmd.extend([str(p), f"{host.username}@{host.hostname}:{remote_path}"])

        try:
            result = subprocess.run(scp_cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                return f"Copied {p.name} to {host.hostname}:{remote_path}"
            return f"SCP error: {result.stderr}"
        except subprocess.TimeoutExpired:
            return "SCP timed out."
        except Exception as e:
            return f"SCP error: {e}"

    def copy_from_remote(self, host_name: str, remote_path: str,
                         local_path: str) -> str:
        """Copy a file from a remote host via SCP."""
        host = self.hosts.get(host_name)
        if not host:
            return f"SSH host '{host_name}' not found."

        scp_cmd = ["scp"]
        if host.port != 22:
            scp_cmd.extend(["-P", str(host.port)])
        if host.key_file:
            scp_cmd.extend(["-i", host.key_file])
        scp_cmd.extend([f"{host.username}@{host.hostname}:{remote_path}", local_path])

        try:
            result = subprocess.run(scp_cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                return f"Downloaded {remote_path} from {host.hostname} to {local_path}"
            return f"SCP error: {result.stderr}"
        except subprocess.TimeoutExpired:
            return "SCP timed out."
        except Exception as e:
            return f"SCP error: {e}"

    def test_connection(self, host_name: str) -> str:
        """Test SSH connection to a host."""
        return self.execute_remote(host_name, "echo 'Connection successful' && uname -a && uptime", timeout=10)

    def get_remote_info(self, host_name: str) -> str:
        """Get system info from a remote host."""
        commands = [
            "uname -a",
            "uptime",
            "free -h 2>/dev/null || echo 'free not available'",
            "df -h / 2>/dev/null || echo 'df not available'",
            "cat /etc/os-release 2>/dev/null | head -3 || echo 'OS info not available'",
        ]
        return self.execute_remote(host_name, " && echo '---' && ".join(commands))

    # ─── Unified Interface ────────────────────────────────────
    def ssh_operation(self, operation: str, **kwargs) -> str:
        """Unified SSH management."""
        name = kwargs.get("name", kwargs.get("host", ""))

        ops = {
            "add": lambda: self.add_host(
                name, kwargs.get("hostname", ""),
                kwargs.get("username", ""), int(kwargs.get("port", 22)),
                kwargs.get("key_file", ""), kwargs.get("description", ""),
            ),
            "remove": lambda: self.remove_host(name),
            "list": lambda: self.list_hosts(),
            "exec": lambda: self.execute_remote(name, kwargs.get("command", "ls")),
            "upload": lambda: self.copy_to_remote(name, kwargs.get("local_path", ""), kwargs.get("remote_path", "")),
            "download": lambda: self.copy_from_remote(name, kwargs.get("remote_path", ""), kwargs.get("local_path", "")),
            "test": lambda: self.test_connection(name),
            "info": lambda: self.get_remote_info(name),
        }
        handler = ops.get(operation)
        if handler:
            return handler()
        return f"Unknown SSH operation: {operation}. Available: {', '.join(ops.keys())}"


# ─── Singleton ────────────────────────────────────────────────
ssh_manager = SSHManager()
