"""
Contact Manager Module — Comprehensive contact management with groups,
import/export, search, and communication integration.
"""

import json
import csv
import re
from datetime import datetime, date
from pathlib import Path
from core.logger import get_logger
import config

log = get_logger("contacts")

CONTACTS_FILE = config.DATA_DIR / "contacts_v2.json"


class Contact:
    """A contact entry with comprehensive details."""
    def __init__(self, first_name: str, last_name: str = "",
                 phone: str = "", email: str = "", company: str = "",
                 job_title: str = "", address: str = "", city: str = "",
                 country: str = "", birthday: str = "", website: str = "",
                 notes: str = "", groups: str = "", social: dict = None):
        self.id = 0
        self.first_name = first_name
        self.last_name = last_name
        self.phone = phone
        self.email = email
        self.company = company
        self.job_title = job_title
        self.address = address
        self.city = city
        self.country = country
        self.birthday = birthday  # YYYY-MM-DD
        self.website = website
        self.notes = notes
        self.groups = groups  # Comma-separated group names
        self.social = social or {}  # {twitter: ..., linkedin: ..., github: ...}
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        self.favorite = False
        self.last_contacted = ""

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def to_dict(self):
        return self.__dict__

    @staticmethod
    def from_dict(d) -> 'Contact':
        c = Contact(d.get("first_name", ""), d.get("last_name", ""))
        for k, v in d.items():
            if hasattr(c, k):
                setattr(c, k, v)
        return c

    def format_display(self) -> str:
        lines = [f"  {'★ ' if self.favorite else ''}#{self.id} {self.full_name}"]
        if self.company:
            lines.append(f"    Company: {self.company}" + (f" — {self.job_title}" if self.job_title else ""))
        if self.phone:
            lines.append(f"    Phone: {self.phone}")
        if self.email:
            lines.append(f"    Email: {self.email}")
        if self.address or self.city:
            loc_parts = [p for p in [self.address, self.city, self.country] if p]
            lines.append(f"    Location: {', '.join(loc_parts)}")
        if self.birthday:
            lines.append(f"    Birthday: {self.birthday}")
            try:
                bday = datetime.strptime(self.birthday, "%Y-%m-%d")
                today = date.today()
                next_bday = bday.replace(year=today.year).date()
                if next_bday < today:
                    next_bday = bday.replace(year=today.year + 1).date()
                days_until = (next_bday - today).days
                if days_until == 0:
                    lines.append(f"    🎂 BIRTHDAY TODAY!")
                elif days_until <= 7:
                    lines.append(f"    🎂 Birthday in {days_until} days!")
            except ValueError:
                pass
        if self.groups:
            lines.append(f"    Groups: {self.groups}")
        if self.website:
            lines.append(f"    Web: {self.website}")
        if self.social:
            social_str = ", ".join(f"{k}: {v}" for k, v in self.social.items() if v)
            if social_str:
                lines.append(f"    Social: {social_str}")
        if self.notes:
            lines.append(f"    Notes: {self.notes[:100]}")
        return "\n".join(lines)


class ContactManager:
    """Comprehensive contact management."""

    def __init__(self):
        self.contacts: list[Contact] = []
        self._next_id = 1
        self._load()

    def _load(self):
        if CONTACTS_FILE.exists():
            try:
                data = json.loads(CONTACTS_FILE.read_text(encoding="utf-8"))
                self.contacts = [Contact.from_dict(c) for c in data.get("contacts", [])]
                self._next_id = data.get("next_id", 1)
            except (json.JSONDecodeError, OSError):
                pass

    def _save(self):
        data = {"contacts": [c.to_dict() for c in self.contacts], "next_id": self._next_id}
        CONTACTS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def add_contact(self, first_name: str, last_name: str = "",
                    phone: str = "", email: str = "", company: str = "",
                    job_title: str = "", notes: str = "", groups: str = "",
                    birthday: str = "", city: str = "", country: str = "") -> str:
        """Add a new contact."""
        contact = Contact(first_name, last_name, phone, email, company,
                         job_title, "", city, country, birthday, "", notes, groups)
        contact.id = self._next_id
        self._next_id += 1
        self.contacts.append(contact)
        self._save()
        return f"Contact added: #{contact.id} {contact.full_name}" + (f" ({company})" if company else "")

    def get_contact(self, contact_id: int) -> str:
        for c in self.contacts:
            if c.id == contact_id:
                return c.format_display()
        return f"Contact #{contact_id} not found."

    def update_contact(self, contact_id: int, **kwargs) -> str:
        for c in self.contacts:
            if c.id == contact_id:
                for k, v in kwargs.items():
                    if hasattr(c, k) and v:
                        setattr(c, k, v)
                c.updated_at = datetime.now().isoformat()
                self._save()
                return f"Contact #{contact_id} updated."
        return f"Contact #{contact_id} not found."

    def delete_contact(self, contact_id: int) -> str:
        for i, c in enumerate(self.contacts):
            if c.id == contact_id:
                name = c.full_name
                self.contacts.pop(i)
                self._save()
                return f"Contact #{contact_id} '{name}' deleted."
        return f"Contact #{contact_id} not found."

    def search(self, query: str) -> str:
        q = query.lower()
        matches = [c for c in self.contacts if
                   q in c.full_name.lower() or q in c.email.lower() or
                   q in c.phone or q in c.company.lower() or
                   q in c.notes.lower() or q in c.groups.lower()]
        if not matches:
            return f"No contacts matching '{query}'."
        lines = [c.format_display() for c in matches[:20]]
        return f"Contacts matching '{query}' ({len(matches)}):\n\n" + "\n\n".join(lines)

    def list_contacts(self, group: str = "", sort_by: str = "name") -> str:
        filtered = self.contacts
        if group:
            filtered = [c for c in filtered if group.lower() in c.groups.lower()]

        sort_opts = {
            "name": lambda c: c.full_name.lower(),
            "company": lambda c: (c.company or "zzz", c.full_name.lower()),
            "recent": lambda c: c.updated_at,
        }
        filtered.sort(key=sort_opts.get(sort_by, sort_opts["name"]),
                      reverse=(sort_by == "recent"))

        if not filtered:
            return "No contacts." if not group else f"No contacts in group '{group}'."
        lines = [c.format_display() for c in filtered[:30]]
        return f"Contacts ({len(filtered)}):\n\n" + "\n\n".join(lines)

    def list_groups(self) -> str:
        groups = {}
        for c in self.contacts:
            for g in c.groups.split(","):
                g = g.strip()
                if g:
                    groups[g] = groups.get(g, 0) + 1
        if not groups:
            return "No groups."
        lines = [f"  {g}: {count} contacts" for g, count in sorted(groups.items())]
        return "Contact Groups:\n" + "\n".join(lines)

    def toggle_favorite(self, contact_id: int) -> str:
        for c in self.contacts:
            if c.id == contact_id:
                c.favorite = not c.favorite
                self._save()
                return f"Contact #{contact_id} {'favorited ★' if c.favorite else 'unfavorited'}."
        return f"Contact #{contact_id} not found."

    def upcoming_birthdays(self, days: int = 30) -> str:
        today = date.today()
        upcoming = []
        for c in self.contacts:
            if not c.birthday:
                continue
            try:
                bday = datetime.strptime(c.birthday, "%Y-%m-%d").date()
                this_year = bday.replace(year=today.year)
                if this_year < today:
                    this_year = bday.replace(year=today.year + 1)
                diff = (this_year - today).days
                if 0 <= diff <= days:
                    upcoming.append((diff, c, this_year))
            except ValueError:
                pass

        if not upcoming:
            return f"No birthdays in the next {days} days."
        upcoming.sort()
        lines = [f"  {'🎂 TODAY!' if d == 0 else f'In {d} days'} — {c.full_name} ({bd.strftime('%b %d')})"
                 for d, c, bd in upcoming]
        return f"Upcoming Birthdays:\n" + "\n".join(lines)

    def export_csv(self, file_path: str = "") -> str:
        if not file_path:
            file_path = str(config.GENERATED_DIR / "contacts_export.csv")
        p = Path(file_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        fields = ["id", "first_name", "last_name", "phone", "email",
                  "company", "job_title", "city", "country", "birthday",
                  "groups", "notes"]
        with open(p, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for c in self.contacts:
                writer.writerow({k: getattr(c, k, "") for k in fields})
        return f"Exported {len(self.contacts)} contacts to {p}"

    def export_vcard(self, file_path: str = "") -> str:
        """Export contacts as vCard (.vcf)."""
        if not file_path:
            file_path = str(config.GENERATED_DIR / "contacts.vcf")
        p = Path(file_path)
        lines = []
        for c in self.contacts:
            lines.append("BEGIN:VCARD")
            lines.append("VERSION:3.0")
            lines.append(f"FN:{c.full_name}")
            lines.append(f"N:{c.last_name};{c.first_name};;;")
            if c.phone:
                lines.append(f"TEL:{c.phone}")
            if c.email:
                lines.append(f"EMAIL:{c.email}")
            if c.company:
                lines.append(f"ORG:{c.company}")
            if c.job_title:
                lines.append(f"TITLE:{c.job_title}")
            if c.birthday:
                lines.append(f"BDAY:{c.birthday}")
            if c.website:
                lines.append(f"URL:{c.website}")
            if c.notes:
                lines.append(f"NOTE:{c.notes[:200]}")
            lines.append("END:VCARD")
            lines.append("")
        p.write_text("\n".join(lines), encoding="utf-8")
        return f"Exported {len(self.contacts)} contacts as vCard to {p}"

    def import_csv(self, file_path: str) -> str:
        p = Path(file_path).expanduser()
        if not p.exists():
            return f"File not found: {p}"
        try:
            with open(p, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                imported = 0
                for row in reader:
                    fn = row.get("first_name", row.get("name", "")).strip()
                    if not fn:
                        continue
                    contact = Contact(
                        first_name=fn,
                        last_name=row.get("last_name", ""),
                        phone=row.get("phone", ""),
                        email=row.get("email", ""),
                        company=row.get("company", row.get("organization", "")),
                    )
                    contact.id = self._next_id
                    self._next_id += 1
                    self.contacts.append(contact)
                    imported += 1
            self._save()
            return f"Imported {imported} contacts from {p}"
        except Exception as e:
            return f"Import error: {e}"

    def get_stats(self) -> str:
        total = len(self.contacts)
        with_email = sum(1 for c in self.contacts if c.email)
        with_phone = sum(1 for c in self.contacts if c.phone)
        favorites = sum(1 for c in self.contacts if c.favorite)
        companies = len(set(c.company for c in self.contacts if c.company))
        return (
            f"Contact Stats:\n"
            f"  Total: {total}\n"
            f"  With email: {with_email}\n"
            f"  With phone: {with_phone}\n"
            f"  Favorites: {favorites}\n"
            f"  Companies: {companies}"
        )

    def contact_operation(self, operation: str, **kwargs) -> str:
        ops = {
            "add": lambda: self.add_contact(kwargs.get("first_name", ""), kwargs.get("last_name", ""), kwargs.get("phone", ""), kwargs.get("email", ""), kwargs.get("company", ""), kwargs.get("job_title", ""), kwargs.get("notes", ""), kwargs.get("groups", ""), kwargs.get("birthday", ""), kwargs.get("city", ""), kwargs.get("country", "")),
            "get": lambda: self.get_contact(int(kwargs.get("contact_id", 0))),
            "update": lambda: self.update_contact(int(kwargs.get("contact_id", 0)), **{k: v for k, v in kwargs.items() if k not in ("operation", "contact_id")}),
            "delete": lambda: self.delete_contact(int(kwargs.get("contact_id", 0))),
            "search": lambda: self.search(kwargs.get("query", "")),
            "list": lambda: self.list_contacts(kwargs.get("group", ""), kwargs.get("sort_by", "name")),
            "groups": lambda: self.list_groups(),
            "favorite": lambda: self.toggle_favorite(int(kwargs.get("contact_id", 0))),
            "birthdays": lambda: self.upcoming_birthdays(int(kwargs.get("days", 30))),
            "export_csv": lambda: self.export_csv(kwargs.get("file_path", "")),
            "export_vcard": lambda: self.export_vcard(kwargs.get("file_path", "")),
            "import_csv": lambda: self.import_csv(kwargs.get("file_path", "")),
            "stats": lambda: self.get_stats(),
        }
        handler = ops.get(operation)
        if handler:
            return handler()
        return f"Unknown contact operation: {operation}. Available: {', '.join(ops.keys())}"


contact_manager = ContactManager()
