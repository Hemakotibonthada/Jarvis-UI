"""
Security Tools Module — Password generation, encryption, hashing, vulnerability scanning,
file integrity checking, port monitoring, and security auditing.
"""

import os
import re
import json
import string
import secrets
import hashlib
import hmac
import base64
import subprocess
from datetime import datetime
from pathlib import Path
from core.logger import get_logger
import config

log = get_logger("security")


# ─── Password Generation ─────────────────────────────────────
class PasswordGenerator:
    """Cryptographically secure password generation."""

    COMMON_PASSWORDS = {
        "123456", "password", "12345678", "qwerty", "123456789",
        "12345", "1234", "111111", "1234567", "dragon", "123123",
        "baseball", "iloveu", "trustno1", "sunshine", "master",
        "welcome", "shadow", "ashley", "football", "jesus",
        "michael", "ninja", "mustang", "password1", "letmein",
    }

    @staticmethod
    def generate(length: int = 16, uppercase: bool = True, lowercase: bool = True,
                 digits: bool = True, special: bool = True,
                 exclude_ambiguous: bool = False,
                 custom_chars: str = "") -> str:
        """Generate a secure random password."""
        length = max(4, min(128, length))
        charset = ""
        required = []

        if custom_chars:
            charset = custom_chars
        else:
            if lowercase:
                chars = string.ascii_lowercase
                if exclude_ambiguous:
                    chars = chars.replace("l", "").replace("o", "")
                charset += chars
                required.append(secrets.choice(chars))
            if uppercase:
                chars = string.ascii_uppercase
                if exclude_ambiguous:
                    chars = chars.replace("I", "").replace("O", "")
                charset += chars
                required.append(secrets.choice(chars))
            if digits:
                chars = string.digits
                if exclude_ambiguous:
                    chars = chars.replace("0", "").replace("1", "")
                charset += chars
                required.append(secrets.choice(chars))
            if special:
                charset += "!@#$%^&*()-_=+[]{}|;:,.<>?"
                required.append(secrets.choice("!@#$%^&*()-_=+[]{}|;:,.<>?"))

        if not charset:
            charset = string.ascii_letters + string.digits

        # Generate password ensuring required characters are included
        remaining = length - len(required)
        password_chars = required + [secrets.choice(charset) for _ in range(remaining)]

        # Shuffle to randomize positions
        password_list = list(password_chars)
        for i in range(len(password_list) - 1, 0, -1):
            j = secrets.randbelow(i + 1)
            password_list[i], password_list[j] = password_list[j], password_list[i]

        return "".join(password_list)

    @staticmethod
    def generate_passphrase(words: int = 4, separator: str = "-",
                            capitalize: bool = True) -> str:
        """Generate a random passphrase from word list."""
        # Common English words for passphrases
        word_list = [
            "apple", "banana", "cherry", "dragon", "elephant", "falcon",
            "garden", "harbor", "island", "jungle", "kingdom", "lantern",
            "mountain", "nebula", "ocean", "phoenix", "quantum", "rainbow",
            "sunset", "thunder", "umbrella", "velvet", "whisper", "xenon",
            "yellow", "zenith", "anchor", "bridge", "castle", "diamond",
            "emerald", "forest", "glacier", "horizon", "ivory", "jasmine",
            "knight", "legend", "marble", "neutron", "oracle", "puzzle",
            "quartz", "rocket", "silver", "tiger", "unity", "voyage",
            "wizard", "crystal", "blazer", "comet", "delta", "echo",
            "flint", "gravity", "helm", "index", "joker", "karma",
            "lemon", "matrix", "nova", "opus", "prism", "quest",
            "ridge", "spark", "tempo", "ultra", "viper", "wraith",
            "axiom", "blaze", "cipher", "dusk", "ember", "flux",
            "glyph", "helix", "iron", "jade", "kite", "lotus",
            "myth", "nexus", "onyx", "pulse", "rune", "storm",
            "titan", "umbra", "vault", "wave", "xerus", "yield", "zephyr",
        ]

        chosen = [secrets.choice(word_list) for _ in range(words)]
        if capitalize:
            chosen = [w.capitalize() for w in chosen]

        # Add a random number for extra entropy
        passphrase = separator.join(chosen)
        passphrase += separator + str(secrets.randbelow(1000))

        return passphrase

    @staticmethod
    def check_strength(password: str) -> str:
        """Check password strength and provide feedback."""
        score = 0
        feedback = []

        # Length
        if len(password) >= 8:
            score += 1
        if len(password) >= 12:
            score += 1
        if len(password) >= 16:
            score += 1
        if len(password) < 8:
            feedback.append("Too short (minimum 8 characters)")

        # Character types
        has_lower = bool(re.search(r'[a-z]', password))
        has_upper = bool(re.search(r'[A-Z]', password))
        has_digit = bool(re.search(r'\d', password))
        has_special = bool(re.search(r'[!@#$%^&*()\-_=+\[\]{}|;:,.<>?]', password))

        if has_lower:
            score += 1
        else:
            feedback.append("Add lowercase letters")
        if has_upper:
            score += 1
        else:
            feedback.append("Add uppercase letters")
        if has_digit:
            score += 1
        else:
            feedback.append("Add numbers")
        if has_special:
            score += 1
        else:
            feedback.append("Add special characters")

        # Patterns to avoid
        if re.search(r'(.)\1{2,}', password):
            score -= 1
            feedback.append("Avoid repeated characters (aaa)")
        if re.search(r'(012|123|234|345|456|567|678|789|890)', password):
            score -= 1
            feedback.append("Avoid sequential numbers")
        if re.search(r'(abc|bcd|cde|def|efg|fgh|ghi)', password.lower()):
            score -= 1
            feedback.append("Avoid sequential letters")

        # Common passwords check
        if password.lower() in PasswordGenerator.COMMON_PASSWORDS:
            score = 0
            feedback = ["This is a commonly used password!"]

        # Entropy estimation
        charset_size = 0
        if has_lower:
            charset_size += 26
        if has_upper:
            charset_size += 26
        if has_digit:
            charset_size += 10
        if has_special:
            charset_size += 32

        import math
        entropy = len(password) * math.log2(max(charset_size, 1))

        # Rating
        if score >= 7:
            rating = "EXCELLENT"
        elif score >= 5:
            rating = "STRONG"
        elif score >= 3:
            rating = "MODERATE"
        elif score >= 1:
            rating = "WEAK"
        else:
            rating = "VERY WEAK"

        result = (
            f"Password Strength Analysis:\n"
            f"  Rating: {rating} (score: {score}/7)\n"
            f"  Length: {len(password)} characters\n"
            f"  Entropy: {entropy:.1f} bits\n"
            f"  Character types: "
            f"{'✓' if has_lower else '✗'} lowercase "
            f"{'✓' if has_upper else '✗'} uppercase "
            f"{'✓' if has_digit else '✗'} digits "
            f"{'✓' if has_special else '✗'} special\n"
        )

        if feedback:
            result += "  Suggestions:\n" + "\n".join(f"    • {f}" for f in feedback)
        else:
            result += "  No issues found. Password looks good!"

        # Time to crack estimation
        attempts_per_sec = 1_000_000_000  # 1 billion per second (GPU)
        total_combinations = charset_size ** len(password) if charset_size else 1
        seconds_to_crack = total_combinations / attempts_per_sec / 2  # average
        if seconds_to_crack < 1:
            crack_time = "instant"
        elif seconds_to_crack < 60:
            crack_time = f"{seconds_to_crack:.0f} seconds"
        elif seconds_to_crack < 3600:
            crack_time = f"{seconds_to_crack / 60:.0f} minutes"
        elif seconds_to_crack < 86400:
            crack_time = f"{seconds_to_crack / 3600:.0f} hours"
        elif seconds_to_crack < 31536000:
            crack_time = f"{seconds_to_crack / 86400:.0f} days"
        elif seconds_to_crack < 31536000 * 1000:
            crack_time = f"{seconds_to_crack / 31536000:.0f} years"
        else:
            crack_time = "billions of years"

        result += f"\n  Estimated crack time (GPU): {crack_time}"
        return result


# ─── Encryption / Decryption ─────────────────────────────────
class CryptoTools:
    """Encryption, decryption, and hashing utilities."""

    @staticmethod
    def hash_text(text: str, algorithm: str = "sha256") -> str:
        """Hash text with various algorithms."""
        algorithms = {
            "md5": hashlib.md5,
            "sha1": hashlib.sha1,
            "sha256": hashlib.sha256,
            "sha384": hashlib.sha384,
            "sha512": hashlib.sha512,
            "sha3_256": hashlib.sha3_256,
            "sha3_512": hashlib.sha3_512,
            "blake2b": hashlib.blake2b,
            "blake2s": hashlib.blake2s,
        }

        if algorithm == "all":
            results = []
            for name, func in algorithms.items():
                try:
                    h = func(text.encode()).hexdigest()
                    results.append(f"  {name.upper():>10}: {h}")
                except Exception:
                    pass
            return "Hash results:\n" + "\n".join(results)

        func = algorithms.get(algorithm.lower())
        if not func:
            return f"Unknown algorithm: {algorithm}. Available: {', '.join(algorithms.keys())}, all"

        h = func(text.encode()).hexdigest()
        return f"{algorithm.upper()}: {h}"

    @staticmethod
    def hash_file(file_path: str, algorithm: str = "sha256") -> str:
        """Hash a file."""
        p = Path(file_path).expanduser()
        if not p.exists():
            return f"File not found: {p}"

        algorithms = {
            "md5": hashlib.md5, "sha1": hashlib.sha1,
            "sha256": hashlib.sha256, "sha512": hashlib.sha512,
        }

        func = algorithms.get(algorithm.lower())
        if not func:
            return f"Unknown algorithm. Available: {', '.join(algorithms.keys())}"

        h = func()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)

        return (
            f"File: {p.name}\n"
            f"Size: {p.stat().st_size:,} bytes\n"
            f"{algorithm.upper()}: {h.hexdigest()}"
        )

    @staticmethod
    def encode_base64(text: str) -> str:
        """Encode text to base64."""
        encoded = base64.b64encode(text.encode()).decode()
        return f"Base64 encoded:\n{encoded}"

    @staticmethod
    def decode_base64(text: str) -> str:
        """Decode base64 text."""
        try:
            decoded = base64.b64decode(text.encode()).decode()
            return f"Base64 decoded:\n{decoded}"
        except Exception as e:
            return f"Decode error: {e}"

    @staticmethod
    def encode_url(text: str) -> str:
        """URL-encode text."""
        import urllib.parse
        return f"URL encoded: {urllib.parse.quote(text)}"

    @staticmethod
    def decode_url(text: str) -> str:
        """URL-decode text."""
        import urllib.parse
        return f"URL decoded: {urllib.parse.unquote(text)}"

    @staticmethod
    def encode_hex(text: str) -> str:
        """Encode text to hexadecimal."""
        return f"Hex: {text.encode().hex()}"

    @staticmethod
    def decode_hex(hex_str: str) -> str:
        """Decode hex to text."""
        try:
            return f"Decoded: {bytes.fromhex(hex_str).decode()}"
        except Exception as e:
            return f"Hex decode error: {e}"

    @staticmethod
    def generate_uuid() -> str:
        """Generate a UUID v4."""
        import uuid
        u = uuid.uuid4()
        return f"UUID: {u}\nURN: {u.urn}\nHex: {u.hex}\nInt: {u.int}"

    @staticmethod
    def generate_token(length: int = 32) -> str:
        """Generate a secure random token."""
        token_hex = secrets.token_hex(length)
        token_url = secrets.token_urlsafe(length)
        return (
            f"Hex token ({length * 2} chars): {token_hex}\n"
            f"URL-safe token: {token_url}"
        )

    @staticmethod
    def caesar_cipher(text: str, shift: int = 3, decrypt: bool = False) -> str:
        """Caesar cipher encode/decode (educational)."""
        if decrypt:
            shift = -shift
        result = []
        for char in text:
            if char.isalpha():
                base = ord('A') if char.isupper() else ord('a')
                result.append(chr((ord(char) - base + shift) % 26 + base))
            else:
                result.append(char)
        mode = "Decrypted" if decrypt else "Encrypted"
        return f"{mode} (shift {abs(shift)}): {''.join(result)}"

    @staticmethod
    def rot13(text: str) -> str:
        """ROT13 encode/decode."""
        import codecs
        return f"ROT13: {codecs.encode(text, 'rot_13')}"

    @staticmethod
    def hmac_sign(message: str, key: str, algorithm: str = "sha256") -> str:
        """Generate HMAC signature."""
        algos = {"sha256": hashlib.sha256, "sha1": hashlib.sha1, "sha512": hashlib.sha512}
        func = algos.get(algorithm)
        if not func:
            return f"Unknown algorithm. Available: {', '.join(algos.keys())}"
        signature = hmac.new(key.encode(), message.encode(), func).hexdigest()
        return f"HMAC-{algorithm.upper()}: {signature}"


# ─── Security Audit ──────────────────────────────────────────
class SecurityAuditor:
    """System security auditing tools."""

    @staticmethod
    def check_open_ports(host: str = "127.0.0.1") -> str:
        """Quick scan of commonly exploited ports."""
        import socket
        dangerous_ports = {
            21: ("FTP", "File transfer, often unencrypted"),
            22: ("SSH", "Secure shell — ensure key-based auth"),
            23: ("Telnet", "INSECURE — disable immediately"),
            25: ("SMTP", "Mail — check for open relay"),
            80: ("HTTP", "Web server — check for updates"),
            135: ("RPC", "Windows RPC — potential attack vector"),
            139: ("NetBIOS", "Windows file sharing — restrict access"),
            443: ("HTTPS", "Secure web — check certificate"),
            445: ("SMB", "Windows file sharing — WannaCry target"),
            1433: ("MSSQL", "Database — should not be public"),
            1434: ("MSSQL Browser", "Database — should not be public"),
            3306: ("MySQL", "Database — should not be public"),
            3389: ("RDP", "Remote desktop — use VPN"),
            5432: ("PostgreSQL", "Database — should not be public"),
            5900: ("VNC", "Remote desktop — often insecure"),
            6379: ("Redis", "Cache — often no auth"),
            8080: ("HTTP-Alt", "Proxy/web server"),
            27017: ("MongoDB", "Database — check auth"),
        }

        open_ports = []
        for port, (service, note) in dangerous_ports.items():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.5)
                result = sock.connect_ex((host, port))
                sock.close()
                if result == 0:
                    open_ports.append((port, service, note))
            except Exception:
                pass

        if not open_ports:
            return f"Security scan of {host}: No commonly exploited ports are open. ✓"

        lines = [f"  ⚠ Port {p:>5} ({s}) — {n}" for p, s, n in open_ports]
        return (
            f"Security Scan of {host}:\n"
            f"  Found {len(open_ports)} potentially sensitive open port(s):\n"
            + "\n".join(lines)
            + "\n\n  Recommendation: Close unused ports or restrict access via firewall."
        )

    @staticmethod
    def check_ssl_cert(hostname: str) -> str:
        """Check SSL certificate details for a hostname."""
        import ssl
        import socket
        try:
            context = ssl.create_default_context()
            with socket.create_connection((hostname, 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()

                    subject = dict(x[0] for x in cert.get("subject", []))
                    issuer = dict(x[0] for x in cert.get("issuer", []))
                    not_before = cert.get("notBefore", "")
                    not_after = cert.get("notAfter", "")
                    serial = cert.get("serialNumber", "")

                    # Check expiry
                    from datetime import datetime
                    expiry = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
                    days_left = (expiry - datetime.utcnow()).days
                    status = "✓ Valid" if days_left > 0 else "✗ EXPIRED"
                    if 0 < days_left < 30:
                        status = f"⚠ Expires in {days_left} days"

                    # SANs
                    sans = []
                    for type_val in cert.get("subjectAltName", []):
                        sans.append(type_val[1])

                    return (
                        f"SSL Certificate for {hostname}:\n"
                        f"  Status: {status}\n"
                        f"  Subject: {subject.get('commonName', '?')}\n"
                        f"  Issuer: {issuer.get('organizationName', '?')}\n"
                        f"  Valid from: {not_before}\n"
                        f"  Valid until: {not_after} ({days_left} days left)\n"
                        f"  Serial: {serial}\n"
                        f"  SANs: {', '.join(sans[:10])}\n"
                        f"  Protocol: {ssock.version()}"
                    )
        except ssl.SSLCertVerificationError as e:
            return f"SSL Error for {hostname}: Certificate verification failed — {e}"
        except Exception as e:
            return f"SSL check error for {hostname}: {e}"

    @staticmethod
    def check_firewall_status() -> str:
        """Check Windows firewall status."""
        if not config.IS_WINDOWS:
            try:
                result = subprocess.run(["ufw", "status"], capture_output=True, text=True, timeout=5)
                return f"Firewall status:\n{result.stdout}"
            except Exception:
                return "Could not check firewall status."
        try:
            result = subprocess.run(
                ["powershell", "-c",
                 "Get-NetFirewallProfile | Select-Object Name,Enabled,DefaultInboundAction,DefaultOutboundAction | Format-Table -AutoSize"],
                capture_output=True, text=True, timeout=10,
            )
            return f"Windows Firewall Status:\n{result.stdout}"
        except Exception as e:
            return f"Firewall check error: {e}"

    @staticmethod
    def check_windows_updates() -> str:
        """Check for pending Windows updates."""
        if not config.IS_WINDOWS:
            return "Windows update check only available on Windows."
        try:
            result = subprocess.run(
                ["powershell", "-c",
                 "Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 10 HotFixID,Description,InstalledOn | Format-Table -AutoSize"],
                capture_output=True, text=True, timeout=15,
            )
            return f"Recent Windows Updates:\n{result.stdout}"
        except Exception as e:
            return f"Update check error: {e}"

    @staticmethod
    def check_suspicious_connections() -> str:
        """Check for suspicious network connections."""
        try:
            import psutil
            suspicious = []
            known_safe_ports = {80, 443, 53, 8080, 8443}

            for conn in psutil.net_connections(kind="inet"):
                if conn.status == "ESTABLISHED" and conn.raddr:
                    remote_port = conn.raddr.port
                    remote_ip = conn.raddr.ip

                    # Check for unusual outbound connections
                    if remote_port not in known_safe_ports and remote_port > 1024:
                        try:
                            proc_name = psutil.Process(conn.pid).name() if conn.pid else "unknown"
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            proc_name = "unknown"

                        suspicious.append({
                            "remote": f"{remote_ip}:{remote_port}",
                            "local_port": conn.laddr.port if conn.laddr else 0,
                            "process": proc_name,
                            "pid": conn.pid,
                        })

            if not suspicious:
                return "No suspicious connections detected. ✓"

            lines = [
                f"  {s['process']:<20} PID:{s['pid']:>6} → {s['remote']}"
                for s in suspicious[:20]
            ]
            return (
                f"Potentially unusual connections ({len(suspicious)}):\n"
                + "\n".join(lines)
                + "\n\n  Note: Not all listed connections are malicious. Review individually."
            )
        except Exception as e:
            return f"Connection check error: {e}"

    @staticmethod
    def file_integrity_check(directory: str, save: bool = False) -> str:
        """Calculate hashes for all files in a directory for integrity checking."""
        p = Path(directory).expanduser()
        if not p.exists():
            return f"Directory not found: {p}"

        hashes = {}
        count = 0
        for f in p.rglob("*"):
            if f.is_file() and count < 500:
                try:
                    h = hashlib.sha256()
                    with open(f, "rb") as fh:
                        for chunk in iter(lambda: fh.read(8192), b""):
                            h.update(chunk)
                    hashes[str(f.relative_to(p))] = h.hexdigest()
                    count += 1
                except (PermissionError, OSError):
                    pass

        if save:
            output = config.DATA_DIR / "integrity_hashes.json"
            output.write_text(json.dumps(hashes, indent=2), encoding="utf-8")
            return f"Integrity hashes saved for {count} files to {output}"

        # Compare with previous if exists
        prev_file = config.DATA_DIR / "integrity_hashes.json"
        if prev_file.exists():
            try:
                prev = json.loads(prev_file.read_text(encoding="utf-8"))
                added = set(hashes.keys()) - set(prev.keys())
                removed = set(prev.keys()) - set(hashes.keys())
                modified = {k for k in hashes if k in prev and hashes[k] != prev[k]}

                if not added and not removed and not modified:
                    return f"Integrity check PASSED: {count} files unchanged. ✓"

                result = f"Integrity check — Changes detected:\n"
                if added:
                    result += f"  Added ({len(added)}):\n" + "\n".join(f"    + {f}" for f in list(added)[:10]) + "\n"
                if removed:
                    result += f"  Removed ({len(removed)}):\n" + "\n".join(f"    - {f}" for f in list(removed)[:10]) + "\n"
                if modified:
                    result += f"  Modified ({len(modified)}):\n" + "\n".join(f"    ~ {f}" for f in list(modified)[:10]) + "\n"
                return result
            except (json.JSONDecodeError, OSError):
                pass

        return f"Calculated hashes for {count} files in {p}. Run with save=True to create baseline."


# ─── Unified Interface ───────────────────────────────────────
_pw_gen = PasswordGenerator()
_crypto = CryptoTools()
_auditor = SecurityAuditor()


async def security_tool(operation: str, **kwargs) -> str:
    """Unified security tools interface."""
    ops = {
        # Password
        "generate_password": lambda: _pw_gen.generate(
            int(kwargs.get("length", 16)),
            kwargs.get("uppercase", True),
            kwargs.get("lowercase", True),
            kwargs.get("digits", True),
            kwargs.get("special", True),
        ),
        "generate_passphrase": lambda: _pw_gen.generate_passphrase(
            int(kwargs.get("words", 4)),
            kwargs.get("separator", "-"),
        ),
        "check_password": lambda: _pw_gen.check_strength(kwargs.get("password", "")),

        # Crypto
        "hash": lambda: _crypto.hash_text(kwargs.get("text", ""), kwargs.get("algorithm", "sha256")),
        "hash_file": lambda: _crypto.hash_file(kwargs.get("path", ""), kwargs.get("algorithm", "sha256")),
        "base64_encode": lambda: _crypto.encode_base64(kwargs.get("text", "")),
        "base64_decode": lambda: _crypto.decode_base64(kwargs.get("text", "")),
        "url_encode": lambda: _crypto.encode_url(kwargs.get("text", "")),
        "url_decode": lambda: _crypto.decode_url(kwargs.get("text", "")),
        "hex_encode": lambda: _crypto.encode_hex(kwargs.get("text", "")),
        "hex_decode": lambda: _crypto.decode_hex(kwargs.get("text", "")),
        "uuid": lambda: _crypto.generate_uuid(),
        "token": lambda: _crypto.generate_token(int(kwargs.get("length", 32))),
        "caesar": lambda: _crypto.caesar_cipher(kwargs.get("text", ""), int(kwargs.get("shift", 3)), kwargs.get("decrypt", False)),
        "rot13": lambda: _crypto.rot13(kwargs.get("text", "")),
        "hmac": lambda: _crypto.hmac_sign(kwargs.get("text", ""), kwargs.get("key", "secret")),

        # Audit
        "port_audit": lambda: _auditor.check_open_ports(kwargs.get("host", "127.0.0.1")),
        "ssl_check": lambda: _auditor.check_ssl_cert(kwargs.get("hostname", "")),
        "firewall": lambda: _auditor.check_firewall_status(),
        "updates": lambda: _auditor.check_windows_updates(),
        "suspicious": lambda: _auditor.check_suspicious_connections(),
        "integrity": lambda: _auditor.file_integrity_check(kwargs.get("directory", "."), kwargs.get("save", False)),
    }

    handler = ops.get(operation)
    if handler:
        return handler()
    return f"Unknown security operation: {operation}. Available: {', '.join(ops.keys())}"
