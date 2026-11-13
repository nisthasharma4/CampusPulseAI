"""Business logic for Student Profile Management in CampusPulse AI."""

from datetime import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from database.queries import (
    clear_student_avatar,
    get_student_profile,
    save_student_profile,
    update_student_avatar,
)
from utils.avatars import (
    PRESET_AVATARS,
    delete_custom_avatar_file,
    validate_and_save_avatar_upload,
)
from utils.config import (
    ATTENDANCE_TARGET,
    DEFAULT_BREAK_MINUTES,
    DEFAULT_STUDY_SESSION_MINUTES,
)
from utils.validators import (
    validate_non_empty_text,
    validate_percentage,
    validate_positive_number,
)

DAYS_OF_WEEK = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def _parse_time_str(time_str: Optional[str], fallback: time) -> time:
    """Parse an HH:MM string into a datetime.time object."""
    if not time_str:
        return fallback
    try:
        parts = str(time_str).strip().split(":")
        return time(int(parts[0]), int(parts[1]))
    except (ValueError, IndexError):
        return fallback


def get_profile(
    db_path: Optional[Union[str, Path]] = None,
) -> Optional[Dict[str, Any]]:
    """Return the saved student profile as a dictionary, or None if not created."""
    row = get_student_profile(db_path=db_path)
    if row is None:
        return None
    profile = dict(row)
    raw_days = profile.get("available_days") or ""
    profile["available_days_list"] = [
        d.strip() for d in raw_days.split(",") if d.strip()
    ]
    daily_minutes = profile.get("daily_available_minutes") or 0
    profile["daily_available_hours"] = round(daily_minutes / 60.0, 2)
    profile["preferred_start_time_obj"] = _parse_time_str(
        profile.get("preferred_start_time"), time(18, 0)
    )
    profile["preferred_end_time_obj"] = _parse_time_str(
        profile.get("preferred_end_time"), time(21, 0)
    )
    return profile


def save_profile(
    name: str,
    college_name: Optional[str] = None,
    branch: Optional[str] = None,
    semester: int = 1,
    weekly_study_target: int = 14,
    daily_available_hours: float = 2.0,
    preferred_start_time: time = time(18, 0),
    preferred_end_time: time = time(21, 0),
    available_days: Optional[List[str]] = None,
    session_duration_minutes: int = DEFAULT_STUDY_SESSION_MINUTES,
    break_duration_minutes: int = DEFAULT_BREAK_MINUTES,
    attendance_target: float = float(ATTENDANCE_TARGET),
    avatar_preset: Optional[str] = None,
    avatar_path: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Validate and save (create or update) the single-user student profile."""
    ok, msg = validate_non_empty_text(name, "Student Name")
    if not ok:
        raise ValueError(msg)

    ok, msg = validate_positive_number(semester, "Semester", allow_zero=False)
    if not ok or int(semester) != semester:
        raise ValueError("Semester must be a positive whole number.")

    ok, msg = validate_positive_number(
        weekly_study_target, "Weekly Study Target (hours)", allow_zero=True
    )
    if not ok:
        raise ValueError(msg)

    ok, msg = validate_positive_number(
        daily_available_hours, "Daily Available Study Hours", allow_zero=True
    )
    if not ok:
        raise ValueError(msg)

    if preferred_start_time >= preferred_end_time:
        raise ValueError("Preferred Study End Time must be after Preferred Start Time.")

    ok, msg = validate_positive_number(
        session_duration_minutes, "Preferred Study Session Duration", allow_zero=False
    )
    if not ok:
        raise ValueError(msg)

    ok, msg = validate_positive_number(
        break_duration_minutes, "Break Duration", allow_zero=True
    )
    if not ok:
        raise ValueError(msg)

    ok, msg = validate_percentage(attendance_target, "Attendance Target Percentage")
    if not ok:
        raise ValueError(msg)

    days_list = available_days if available_days is not None else []
    days_csv = ",".join(day for day in DAYS_OF_WEEK if day in days_list)
    daily_minutes = int(round(float(daily_available_hours) * 60))

    return save_student_profile(
        name=name.strip(),
        branch=branch.strip() if branch else None,
        semester=int(semester),
        college_name=college_name.strip() if college_name else None,
        weekly_study_target=int(weekly_study_target),
        preferred_start_time=preferred_start_time.strftime("%H:%M"),
        preferred_end_time=preferred_end_time.strftime("%H:%M"),
        available_days=days_csv,
        daily_available_minutes=daily_minutes,
        session_duration_minutes=int(session_duration_minutes),
        break_duration_minutes=int(break_duration_minutes),
        attendance_target=float(attendance_target),
        avatar_preset=avatar_preset,
        avatar_path=avatar_path,
        db_path=db_path,
    )


def set_avatar_preset(
    preset_key: str,
    db_path: Optional[Union[str, Path]] = None,
) -> bool:
    """Set student avatar to one of the built-in SVG presets.

    Cleans up any previously uploaded photo file.
    """
    if preset_key not in PRESET_AVATARS:
        raise ValueError(f"Unknown preset key '{preset_key}'. Choose from: {list(PRESET_AVATARS.keys())}")

    profile = get_student_profile(db_path=db_path)
    if profile is None:
        raise ValueError("Cannot set avatar: student profile does not exist yet.")

    # If student had a custom uploaded photo, remove it
    old_path = profile["avatar_path"] if "avatar_path" in profile.keys() else None
    if old_path:
        delete_custom_avatar_file(old_path)

    return update_student_avatar(
        avatar_preset=preset_key,
        avatar_path=None,
        db_path=db_path,
    )


def set_avatar_upload(
    uploaded_file: Any,
    db_path: Optional[Union[str, Path]] = None,
) -> Tuple[bool, str]:
    """Validate, thumbnail, save uploaded photo and link it to student profile."""
    profile = get_student_profile(db_path=db_path)
    if profile is None:
        return False, "Cannot upload avatar: student profile does not exist yet."

    ok, msg, relative_path = validate_and_save_avatar_upload(uploaded_file)
    if not ok or not relative_path:
        return False, msg

    # Clean up previous photo file if one existed
    old_path = profile["avatar_path"] if "avatar_path" in profile.keys() else None
    if old_path and old_path != relative_path:
        delete_custom_avatar_file(old_path)

    update_student_avatar(
        avatar_preset=None,
        avatar_path=relative_path,
        db_path=db_path,
    )
    return True, "Profile photo updated successfully."


def remove_avatar(
    db_path: Optional[Union[str, Path]] = None,
) -> bool:
    """Reset avatar to default initials SVG, removing any stored photo."""
    profile = get_student_profile(db_path=db_path)
    if profile is None:
        return False
    old_path = profile["avatar_path"] if "avatar_path" in profile.keys() else None
    if old_path:
        delete_custom_avatar_file(old_path)
    return clear_student_avatar(db_path=db_path)
