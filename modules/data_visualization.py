"""
Data Visualization Module — Generate charts and visualizations as SVG or images.
Creates bar charts, line charts, pie charts, and sparklines using pure Python,
without requiring matplotlib (falls back to it if available).
"""

import json
import math
from datetime import datetime
from pathlib import Path
from core.logger import get_logger
import config

log = get_logger("charts")


class SVGChart:
    """Generate SVG charts from data."""

    COLORS = [
        "#00d4ff", "#00ff88", "#ffaa00", "#ff3355", "#aa55ff",
        "#ff6644", "#44ddff", "#88ff44", "#ff44aa", "#ffdd44",
        "#4488ff", "#ff8844", "#44ffaa", "#dd44ff", "#aaff44",
    ]

    @staticmethod
    def _svg_header(width: int, height: int, title: str = "") -> str:
        header = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" style="background:#0a0e17;font-family:Arial,sans-serif">'
        if title:
            header += f'<text x="{width//2}" y="25" fill="#00d4ff" font-size="14" text-anchor="middle" font-weight="bold">{title}</text>'
        return header

    @staticmethod
    def bar_chart(data: dict, title: str = "Bar Chart",
                  width: int = 600, height: int = 400) -> str:
        """Generate an SVG bar chart. data = {label: value, ...}"""
        if not data:
            return "<svg></svg>"

        labels = list(data.keys())
        values = [float(v) for v in data.values()]
        max_val = max(values) if values else 1

        padding = {"top": 50, "right": 30, "bottom": 80, "left": 60}
        chart_w = width - padding["left"] - padding["right"]
        chart_h = height - padding["top"] - padding["bottom"]
        bar_width = max(10, chart_w // len(labels) - 10)
        gap = (chart_w - bar_width * len(labels)) / (len(labels) + 1)

        svg = SVGChart._svg_header(width, height, title)

        # Y-axis grid lines and labels
        num_gridlines = 5
        for i in range(num_gridlines + 1):
            y = padding["top"] + chart_h - (i / num_gridlines) * chart_h
            val = (i / num_gridlines) * max_val
            svg += f'<line x1="{padding["left"]}" y1="{y:.0f}" x2="{width - padding["right"]}" y2="{y:.0f}" stroke="#1a2844" stroke-width="1"/>'
            svg += f'<text x="{padding["left"] - 8}" y="{y + 4:.0f}" fill="#6688aa" font-size="10" text-anchor="end">{val:.0f}</text>'

        # Bars
        for i, (label, value) in enumerate(zip(labels, values)):
            x = padding["left"] + gap + i * (bar_width + gap)
            bar_height = (value / max_val) * chart_h if max_val else 0
            y = padding["top"] + chart_h - bar_height
            color = SVGChart.COLORS[i % len(SVGChart.COLORS)]

            # Bar with rounded top
            svg += f'<rect x="{x:.0f}" y="{y:.0f}" width="{bar_width}" height="{bar_height:.0f}" fill="{color}" rx="3" opacity="0.85"/>'

            # Value label on top
            svg += f'<text x="{x + bar_width / 2:.0f}" y="{y - 5:.0f}" fill="#c0d8f0" font-size="11" text-anchor="middle">{value:.0f}</text>'

            # X-axis label (rotated for long labels)
            label_y = padding["top"] + chart_h + 15
            truncated = label[:12] + ".." if len(label) > 14 else label
            svg += f'<text x="{x + bar_width / 2:.0f}" y="{label_y}" fill="#8899aa" font-size="10" text-anchor="middle" transform="rotate(-30, {x + bar_width / 2:.0f}, {label_y})">{truncated}</text>'

        # Axes
        svg += f'<line x1="{padding["left"]}" y1="{padding["top"]}" x2="{padding["left"]}" y2="{padding["top"] + chart_h}" stroke="#334466" stroke-width="1.5"/>'
        svg += f'<line x1="{padding["left"]}" y1="{padding["top"] + chart_h}" x2="{width - padding["right"]}" y2="{padding["top"] + chart_h}" stroke="#334466" stroke-width="1.5"/>'

        svg += "</svg>"
        return svg

    @staticmethod
    def line_chart(data: dict, title: str = "Line Chart",
                   width: int = 600, height: int = 400) -> str:
        """Generate an SVG line chart. data = {label: value, ...} or [[x,y], ...]"""
        if not data:
            return "<svg></svg>"

        if isinstance(data, dict):
            labels = list(data.keys())
            values = [float(v) for v in data.values()]
        elif isinstance(data, list):
            labels = [str(i) for i in range(len(data))]
            values = [float(v) for v in data]
        else:
            return "<svg></svg>"

        max_val = max(values) if values else 1
        min_val = min(values) if values else 0
        val_range = max_val - min_val or 1

        padding = {"top": 50, "right": 30, "bottom": 60, "left": 60}
        chart_w = width - padding["left"] - padding["right"]
        chart_h = height - padding["top"] - padding["bottom"]

        svg = SVGChart._svg_header(width, height, title)

        # Grid
        for i in range(6):
            y = padding["top"] + chart_h - (i / 5) * chart_h
            val = min_val + (i / 5) * val_range
            svg += f'<line x1="{padding["left"]}" y1="{y:.0f}" x2="{width - padding["right"]}" y2="{y:.0f}" stroke="#1a2844" stroke-width="1"/>'
            svg += f'<text x="{padding["left"] - 8}" y="{y + 4:.0f}" fill="#6688aa" font-size="10" text-anchor="end">{val:.1f}</text>'

        # Line path
        points = []
        for i, value in enumerate(values):
            x = padding["left"] + (i / max(len(values) - 1, 1)) * chart_w
            y = padding["top"] + chart_h - ((value - min_val) / val_range) * chart_h
            points.append(f"{x:.1f},{y:.1f}")

        # Area fill
        if points:
            area_points = points + [
                f"{padding['left'] + chart_w},{padding['top'] + chart_h}",
                f"{padding['left']},{padding['top'] + chart_h}",
            ]
            svg += f'<polygon points="{" ".join(area_points)}" fill="#00d4ff" opacity="0.1"/>'

        # Line
        svg += f'<polyline points="{" ".join(points)}" fill="none" stroke="#00d4ff" stroke-width="2" stroke-linejoin="round"/>'

        # Data points
        for i, (px, py) in enumerate(p.split(",") for p in points):
            svg += f'<circle cx="{px}" cy="{py}" r="3" fill="#00d4ff" stroke="#0a0e17" stroke-width="1.5"/>'

        # X-axis labels (show max 10)
        step = max(1, len(labels) // 10)
        for i in range(0, len(labels), step):
            x = padding["left"] + (i / max(len(values) - 1, 1)) * chart_w
            svg += f'<text x="{x:.0f}" y="{padding["top"] + chart_h + 20}" fill="#8899aa" font-size="9" text-anchor="middle">{labels[i][:8]}</text>'

        # Axes
        svg += f'<line x1="{padding["left"]}" y1="{padding["top"]}" x2="{padding["left"]}" y2="{padding["top"] + chart_h}" stroke="#334466" stroke-width="1.5"/>'
        svg += f'<line x1="{padding["left"]}" y1="{padding["top"] + chart_h}" x2="{width - padding["right"]}" y2="{padding["top"] + chart_h}" stroke="#334466" stroke-width="1.5"/>'

        svg += "</svg>"
        return svg

    @staticmethod
    def pie_chart(data: dict, title: str = "Pie Chart",
                  width: int = 400, height: int = 400) -> str:
        """Generate an SVG pie chart. data = {label: value, ...}"""
        if not data:
            return "<svg></svg>"

        total = sum(float(v) for v in data.values())
        if total == 0:
            return "<svg></svg>"

        cx, cy = width // 2, height // 2 + 15
        radius = min(width, height) // 2 - 60

        svg = SVGChart._svg_header(width, height, title)

        start_angle = -90  # Start from top
        legend_y = 0

        for i, (label, value) in enumerate(data.items()):
            fraction = float(value) / total
            angle = fraction * 360
            end_angle = start_angle + angle

            # Convert to radians
            start_rad = math.radians(start_angle)
            end_rad = math.radians(end_angle)

            # Arc endpoints
            x1 = cx + radius * math.cos(start_rad)
            y1 = cy + radius * math.sin(start_rad)
            x2 = cx + radius * math.cos(end_rad)
            y2 = cy + radius * math.sin(end_rad)

            large_arc = 1 if angle > 180 else 0
            color = SVGChart.COLORS[i % len(SVGChart.COLORS)]

            # Path
            if fraction >= 0.999:
                # Full circle
                svg += f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="{color}" opacity="0.85"/>'
            else:
                svg += f'<path d="M {cx},{cy} L {x1:.1f},{y1:.1f} A {radius},{radius} 0 {large_arc},1 {x2:.1f},{y2:.1f} Z" fill="{color}" opacity="0.85" stroke="#0a0e17" stroke-width="1"/>'

            # Percentage label on slice
            mid_angle = math.radians(start_angle + angle / 2)
            label_r = radius * 0.65
            lx = cx + label_r * math.cos(mid_angle)
            ly = cy + label_r * math.sin(mid_angle)
            pct = fraction * 100
            if pct > 5:
                svg += f'<text x="{lx:.0f}" y="{ly:.0f}" fill="white" font-size="11" text-anchor="middle" font-weight="bold">{pct:.0f}%</text>'

            # Legend
            legend_x = width - 120
            ly_legend = 50 + legend_y * 20
            svg += f'<rect x="{legend_x}" y="{ly_legend - 8}" width="10" height="10" fill="{color}" rx="2"/>'
            svg += f'<text x="{legend_x + 15}" y="{ly_legend}" fill="#c0d8f0" font-size="10">{label[:15]} ({pct:.1f}%)</text>'
            legend_y += 1

            start_angle = end_angle

        svg += "</svg>"
        return svg

    @staticmethod
    def sparkline(values: list, width: int = 200, height: int = 40,
                  color: str = "#00d4ff") -> str:
        """Generate a small inline sparkline SVG."""
        if not values or len(values) < 2:
            return "<svg></svg>"

        max_val = max(values)
        min_val = min(values)
        val_range = max_val - min_val or 1

        points = []
        for i, v in enumerate(values):
            x = (i / (len(values) - 1)) * width
            y = height - ((v - min_val) / val_range) * (height - 4) - 2
            points.append(f"{x:.1f},{y:.1f}")

        svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
        svg += f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="1.5" stroke-linejoin="round"/>'
        # End dot
        last = points[-1].split(",")
        svg += f'<circle cx="{last[0]}" cy="{last[1]}" r="2" fill="{color}"/>'
        svg += "</svg>"
        return svg

    @staticmethod
    def horizontal_bar(data: dict, title: str = "Horizontal Bar Chart",
                       width: int = 500, height: int = 0) -> str:
        """Generate horizontal bar chart."""
        if not data:
            return "<svg></svg>"

        bar_height = 25
        gap = 8
        items = list(data.items())
        if not height:
            height = len(items) * (bar_height + gap) + 80

        max_val = max(float(v) for v in data.values()) if data else 1
        padding_left = 120
        chart_w = width - padding_left - 60

        svg = SVGChart._svg_header(width, height, title)

        for i, (label, value) in enumerate(items):
            y = 50 + i * (bar_height + gap)
            bar_w = (float(value) / max_val) * chart_w if max_val else 0
            color = SVGChart.COLORS[i % len(SVGChart.COLORS)]

            # Label
            svg += f'<text x="{padding_left - 8}" y="{y + bar_height / 2 + 4}" fill="#c0d8f0" font-size="11" text-anchor="end">{label[:15]}</text>'
            # Bar
            svg += f'<rect x="{padding_left}" y="{y}" width="{bar_w:.0f}" height="{bar_height}" fill="{color}" rx="3" opacity="0.85"/>'
            # Value
            svg += f'<text x="{padding_left + bar_w + 8:.0f}" y="{y + bar_height / 2 + 4}" fill="#8899aa" font-size="11">{float(value):.0f}</text>'

        svg += "</svg>"
        return svg

    @staticmethod
    def gauge(value: float, max_value: float = 100, title: str = "",
              width: int = 200, height: int = 130) -> str:
        """Generate a gauge/meter SVG."""
        pct = min(1, max(0, value / max_value))
        cx, cy = width // 2, height - 20
        radius = min(width // 2 - 10, height - 30)

        svg = SVGChart._svg_header(width, height, title)

        # Background arc
        svg += f'<path d="M {cx - radius},{cy} A {radius},{radius} 0 0,1 {cx + radius},{cy}" fill="none" stroke="#1a2844" stroke-width="12" stroke-linecap="round"/>'

        # Value arc (partial)
        angle = pct * 180
        end_rad = math.radians(180 - angle)
        ex = cx + radius * math.cos(end_rad)
        ey = cy - radius * math.sin(end_rad)
        large_arc = 1 if angle > 180 else 0

        color = "#00ff88" if pct < 0.6 else "#ffaa00" if pct < 0.85 else "#ff3355"
        svg += f'<path d="M {cx - radius},{cy} A {radius},{radius} 0 {large_arc},1 {ex:.1f},{ey:.1f}" fill="none" stroke="{color}" stroke-width="12" stroke-linecap="round"/>'

        # Value text
        svg += f'<text x="{cx}" y="{cy - radius // 3}" fill="#e0f0ff" font-size="22" text-anchor="middle" font-weight="bold">{value:.0f}</text>'
        svg += f'<text x="{cx}" y="{cy - radius // 3 + 16}" fill="#6688aa" font-size="10" text-anchor="middle">/ {max_value:.0f}</text>'

        svg += "</svg>"
        return svg


# ─── Chart Manager ────────────────────────────────────────────
class ChartManager:
    """Create and save charts."""

    def __init__(self):
        self.chart = SVGChart()

    def create_chart(self, chart_type: str, data: dict, title: str = "",
                     save_path: str = "", **kwargs) -> str:
        """Create a chart and optionally save it."""
        types = {
            "bar": lambda: self.chart.bar_chart(data, title, **kwargs),
            "line": lambda: self.chart.line_chart(data, title, **kwargs),
            "pie": lambda: self.chart.pie_chart(data, title, **kwargs),
            "horizontal_bar": lambda: self.chart.horizontal_bar(data, title, **kwargs),
        }

        generator = types.get(chart_type)
        if not generator:
            return f"Unknown chart type: {chart_type}. Available: {', '.join(types.keys())}"

        svg = generator()

        if save_path:
            p = Path(save_path).expanduser()
        else:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            p = config.GENERATED_DIR / f"chart_{chart_type}_{ts}.svg"

        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(svg, encoding="utf-8")

        return f"Chart created: {p}\nType: {chart_type}\nData points: {len(data)}"

    def create_gauge(self, value: float, max_value: float = 100,
                     title: str = "", save_path: str = "") -> str:
        """Create a gauge chart."""
        svg = self.chart.gauge(value, max_value, title)
        if save_path:
            p = Path(save_path).expanduser()
        else:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            p = config.GENERATED_DIR / f"gauge_{ts}.svg"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(svg, encoding="utf-8")
        return f"Gauge chart created: {p} (value: {value}/{max_value})"

    def create_sparkline(self, values: list, save_path: str = "",
                         color: str = "#00d4ff") -> str:
        """Create a sparkline."""
        svg = self.chart.sparkline(values, color=color)
        if save_path:
            p = Path(save_path).expanduser()
        else:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            p = config.GENERATED_DIR / f"sparkline_{ts}.svg"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(svg, encoding="utf-8")
        return f"Sparkline created: {p} ({len(values)} points)"

    def chart_from_csv(self, csv_path: str, chart_type: str = "bar",
                       x_col: int = 0, y_col: int = 1, title: str = "") -> str:
        """Create a chart from CSV data."""
        import csv
        p = Path(csv_path).expanduser()
        if not p.exists():
            return f"CSV file not found: {p}"

        try:
            with open(p, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                rows = list(reader)

            if len(rows) < 2:
                return "CSV needs at least a header and one data row."

            headers = rows[0]
            data = {}
            for row in rows[1:51]:  # Limit to 50 rows
                try:
                    label = row[x_col] if x_col < len(row) else str(len(data))
                    value = float(row[y_col]) if y_col < len(row) else 0
                    data[label] = value
                except (ValueError, IndexError):
                    continue

            if not title:
                title = f"{headers[y_col] if y_col < len(headers) else 'Values'} by {headers[x_col] if x_col < len(headers) else 'Label'}"

            return self.create_chart(chart_type, data, title)
        except Exception as e:
            return f"CSV chart error: {e}"

    def visualization_operation(self, operation: str, **kwargs) -> str:
        """Unified visualization interface."""
        ops = {
            "bar": lambda: self.create_chart("bar", kwargs.get("data", {}), kwargs.get("title", "Bar Chart")),
            "line": lambda: self.create_chart("line", kwargs.get("data", {}), kwargs.get("title", "Line Chart")),
            "pie": lambda: self.create_chart("pie", kwargs.get("data", {}), kwargs.get("title", "Pie Chart")),
            "horizontal_bar": lambda: self.create_chart("horizontal_bar", kwargs.get("data", {}), kwargs.get("title", "Horizontal Bar Chart")),
            "gauge": lambda: self.create_gauge(float(kwargs.get("value", 50)), float(kwargs.get("max_value", 100)), kwargs.get("title", "")),
            "sparkline": lambda: self.create_sparkline(kwargs.get("values", []), kwargs.get("save_path", "")),
            "from_csv": lambda: self.chart_from_csv(kwargs.get("csv_path", ""), kwargs.get("chart_type", "bar"), int(kwargs.get("x_col", 0)), int(kwargs.get("y_col", 1))),
        }
        handler = ops.get(operation)
        if handler:
            return handler()
        return f"Unknown visualization operation: {operation}. Available: {', '.join(ops.keys())}"


# ─── Singleton ────────────────────────────────────────────────
chart_manager = ChartManager()
