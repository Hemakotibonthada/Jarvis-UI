"""
Expense Tracker Module — Personal finance tracking with categories,
budgets, reports, and spending analysis.
"""

import json
import csv
from datetime import datetime, timedelta, date
from pathlib import Path
from collections import defaultdict
from core.logger import get_logger
import config

log = get_logger("expenses")

EXPENSES_FILE = config.DATA_DIR / "expenses.json"


class Expense:
    """A single expense/income entry."""
    def __init__(self, amount: float, description: str, category: str = "",
                 expense_type: str = "expense", payment_method: str = "",
                 tags: str = "", notes: str = "", recurring: str = ""):
        self.id = 0
        self.amount = abs(amount)
        self.description = description
        self.category = category
        self.expense_type = expense_type  # expense, income
        self.payment_method = payment_method  # cash, card, bank, etc.
        self.tags = tags
        self.notes = notes
        self.recurring = recurring  # none, daily, weekly, monthly, yearly
        self.date = datetime.now().strftime("%Y-%m-%d")
        self.time = datetime.now().strftime("%H:%M")
        self.created_at = datetime.now().isoformat()

    def to_dict(self):
        return self.__dict__

    @staticmethod
    def from_dict(d) -> 'Expense':
        e = Expense(d.get("amount", 0), d.get("description", ""))
        for k, v in d.items():
            if hasattr(e, k):
                setattr(e, k, v)
        return e


class Budget:
    """A monthly budget for a category."""
    def __init__(self, category: str, monthly_limit: float):
        self.category = category
        self.monthly_limit = monthly_limit
        self.created_at = datetime.now().isoformat()

    def to_dict(self):
        return self.__dict__

    @staticmethod
    def from_dict(d) -> 'Budget':
        return Budget(d.get("category", ""), d.get("monthly_limit", 0))


class ExpenseTracker:
    """Personal expense and income tracking."""

    def __init__(self):
        self.expenses: list[Expense] = []
        self.budgets: list[Budget] = []
        self._next_id = 1
        self._load()

    def _load(self):
        if EXPENSES_FILE.exists():
            try:
                data = json.loads(EXPENSES_FILE.read_text(encoding="utf-8"))
                self.expenses = [Expense.from_dict(e) for e in data.get("expenses", [])]
                self.budgets = [Budget.from_dict(b) for b in data.get("budgets", [])]
                self._next_id = data.get("next_id", 1)
            except (json.JSONDecodeError, OSError):
                pass

    def _save(self):
        data = {
            "expenses": [e.to_dict() for e in self.expenses],
            "budgets": [b.to_dict() for b in self.budgets],
            "next_id": self._next_id,
        }
        EXPENSES_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def add_expense(self, amount: float, description: str, category: str = "",
                    payment_method: str = "", tags: str = "",
                    expense_date: str = "", notes: str = "") -> str:
        """Add an expense."""
        exp = Expense(amount, description, category, "expense", payment_method, tags, notes)
        if expense_date:
            exp.date = expense_date
        exp.id = self._next_id
        self._next_id += 1
        self.expenses.append(exp)
        self._save()

        # Check budget
        budget_warn = ""
        if category:
            spent = self._month_spent(category)
            budget = self._get_budget(category)
            if budget and spent > budget.monthly_limit:
                budget_warn = f"\n  ⚠ Over budget! {category}: ${spent:.2f}/${budget.monthly_limit:.2f}"
            elif budget and spent > budget.monthly_limit * 0.8:
                budget_warn = f"\n  ⚠ Nearing budget limit! {category}: ${spent:.2f}/${budget.monthly_limit:.2f}"

        return f"Expense added: #{exp.id} ${amount:.2f} — {description}" + (f" [{category}]" if category else "") + budget_warn

    def add_income(self, amount: float, description: str, category: str = "income",
                   notes: str = "", income_date: str = "") -> str:
        """Add income."""
        inc = Expense(amount, description, category, "income", "", "", notes)
        if income_date:
            inc.date = income_date
        inc.id = self._next_id
        self._next_id += 1
        self.expenses.append(inc)
        self._save()
        return f"Income added: #{inc.id} +${amount:.2f} — {description}"

    def delete_entry(self, entry_id: int) -> str:
        for i, e in enumerate(self.expenses):
            if e.id == entry_id:
                self.expenses.pop(i)
                self._save()
                return f"Entry #{entry_id} deleted."
        return f"Entry #{entry_id} not found."

    def _month_spent(self, category: str = "", month: str = "") -> float:
        if not month:
            month = datetime.now().strftime("%Y-%m")
        return sum(
            e.amount for e in self.expenses
            if e.expense_type == "expense" and e.date.startswith(month)
            and (not category or e.category.lower() == category.lower())
        )

    def _get_budget(self, category: str) -> Budget | None:
        for b in self.budgets:
            if b.category.lower() == category.lower():
                return b
        return None

    def today_summary(self) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        todays = [e for e in self.expenses if e.date == today]
        expenses = [e for e in todays if e.expense_type == "expense"]
        income = [e for e in todays if e.expense_type == "income"]

        total_out = sum(e.amount for e in expenses)
        total_in = sum(e.amount for e in income)

        lines = [f"Today's Finances ({today}):", ""]
        if expenses:
            lines.append(f"  Expenses ({len(expenses)}):")
            for e in expenses:
                lines.append(f"    #{e.id} ${e.amount:.2f} — {e.description} [{e.category}]")
        if income:
            lines.append(f"  Income ({len(income)}):")
            for e in income:
                lines.append(f"    #{e.id} +${e.amount:.2f} — {e.description}")

        lines.append(f"\n  Total spent: ${total_out:.2f}")
        lines.append(f"  Total income: ${total_in:.2f}")
        lines.append(f"  Net: ${total_in - total_out:+.2f}")
        return "\n".join(lines)

    def month_summary(self, month: str = "") -> str:
        if not month:
            month = datetime.now().strftime("%Y-%m")

        month_entries = [e for e in self.expenses if e.date.startswith(month)]
        expenses = [e for e in month_entries if e.expense_type == "expense"]
        income = [e for e in month_entries if e.expense_type == "income"]

        total_out = sum(e.amount for e in expenses)
        total_in = sum(e.amount for e in income)

        # By category
        categories = defaultdict(float)
        for e in expenses:
            categories[e.category or "Uncategorized"] += e.amount

        lines = [f"Monthly Summary: {month}", ""]
        lines.append(f"  Total expenses: ${total_out:.2f} ({len(expenses)} entries)")
        lines.append(f"  Total income: ${total_in:.2f} ({len(income)} entries)")
        lines.append(f"  Net: ${total_in - total_out:+.2f}")

        if categories:
            lines.append(f"\n  By Category:")
            for cat, amt in sorted(categories.items(), key=lambda x: -x[1]):
                pct = (amt / total_out * 100) if total_out else 0
                budget = self._get_budget(cat)
                budget_str = f" / ${budget.monthly_limit:.0f}" if budget else ""
                bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
                lines.append(f"    {cat:<15} ${amt:>8.2f}{budget_str} [{bar}] {pct:.0f}%")

        return "\n".join(lines)

    def set_budget(self, category: str, monthly_limit: float) -> str:
        """Set a monthly budget for a category."""
        for b in self.budgets:
            if b.category.lower() == category.lower():
                b.monthly_limit = monthly_limit
                self._save()
                return f"Budget updated: {category} = ${monthly_limit:.2f}/month"

        self.budgets.append(Budget(category, monthly_limit))
        self._save()
        return f"Budget set: {category} = ${monthly_limit:.2f}/month"

    def budget_status(self) -> str:
        """Check all budget statuses for current month."""
        if not self.budgets:
            return "No budgets set. Use set_budget to create one."

        month = datetime.now().strftime("%Y-%m")
        lines = [f"Budget Status ({month}):\n"]

        for budget in self.budgets:
            spent = self._month_spent(budget.category, month)
            remaining = budget.monthly_limit - spent
            pct = (spent / budget.monthly_limit * 100) if budget.monthly_limit else 0

            if pct >= 100:
                status = "🔴 OVER"
            elif pct >= 80:
                status = "🟡 WARN"
            else:
                status = "🟢 OK"

            bar = "█" * int(min(pct, 100) / 5) + "░" * (20 - int(min(pct, 100) / 5))
            lines.append(f"  {status} {budget.category:<15} ${spent:>8.2f} / ${budget.monthly_limit:>8.2f} [{bar}] {pct:.0f}%")
            if remaining > 0:
                lines.append(f"       Remaining: ${remaining:.2f}")

        return "\n".join(lines)

    def search(self, query: str) -> str:
        q = query.lower()
        matches = [e for e in self.expenses if
                   q in e.description.lower() or q in e.category.lower() or
                   q in e.tags.lower() or q in e.notes.lower()]
        if not matches:
            return f"No entries matching '{query}'."
        lines = [f"  #{e.id} {e.date} {'−' if e.expense_type == 'expense' else '+'}"
                 f"${e.amount:.2f} — {e.description} [{e.category}]"
                 for e in matches[-20:]]
        return f"Expense search ({len(matches)} matches):\n" + "\n".join(lines)

    def list_recent(self, count: int = 20) -> str:
        recent = self.expenses[-count:]
        if not recent:
            return "No expense entries."
        lines = [f"  #{e.id} {e.date} {'−' if e.expense_type == 'expense' else '+'}"
                 f"${e.amount:.2f} — {e.description} [{e.category}]"
                 for e in reversed(recent)]
        return f"Recent Entries ({len(recent)}):\n" + "\n".join(lines)

    def export_csv(self, file_path: str = "") -> str:
        if not file_path:
            file_path = str(config.GENERATED_DIR / "expenses_export.csv")
        p = Path(file_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        fields = ["id", "date", "expense_type", "amount", "description", "category", "payment_method", "tags", "notes"]
        with open(p, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for e in self.expenses:
                writer.writerow({k: getattr(e, k, "") for k in fields})
        return f"Exported {len(self.expenses)} entries to {p}"

    def yearly_summary(self, year: str = "") -> str:
        if not year:
            year = datetime.now().strftime("%Y")
        entries = [e for e in self.expenses if e.date.startswith(year)]
        if not entries:
            return f"No data for {year}."

        total_expense = sum(e.amount for e in entries if e.expense_type == "expense")
        total_income = sum(e.amount for e in entries if e.expense_type == "income")

        # Monthly breakdown
        monthly = defaultdict(lambda: {"expense": 0, "income": 0})
        for e in entries:
            month = e.date[:7]
            monthly[month][e.expense_type] += e.amount

        lines = [f"Yearly Summary: {year}", f"  Total expenses: ${total_expense:,.2f}",
                 f"  Total income: ${total_income:,.2f}",
                 f"  Net: ${total_income - total_expense:+,.2f}", "",
                 "  Monthly Breakdown:"]
        for month in sorted(monthly.keys()):
            m = monthly[month]
            lines.append(f"    {month}: Expense ${m['expense']:>10,.2f} | Income ${m['income']:>10,.2f} | Net ${m['income'] - m['expense']:>+10,.2f}")

        return "\n".join(lines)

    # ─── Unified Interface ────────────────────────────────
    def expense_operation(self, operation: str, **kwargs) -> str:
        ops = {
            "add": lambda: self.add_expense(float(kwargs.get("amount", 0)), kwargs.get("description", ""), kwargs.get("category", ""), kwargs.get("payment_method", ""), kwargs.get("tags", ""), kwargs.get("date", "")),
            "income": lambda: self.add_income(float(kwargs.get("amount", 0)), kwargs.get("description", "")),
            "delete": lambda: self.delete_entry(int(kwargs.get("entry_id", 0))),
            "today": lambda: self.today_summary(),
            "month": lambda: self.month_summary(kwargs.get("month", "")),
            "year": lambda: self.yearly_summary(kwargs.get("year", "")),
            "set_budget": lambda: self.set_budget(kwargs.get("category", ""), float(kwargs.get("limit", 0))),
            "budget": lambda: self.budget_status(),
            "search": lambda: self.search(kwargs.get("query", "")),
            "recent": lambda: self.list_recent(int(kwargs.get("count", 20))),
            "export": lambda: self.export_csv(kwargs.get("file_path", "")),
        }
        handler = ops.get(operation)
        if handler:
            return handler()
        return f"Unknown expense operation: {operation}. Available: {', '.join(ops.keys())}"


expense_tracker = ExpenseTracker()
