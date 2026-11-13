"""Reusable presentation formatters for CampusPulse AI.

Provides:
- 12-hour AM/PM time formatting (format_time_12h)
- 12-hour time range formatting (format_time_range_12h)
- 12-hour to canonical 24-hour HH:MM parser (parse_time_12h_to_24h)
- Discrete 12-hour time options generator for UI selectboxes
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any, List, Optional, Tuple, Union


def format_time_12h(value: Any, fallback: str = "—") -> str:
    """Format any time value into a clean 12-hour string (e.g., '6:00 PM', '7:30 AM').

    Supports:
    - 'HH:MM' (e.g. '06:00' -> '6:00 AM', '18:00' -> '6:00 PM')
    - 'HH:MM:SS' (e.g. '19:45:00' -> '7:45 PM')
    - '00:00' -> '12:00 AM', '12:00' -> '12:00 PM'
    - datetime.time and datetime.datetime objects
    - Gracefully handles None, empty strings, and invalid values without crashing
    """
    if value is None:
        return fallback

    s_val = str(value).strip()
    if not s_val or s_val in ("None", "null", "—", "-"):
        return fallback

    h: int
    m: int
    if isinstance(value, (datetime, time)):
        h, m = value.hour, value.minute
    else:
        # Check if already in AM/PM format
        upper = s_val.upper()
        if "AM" in upper or "PM" in upper:
            return s_val

        parts = s_val.split(":")
        if len(parts) >= 2:
            try:
                h = int(parts[0])
                m = int(parts[1])
            except ValueError:
                return s_val
        else:
            return s_val

    if not (0 <= h <= 23 and 0 <= m <= 59):
        return s_val

    period = "AM" if h < 12 else "PM"
    h12 = h % 12
    if h12 == 0:
        h12 = 12

    return f"{h12}:{m:02d} {period}"


def format_time_range_12h(
    start: Any,
    end: Any,
    separator: str = " – ",
    fallback: str = "—",
) -> str:
    """Format start and end times into a clean 12-hour range string (e.g. '7:00 AM – 8:30 AM')."""
    if not start and not end:
        return fallback
    start_fmt = format_time_12h(start, fallback=fallback)
    end_fmt = format_time_12h(end, fallback=fallback)
    if start_fmt == fallback and end_fmt == fallback:
        return fallback
    return f"{start_fmt}{separator}{end_fmt}"


def parse_time_12h_to_24h(val: Any) -> Optional[str]:
    """Convert any 12-hour or 24-hour time representation into canonical 'HH:MM' string.

    Supports:
    - '6:00 PM' -> '18:00'
    - '7:30 AM' -> '07:30'
    - '12:00 AM' -> '00:00'
    - '12:00 PM' -> '12:00'
    - '18:00' -> '18:00'
    - datetime.time / datetime.datetime
    """
    if val is None:
        return None
    if isinstance(val, (datetime, time)):
        return val.strftime("%H:%M")

    s = str(val).strip()
    if not s or s in ("None", "null", "—"):
        return None

    upper = s.upper()
    if "AM" in upper or "PM" in upper:
        is_pm = "PM" in upper
        cleaned = upper.replace("AM", "").replace("PM", "").strip()
        parts = cleaned.split(":")
        if len(parts) >= 2:
            try:
                h = int(parts[0])
                m = int(parts[1])
                if h == 12:
                    h = 12 if is_pm else 0
                elif is_pm:
                    h += 12
                if 0 <= h <= 23 and 0 <= m <= 59:
                    return f"{h:02d}:{m:02d}"
            except ValueError:
                pass

    # Try 24h parse
    parts = s.split(":")
    if len(parts) >= 2:
        try:
            h = int(parts[0])
            m = int(parts[1])
            if 0 <= h <= 23 and 0 <= m <= 59:
                return f"{h:02d}:{m:02d}"
        except ValueError:
            pass

    return None


def parse_time_to_time_obj(val: Any, fallback: Optional[time] = None) -> time:
    """Parse any time input (12h, 24h, time object) into a python datetime.time object."""
    if isinstance(val, time) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.time()
    hhmm = parse_time_12h_to_24h(val)
    if hhmm:
        try:
            parts = hhmm.split(":")
            return time(int(parts[0]), int(parts[1]))
        except Exception:
            pass
    return fallback if fallback is not None else time(18, 0)


def generate_12h_time_options(step_minutes: int = 15) -> List[str]:
    """Generate a sequence of discrete 12-hour formatted time strings covering 24 hours.

    By default generates 96 slots at 15-minute intervals starting from '12:00 AM' to '11:45 PM'.
    """
    options: List[str] = []
    total_minutes = 24 * 60
    for m in range(0, total_minutes, max(1, step_minutes)):
        h = m // 60
        mins = m % 60
        options.append(format_time_12h(time(h, mins)))
    return options
