"""
Advanced Network Tools — Port scanning, bandwidth monitoring, DNS, traceroute.
"""

import asyncio
import socket
import subprocess
import time
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from core.logger import get_logger
import config

log = get_logger("network")


# ─── Port Scanner ────────────────────────────────────────────
def scan_port(host: str, port: int, timeout: float = 1.0) -> bool:
    """Check if a port is open."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def port_scan(host: str, start_port: int = 1, end_port: int = 1024,
              timeout: float = 0.5) -> str:
    """Scan a range of ports on a host."""
    # Limit range for safety
    end_port = min(end_port, 65535)
    start_port = max(start_port, 1)
    if end_port - start_port > 5000:
        end_port = start_port + 5000

    open_ports = []
    common_services = {
        21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
        80: "HTTP", 110: "POP3", 143: "IMAP", 443: "HTTPS", 445: "SMB",
        993: "IMAPS", 995: "POP3S", 3306: "MySQL", 3389: "RDP",
        5432: "PostgreSQL", 5900: "VNC", 6379: "Redis", 8080: "HTTP-Alt",
        8443: "HTTPS-Alt", 27017: "MongoDB",
    }

    log.info(f"Scanning {host} ports {start_port}-{end_port}")

    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = {}
        for port in range(start_port, end_port + 1):
            futures[port] = executor.submit(scan_port, host, port, timeout)

        for port, future in futures.items():
            if future.result():
                service = common_services.get(port, "Unknown")
                open_ports.append((port, service))

    if not open_ports:
        return f"No open ports found on {host} ({start_port}-{end_port})."

    open_ports.sort()
    lines = [f"  Port {p:>5} — {s}" for p, s in open_ports]
    return f"Open ports on {host} ({len(open_ports)} found):\n" + "\n".join(lines)


def quick_scan(host: str) -> str:
    """Quick scan of common ports."""
    common = [21, 22, 23, 25, 53, 80, 110, 143, 443, 445, 993, 995,
              3306, 3389, 5432, 5900, 6379, 8080, 8443, 27017]
    return port_scan(host, common[0], common[-1])


# ─── DNS Lookup ───────────────────────────────────────────────
def dns_lookup(hostname: str) -> str:
    """Perform DNS lookup for a hostname."""
    try:
        results = []

        # A record (IPv4)
        try:
            ips = socket.getaddrinfo(hostname, None, socket.AF_INET)
            ipv4s = list(set(ip[4][0] for ip in ips))
            results.append(f"  A (IPv4): {', '.join(ipv4s)}")
        except socket.gaierror:
            results.append("  A (IPv4): Not found")

        # AAAA record (IPv6)
        try:
            ips6 = socket.getaddrinfo(hostname, None, socket.AF_INET6)
            ipv6s = list(set(ip[4][0] for ip in ips6))[:3]
            results.append(f"  AAAA (IPv6): {', '.join(ipv6s)}")
        except socket.gaierror:
            results.append("  AAAA (IPv6): Not found")

        # Reverse lookup
        try:
            first_ip = socket.gethostbyname(hostname)
            reverse = socket.gethostbyaddr(first_ip)
            results.append(f"  Reverse: {reverse[0]}")
        except (socket.herror, socket.gaierror):
            pass

        # nslookup for more detail
        try:
            ns_result = subprocess.run(
                ["nslookup", hostname],
                capture_output=True, text=True, timeout=10,
            )
            # Extract relevant lines
            for line in ns_result.stdout.split("\n"):
                if "server" in line.lower() or "address" in line.lower():
                    results.append(f"  {line.strip()}")
        except Exception:
            pass

        return f"DNS Lookup for {hostname}:\n" + "\n".join(results)
    except Exception as e:
        return f"DNS lookup error: {e}"


# ─── Traceroute ───────────────────────────────────────────────
def traceroute(host: str) -> str:
    """Run traceroute to a host."""
    try:
        if config.IS_WINDOWS:
            cmd = ["tracert", "-d", "-w", "2000", "-h", "20", host]
        else:
            cmd = ["traceroute", "-n", "-m", "20", "-w", "2", host]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return result.stdout or result.stderr or "Traceroute produced no output."
    except subprocess.TimeoutExpired:
        return "Traceroute timed out."
    except FileNotFoundError:
        return "Traceroute command not found."
    except Exception as e:
        return f"Traceroute error: {e}"


# ─── IP Info ──────────────────────────────────────────────────
async def ip_info(ip: str = "") -> str:
    """Get geolocation and info for an IP address."""
    import aiohttp
    try:
        url = f"http://ip-api.com/json/{ip}" if ip else "http://ip-api.com/json/"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return (
                        f"IP Information:\n"
                        f"  IP: {data.get('query', '?')}\n"
                        f"  ISP: {data.get('isp', '?')}\n"
                        f"  Organization: {data.get('org', '?')}\n"
                        f"  City: {data.get('city', '?')}\n"
                        f"  Region: {data.get('regionName', '?')}\n"
                        f"  Country: {data.get('country', '?')}\n"
                        f"  Timezone: {data.get('timezone', '?')}\n"
                        f"  Location: {data.get('lat', '?')}, {data.get('lon', '?')}"
                    )
                return f"IP info error: status {resp.status}"
    except Exception as e:
        return f"IP info error: {e}"


# ─── Bandwidth Test ───────────────────────────────────────────
async def bandwidth_test() -> str:
    """Simple bandwidth estimation by downloading a test file."""
    import aiohttp
    test_urls = [
        ("1MB", "https://speed.cloudflare.com/__down?bytes=1000000"),
        ("5MB", "https://speed.cloudflare.com/__down?bytes=5000000"),
    ]

    results = []
    for label, url in test_urls:
        try:
            start = time.time()
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    data = await resp.read()
                    elapsed = time.time() - start
                    size_mb = len(data) / (1024 * 1024)
                    speed_mbps = (size_mb * 8) / elapsed
                    results.append(f"  {label}: {speed_mbps:.1f} Mbps ({elapsed:.2f}s)")
        except Exception as e:
            results.append(f"  {label}: Failed ({e})")

    return "Bandwidth Test:\n" + "\n".join(results)


# ─── ARP Table ────────────────────────────────────────────────
def arp_table() -> str:
    """Get the ARP table (devices on local network)."""
    try:
        result = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=10)
        return f"ARP Table:\n{result.stdout}" if result.stdout else "No ARP entries found."
    except Exception as e:
        return f"ARP table error: {e}"


# ─── Whois Lookup ─────────────────────────────────────────────
async def whois_lookup(domain: str) -> str:
    """Perform a simple WHOIS lookup."""
    try:
        if config.IS_WINDOWS:
            # Try PowerShell approach
            result = subprocess.run(
                ["powershell", "-c", f"Resolve-DnsName {domain} | Format-List"],
                capture_output=True, text=True, timeout=15,
            )
            return result.stdout or f"No WHOIS data for {domain}."
        else:
            result = subprocess.run(["whois", domain], capture_output=True, text=True, timeout=15)
            return result.stdout[:3000] or f"No WHOIS data for {domain}."
    except FileNotFoundError:
        return "whois command not available."
    except Exception as e:
        return f"WHOIS error: {e}"


# ─── Network Speed Monitor ───────────────────────────────────
def network_usage() -> str:
    """Get current network I/O statistics."""
    import psutil
    counters = psutil.net_io_counters()
    per_nic = psutil.net_io_counters(pernic=True)

    lines = [
        f"  Total Sent: {counters.bytes_sent / (1024**2):.1f} MB",
        f"  Total Received: {counters.bytes_recv / (1024**2):.1f} MB",
        f"  Packets Sent: {counters.packets_sent:,}",
        f"  Packets Received: {counters.packets_recv:,}",
        f"  Errors In: {counters.errin}",
        f"  Errors Out: {counters.errout}",
        "",
        "  Per Interface:",
    ]

    for name, nic in per_nic.items():
        if nic.bytes_sent == 0 and nic.bytes_recv == 0:
            continue
        lines.append(
            f"    {name}: ↑{nic.bytes_sent / (1024**2):.1f}MB ↓{nic.bytes_recv / (1024**2):.1f}MB"
        )

    return "Network Usage:\n" + "\n".join(lines)


# ─── Connection List ──────────────────────────────────────────
def active_connections() -> str:
    """List active network connections."""
    import psutil
    connections = psutil.net_connections(kind="inet")
    lines = []
    for conn in connections[:50]:
        status = conn.status
        local = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "N/A"
        remote = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "N/A"
        pid = conn.pid or "N/A"
        # Get process name
        try:
            proc_name = psutil.Process(conn.pid).name() if conn.pid else "N/A"
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            proc_name = "N/A"
        lines.append(f"  {status:<12} {local:<22} → {remote:<22} PID:{pid} ({proc_name})")

    if not lines:
        return "No active network connections."
    return f"Active connections ({len(lines)}):\n" + "\n".join(lines)


# ─── Unified Network Tool ────────────────────────────────────
async def network_tool(operation: str, **kwargs) -> str:
    """Unified network tools interface."""
    target = kwargs.get("target", kwargs.get("host", ""))

    if operation == "port_scan":
        return port_scan(target, int(kwargs.get("start_port", 1)), int(kwargs.get("end_port", 1024)))
    elif operation == "quick_scan":
        return quick_scan(target)
    elif operation == "dns":
        return dns_lookup(target)
    elif operation == "traceroute":
        return traceroute(target)
    elif operation == "ip_info":
        return await ip_info(target)
    elif operation == "bandwidth":
        return await bandwidth_test()
    elif operation == "arp":
        return arp_table()
    elif operation == "whois":
        return await whois_lookup(target)
    elif operation == "usage":
        return network_usage()
    elif operation == "connections":
        return active_connections()
    else:
        return (
            f"Unknown network operation: {operation}. Available: "
            "port_scan, quick_scan, dns, traceroute, ip_info, bandwidth, arp, whois, usage, connections"
        )
