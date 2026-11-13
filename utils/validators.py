"""Reusable input validation helpers for CampusPulse AI."""

from datetime import date
from typing import Tuple


def validate_non_empty_text(value: str, field_name: str = "Field") -> Tuple[bool, str]:
    """Check that a string is not None, empty, or whitespace-only."""
    if value is None or not str(value).strip():
        return False, f"{field_name} cannot be empty."
    return True, ""


def validate_positive_number(
    value: float,
    field_name: str = "Value",
    allow_zero: bool = False,
) -> Tuple[bool, str]:
    """Check that a numeric value is positive (or >= 0 when allow_zero is True)."""
    if value is None:
        return False, f"{field_name} is required."
    if allow_zero:
        if value < 0:
            return False, f"{field_name} cannot be negative."
    else:
        if value <= 0:
            return False, f"{field_name} must be greater than zero."
    return True, ""


def validate_percentage(value: float, field_name: str = "Percentage") -> Tuple[bool, str]:
    """Check that a percentage value lies between 0 and 100 inclusive."""
    if value is None:
        return False, f"{field_name} is required."
    if value < 0 or value > 100:
        return False, f"{field_name} must be between 0 and 100."
    return True, ""


def validate_date_range(
    start_date: date,
    end_date: date,
    start_label: str = "Start date",
    end_label: str = "End date",
) -> Tuple[bool, str]:
    """Check that end_date is not earlier than start_date."""
    if start_date is None or end_date is None:
        return False, f"Both {start_label.lower()} and {end_label.lower()} are required."
    if end_date < start_date:
        return False, f"{end_label} cannot be earlier than {start_label.lower()}."
    return True, ""
