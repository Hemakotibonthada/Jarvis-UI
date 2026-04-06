"""
Home Inventory Module — Track possessions, electronics, warranties,
serial numbers, and generate insurance summaries.
"""

import json
from datetime import datetime, date
from pathlib import Path
from core.logger import get_logger
import config

log = get_logger("inventory")

INVENTORY_FILE = config.DATA_DIR / "home_inventory.json"


class InventoryItem:
    """Represents a tracked possession."""

    def __init__(self, name: str, category: str = "", location: str = "",
                 purchase_date: str = "", purchase_price: float = 0,
                 serial_number: str = "", model: str = "", brand: str = "",
                 warranty_until: str = "", notes: str = "",
                 condition: str = "good", quantity: int = 1):
        self.id = 0
        self.name = name
        self.category = category
        self.location = location
        self.purchase_date = purchase_date
        self.purchase_price = purchase_price
        self.serial_number = serial_number
        self.model = model
        self.brand = brand
        self.warranty_until = warranty_until
        self.notes = notes
        self.condition = condition  # excellent, good, fair, poor
        self.quantity = quantity
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}

    @staticmethod
    def from_dict(data: dict) -> 'InventoryItem':
        item = InventoryItem(name=data.get("name", ""))
        for k, v in data.items():
            if hasattr(item, k):
                setattr(item, k, v)
        return item

    def format_display(self) -> str:
        lines = [f"  #{self.id} {self.name}"]
        if self.brand or self.model:
            lines.append(f"    Brand/Model: {self.brand} {self.model}".strip())
        if self.category:
            lines.append(f"    Category: {self.category}")
        if self.location:
            lines.append(f"    Location: {self.location}")
        if self.serial_number:
            lines.append(f"    Serial: {self.serial_number}")
        if self.purchase_price:
            lines.append(f"    Price: ${self.purchase_price:,.2f}")
        if self.purchase_date:
            lines.append(f"    Purchased: {self.purchase_date}")
        if self.warranty_until:
            try:
                warranty = datetime.strptime(self.warranty_until, "%Y-%m-%d").date()
                if warranty >= date.today():
                    days = (warranty - date.today()).days
                    lines.append(f"    Warranty: Active ({days} days remaining)")
                else:
                    lines.append(f"    Warranty: Expired ({self.warranty_until})")
            except ValueError:
                lines.append(f"    Warranty: {self.warranty_until}")
        lines.append(f"    Condition: {self.condition} | Qty: {self.quantity}")
        if self.notes:
            lines.append(f"    Notes: {self.notes[:100]}")
        return "\n".join(lines)


class InventoryManager:
    """Manage a home inventory system."""

    def __init__(self):
        self.items: list[InventoryItem] = []
        self._next_id = 1
        self._load()

    def _load(self):
        if INVENTORY_FILE.exists():
            try:
                data = json.loads(INVENTORY_FILE.read_text(encoding="utf-8"))
                self.items = [InventoryItem.from_dict(i) for i in data.get("items", [])]
                self._next_id = data.get("next_id", 1)
            except (json.JSONDecodeError, OSError):
                pass

    def _save(self):
        data = {
            "items": [i.to_dict() for i in self.items],
            "next_id": self._next_id,
        }
        INVENTORY_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def add_item(self, name: str, category: str = "", location: str = "",
                 purchase_price: float = 0, serial_number: str = "",
                 model: str = "", brand: str = "", warranty_until: str = "",
                 notes: str = "", condition: str = "good",
                 quantity: int = 1, purchase_date: str = "") -> str:
        """Add an item to inventory."""
        item = InventoryItem(
            name=name, category=category, location=location,
            purchase_date=purchase_date or datetime.now().strftime("%Y-%m-%d"),
            purchase_price=purchase_price, serial_number=serial_number,
            model=model, brand=brand, warranty_until=warranty_until,
            notes=notes, condition=condition, quantity=quantity,
        )
        item.id = self._next_id
        self._next_id += 1
        self.items.append(item)
        self._save()

        result = f"Item added: #{item.id} {name}"
        if brand:
            result += f" ({brand})"
        if purchase_price:
            result += f" — ${purchase_price:,.2f}"
        return result

    def get_item(self, item_id: int) -> str:
        """Get item details."""
        for item in self.items:
            if item.id == item_id:
                return item.format_display()
        return f"Item #{item_id} not found."

    def update_item(self, item_id: int, **kwargs) -> str:
        """Update an inventory item."""
        for item in self.items:
            if item.id == item_id:
                for k, v in kwargs.items():
                    if hasattr(item, k) and v:
                        setattr(item, k, v)
                item.updated_at = datetime.now().isoformat()
                self._save()
                return f"Item #{item_id} updated."
        return f"Item #{item_id} not found."

    def delete_item(self, item_id: int) -> str:
        """Remove an item from inventory."""
        for i, item in enumerate(self.items):
            if item.id == item_id:
                name = item.name
                self.items.pop(i)
                self._save()
                return f"Item #{item_id} '{name}' removed."
        return f"Item #{item_id} not found."

    def list_items(self, category: str = "", location: str = "",
                   sort_by: str = "name") -> str:
        """List inventory items."""
        filtered = self.items
        if category:
            filtered = [i for i in filtered if i.category.lower() == category.lower()]
        if location:
            filtered = [i for i in filtered if i.location.lower() == location.lower()]

        sort_opts = {
            "name": lambda x: x.name.lower(),
            "price": lambda x: -(x.purchase_price or 0),
            "date": lambda x: x.purchase_date or "",
            "category": lambda x: (x.category or "", x.name.lower()),
            "location": lambda x: (x.location or "", x.name.lower()),
        }
        filtered.sort(key=sort_opts.get(sort_by, sort_opts["name"]))

        if not filtered:
            return "No items in inventory." if not category else f"No items in category '{category}'."

        lines = [i.format_display() for i in filtered[:40]]
        return f"Inventory ({len(filtered)} items):\n\n" + "\n\n".join(lines)

    def search_items(self, query: str) -> str:
        """Search inventory."""
        q = query.lower()
        matches = [
            i for i in self.items
            if q in i.name.lower() or q in i.brand.lower() or
               q in i.model.lower() or q in i.notes.lower() or
               q in i.serial_number.lower()
        ]
        if not matches:
            return f"No items matching '{query}'."
        lines = [i.format_display() for i in matches[:20]]
        return f"Search results ({len(matches)}):\n\n" + "\n\n".join(lines)

    def list_categories(self) -> str:
        """List item categories with counts and values."""
        categories = {}
        for item in self.items:
            cat = item.category or "Uncategorized"
            if cat not in categories:
                categories[cat] = {"count": 0, "value": 0}
            categories[cat]["count"] += item.quantity
            categories[cat]["value"] += item.purchase_price * item.quantity

        if not categories:
            return "No categories."
        lines = [f"  {cat}: {d['count']} items (${d['value']:,.2f})" for cat, d in sorted(categories.items())]
        return "Inventory Categories:\n" + "\n".join(lines)

    def list_locations(self) -> str:
        """List storage locations with item counts."""
        locations = {}
        for item in self.items:
            loc = item.location or "Unassigned"
            locations[loc] = locations.get(loc, 0) + item.quantity

        if not locations:
            return "No locations."
        lines = [f"  {loc}: {count} items" for loc, count in sorted(locations.items())]
        return "Storage Locations:\n" + "\n".join(lines)

    def warranty_check(self) -> str:
        """Check warranty status of all items."""
        active = []
        expired = []
        expiring_soon = []

        for item in self.items:
            if not item.warranty_until:
                continue
            try:
                warranty = datetime.strptime(item.warranty_until, "%Y-%m-%d").date()
                days = (warranty - date.today()).days
                if days < 0:
                    expired.append((item, days))
                elif days <= 30:
                    expiring_soon.append((item, days))
                else:
                    active.append((item, days))
            except ValueError:
                pass

        result = "Warranty Status:\n"
        if expiring_soon:
            result += "\n  ⚠ Expiring Soon:\n"
            for item, days in expiring_soon:
                result += f"    {item.name}: {days} days left!\n"
        if active:
            result += f"\n  ✓ Active ({len(active)}):\n"
            for item, days in active[:10]:
                result += f"    {item.name}: {days} days remaining\n"
        if expired:
            result += f"\n  ✗ Expired ({len(expired)}):\n"
            for item, days in expired[:10]:
                result += f"    {item.name}: expired {abs(days)} days ago\n"

        if not active and not expired and not expiring_soon:
            result += "  No warranty information recorded."
        return result

    def total_value(self) -> str:
        """Calculate total inventory value."""
        total = sum(i.purchase_price * i.quantity for i in self.items)
        by_category = {}
        for item in self.items:
            cat = item.category or "Uncategorized"
            by_category[cat] = by_category.get(cat, 0) + item.purchase_price * item.quantity

        lines = [f"  {cat}: ${val:,.2f}" for cat, val in sorted(by_category.items(), key=lambda x: -x[1])]
        return (
            f"Total Inventory Value: ${total:,.2f}\n"
            f"  Items: {len(self.items)}\n\n"
            f"  By Category:\n" + "\n".join(lines)
        )

    def export_csv(self, file_path: str = "") -> str:
        """Export inventory to CSV."""
        import csv
        if not file_path:
            file_path = str(config.GENERATED_DIR / "inventory_export.csv")
        p = Path(file_path)
        p.parent.mkdir(parents=True, exist_ok=True)

        with open(p, "w", newline="", encoding="utf-8") as f:
            fields = ["id", "name", "brand", "model", "category", "location",
                      "serial_number", "purchase_date", "purchase_price",
                      "warranty_until", "condition", "quantity", "notes"]
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for item in self.items:
                writer.writerow({k: getattr(item, k, "") for k in fields})

        return f"Inventory exported to: {p} ({len(self.items)} items)"

    # ─── Unified Interface ────────────────────────────────────
    def inventory_operation(self, operation: str, **kwargs) -> str:
        """Unified inventory management."""
        ops = {
            "add": lambda: self.add_item(
                kwargs.get("name", ""), kwargs.get("category", ""),
                kwargs.get("location", ""), float(kwargs.get("price", 0)),
                kwargs.get("serial", ""), kwargs.get("model", ""),
                kwargs.get("brand", ""), kwargs.get("warranty", ""),
                kwargs.get("notes", ""), kwargs.get("condition", "good"),
                int(kwargs.get("quantity", 1)),
            ),
            "get": lambda: self.get_item(int(kwargs.get("item_id", 0))),
            "update": lambda: self.update_item(int(kwargs.get("item_id", 0)), **{k: v for k, v in kwargs.items() if k not in ("operation", "item_id")}),
            "delete": lambda: self.delete_item(int(kwargs.get("item_id", 0))),
            "list": lambda: self.list_items(kwargs.get("category", ""), kwargs.get("location", ""), kwargs.get("sort_by", "name")),
            "search": lambda: self.search_items(kwargs.get("query", "")),
            "categories": lambda: self.list_categories(),
            "locations": lambda: self.list_locations(),
            "warranty": lambda: self.warranty_check(),
            "value": lambda: self.total_value(),
            "export": lambda: self.export_csv(kwargs.get("file_path", "")),
        }
        handler = ops.get(operation)
        if handler:
            return handler()
        return f"Unknown inventory operation: {operation}. Available: {', '.join(ops.keys())}"


# ─── Singleton ────────────────────────────────────────────────
inventory_manager = InventoryManager()
