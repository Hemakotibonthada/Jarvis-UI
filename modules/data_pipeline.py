"""
Data Pipeline Module — ETL (Extract, Transform, Load) pipeline builder for
automating data processing workflows. CSV/JSON/XML processing, filtering,
mapping, aggregation, and output formatting.
"""

import csv
import json
import io
import re
import os
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from core.logger import get_logger
import config

log = get_logger("pipeline")


class DataPipeline:
    """Build and execute data processing pipelines."""

    def __init__(self):
        self._data = []
        self._original_data = []
        self._operations = []
        self._name = ""

    def load_csv(self, file_path: str, delimiter: str = ",", encoding: str = "utf-8") -> str:
        """Load data from CSV file."""
        p = Path(file_path).expanduser()
        if not p.exists():
            return f"File not found: {p}"
        try:
            with open(p, "r", encoding=encoding) as f:
                reader = csv.DictReader(f, delimiter=delimiter)
                self._data = list(reader)
                self._original_data = list(self._data)
            return f"Loaded {len(self._data)} rows from {p.name} ({len(self._data[0].keys()) if self._data else 0} columns)"
        except Exception as e:
            return f"CSV load error: {e}"

    def load_json(self, file_path: str) -> str:
        """Load data from JSON file (must be array of objects)."""
        p = Path(file_path).expanduser()
        if not p.exists():
            return f"File not found: {p}"
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, list):
                self._data = data
            elif isinstance(data, dict):
                self._data = [data]
            else:
                return "JSON must be an array of objects."
            self._original_data = list(self._data)
            return f"Loaded {len(self._data)} records from {p.name}"
        except Exception as e:
            return f"JSON load error: {e}"

    def load_from_text(self, text: str, format: str = "csv") -> str:
        """Load data from text string."""
        try:
            if format == "csv":
                reader = csv.DictReader(io.StringIO(text))
                self._data = list(reader)
            elif format == "json":
                self._data = json.loads(text)
                if not isinstance(self._data, list):
                    self._data = [self._data]
            else:
                # Line-by-line
                self._data = [{"line": line} for line in text.strip().split("\n")]
            self._original_data = list(self._data)
            return f"Loaded {len(self._data)} records from text ({format})"
        except Exception as e:
            return f"Text load error: {e}"

    # ─── Transform Operations ─────────────────────────────────
    def filter_rows(self, column: str, operator: str, value: str) -> str:
        """Filter rows. Operators: ==, !=, >, <, >=, <=, contains, startswith, endswith, regex."""
        before = len(self._data)
        filtered = []

        for row in self._data:
            cell = str(row.get(column, ""))
            try:
                if operator == "==":
                    match = cell == value
                elif operator == "!=":
                    match = cell != value
                elif operator == ">":
                    match = float(cell) > float(value)
                elif operator == "<":
                    match = float(cell) < float(value)
                elif operator == ">=":
                    match = float(cell) >= float(value)
                elif operator == "<=":
                    match = float(cell) <= float(value)
                elif operator == "contains":
                    match = value.lower() in cell.lower()
                elif operator == "startswith":
                    match = cell.lower().startswith(value.lower())
                elif operator == "endswith":
                    match = cell.lower().endswith(value.lower())
                elif operator == "regex":
                    match = bool(re.search(value, cell))
                elif operator == "empty":
                    match = not cell.strip()
                elif operator == "notempty":
                    match = bool(cell.strip())
                else:
                    match = True
            except (ValueError, TypeError):
                match = False

            if match:
                filtered.append(row)

        self._data = filtered
        return f"Filter: {before} → {len(self._data)} rows (removed {before - len(self._data)})"

    def select_columns(self, columns: list) -> str:
        """Select specific columns."""
        self._data = [{c: row.get(c, "") for c in columns} for row in self._data]
        return f"Selected {len(columns)} columns: {', '.join(columns)}"

    def rename_column(self, old_name: str, new_name: str) -> str:
        """Rename a column."""
        for row in self._data:
            if old_name in row:
                row[new_name] = row.pop(old_name)
        return f"Renamed column: {old_name} → {new_name}"

    def add_column(self, name: str, value: str = "", expression: str = "") -> str:
        """Add a new column with a static value or expression."""
        for row in self._data:
            if expression:
                try:
                    # Simple expression evaluation with row context
                    result = eval(expression, {"__builtins__": {"len": len, "int": int, "float": float, "str": str}}, row)
                    row[name] = str(result)
                except Exception:
                    row[name] = ""
            else:
                row[name] = value
        return f"Added column: {name}"

    def sort_data(self, column: str, descending: bool = False) -> str:
        """Sort data by a column."""
        try:
            # Try numeric sort
            self._data.sort(key=lambda r: float(r.get(column, 0) or 0), reverse=descending)
        except (ValueError, TypeError):
            self._data.sort(key=lambda r: str(r.get(column, "")), reverse=descending)
        return f"Sorted by {column} ({'desc' if descending else 'asc'})"

    def limit(self, count: int) -> str:
        """Limit to first N rows."""
        before = len(self._data)
        self._data = self._data[:count]
        return f"Limited: {before} → {len(self._data)} rows"

    def skip(self, count: int) -> str:
        """Skip first N rows."""
        before = len(self._data)
        self._data = self._data[count:]
        return f"Skipped {count} rows: {before} → {len(self._data)}"

    def deduplicate(self, column: str = "") -> str:
        """Remove duplicate rows (or by a specific column)."""
        before = len(self._data)
        if column:
            seen = set()
            unique = []
            for row in self._data:
                val = row.get(column, "")
                if val not in seen:
                    seen.add(val)
                    unique.append(row)
            self._data = unique
        else:
            seen = set()
            unique = []
            for row in self._data:
                key = json.dumps(row, sort_keys=True)
                if key not in seen:
                    seen.add(key)
                    unique.append(row)
            self._data = unique
        return f"Deduplicate: {before} → {len(self._data)} rows (removed {before - len(self._data)} duplicates)"

    def transform_column(self, column: str, operation: str) -> str:
        """Transform values in a column. Operations: upper, lower, trim, round, abs, int, float, replace:old:new."""
        count = 0
        for row in self._data:
            val = row.get(column, "")
            try:
                if operation == "upper":
                    row[column] = str(val).upper()
                elif operation == "lower":
                    row[column] = str(val).lower()
                elif operation == "trim":
                    row[column] = str(val).strip()
                elif operation == "round":
                    row[column] = str(round(float(val), 2))
                elif operation == "abs":
                    row[column] = str(abs(float(val)))
                elif operation == "int":
                    row[column] = str(int(float(val)))
                elif operation == "float":
                    row[column] = str(float(val))
                elif operation.startswith("replace:"):
                    parts = operation.split(":", 2)
                    if len(parts) == 3:
                        row[column] = str(val).replace(parts[1], parts[2])
                count += 1
            except (ValueError, TypeError):
                pass
        return f"Transformed {count} values in '{column}' ({operation})"

    # ─── Aggregation ──────────────────────────────────────────
    def aggregate(self, group_by: str, agg_column: str, function: str = "count") -> str:
        """Aggregate data. Functions: count, sum, avg, min, max, list."""
        groups = defaultdict(list)
        for row in self._data:
            key = row.get(group_by, "")
            groups[key].append(row.get(agg_column, ""))

        result_data = []
        for key, values in groups.items():
            result = {group_by: key}
            numeric = []
            for v in values:
                try:
                    numeric.append(float(v))
                except (ValueError, TypeError):
                    pass

            if function == "count":
                result[f"{agg_column}_count"] = len(values)
            elif function == "sum" and numeric:
                result[f"{agg_column}_sum"] = sum(numeric)
            elif function == "avg" and numeric:
                result[f"{agg_column}_avg"] = round(sum(numeric) / len(numeric), 2)
            elif function == "min" and numeric:
                result[f"{agg_column}_min"] = min(numeric)
            elif function == "max" and numeric:
                result[f"{agg_column}_max"] = max(numeric)
            elif function == "list":
                result[f"{agg_column}_values"] = ", ".join(str(v) for v in values[:10])

            result_data.append(result)

        self._data = result_data
        return f"Aggregated: {len(groups)} groups by '{group_by}' ({function} of '{agg_column}')"

    def pivot(self, index: str, columns: str, values: str) -> str:
        """Simple pivot table."""
        pivot_data = {}
        col_values = set()

        for row in self._data:
            idx = row.get(index, "")
            col = row.get(columns, "")
            val = row.get(values, "")
            col_values.add(col)
            if idx not in pivot_data:
                pivot_data[idx] = {index: idx}
            pivot_data[idx][col] = val

        self._data = list(pivot_data.values())
        return f"Pivoted: {len(self._data)} rows, {len(col_values)} column values"

    # ─── Statistics ───────────────────────────────────────────
    def describe(self, column: str = "") -> str:
        """Get statistical summary of data."""
        if not self._data:
            return "No data loaded."

        if column:
            values = [row.get(column, "") for row in self._data]
            numeric = []
            for v in values:
                try:
                    numeric.append(float(v))
                except (ValueError, TypeError):
                    pass

            result = f"Column: {column}\n  Count: {len(values)}\n  Non-empty: {sum(1 for v in values if v)}\n  Unique: {len(set(values))}\n"
            if numeric:
                result += (
                    f"  Min: {min(numeric)}\n  Max: {max(numeric)}\n"
                    f"  Mean: {sum(numeric) / len(numeric):.2f}\n"
                    f"  Sum: {sum(numeric):.2f}\n"
                )
            return result

        # General overview
        columns = list(self._data[0].keys()) if self._data else []
        return (
            f"Data Overview:\n"
            f"  Rows: {len(self._data)}\n"
            f"  Columns: {len(columns)}\n"
            f"  Column names: {', '.join(columns)}\n"
            f"  Sample (first row): {json.dumps(self._data[0], indent=2)[:300] if self._data else '(empty)'}"
        )

    def preview(self, rows: int = 5) -> str:
        """Preview first N rows."""
        if not self._data:
            return "No data loaded."
        preview = self._data[:rows]
        lines = [json.dumps(row, ensure_ascii=False)[:200] for row in preview]
        return f"Preview ({len(preview)} of {len(self._data)} rows):\n" + "\n".join(f"  {l}" for l in lines)

    # ─── Export ───────────────────────────────────────────────
    def save_csv(self, file_path: str = "") -> str:
        """Save data to CSV."""
        if not self._data:
            return "No data to save."
        if not file_path:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = str(config.GENERATED_DIR / f"pipeline_output_{ts}.csv")
        p = Path(file_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self._data[0].keys())
            writer.writeheader()
            writer.writerows(self._data)
        return f"Saved {len(self._data)} rows to {p}"

    def save_json(self, file_path: str = "") -> str:
        """Save data to JSON."""
        if not self._data:
            return "No data to save."
        if not file_path:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = str(config.GENERATED_DIR / f"pipeline_output_{ts}.json")
        p = Path(file_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8")
        return f"Saved {len(self._data)} records to {p}"

    def to_table(self) -> str:
        """Format data as a text table."""
        if not self._data:
            return "No data."
        cols = list(self._data[0].keys())
        # Calculate column widths
        widths = {c: max(len(c), max(len(str(row.get(c, ""))[:20]) for row in self._data[:30])) for c in cols}

        header = " | ".join(c.ljust(widths[c])[:20] for c in cols)
        separator = "-+-".join("-" * min(widths[c], 20) for c in cols)
        rows = []
        for row in self._data[:50]:
            rows.append(" | ".join(str(row.get(c, "")).ljust(widths[c])[:20] for c in cols))

        result = f"{header}\n{separator}\n" + "\n".join(rows)
        if len(self._data) > 50:
            result += f"\n... ({len(self._data) - 50} more rows)"
        return result

    def reset(self) -> str:
        """Reset to original loaded data."""
        self._data = list(self._original_data)
        return f"Reset to original data: {len(self._data)} rows"

    # ─── Unified Interface ────────────────────────────────
    def pipeline_operation(self, operation: str, **kwargs) -> str:
        """Unified data pipeline interface."""
        ops = {
            "load_csv": lambda: self.load_csv(kwargs.get("file_path", ""), kwargs.get("delimiter", ",")),
            "load_json": lambda: self.load_json(kwargs.get("file_path", "")),
            "load_text": lambda: self.load_from_text(kwargs.get("text", ""), kwargs.get("format", "csv")),
            "filter": lambda: self.filter_rows(kwargs.get("column", ""), kwargs.get("operator", "=="), kwargs.get("value", "")),
            "select": lambda: self.select_columns(kwargs.get("columns", [])),
            "rename": lambda: self.rename_column(kwargs.get("old_name", ""), kwargs.get("new_name", "")),
            "add_column": lambda: self.add_column(kwargs.get("name", ""), kwargs.get("value", ""), kwargs.get("expression", "")),
            "sort": lambda: self.sort_data(kwargs.get("column", ""), kwargs.get("descending", False)),
            "limit": lambda: self.limit(int(kwargs.get("count", 10))),
            "skip": lambda: self.skip(int(kwargs.get("count", 0))),
            "deduplicate": lambda: self.deduplicate(kwargs.get("column", "")),
            "transform": lambda: self.transform_column(kwargs.get("column", ""), kwargs.get("transform", "trim")),
            "aggregate": lambda: self.aggregate(kwargs.get("group_by", ""), kwargs.get("agg_column", ""), kwargs.get("function", "count")),
            "pivot": lambda: self.pivot(kwargs.get("index", ""), kwargs.get("columns_field", ""), kwargs.get("values_field", "")),
            "describe": lambda: self.describe(kwargs.get("column", "")),
            "preview": lambda: self.preview(int(kwargs.get("rows", 5))),
            "table": lambda: self.to_table(),
            "save_csv": lambda: self.save_csv(kwargs.get("file_path", "")),
            "save_json": lambda: self.save_json(kwargs.get("file_path", "")),
            "reset": lambda: self.reset(),
        }
        handler = ops.get(operation)
        if handler:
            return handler()
        return f"Unknown pipeline operation: {operation}. Available: {', '.join(ops.keys())}"


data_pipeline = DataPipeline()
