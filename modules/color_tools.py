"""
Color Tools Module — Color conversion, palette generation, accessibility checking,
and color manipulation utilities for design and development.
"""

import math
import random
from core.logger import get_logger

log = get_logger("colors")


class Color:
    """Represents a color with conversions between formats."""

    def __init__(self, r: int = 0, g: int = 0, b: int = 0, a: float = 1.0):
        self.r = max(0, min(255, r))
        self.g = max(0, min(255, g))
        self.b = max(0, min(255, b))
        self.a = max(0, min(1, a))

    @staticmethod
    def from_hex(hex_str: str) -> 'Color':
        """Create Color from hex string (#RRGGBB or #RGB)."""
        h = hex_str.lstrip("#")
        if len(h) == 3:
            h = h[0] * 2 + h[1] * 2 + h[2] * 2
        if len(h) == 8:
            return Color(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), int(h[6:8], 16) / 255)
        if len(h) == 6:
            return Color(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
        raise ValueError(f"Invalid hex: {hex_str}")

    @staticmethod
    def from_hsl(h: float, s: float, l: float) -> 'Color':
        """Create Color from HSL (h: 0-360, s: 0-100, l: 0-100)."""
        s /= 100
        l /= 100
        c = (1 - abs(2 * l - 1)) * s
        x = c * (1 - abs((h / 60) % 2 - 1))
        m = l - c / 2
        if h < 60:
            r, g, b = c, x, 0
        elif h < 120:
            r, g, b = x, c, 0
        elif h < 180:
            r, g, b = 0, c, x
        elif h < 240:
            r, g, b = 0, x, c
        elif h < 300:
            r, g, b = x, 0, c
        else:
            r, g, b = c, 0, x
        return Color(round((r + m) * 255), round((g + m) * 255), round((b + m) * 255))

    @staticmethod
    def from_name(name: str) -> 'Color':
        """Create Color from CSS color name."""
        names = {
            "red": (255, 0, 0), "green": (0, 128, 0), "blue": (0, 0, 255),
            "white": (255, 255, 255), "black": (0, 0, 0), "yellow": (255, 255, 0),
            "cyan": (0, 255, 255), "magenta": (255, 0, 255), "orange": (255, 165, 0),
            "purple": (128, 0, 128), "pink": (255, 192, 203), "lime": (0, 255, 0),
            "navy": (0, 0, 128), "teal": (0, 128, 128), "maroon": (128, 0, 0),
            "olive": (128, 128, 0), "silver": (192, 192, 192), "gray": (128, 128, 128),
            "gold": (255, 215, 0), "coral": (255, 127, 80), "salmon": (250, 128, 114),
            "indigo": (75, 0, 130), "violet": (238, 130, 238), "turquoise": (64, 224, 208),
            "crimson": (220, 20, 60), "chocolate": (210, 105, 30), "tomato": (255, 99, 71),
            "steel blue": (70, 130, 180), "slate gray": (112, 128, 144),
        }
        rgb = names.get(name.lower())
        if rgb:
            return Color(*rgb)
        raise ValueError(f"Unknown color name: {name}")

    @property
    def hex(self) -> str:
        return f"#{self.r:02X}{self.g:02X}{self.b:02X}"

    @property
    def rgb(self) -> str:
        return f"rgb({self.r}, {self.g}, {self.b})"

    @property
    def rgba(self) -> str:
        return f"rgba({self.r}, {self.g}, {self.b}, {self.a})"

    @property
    def hsl(self) -> tuple:
        r, g, b = self.r / 255, self.g / 255, self.b / 255
        mx, mn = max(r, g, b), min(r, g, b)
        l = (mx + mn) / 2
        if mx == mn:
            h = s = 0
        else:
            d = mx - mn
            s = d / (2 - mx - mn) if l > 0.5 else d / (mx + mn)
            if mx == r:
                h = ((g - b) / d + (6 if g < b else 0)) * 60
            elif mx == g:
                h = ((b - r) / d + 2) * 60
            else:
                h = ((r - g) / d + 4) * 60
        return (round(h), round(s * 100), round(l * 100))

    @property
    def hsl_str(self) -> str:
        h, s, l = self.hsl
        return f"hsl({h}, {s}%, {l}%)"

    @property
    def luminance(self) -> float:
        """Relative luminance (WCAG formula)."""
        def srgb(c):
            c = c / 255
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
        return 0.2126 * srgb(self.r) + 0.7152 * srgb(self.g) + 0.0722 * srgb(self.b)

    def info(self) -> str:
        h, s, l = self.hsl
        return (
            f"Color Info:\n"
            f"  HEX: {self.hex}\n"
            f"  RGB: {self.rgb}\n"
            f"  HSL: {self.hsl_str}\n"
            f"  Luminance: {self.luminance:.4f}\n"
            f"  Is dark: {self.luminance < 0.5}\n"
            f"  CSS: {self.hex}"
        )


def contrast_ratio(color1: str, color2: str) -> str:
    """Calculate WCAG contrast ratio between two colors."""
    try:
        c1 = Color.from_hex(color1) if color1.startswith("#") else Color.from_name(color1)
        c2 = Color.from_hex(color2) if color2.startswith("#") else Color.from_name(color2)
    except ValueError as e:
        return str(e)

    l1 = max(c1.luminance, c2.luminance)
    l2 = min(c1.luminance, c2.luminance)
    ratio = (l1 + 0.05) / (l2 + 0.05)

    aa_normal = "✓ Pass" if ratio >= 4.5 else "✗ Fail"
    aa_large = "✓ Pass" if ratio >= 3 else "✗ Fail"
    aaa_normal = "✓ Pass" if ratio >= 7 else "✗ Fail"
    aaa_large = "✓ Pass" if ratio >= 4.5 else "✗ Fail"

    return (
        f"Contrast Ratio: {ratio:.2f}:1\n"
        f"  {c1.hex} vs {c2.hex}\n\n"
        f"  WCAG AA  (normal text): {aa_normal} (need 4.5:1)\n"
        f"  WCAG AA  (large text):  {aa_large} (need 3:1)\n"
        f"  WCAG AAA (normal text): {aaa_normal} (need 7:1)\n"
        f"  WCAG AAA (large text):  {aaa_large} (need 4.5:1)"
    )


def generate_palette(base_color: str, scheme: str = "complementary") -> str:
    """Generate a color palette. Schemes: complementary, analogous, triadic, split, tetradic, monochromatic."""
    try:
        base = Color.from_hex(base_color) if base_color.startswith("#") else Color.from_name(base_color)
    except ValueError as e:
        return str(e)

    h, s, l = base.hsl
    colors = [base]

    if scheme == "complementary":
        colors.append(Color.from_hsl((h + 180) % 360, s, l))
    elif scheme == "analogous":
        colors.append(Color.from_hsl((h + 30) % 360, s, l))
        colors.append(Color.from_hsl((h - 30) % 360, s, l))
    elif scheme == "triadic":
        colors.append(Color.from_hsl((h + 120) % 360, s, l))
        colors.append(Color.from_hsl((h + 240) % 360, s, l))
    elif scheme == "split":
        colors.append(Color.from_hsl((h + 150) % 360, s, l))
        colors.append(Color.from_hsl((h + 210) % 360, s, l))
    elif scheme == "tetradic":
        colors.append(Color.from_hsl((h + 90) % 360, s, l))
        colors.append(Color.from_hsl((h + 180) % 360, s, l))
        colors.append(Color.from_hsl((h + 270) % 360, s, l))
    elif scheme == "monochromatic":
        for i in range(1, 5):
            colors.append(Color.from_hsl(h, s, max(10, min(90, l + (i - 2) * 15))))
    else:
        return f"Unknown scheme: {scheme}. Available: complementary, analogous, triadic, split, tetradic, monochromatic"

    lines = [f"  {c.hex} — {c.rgb} — {c.hsl_str}" for c in colors]
    return f"Color Palette ({scheme} from {base.hex}):\n" + "\n".join(lines)


def random_color() -> str:
    """Generate a random color."""
    c = Color(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    return c.info()


def color_mix(color1: str, color2: str, ratio: float = 0.5) -> str:
    """Mix two colors."""
    try:
        c1 = Color.from_hex(color1) if color1.startswith("#") else Color.from_name(color1)
        c2 = Color.from_hex(color2) if color2.startswith("#") else Color.from_name(color2)
    except ValueError as e:
        return str(e)

    r = round(c1.r * (1 - ratio) + c2.r * ratio)
    g = round(c1.g * (1 - ratio) + c2.g * ratio)
    b = round(c1.b * (1 - ratio) + c2.b * ratio)
    result = Color(r, g, b)
    return f"Color Mix ({int(ratio * 100)}% blend):\n  {c1.hex} + {c2.hex} = {result.hex}\n  {result.rgb}"


def color_info(color_input: str) -> str:
    """Get info about a color (hex, name, or RGB)."""
    try:
        if color_input.startswith("#"):
            c = Color.from_hex(color_input)
        elif color_input.startswith("rgb"):
            nums = [int(x) for x in color_input.replace("rgb(", "").replace(")", "").split(",")]
            c = Color(*nums[:3])
        else:
            c = Color.from_name(color_input)
        return c.info()
    except (ValueError, IndexError) as e:
        return f"Color parse error: {e}"


def color_operation(operation: str, **kwargs) -> str:
    """Unified color tools interface."""
    ops = {
        "info": lambda: color_info(kwargs.get("color", "")),
        "contrast": lambda: contrast_ratio(kwargs.get("color1", ""), kwargs.get("color2", "")),
        "palette": lambda: generate_palette(kwargs.get("color", ""), kwargs.get("scheme", "complementary")),
        "random": lambda: random_color(),
        "mix": lambda: color_mix(kwargs.get("color1", ""), kwargs.get("color2", ""), float(kwargs.get("ratio", 0.5))),
    }
    handler = ops.get(operation)
    if handler:
        return handler()
    return f"Unknown color operation: {operation}. Available: {', '.join(ops.keys())}"
