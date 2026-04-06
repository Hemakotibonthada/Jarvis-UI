"""
World Clock & Time Zone Module — Time zone conversions, world clock display,
countdown timers, stopwatch, and meeting scheduler across time zones.
"""

import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, available_timezones
from core.logger import get_logger

log = get_logger("worldclock")


# Common timezone aliases
TZ_ALIASES = {
    "est": "America/New_York", "edt": "America/New_York",
    "cst": "America/Chicago", "cdt": "America/Chicago",
    "mst": "America/Denver", "mdt": "America/Denver",
    "pst": "America/Los_Angeles", "pdt": "America/Los_Angeles",
    "gmt": "Europe/London", "utc": "UTC",
    "bst": "Europe/London", "cet": "Europe/Berlin",
    "eet": "Europe/Helsinki", "ist": "Asia/Kolkata",
    "jst": "Asia/Tokyo", "kst": "Asia/Seoul",
    "cst_asia": "Asia/Shanghai", "aest": "Australia/Sydney",
    "nzst": "Pacific/Auckland", "hst": "Pacific/Honolulu",
    "sgt": "Asia/Singapore", "hkt": "Asia/Hong_Kong",
    "brt": "America/Sao_Paulo", "art": "America/Argentina/Buenos_Aires",
    "msk": "Europe/Moscow", "gulf": "Asia/Dubai",
}

# Major cities and their timezones
CITY_TIMEZONES = {
    "new york": "America/New_York", "los angeles": "America/Los_Angeles",
    "chicago": "America/Chicago", "denver": "America/Denver",
    "london": "Europe/London", "paris": "Europe/Paris",
    "berlin": "Europe/Berlin", "rome": "Europe/Rome",
    "moscow": "Europe/Moscow", "dubai": "Asia/Dubai",
    "mumbai": "Asia/Kolkata", "delhi": "Asia/Kolkata",
    "bangalore": "Asia/Kolkata", "tokyo": "Asia/Tokyo",
    "beijing": "Asia/Shanghai", "shanghai": "Asia/Shanghai",
    "hong kong": "Asia/Hong_Kong", "singapore": "Asia/Singapore",
    "sydney": "Australia/Sydney", "melbourne": "Australia/Melbourne",
    "auckland": "Pacific/Auckland", "honolulu": "Pacific/Honolulu",
    "toronto": "America/Toronto", "vancouver": "America/Vancouver",
    "sao paulo": "America/Sao_Paulo", "buenos aires": "America/Argentina/Buenos_Aires",
    "seoul": "Asia/Seoul", "bangkok": "Asia/Bangkok",
    "cairo": "Africa/Cairo", "johannesburg": "Africa/Johannesburg",
    "istanbul": "Europe/Istanbul", "madrid": "Europe/Madrid",
    "amsterdam": "Europe/Amsterdam", "zurich": "Europe/Zurich",
    "stockholm": "Europe/Stockholm", "oslo": "Europe/Oslo",
    "helsinki": "Europe/Helsinki", "warsaw": "Europe/Warsaw",
    "athens": "Europe/Athens", "lisbon": "Europe/Lisbon",
    "dublin": "Europe/Dublin", "edinburgh": "Europe/London",
    "mexico city": "America/Mexico_City", "lima": "America/Lima",
    "bogota": "America/Bogota", "santiago": "America/Santiago",
    "lagos": "Africa/Lagos", "nairobi": "Africa/Nairobi",
    "riyadh": "Asia/Riyadh", "tehran": "Asia/Tehran",
    "karachi": "Asia/Karachi", "dhaka": "Asia/Dhaka",
    "jakarta": "Asia/Jakarta", "manila": "Asia/Manila",
    "hanoi": "Asia/Ho_Chi_Minh", "taipei": "Asia/Taipei",
    "kuala lumpur": "Asia/Kuala_Lumpur",
}


def _resolve_tz(tz_input: str) -> str:
    """Resolve a timezone name, city, or abbreviation to IANA timezone."""
    if not tz_input:
        return ""
    lower = tz_input.lower().strip()

    # Check aliases
    if lower in TZ_ALIASES:
        return TZ_ALIASES[lower]

    # Check cities
    if lower in CITY_TIMEZONES:
        return CITY_TIMEZONES[lower]

    # Check if it's already a valid IANA zone
    if tz_input in available_timezones():
        return tz_input

    # Partial match on IANA zones
    for tz in sorted(available_timezones()):
        if lower in tz.lower():
            return tz

    return ""


def get_time_in_zone(zone: str) -> str:
    """Get current time in a specific timezone."""
    tz_name = _resolve_tz(zone)
    if not tz_name:
        return f"Unknown timezone/city: '{zone}'. Try city names like 'tokyo', 'london', or IANA names like 'America/New_York'."

    try:
        tz = ZoneInfo(tz_name)
        now = datetime.now(tz)
        utc_offset = now.strftime("%z")
        utc_offset_formatted = f"UTC{utc_offset[:3]}:{utc_offset[3:]}"

        return (
            f"Time in {tz_name}:\n"
            f"  {now.strftime('%A, %B %d, %Y')}\n"
            f"  {now.strftime('%I:%M:%S %p')} ({now.strftime('%H:%M:%S')})\n"
            f"  Offset: {utc_offset_formatted}"
        )
    except Exception as e:
        return f"Timezone error: {e}"


def world_clock(cities: list = None) -> str:
    """Show current time in multiple cities."""
    if not cities:
        cities = ["new york", "london", "tokyo", "sydney", "mumbai", "dubai"]

    lines = ["World Clock:", ""]
    max_name = max(len(c) for c in cities)

    for city in cities:
        tz_name = _resolve_tz(city)
        if not tz_name:
            lines.append(f"  {city:<{max_name}}  — Unknown timezone")
            continue
        try:
            tz = ZoneInfo(tz_name)
            now = datetime.now(tz)
            time_str = now.strftime("%I:%M %p")
            date_str = now.strftime("%b %d")
            day = now.strftime("%a")
            offset = now.strftime("%z")

            # Day/night indicator
            hour = now.hour
            if 6 <= hour < 18:
                indicator = "☀"
            elif 18 <= hour < 21 or 5 <= hour < 6:
                indicator = "🌅"
            else:
                indicator = "🌙"

            lines.append(f"  {indicator} {city.title():<{max_name}}  {time_str:>8}  {day} {date_str}  (UTC{offset[:3]}:{offset[3:]})")
        except Exception:
            lines.append(f"  {city:<{max_name}}  — Error")

    return "\n".join(lines)


def convert_time(time_str: str, from_zone: str, to_zone: str) -> str:
    """Convert a time from one timezone to another."""
    from_tz_name = _resolve_tz(from_zone)
    to_tz_name = _resolve_tz(to_zone)

    if not from_tz_name:
        return f"Unknown source timezone: '{from_zone}'"
    if not to_tz_name:
        return f"Unknown target timezone: '{to_zone}'"

    try:
        from_tz = ZoneInfo(from_tz_name)
        to_tz = ZoneInfo(to_tz_name)

        # Parse time
        formats = ["%H:%M", "%I:%M %p", "%I:%M%p", "%H:%M:%S"]
        parsed = None
        for fmt in formats:
            try:
                t = datetime.strptime(time_str.strip(), fmt)
                parsed = datetime.now(from_tz).replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
                break
            except ValueError:
                continue

        if not parsed:
            return f"Could not parse time: '{time_str}'. Use formats like '14:30' or '2:30 PM'."

        converted = parsed.astimezone(to_tz)
        diff_hours = (converted.utcoffset().total_seconds() - parsed.utcoffset().total_seconds()) / 3600

        return (
            f"Time Conversion:\n"
            f"  {parsed.strftime('%I:%M %p')} in {from_tz_name}\n"
            f"  = {converted.strftime('%I:%M %p')} in {to_tz_name}\n"
            f"  ({converted.strftime('%A, %b %d')})\n"
            f"  Difference: {diff_hours:+.1f} hours"
        )
    except Exception as e:
        return f"Conversion error: {e}"


def meeting_planner(time_str: str, host_zone: str, attendee_zones: list) -> str:
    """Plan a meeting across timezones. Show the time for all attendees."""
    host_tz = _resolve_tz(host_zone)
    if not host_tz:
        return f"Unknown host timezone: '{host_zone}'"

    try:
        tz = ZoneInfo(host_tz)
        formats = ["%H:%M", "%I:%M %p", "%I:%M%p"]
        parsed = None
        for fmt in formats:
            try:
                t = datetime.strptime(time_str.strip(), fmt)
                parsed = datetime.now(tz).replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
                break
            except ValueError:
                continue

        if not parsed:
            return f"Could not parse time: '{time_str}'"

        lines = [
            f"Meeting Planner:",
            f"  Proposed time: {parsed.strftime('%I:%M %p')} {host_tz} ({host_zone})",
            "",
        ]

        all_zones = [(host_zone, host_tz)] + [(z, _resolve_tz(z)) for z in attendee_zones]

        for zone_name, tz_name in all_zones:
            if not tz_name:
                lines.append(f"  ❓ {zone_name}: Unknown timezone")
                continue
            target_tz = ZoneInfo(tz_name)
            target_time = parsed.astimezone(target_tz)
            hour = target_time.hour

            # Availability indicator
            if 9 <= hour < 17:
                indicator = "✓ Business hours"
            elif 7 <= hour < 9 or 17 <= hour < 21:
                indicator = "⚠ Early/late"
            else:
                indicator = "✗ Outside hours"

            is_host = "(host)" if tz_name == host_tz else ""
            lines.append(
                f"  {target_time.strftime('%I:%M %p'):>8} {zone_name} — {indicator} {is_host}"
            )

        return "\n".join(lines)
    except Exception as e:
        return f"Meeting planner error: {e}"


def list_timezones(region: str = "") -> str:
    """List available timezones, optionally filtered by region."""
    all_tz = sorted(available_timezones())
    if region:
        all_tz = [tz for tz in all_tz if region.lower() in tz.lower()]

    if not all_tz:
        return f"No timezones matching '{region}'. Try: America, Europe, Asia, Pacific, Africa."

    # Group by region
    regions = {}
    for tz in all_tz:
        parts = tz.split("/")
        r = parts[0]
        regions.setdefault(r, []).append(tz)

    lines = []
    for r, zones in sorted(regions.items()):
        lines.append(f"  {r} ({len(zones)} zones):")
        for tz in zones[:10]:
            try:
                now = datetime.now(ZoneInfo(tz))
                lines.append(f"    {tz}: {now.strftime('%H:%M')} (UTC{now.strftime('%z')[:3]})")
            except Exception:
                lines.append(f"    {tz}")

        if len(zones) > 10:
            lines.append(f"    ... and {len(zones) - 10} more")

    total = len(all_tz)
    return f"Timezones ({total}):\n" + "\n".join(lines[:60])


def time_until(target: str, zone: str = "") -> str:
    """Calculate time until a specific date/time."""
    tz_name = _resolve_tz(zone) if zone else None
    tz = ZoneInfo(tz_name) if tz_name else None

    formats = [
        "%Y-%m-%d %H:%M", "%Y-%m-%d", "%m/%d/%Y %H:%M",
        "%m/%d/%Y", "%B %d, %Y", "%b %d, %Y",
    ]

    parsed = None
    for fmt in formats:
        try:
            parsed = datetime.strptime(target.strip(), fmt)
            if tz:
                parsed = parsed.replace(tzinfo=tz)
            break
        except ValueError:
            continue

    if not parsed:
        return f"Could not parse date: '{target}'. Use: YYYY-MM-DD HH:MM"

    now = datetime.now(tz) if tz else datetime.now()
    if parsed.tzinfo is None and now.tzinfo:
        parsed = parsed.replace(tzinfo=now.tzinfo)

    diff = parsed - now

    if diff.total_seconds() < 0:
        total_seconds = abs(diff.total_seconds())
        direction = "ago"
    else:
        total_seconds = diff.total_seconds()
        direction = "from now"

    days = int(total_seconds // 86400)
    hours = int((total_seconds % 86400) // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)

    parts = []
    if days:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if not parts:
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")

    return (
        f"Time {'until' if direction == 'from now' else 'since'}: {target}\n"
        f"  {', '.join(parts)} {direction}\n"
        f"  ({int(total_seconds):,} total seconds)"
    )


def time_difference(zone1: str, zone2: str) -> str:
    """Calculate time difference between two zones."""
    tz1_name = _resolve_tz(zone1)
    tz2_name = _resolve_tz(zone2)

    if not tz1_name:
        return f"Unknown timezone: '{zone1}'"
    if not tz2_name:
        return f"Unknown timezone: '{zone2}'"

    now1 = datetime.now(ZoneInfo(tz1_name))
    now2 = datetime.now(ZoneInfo(tz2_name))

    offset1 = now1.utcoffset().total_seconds() / 3600
    offset2 = now2.utcoffset().total_seconds() / 3600
    diff = offset2 - offset1

    return (
        f"Time Difference:\n"
        f"  {zone1}: {now1.strftime('%I:%M %p')} (UTC{offset1:+.1f})\n"
        f"  {zone2}: {now2.strftime('%I:%M %p')} (UTC{offset2:+.1f})\n"
        f"  Difference: {diff:+.1f} hours\n"
        f"  {zone2} is {'ahead' if diff > 0 else 'behind'} by {abs(diff):.1f} hours"
    )


# ─── Unified Interface ───────────────────────────────────────
def timezone_operation(operation: str, **kwargs) -> str:
    """Unified timezone operations."""
    ops = {
        "time_in": lambda: get_time_in_zone(kwargs.get("zone", "")),
        "world_clock": lambda: world_clock(kwargs.get("cities", None)),
        "convert": lambda: convert_time(kwargs.get("time", ""), kwargs.get("from_zone", ""), kwargs.get("to_zone", "")),
        "meeting": lambda: meeting_planner(kwargs.get("time", ""), kwargs.get("host_zone", ""), kwargs.get("attendee_zones", [])),
        "list": lambda: list_timezones(kwargs.get("region", "")),
        "until": lambda: time_until(kwargs.get("target", ""), kwargs.get("zone", "")),
        "difference": lambda: time_difference(kwargs.get("zone1", ""), kwargs.get("zone2", "")),
    }

    handler = ops.get(operation)
    if handler:
        return handler()
    return f"Unknown timezone operation: {operation}. Available: {', '.join(ops.keys())}"
