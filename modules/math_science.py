"""
Math & Science Module — Scientific calculations, unit systems,
constants, equation solving, and number base conversions.
"""

import math
import re
import cmath
from fractions import Fraction
from decimal import Decimal
from core.logger import get_logger

log = get_logger("math_science")


# ─── Physical Constants ──────────────────────────────────────
CONSTANTS = {
    "c": (299792458, "m/s", "Speed of light in vacuum"),
    "G": (6.674e-11, "m³/(kg·s²)", "Gravitational constant"),
    "h": (6.626e-34, "J·s", "Planck constant"),
    "hbar": (1.055e-34, "J·s", "Reduced Planck constant"),
    "e": (1.602e-19, "C", "Elementary charge"),
    "me": (9.109e-31, "kg", "Electron mass"),
    "mp": (1.673e-27, "kg", "Proton mass"),
    "mn": (1.675e-27, "kg", "Neutron mass"),
    "k": (1.381e-23, "J/K", "Boltzmann constant"),
    "Na": (6.022e23, "1/mol", "Avogadro number"),
    "R": (8.314, "J/(mol·K)", "Gas constant"),
    "sigma": (5.670e-8, "W/(m²·K⁴)", "Stefan-Boltzmann constant"),
    "mu0": (1.257e-6, "N/A²", "Vacuum permeability"),
    "eps0": (8.854e-12, "F/m", "Vacuum permittivity"),
    "g": (9.80665, "m/s²", "Standard gravity"),
    "atm": (101325, "Pa", "Standard atmosphere"),
    "pi": (math.pi, "", "Pi (π)"),
    "euler": (math.e, "", "Euler's number (e)"),
    "phi": ((1 + math.sqrt(5)) / 2, "", "Golden ratio (φ)"),
    "ly": (9.461e15, "m", "Light-year"),
    "au": (1.496e11, "m", "Astronomical unit"),
    "eV": (1.602e-19, "J", "Electronvolt"),
}


def get_constant(name: str) -> str:
    """Get a physical/mathematical constant."""
    if name.lower() == "all" or name.lower() == "list":
        lines = [f"  {k:>6} = {v[0]:>15.6e} {v[1]:<15} — {v[2]}" for k, v in CONSTANTS.items()]
        return "Physical & Mathematical Constants:\n" + "\n".join(lines)

    key = name.strip()
    if key in CONSTANTS:
        val, unit, desc = CONSTANTS[key]
        return f"{desc}:\n  {key} = {val} {unit}"

    # Fuzzy search
    matches = [(k, v) for k, v in CONSTANTS.items() if name.lower() in v[2].lower() or name.lower() in k.lower()]
    if matches:
        lines = [f"  {k} = {v[0]} {v[1]} — {v[2]}" for k, v in matches]
        return f"Constants matching '{name}':\n" + "\n".join(lines)

    return f"Constant '{name}' not found. Use 'list' to see all."


# ─── Number Base Conversions ─────────────────────────────────
def base_convert(value: str, from_base: int = 10, to_base: int = 2) -> str:
    """Convert a number between bases (2-36)."""
    try:
        # Parse the input number
        decimal_val = int(value, from_base)

        # Convert to target base
        if to_base == 10:
            result = str(decimal_val)
        elif to_base == 2:
            result = bin(decimal_val)
        elif to_base == 8:
            result = oct(decimal_val)
        elif to_base == 16:
            result = hex(decimal_val)
        else:
            digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            if decimal_val == 0:
                result = "0"
            else:
                parts = []
                n = abs(decimal_val)
                while n:
                    parts.append(digits[n % to_base])
                    n //= to_base
                result = ("-" if decimal_val < 0 else "") + "".join(reversed(parts))

        return f"Base conversion:\n  {value} (base {from_base}) = {result} (base {to_base})\n  Decimal: {decimal_val}"
    except ValueError as e:
        return f"Conversion error: {e}"


def number_info(value: str) -> str:
    """Get comprehensive information about a number."""
    try:
        num = int(value) if "." not in value else float(value)
    except ValueError:
        return f"'{value}' is not a valid number."

    info = [f"Number Analysis: {value}", ""]

    if isinstance(num, int):
        info.append(f"  Decimal: {num:,}")
        info.append(f"  Binary:  {bin(num)}")
        info.append(f"  Octal:   {oct(num)}")
        info.append(f"  Hex:     {hex(num)}")
        info.append(f"  Scientific: {num:.6e}")
        info.append(f"  Bits needed: {num.bit_length()}")

        # Properties
        is_even = num % 2 == 0
        is_prime = _is_prime(abs(num)) if abs(num) > 1 else False
        is_perfect_sq = math.isqrt(abs(num)) ** 2 == abs(num) if num >= 0 else False

        info.append(f"\n  Properties:")
        info.append(f"    Even: {is_even}")
        info.append(f"    Prime: {is_prime}")
        info.append(f"    Perfect square: {is_perfect_sq}")

        if abs(num) <= 10000 and num > 0:
            factors = _factorize(num)
            info.append(f"    Factors: {factors}")
            divisors = [i for i in range(1, num + 1) if num % i == 0]
            if len(divisors) <= 20:
                info.append(f"    Divisors: {divisors}")

        # Fraction representation
        if isinstance(num, float):
            frac = Fraction(num).limit_denominator(1000)
            info.append(f"    Fraction: {frac}")

    elif isinstance(num, float):
        info.append(f"  Value: {num}")
        info.append(f"  Scientific: {num:.10e}")
        info.append(f"  Floor: {math.floor(num)}")
        info.append(f"  Ceil: {math.ceil(num)}")
        frac = Fraction(num).limit_denominator(1000)
        info.append(f"  Fraction: {frac}")

    return "\n".join(info)


def _is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n < 4:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True


def _factorize(n: int) -> str:
    if n <= 1:
        return str(n)
    factors = []
    d = 2
    while d * d <= n:
        while n % d == 0:
            factors.append(d)
            n //= d
        d += 1
    if n > 1:
        factors.append(n)
    if len(factors) == 1:
        return f"{factors[0]} (prime)"
    return " × ".join(str(f) for f in factors)


# ─── Advanced Math ────────────────────────────────────────────
def solve_quadratic(a: float, b: float, c: float) -> str:
    """Solve ax² + bx + c = 0."""
    if a == 0:
        if b == 0:
            return "Not a valid equation (a=0, b=0)."
        x = -c / b
        return f"Linear equation: x = {x}"

    discriminant = b ** 2 - 4 * a * c

    if discriminant > 0:
        x1 = (-b + math.sqrt(discriminant)) / (2 * a)
        x2 = (-b - math.sqrt(discriminant)) / (2 * a)
        return (
            f"Quadratic: {a}x² + {b}x + {c} = 0\n"
            f"  Discriminant: {discriminant} (positive → 2 real roots)\n"
            f"  x₁ = {x1:.6f}\n"
            f"  x₂ = {x2:.6f}"
        )
    elif discriminant == 0:
        x = -b / (2 * a)
        return (
            f"Quadratic: {a}x² + {b}x + {c} = 0\n"
            f"  Discriminant: 0 (one repeated root)\n"
            f"  x = {x:.6f}"
        )
    else:
        real = -b / (2 * a)
        imag = math.sqrt(abs(discriminant)) / (2 * a)
        return (
            f"Quadratic: {a}x² + {b}x + {c} = 0\n"
            f"  Discriminant: {discriminant} (negative → complex roots)\n"
            f"  x₁ = {real:.6f} + {imag:.6f}i\n"
            f"  x₂ = {real:.6f} - {imag:.6f}i"
        )


def statistics_calc(numbers: list) -> str:
    """Calculate comprehensive statistics for a list of numbers."""
    if not numbers:
        return "No numbers provided."

    n = len(numbers)
    nums = sorted(float(x) for x in numbers)
    total = sum(nums)
    mean = total / n

    # Median
    if n % 2:
        median = nums[n // 2]
    else:
        median = (nums[n // 2 - 1] + nums[n // 2]) / 2

    # Mode
    from collections import Counter
    counts = Counter(nums)
    mode_val = counts.most_common(1)[0] if counts else (0, 0)

    # Variance and std dev
    variance = sum((x - mean) ** 2 for x in nums) / n
    std_dev = math.sqrt(variance)

    # Quartiles
    q1 = nums[n // 4] if n >= 4 else nums[0]
    q3 = nums[3 * n // 4] if n >= 4 else nums[-1]
    iqr = q3 - q1

    return (
        f"Statistical Analysis ({n} values):\n"
        f"  Sum: {total:.4f}\n"
        f"  Mean: {mean:.4f}\n"
        f"  Median: {median:.4f}\n"
        f"  Mode: {mode_val[0]} (appears {mode_val[1]}x)\n"
        f"  Min: {nums[0]:.4f}\n"
        f"  Max: {nums[-1]:.4f}\n"
        f"  Range: {nums[-1] - nums[0]:.4f}\n"
        f"  Variance: {variance:.4f}\n"
        f"  Std Dev: {std_dev:.4f}\n"
        f"  Q1: {q1:.4f}\n"
        f"  Q3: {q3:.4f}\n"
        f"  IQR: {iqr:.4f}"
    )


def matrix_operations(matrix_a: list, matrix_b: list = None, operation: str = "info") -> str:
    """Basic matrix operations: determinant, transpose, multiply, info."""
    if not matrix_a:
        return "Empty matrix."

    rows = len(matrix_a)
    cols = len(matrix_a[0]) if matrix_a else 0

    if operation == "info":
        flat = [v for row in matrix_a for v in row]
        return (
            f"Matrix ({rows}×{cols}):\n"
            f"  {matrix_a}\n"
            f"  Sum: {sum(flat)}\n"
            f"  Min: {min(flat)}\n"
            f"  Max: {max(flat)}"
        )

    elif operation == "transpose":
        t = [[matrix_a[j][i] for j in range(rows)] for i in range(cols)]
        return f"Transpose ({cols}×{rows}):\n  {t}"

    elif operation == "determinant":
        if rows != cols:
            return "Determinant only for square matrices."
        if rows == 2:
            det = matrix_a[0][0] * matrix_a[1][1] - matrix_a[0][1] * matrix_a[1][0]
            return f"Determinant (2×2): {det}"
        elif rows == 3:
            a = matrix_a
            det = (a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1])
                   - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
                   + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]))
            return f"Determinant (3×3): {det}"
        return "Determinant only supported for 2×2 and 3×3 matrices."

    elif operation == "multiply" and matrix_b:
        if cols != len(matrix_b):
            return f"Cannot multiply {rows}×{cols} by {len(matrix_b)}×{len(matrix_b[0]) if matrix_b else 0}."
        b_cols = len(matrix_b[0])
        result = [[sum(matrix_a[i][k] * matrix_b[k][j] for k in range(cols)) for j in range(b_cols)] for i in range(rows)]
        return f"Product ({rows}×{b_cols}):\n  {result}"

    return f"Unknown matrix operation: {operation}. Available: info, transpose, determinant, multiply"


def generate_primes(limit: int = 100) -> str:
    """Generate prime numbers up to a limit."""
    limit = min(limit, 10000)
    sieve = [True] * (limit + 1)
    sieve[0] = sieve[1] = False
    for i in range(2, int(limit ** 0.5) + 1):
        if sieve[i]:
            for j in range(i * i, limit + 1, i):
                sieve[j] = False
    primes = [i for i in range(limit + 1) if sieve[i]]
    return f"Primes up to {limit} ({len(primes)} found):\n  {primes[:100]}" + (f"\n  ... ({len(primes) - 100} more)" if len(primes) > 100 else "")


def fibonacci(n: int = 20) -> str:
    """Generate Fibonacci sequence."""
    n = min(n, 100)
    seq = [0, 1]
    for _ in range(n - 2):
        seq.append(seq[-1] + seq[-2])
    return f"Fibonacci ({n} terms):\n  {seq}"


def gcd_lcm(a: int, b: int) -> str:
    """Calculate GCD and LCM."""
    g = math.gcd(a, b)
    l = abs(a * b) // g if g else 0
    return f"GCD({a}, {b}) = {g}\nLCM({a}, {b}) = {l}"


def percentage_calc(operation: str, value: float = 0, total: float = 0,
                     percent: float = 0) -> str:
    """Percentage calculations."""
    if operation == "of":
        result = (percent / 100) * total
        return f"{percent}% of {total} = {result}"
    elif operation == "is":
        if total == 0:
            return "Cannot divide by zero."
        result = (value / total) * 100
        return f"{value} is {result:.2f}% of {total}"
    elif operation == "change":
        if value == 0:
            return "Cannot calculate change from zero."
        change = ((total - value) / value) * 100
        return f"Change from {value} to {total} = {change:+.2f}%"
    elif operation == "increase":
        result = value * (1 + percent / 100)
        return f"{value} + {percent}% = {result}"
    elif operation == "decrease":
        result = value * (1 - percent / 100)
        return f"{value} - {percent}% = {result}"
    return f"Unknown percentage operation. Available: of, is, change, increase, decrease"


# ─── Unified Interface ───────────────────────────────────────
def math_science_operation(operation: str, **kwargs) -> str:
    """Unified math and science interface."""
    ops = {
        "constant": lambda: get_constant(kwargs.get("name", "list")),
        "base_convert": lambda: base_convert(kwargs.get("value", "0"), int(kwargs.get("from_base", 10)), int(kwargs.get("to_base", 2))),
        "number_info": lambda: number_info(kwargs.get("value", "0")),
        "quadratic": lambda: solve_quadratic(float(kwargs.get("a", 1)), float(kwargs.get("b", 0)), float(kwargs.get("c", 0))),
        "statistics": lambda: statistics_calc(kwargs.get("numbers", [])),
        "matrix": lambda: matrix_operations(kwargs.get("matrix_a", []), kwargs.get("matrix_b"), kwargs.get("matrix_op", "info")),
        "primes": lambda: generate_primes(int(kwargs.get("limit", 100))),
        "fibonacci": lambda: fibonacci(int(kwargs.get("n", 20))),
        "gcd_lcm": lambda: gcd_lcm(int(kwargs.get("a", 0)), int(kwargs.get("b", 0))),
        "percentage": lambda: percentage_calc(kwargs.get("calc_type", "of"), float(kwargs.get("value", 0)), float(kwargs.get("total", 0)), float(kwargs.get("percent", 0))),
    }
    handler = ops.get(operation)
    if handler:
        return handler()
    return f"Unknown math operation: {operation}. Available: {', '.join(ops.keys())}"
