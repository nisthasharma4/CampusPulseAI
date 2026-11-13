"""Business logic for Assignment Manager and In-App Deadline Reminder Engine."""

from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from database.db import execute_query, fetch_all, fetch_one
from database.queries import (
    VALID_ASSIGNMENT_STATUSES,
    VALID_PRIORITIES,
    save_assignment,
)
from services.subject_service import get_subject
from utils.validators import validate_date_range, validate_non_empty_text

ASSIGNMENT_FILTER_OPTIONS = (
    "All Assignments",
    "Pending",
    "In Progress",
    "Completed",
    "Overdue",
    "Due Today",
    "Due Within 3 Days",
)


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
    """Convert a datetime or string to ISO-8601 YYYY-MM-DDTHH:MM:SS."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    text = str(value).strip()
    if not text:
        return None
    parsed = datetime.fromisoformat(text)
    return parsed.isoformat(timespec="seconds")


def _build_deadline_datetime(deadline_date_str: str, deadline_time_str: Optional[str]) -> datetime:
    """Construct a datetime representing the assignment's exact deadline."""
    d = date.fromisoformat(deadline_date_str)
    if deadline_time_str:
        parts = deadline_time_str.split(":")
        return datetime(d.year, d.month, d.day, int(parts[0]), int(parts[1]), 0)
    return datetime(d.year, d.month, d.day, 23, 59, 59)


def calculate_days_remaining(
    deadline_date_str: str,
    current_dt: Optional[datetime] = None,
) -> int:
    """Return calendar days remaining until deadline (negative if past)."""
    now = current_dt or datetime.now()
    d = date.fromisoformat(deadline_date_str)
    return (d - now.date()).days


def calculate_reminder_state(
    assignment_row: Dict[str, Any],
    current_dt: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Compute reminder category, severity, message, and reminder_triggered flag."""
    now = current_dt or datetime.now()
    status = assignment_row.get("status", "Pending")
    deadline_date_str = assignment_row["deadline_date"]
    deadline_time_str = assignment_row.get("deadline_time")
    reminder_at_str = assignment_row.get("reminder_at")

    if status == "Completed":
        return {
            "category": "Completed",
            "severity": "success",
            "message": "Completed",
            "days_remaining": 0,
            "reminder_triggered": False,
        }

    deadline_dt = _build_deadline_datetime(deadline_date_str, deadline_time_str)
    days_rem = (deadline_dt.date() - now.date()).days

    reminder_triggered = False
    if reminder_at_str:
        try:
            rem_dt = datetime.fromisoformat(reminder_at_str)
            if now >= rem_dt:
                reminder_triggered = True
        except ValueError:
            pass

    if now > deadline_dt:
        return {
            "category": "Overdue",
            "severity": "error",
            "message": "This assignment is overdue.",
            "days_remaining": days_rem,
            "reminder_triggered": reminder_triggered,
        }
    if deadline_dt.date() == now.date():
        return {
            "category": "Due Today",
            "severity": "warning",
            "message": "This assignment is due today.",
            "days_remaining": 0,
            "reminder_triggered": reminder_triggered,
        }
    if 0 < days_rem <= 3:
        return {
            "category": "Due Soon",
            "severity": "warning",
            "message": "This assignment is due soon.",
            "days_remaining": days_rem,
            "reminder_triggered": reminder_triggered,
        }

    return {
        "category": "Upcoming",
        "severity": "info",
        "message": f"Due on {deadline_date_str} ({days_rem} day(s) remaining).",
        "days_remaining": days_rem,
        "reminder_triggered": reminder_triggered,
    }


def create_assignment(
    subject_id: int,
    title: str,
    deadline_date: Union[date, str],
    description: Optional[str] = None,
    assigned_date: Optional[Union[date, str]] = None,
    deadline_time: Optional[Union[time, str]] = None,
    reminder_at: Optional[Union[datetime, str]] = None,
    priority: str = "Medium",
    status: str = "Pending",
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Validate and save a new assignment in SQLite."""
    if get_subject(subject_id, db_path=db_path) is None:
        raise ValueError("Selected subject does not exist.")

    ok, msg = validate_non_empty_text(title, "Assignment Title")
    if not ok:
        raise ValueError(msg)

    if priority not in VALID_PRIORITIES:
        raise ValueError(f"Invalid priority: {priority}")
    if status not in VALID_ASSIGNMENT_STATUSES:
        raise ValueError(f"Invalid status: {status}")

    deadline_iso = _to_iso_date(deadline_date)
    if not deadline_iso:
        raise ValueError("Submission Deadline Date is required.")
    assigned_iso = _to_iso_date(assigned_date)
    time_str = _to_time_str(deadline_time)
    reminder_iso = _to_iso_datetime(reminder_at)

    if assigned_iso:
        ok, msg = validate_date_range(
            date.fromisoformat(assigned_iso),
            date.fromisoformat(deadline_iso),
            "Assigned Date",
            "Submission Deadline Date",
        )
        if not ok:
            raise ValueError(msg)

    if reminder_iso:
        deadline_dt = _build_deadline_datetime(deadline_iso, time_str)
        if datetime.fromisoformat(reminder_iso) > deadline_dt:
            raise ValueError("Reminder date/time cannot be later than the submission deadline.")

    # Prevent accidental duplicate submission for same subject, title, and deadline
    existing = fetch_one(
        """
        SELECT id FROM assignments
        WHERE subject_id = ? AND lower(trim(title)) = lower(trim(?)) AND deadline_date = ?;
        """,
        (subject_id, title, deadline_iso),
        db_path=db_path,
    )
    if existing is not None:
        raise ValueError(
            f"An assignment titled '{title.strip()}' with deadline {deadline_iso} already exists for this subject."
        )

    completed_at = _now_iso() if status == "Completed" else None

    return save_assignment(
        subject_id=subject_id,
        title=title.strip(),
        deadline_date=deadline_iso,
        description=description.strip() if description else None,
        assigned_date=assigned_iso,
        deadline_time=time_str,
        reminder_at=reminder_iso,
        priority=priority,
        status=status,
        completed_at=completed_at,
        db_path=db_path,
    )


def get_assignment(
    assignment_id: int,
    db_path: Optional[Union[str, Path]] = None,
) -> Optional[Dict[str, Any]]:
    """Fetch a single assignment by ID."""
    row = fetch_one(
        """
        SELECT a.*, s.subject_name
        FROM assignments a
        JOIN subjects s ON a.subject_id = s.id
        WHERE a.id = ?;
        """,
        (assignment_id,),
        db_path=db_path,
    )
    return dict(row) if row is not None else None


def update_assignment(
    assignment_id: int,
    subject_id: int,
    title: str,
    deadline_date: Union[date, str],
    description: Optional[str] = None,
    assigned_date: Optional[Union[date, str]] = None,
    deadline_time: Optional[Union[time, str]] = None,
    reminder_at: Optional[Union[datetime, str]] = None,
    priority: str = "Medium",
    status: str = "Pending",
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Update an assignment while preserving historical completed_at / created_at rules."""
    existing = get_assignment(assignment_id, db_path=db_path)
    if existing is None:
        raise ValueError(f"Assignment ID {assignment_id} does not exist.")
    if get_subject(subject_id, db_path=db_path) is None:
        raise ValueError("Selected subject does not exist.")

    ok, msg = validate_non_empty_text(title, "Assignment Title")
    if not ok:
        raise ValueError(msg)
    if priority not in VALID_PRIORITIES:
        raise ValueError(f"Invalid priority: {priority}")
    if status not in VALID_ASSIGNMENT_STATUSES:
        raise ValueError(f"Invalid status: {status}")

    deadline_iso = _to_iso_date(deadline_date)
    if not deadline_iso:
        raise ValueError("Submission Deadline Date is required.")
    assigned_iso = (
        _to_iso_date(assigned_date)
        if assigned_date is not None
        else existing.get("assigned_date")
    )
    time_str = _to_time_str(deadline_time)
    reminder_iso = _to_iso_datetime(reminder_at)

    if assigned_iso:
        ok, msg = validate_date_range(
            date.fromisoformat(assigned_iso),
            date.fromisoformat(deadline_iso),
            "Assigned Date",
            "Submission Deadline Date",
        )
        if not ok:
            raise ValueError(msg)

    if reminder_iso:
        deadline_dt = _build_deadline_datetime(deadline_iso, time_str)
        if datetime.fromisoformat(reminder_iso) > deadline_dt:
            raise ValueError("Reminder date/time cannot be later than the submission deadline.")

    old_status = existing["status"]
    completed_at = existing.get("completed_at")
    if old_status != "Completed" and status == "Completed":
        completed_at = _now_iso()
    elif old_status == "Completed" and status in ("Pending", "In Progress"):
        completed_at = None

    execute_query(
        """
        UPDATE assignments
        SET subject_id = ?, title = ?, description = ?, assigned_date = ?,
            deadline_date = ?, deadline_time = ?, reminder_at = ?,
            priority = ?, status = ?, completed_at = ?, updated_at = ?
        WHERE id = ?;
        """,
        (
            subject_id,
            title.strip(),
            description.strip() if description else None,
            assigned_iso,
            deadline_iso,
            time_str,
            reminder_iso,
            priority,
            status,
            completed_at,
            _now_iso(),
            assignment_id,
        ),
        db_path=db_path,
    )
    return assignment_id


def mark_assignment_completed(
    assignment_id: int,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Mark an assignment as Completed and record completed_at."""
    existing = get_assignment(assignment_id, db_path=db_path)
    if existing is None:
        raise ValueError(f"Assignment ID {assignment_id} does not exist.")
    completed_at = existing.get("completed_at") or _now_iso()
    execute_query(
        """
        UPDATE assignments
        SET status = 'Completed', completed_at = ?, updated_at = ?
        WHERE id = ?;
        """,
        (completed_at, _now_iso(), assignment_id),
        db_path=db_path,
    )
    return assignment_id


def delete_assignment(
    assignment_id: int,
    db_path: Optional[Union[str, Path]] = None,
) -> None:
    """Delete an assignment by ID."""
    execute_query("DELETE FROM assignments WHERE id = ?;", (assignment_id,), db_path=db_path)


def fetch_assignments(
    status: Optional[str] = None,
    subject_id: Optional[int] = None,
    filter_mode: Optional[str] = None,
    current_dt: Optional[datetime] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Fetch assignments sorted by nearest deadline with computed reminder states."""
    clauses: List[str] = []
    params: List[Any] = []
    if status is not None and status != "All":
        clauses.append("a.status = ?")
        params.append(status)
    if subject_id is not None:
        clauses.append("a.subject_id = ?")
        params.append(subject_id)

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = fetch_all(
        f"""
        SELECT a.*, s.subject_name
        FROM assignments a
        JOIN subjects s ON a.subject_id = s.id
        {where_sql}
        ORDER BY a.deadline_date ASC, COALESCE(a.deadline_time, '23:59') ASC, a.id ASC;
        """,
        tuple(params),
        db_path=db_path,
    )

    now = current_dt or datetime.now()
    enriched: List[Dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        rem_state = calculate_reminder_state(item, current_dt=now)
        item["reminder_state"] = rem_state
        item["days_remaining"] = rem_state["days_remaining"]
        enriched.append(item)

    if filter_mode and filter_mode != "All Assignments":
        if filter_mode in ("Pending", "In Progress", "Completed"):
            enriched = [a for a in enriched if a["status"] == filter_mode]
        elif filter_mode == "Overdue":
            enriched = [a for a in enriched if a["reminder_state"]["category"] == "Overdue"]
        elif filter_mode == "Due Today":
            enriched = [a for a in enriched if a["reminder_state"]["category"] == "Due Today"]
        elif filter_mode == "Due Within 3 Days":
            enriched = [
                a
                for a in enriched
                if a["reminder_state"]["category"] in ("Due Today", "Due Soon")
            ]

    return enriched


def fetch_assignments_by_status(
    status: str,
    current_dt: Optional[datetime] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Fetch assignments matching a specific status."""
    return fetch_assignments(status=status, current_dt=current_dt, db_path=db_path)


def fetch_overdue_assignments(
    current_dt: Optional[datetime] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Return all incomplete assignments whose deadline has passed."""
    return fetch_assignments(filter_mode="Overdue", current_dt=current_dt, db_path=db_path)


def fetch_upcoming_deadlines(
    days: int = 3,
    current_dt: Optional[datetime] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Return incomplete assignments due within the next `days` days (including today)."""
    now = current_dt or datetime.now()
    all_items = fetch_assignments(current_dt=now, db_path=db_path)
    return [
        a
        for a in all_items
        if a["status"] != "Completed"
        and 0 <= a["days_remaining"] <= days
        and a["reminder_state"]["category"] != "Overdue"
    ]


def fetch_active_reminders(
    current_dt: Optional[datetime] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Return deduplicated active reminders for incomplete assignments."""
    now = current_dt or datetime.now()
    all_items = fetch_assignments(current_dt=now, db_path=db_path)
    active: List[Dict[str, Any]] = []
    seen_ids = set()

    for item in all_items:
        if item["status"] == "Completed":
            continue
        state = item["reminder_state"]
        if state["category"] in ("Overdue", "Due Today", "Due Soon") or state["reminder_triggered"]:
            if item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                active.append(item)

    return active


def calculate_assignment_completion_percentage(
    db_path: Optional[Union[str, Path]] = None,
) -> float:
    """Return percentage of completed assignments (0.0 if none exist)."""
    all_items = fetch_assignments(db_path=db_path)
    if not all_items:
        return 0.0
    completed = sum(1 for a in all_items if a["status"] == "Completed")
    return round((completed / len(all_items)) * 100.0, 1)


def get_assignment_overview(
    current_dt: Optional[datetime] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Return summary counts for the Assignment Overview dashboard."""
    all_items = fetch_assignments(current_dt=current_dt, db_path=db_path)
    return {
        "total": len(all_items),
        "pending": sum(1 for a in all_items if a["status"] == "Pending"),
        "in_progress": sum(1 for a in all_items if a["status"] == "In Progress"),
        "completed": sum(1 for a in all_items if a["status"] == "Completed"),
        "overdue": sum(1 for a in all_items if a["reminder_state"]["category"] == "Overdue"),
        "due_today": sum(1 for a in all_items if a["reminder_state"]["category"] == "Due Today"),
        "completion_percentage": calculate_assignment_completion_percentage(db_path=db_path),
    }
