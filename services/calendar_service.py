"""Business logic for College Academic Calendar and Combined Upcoming Schedule."""

from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from database.db import execute_query, fetch_all, fetch_one
from database.queries import VALID_EVENT_TYPES, save_calendar_event
from services.assignment_service import fetch_assignments
from utils.validators import validate_date_range, validate_non_empty_text


def _now_iso() -> str:
    """Return current local timestamp as ISO-8601 string."""
    return datetime.now().isoformat(timespec="seconds")


def _to_iso_date(value: Optional[Union[date, str]]) -> Optional[str]:
    """Convert a date or string to YYYY-MM-DD."""
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value.isoformat()
    text = str(value).strip()
    if not text:
        return None
    date.fromisoformat(text)
    return text


def _to_time_str(value: Optional[Union[time, str]]) -> Optional[str]:
    """Convert a time or string to HH:MM."""
    if value is None:
        return None
    if isinstance(value, time):
        return value.strftime("%H:%M")
    text = str(value).strip()
    if not text:
        return None
    parts = text.split(":")
    time(int(parts[0]), int(parts[1]))
    return f"{int(parts[0]):02d}:{int(parts[1]):02d}"


def _to_iso_datetime(value: Optional[Union[datetime, str]]) -> Optional[str]:
    """Convert a datetime or string to ISO-8601."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    text = str(value).strip()
    if not text:
        return None
    return datetime.fromisoformat(text).isoformat(timespec="seconds")


def create_calendar_event(
    title: str,
    event_type: str,
    start_date: Union[date, str],
    end_date: Optional[Union[date, str]] = None,
    start_time: Optional[Union[time, str]] = None,
    description: Optional[str] = None,
    reminder_at: Optional[Union[datetime, str]] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Validate and save a college academic calendar event."""
    ok, msg = validate_non_empty_text(title, "Event Title")
    if not ok:
        raise ValueError(msg)

    if event_type not in VALID_EVENT_TYPES:
        raise ValueError(f"Invalid event type: {event_type}")

    start_iso = _to_iso_date(start_date)
    if not start_iso:
        raise ValueError("Start Date is required.")
    end_iso = _to_iso_date(end_date) or start_iso

    ok, msg = validate_date_range(
        date.fromisoformat(start_iso),
        date.fromisoformat(end_iso),
        "Start Date",
        "End Date",
    )
    if not ok:
        raise ValueError(msg)

    time_str = _to_time_str(start_time)
    reminder_iso = _to_iso_datetime(reminder_at)
    if reminder_iso:
        end_d = date.fromisoformat(end_iso)
        event_end_dt = datetime(end_d.year, end_d.month, end_d.day, 23, 59, 59)
        if datetime.fromisoformat(reminder_iso) > event_end_dt:
            raise ValueError("Reminder date/time cannot be after the event end date.")

    existing = fetch_one(
        """
        SELECT id FROM calendar_events
        WHERE lower(trim(title)) = lower(trim(?))
          AND event_type = ?
          AND start_date = ?;
        """,
        (title, event_type, start_iso),
        db_path=db_path,
    )
    if existing is not None:
        raise ValueError(
            f"Event '{title.strip()}' ({event_type}) on {start_iso} already exists."
        )

    return save_calendar_event(
        title=title.strip(),
        event_type=event_type,
        start_date=start_iso,
        end_date=end_iso,
        start_time=time_str,
        description=description.strip() if description else None,
        reminder_at=reminder_iso,
        db_path=db_path,
    )


def get_calendar_event(
    event_id: int,
    db_path: Optional[Union[str, Path]] = None,
) -> Optional[Dict[str, Any]]:
    """Fetch a single calendar event by ID."""
    row = fetch_one(
        "SELECT * FROM calendar_events WHERE id = ?;",
        (event_id,),
        db_path=db_path,
    )
    return dict(row) if row is not None else None


def update_calendar_event(
    event_id: int,
    title: str,
    event_type: str,
    start_date: Union[date, str],
    end_date: Optional[Union[date, str]] = None,
    start_time: Optional[Union[time, str]] = None,
    description: Optional[str] = None,
    reminder_at: Optional[Union[datetime, str]] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Validate and update an existing calendar event."""
    if get_calendar_event(event_id, db_path=db_path) is None:
        raise ValueError(f"Event ID {event_id} does not exist.")

    ok, msg = validate_non_empty_text(title, "Event Title")
    if not ok:
        raise ValueError(msg)
    if event_type not in VALID_EVENT_TYPES:
        raise ValueError(f"Invalid event type: {event_type}")

    start_iso = _to_iso_date(start_date)
    if not start_iso:
        raise ValueError("Start Date is required.")
    end_iso = _to_iso_date(end_date) or start_iso

    ok, msg = validate_date_range(
        date.fromisoformat(start_iso),
        date.fromisoformat(end_iso),
        "Start Date",
        "End Date",
    )
    if not ok:
        raise ValueError(msg)

    time_str = _to_time_str(start_time)
    reminder_iso = _to_iso_datetime(reminder_at)
    if reminder_iso:
        end_d = date.fromisoformat(end_iso)
        event_end_dt = datetime(end_d.year, end_d.month, end_d.day, 23, 59, 59)
        if datetime.fromisoformat(reminder_iso) > event_end_dt:
            raise ValueError("Reminder date/time cannot be after the event end date.")

    execute_query(
        """
        UPDATE calendar_events
        SET title = ?, event_type = ?, start_date = ?, end_date = ?,
            start_time = ?, description = ?, reminder_at = ?, updated_at = ?
        WHERE id = ?;
        """,
        (
            title.strip(),
            event_type,
            start_iso,
            end_iso,
            time_str,
            description.strip() if description else None,
            reminder_iso,
            _now_iso(),
            event_id,
        ),
        db_path=db_path,
    )
    return event_id


def delete_calendar_event(
    event_id: int,
    db_path: Optional[Union[str, Path]] = None,
) -> None:
    """Delete a calendar event by ID."""
    execute_query("DELETE FROM calendar_events WHERE id = ?;", (event_id,), db_path=db_path)


def fetch_all_events(
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Fetch all calendar events sorted by start_date ascending."""
    rows = fetch_all(
        "SELECT * FROM calendar_events ORDER BY start_date ASC, COALESCE(start_time, '00:00') ASC, id ASC;",
        db_path=db_path,
    )
    return [dict(r) for r in rows]


def fetch_events_by_type(
    event_type: str,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Fetch calendar events matching a specific event_type."""
    if event_type == "All":
        return fetch_all_events(db_path=db_path)
    rows = fetch_all(
        """
        SELECT * FROM calendar_events
        WHERE event_type = ?
        ORDER BY start_date ASC, COALESCE(start_time, '00:00') ASC, id ASC;
        """,
        (event_type,),
        db_path=db_path,
    )
    return [dict(r) for r in rows]


def fetch_events_by_date_range(
    start_date: Union[date, str],
    end_date: Union[date, str],
    event_type: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Fetch calendar events overlapping [start_date, end_date]."""
    start_iso = _to_iso_date(start_date)
    end_iso = _to_iso_date(end_date)
    ok, msg = validate_date_range(
        date.fromisoformat(start_iso),
        date.fromisoformat(end_iso),
        "From Date",
        "To Date",
    )
    if not ok:
        raise ValueError(msg)

    clauses = ["COALESCE(end_date, start_date) >= ?", "start_date <= ?"]
    params: List[Any] = [start_iso, end_iso]
    if event_type and event_type != "All":
        clauses.append("event_type = ?")
        params.append(event_type)

    rows = fetch_all(
        f"""
        SELECT * FROM calendar_events
        WHERE {' AND '.join(clauses)}
        ORDER BY start_date ASC, COALESCE(start_time, '00:00') ASC, id ASC;
        """,
        tuple(params),
        db_path=db_path,
    )
    return [dict(r) for r in rows]


def fetch_events_by_month(
    year: int,
    month: int,
    event_type: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Fetch calendar events occurring in a given year and month."""
    if month < 1 or month > 12:
        raise ValueError("Month must be between 1 and 12.")
    month_start = date(year, month, 1)
    if month == 12:
        month_end = date(year, 12, 31)
    else:
        next_month = date(year, month + 1, 1)
        month_end = date.fromordinal(next_month.toordinal() - 1)
    return fetch_events_by_date_range(
        month_start, month_end, event_type=event_type, db_path=db_path
    )


def fetch_upcoming_events(
    reference_date: Optional[Union[date, str]] = None,
    event_type: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Fetch future or ongoing college events sorted by start_date."""
    ref_iso = _to_iso_date(reference_date) or date.today().isoformat()
    clauses = ["COALESCE(end_date, start_date) >= ?"]
    params: List[Any] = [ref_iso]
    if event_type and event_type != "All":
        clauses.append("event_type = ?")
        params.append(event_type)

    rows = fetch_all(
        f"""
        SELECT * FROM calendar_events
        WHERE {' AND '.join(clauses)}
        ORDER BY start_date ASC, COALESCE(start_time, '00:00') ASC, id ASC;
        """,
        tuple(params),
        db_path=db_path,
    )
    return [dict(r) for r in rows]


def get_combined_upcoming_schedule(
    reference_date: Optional[Union[date, str]] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Combine pending assignments and upcoming college events chronologically."""
    ref_iso = _to_iso_date(reference_date) or date.today().isoformat()
    ref_dt = datetime.combine(date.fromisoformat(ref_iso), time(0, 0))

    combined: List[Dict[str, Any]] = []

    for event in fetch_upcoming_events(reference_date=ref_iso, db_path=db_path):
        combined.append(
            {
                "source_type": "College Event",
                "source_id": event["id"],
                "title": event["title"],
                "category": event["event_type"],
                "date": event["start_date"],
                "end_date": event.get("end_date"),
                "time": event.get("start_time") or "",
                "details": event.get("description") or "",
            }
        )

    for assign in fetch_assignments(current_dt=ref_dt, db_path=db_path):
        if assign["status"] == "Completed":
            continue
        combined.append(
            {
                "source_type": "Assignment Deadline",
                "source_id": assign["id"],
                "title": assign["title"],
                "category": f"{assign['subject_name']} ({assign['priority']} Priority)",
                "date": assign["deadline_date"],
                "end_date": assign["deadline_date"],
                "time": assign.get("deadline_time") or "",
                "details": assign["reminder_state"]["message"],
            }
        )

    combined.sort(
        key=lambda item: (
            item["date"],
            item["time"] or "23:59",
            item["source_type"],
            item["title"].lower(),
        )
    )
    return combined
