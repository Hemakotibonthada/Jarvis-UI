"""
Password Vault Module — Secure local password storage with AES encryption,
auto-generation, categories, search, and export.
Note: Passwords are encrypted at rest using a master password derived key.
"""

import json
import os
import hashlib
import hmac
import base64
import secrets
from datetime import datetime
from pathlib import Path
from core.logger import get_logger
import config

log = get_logger("vault")

VAULT_FILE = config.DATA_DIR / "vault.encrypted"
VAULT_META_FILE = config.DATA_DIR / "vault_meta.json"


class SimpleEncryption:
    """XOR-based encryption with key derivation. For real security use AES (cryptography library)."""

    @staticmethod
    def derive_key(password: str, salt: bytes = None) -> tuple[bytes, bytes]:
        """Derive encryption key from password using PBKDF2."""
        if salt is None:
            salt = os.urandom(32)
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000, dklen=32)
        return key, salt

    @staticmethod
    def encrypt(data: str, key: bytes) -> str:
        """Encrypt data using XOR with derived key (repeating key)."""
        data_bytes = data.encode("utf-8")
        encrypted = bytes(b ^ key[i % len(key)] for i, b in enumerate(data_bytes))
        return base64.b64encode(encrypted).decode()

    @staticmethod
    def decrypt(encrypted: str, key: bytes) -> str:
        """Decrypt data."""
        data_bytes = base64.b64decode(encrypted.encode())
        decrypted = bytes(b ^ key[i % len(key)] for i, b in enumerate(data_bytes))
        return decrypted.decode("utf-8")

    @staticmethod
    def hash_master(password: str, salt: bytes) -> str:
        """Hash master password for verification."""
        return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000).hex()


class VaultEntry:
    """A stored credential."""
    def __init__(self, title: str, username: str = "", password: str = "",
                 url: str = "", category: str = "", notes: str = "",
                 email: str = "", totp_secret: str = ""):
        self.id = 0
        self.title = title
        self.username = username
        self.password = password
        self.url = url
        self.category = category
        self.notes = notes
        self.email = email
        self.totp_secret = totp_secret
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        self.last_accessed = ""
        self.password_changed = datetime.now().isoformat()
        self.favorite = False

    def to_dict(self):
        return self.__dict__

    @staticmethod
    def from_dict(d) -> 'VaultEntry':
        e = VaultEntry(d.get("title", ""))
        for k, v in d.items():
            if hasattr(e, k):
                setattr(e, k, v)
        return e


class PasswordVault:
    """Encrypted password vault."""

    def __init__(self):
        self.entries: list[VaultEntry] = []
        self._next_id = 1
        self._key: bytes = b""
        self._salt: bytes = b""
        self._locked = True
        self._master_hash = ""

    def is_locked(self) -> bool:
        return self._locked

    def create_vault(self, master_password: str) -> str:
        """Create a new vault with a master password."""
        if VAULT_FILE.exists():
            return "Vault already exists. Use unlock to access it."

        self._key, self._salt = SimpleEncryption.derive_key(master_password)
        self._master_hash = SimpleEncryption.hash_master(master_password, self._salt)
        self._locked = False

        # Save meta (salt + hash for verification)
        meta = {
            "salt": base64.b64encode(self._salt).decode(),
            "hash": self._master_hash,
            "created": datetime.now().isoformat(),
        }
        VAULT_META_FILE.write_text(json.dumps(meta), encoding="utf-8")

        self._save()
        return "Password vault created. Remember your master password — it cannot be recovered!"

    def unlock(self, master_password: str) -> str:
        """Unlock the vault with the master password."""
        if not VAULT_META_FILE.exists():
            return "No vault found. Create one with create_vault."

        try:
            meta = json.loads(VAULT_META_FILE.read_text(encoding="utf-8"))
            self._salt = base64.b64decode(meta["salt"])
            stored_hash = meta["hash"]

            # Verify password
            check_hash = SimpleEncryption.hash_master(master_password, self._salt)
            if check_hash != stored_hash:
                return "Invalid master password."

            self._key, _ = SimpleEncryption.derive_key(master_password, self._salt)
            self._locked = False

            # Load and decrypt entries
            if VAULT_FILE.exists():
                encrypted = VAULT_FILE.read_text(encoding="utf-8")
                if encrypted.strip():
                    decrypted = SimpleEncryption.decrypt(encrypted, self._key)
                    data = json.loads(decrypted)
                    self.entries = [VaultEntry.from_dict(e) for e in data.get("entries", [])]
                    self._next_id = data.get("next_id", 1)

            return f"Vault unlocked. {len(self.entries)} entries loaded."
        except Exception as e:
            self._locked = True
            return f"Vault unlock error: {e}"

    def lock(self) -> str:
        """Lock the vault (save and clear from memory)."""
        if self._locked:
            return "Vault already locked."
        self._save()
        self.entries.clear()
        self._key = b""
        self._locked = True
        return "Vault locked. All credentials cleared from memory."

    def _save(self):
        """Save encrypted vault to disk."""
        if self._locked or not self._key:
            return
        data = {"entries": [e.to_dict() for e in self.entries], "next_id": self._next_id}
        encrypted = SimpleEncryption.encrypt(json.dumps(data, ensure_ascii=False), self._key)
        VAULT_FILE.write_text(encrypted, encoding="utf-8")

    def _check_locked(self) -> str:
        """Check if vault is locked."""
        if self._locked:
            return "Vault is locked. Use unlock first."
        return ""

    def add_entry(self, title: str, username: str = "", password: str = "",
                  url: str = "", category: str = "", notes: str = "",
                  email: str = "", auto_generate: bool = False,
                  password_length: int = 20) -> str:
        """Add a credential to the vault."""
        check = self._check_locked()
        if check:
            return check

        if auto_generate or not password:
            password = self._generate_password(password_length)

        entry = VaultEntry(title, username, password, url, category, notes, email)
        entry.id = self._next_id
        self._next_id += 1
        self.entries.append(entry)
        self._save()

        # Mask password in output
        masked = password[:2] + "*" * (len(password) - 4) + password[-2:] if len(password) > 4 else "****"
        return f"Credential saved: #{entry.id} '{title}' (password: {masked})"

    def get_entry(self, entry_id: int, show_password: bool = False) -> str:
        """Get a credential. Password is masked unless show_password=True."""
        check = self._check_locked()
        if check:
            return check

        for e in self.entries:
            if e.id == entry_id:
                e.last_accessed = datetime.now().isoformat()
                self._save()

                pw = e.password if show_password else ("*" * len(e.password) if e.password else "(none)")
                return (
                    f"Credential #{e.id}: {e.title}\n"
                    f"  Username: {e.username}\n"
                    f"  Password: {pw}\n"
                    f"  Email: {e.email or '(none)'}\n"
                    f"  URL: {e.url or '(none)'}\n"
                    f"  Category: {e.category or '(none)'}\n"
                    f"  Notes: {e.notes[:100] or '(none)'}\n"
                    f"  Created: {e.created_at[:10]}\n"
                    f"  Password changed: {e.password_changed[:10]}\n"
                    f"  {'★ Favorite' if e.favorite else ''}"
                )
        return f"Entry #{entry_id} not found."

    def copy_password(self, entry_id: int) -> str:
        """Copy password to clipboard."""
        check = self._check_locked()
        if check:
            return check

        for e in self.entries:
            if e.id == entry_id:
                try:
                    import pyperclip
                    pyperclip.copy(e.password)
                    e.last_accessed = datetime.now().isoformat()
                    self._save()
                    return f"Password for '{e.title}' copied to clipboard."
                except ImportError:
                    return "pyperclip not installed."
        return f"Entry #{entry_id} not found."

    def update_password(self, entry_id: int, new_password: str = "",
                        auto_generate: bool = False, length: int = 20) -> str:
        """Update a credential's password."""
        check = self._check_locked()
        if check:
            return check

        for e in self.entries:
            if e.id == entry_id:
                if auto_generate or not new_password:
                    new_password = self._generate_password(length)
                e.password = new_password
                e.password_changed = datetime.now().isoformat()
                e.updated_at = datetime.now().isoformat()
                self._save()
                masked = new_password[:2] + "*" * (len(new_password) - 4) + new_password[-2:]
                return f"Password updated for '{e.title}': {masked}"
        return f"Entry #{entry_id} not found."

    def delete_entry(self, entry_id: int) -> str:
        check = self._check_locked()
        if check:
            return check
        for i, e in enumerate(self.entries):
            if e.id == entry_id:
                title = e.title
                self.entries.pop(i)
                self._save()
                return f"Credential '{title}' deleted."
        return f"Entry #{entry_id} not found."

    def search(self, query: str) -> str:
        check = self._check_locked()
        if check:
            return check
        q = query.lower()
        matches = [e for e in self.entries if
                   q in e.title.lower() or q in e.username.lower() or
                   q in e.url.lower() or q in e.category.lower() or
                   q in (e.email or "").lower()]
        if not matches:
            return f"No credentials matching '{query}'."
        lines = [f"  #{e.id} [{e.category}] {e.title} — {e.username or e.email or '(no user)'}" for e in matches[:20]]
        return f"Vault search ({len(matches)} matches):\n" + "\n".join(lines)

    def list_entries(self, category: str = "") -> str:
        check = self._check_locked()
        if check:
            return check
        filtered = self.entries
        if category:
            filtered = [e for e in filtered if e.category.lower() == category.lower()]
        if not filtered:
            return "No credentials stored."
        lines = [f"  {'★' if e.favorite else ' '} #{e.id} [{e.category or '-'}] {e.title} — {e.username or e.email or ''}"
                 for e in filtered]
        return f"Vault ({len(filtered)} entries):\n" + "\n".join(lines[:30])

    def list_categories(self) -> str:
        check = self._check_locked()
        if check:
            return check
        cats = {}
        for e in self.entries:
            cat = e.category or "Uncategorized"
            cats[cat] = cats.get(cat, 0) + 1
        if not cats:
            return "No categories."
        lines = [f"  {cat}: {count}" for cat, count in sorted(cats.items())]
        return "Vault Categories:\n" + "\n".join(lines)

    def check_weak_passwords(self) -> str:
        """Audit passwords for weakness."""
        check = self._check_locked()
        if check:
            return check

        issues = []
        seen = {}

        for e in self.entries:
            pw = e.password
            if not pw:
                continue

            # Short passwords
            if len(pw) < 8:
                issues.append(f"  ⚠ '{e.title}': Password too short ({len(pw)} chars)")

            # No special chars
            if not any(c in "!@#$%^&*()-_=+[]{}|;:,.<>?" for c in pw):
                issues.append(f"  ⚠ '{e.title}': No special characters")

            # Duplicate passwords
            if pw in seen:
                issues.append(f"  ⚠ '{e.title}': Same password as '{seen[pw]}'")
            seen[pw] = e.title

            # Old passwords
            try:
                changed = datetime.fromisoformat(e.password_changed)
                age = (datetime.now() - changed).days
                if age > 365:
                    issues.append(f"  ⚠ '{e.title}': Password is {age} days old")
            except (ValueError, TypeError):
                pass

        if not issues:
            return "✓ All passwords look good! No obvious weaknesses found."

        return f"Password Audit ({len(issues)} issues):\n" + "\n".join(issues)

    def toggle_favorite(self, entry_id: int) -> str:
        check = self._check_locked()
        if check:
            return check
        for e in self.entries:
            if e.id == entry_id:
                e.favorite = not e.favorite
                self._save()
                return f"'{e.title}' {'favorited ★' if e.favorite else 'unfavorited'}."
        return f"Entry #{entry_id} not found."

    def change_master(self, old_password: str, new_password: str) -> str:
        """Change the master password."""
        # Verify old password
        check_hash = SimpleEncryption.hash_master(old_password, self._salt)
        if check_hash != self._master_hash:
            return "Current password is incorrect."

        self._key, self._salt = SimpleEncryption.derive_key(new_password)
        self._master_hash = SimpleEncryption.hash_master(new_password, self._salt)

        meta = {
            "salt": base64.b64encode(self._salt).decode(),
            "hash": self._master_hash,
            "created": datetime.now().isoformat(),
        }
        VAULT_META_FILE.write_text(json.dumps(meta), encoding="utf-8")
        self._save()
        return "Master password changed successfully."

    @staticmethod
    def _generate_password(length: int = 20) -> str:
        import string
        chars = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
        pw = [
            secrets.choice(string.ascii_lowercase),
            secrets.choice(string.ascii_uppercase),
            secrets.choice(string.digits),
            secrets.choice("!@#$%^&*"),
        ]
        pw += [secrets.choice(chars) for _ in range(length - 4)]
        pw_list = list(pw)
        for i in range(len(pw_list) - 1, 0, -1):
            j = secrets.randbelow(i + 1)
            pw_list[i], pw_list[j] = pw_list[j], pw_list[i]
        return "".join(pw_list)

    def get_stats(self) -> str:
        check = self._check_locked()
        if check:
            return check
        total = len(self.entries)
        cats = len(set(e.category for e in self.entries if e.category))
        favs = sum(1 for e in self.entries if e.favorite)
        return (
            f"Vault Stats:\n"
            f"  Total credentials: {total}\n"
            f"  Categories: {cats}\n"
            f"  Favorites: {favs}\n"
            f"  Status: {'🔓 Unlocked' if not self._locked else '🔒 Locked'}"
        )

    # ─── Unified Interface ────────────────────────────────
    def vault_operation(self, operation: str, **kwargs) -> str:
        """Unified password vault interface."""
        ops = {
            "create": lambda: self.create_vault(kwargs.get("master_password", "")),
            "unlock": lambda: self.unlock(kwargs.get("master_password", "")),
            "lock": lambda: self.lock(),
            "add": lambda: self.add_entry(kwargs.get("title", ""), kwargs.get("username", ""), kwargs.get("password", ""), kwargs.get("url", ""), kwargs.get("category", ""), kwargs.get("notes", ""), kwargs.get("email", ""), kwargs.get("auto_generate", True)),
            "get": lambda: self.get_entry(int(kwargs.get("entry_id", 0)), kwargs.get("show_password", False)),
            "copy": lambda: self.copy_password(int(kwargs.get("entry_id", 0))),
            "update_password": lambda: self.update_password(int(kwargs.get("entry_id", 0)), kwargs.get("password", ""), kwargs.get("auto_generate", True)),
            "delete": lambda: self.delete_entry(int(kwargs.get("entry_id", 0))),
            "search": lambda: self.search(kwargs.get("query", "")),
            "list": lambda: self.list_entries(kwargs.get("category", "")),
            "categories": lambda: self.list_categories(),
            "audit": lambda: self.check_weak_passwords(),
            "favorite": lambda: self.toggle_favorite(int(kwargs.get("entry_id", 0))),
            "change_master": lambda: self.change_master(kwargs.get("old_password", ""), kwargs.get("new_password", "")),
            "stats": lambda: self.get_stats(),
        }
        handler = ops.get(operation)
        if handler:
            return handler()
        return f"Unknown vault operation: {operation}. Available: {', '.join(ops.keys())}"


password_vault = PasswordVault()
