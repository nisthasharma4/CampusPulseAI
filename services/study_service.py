"""Business logic for Daily Study Tracker, Study Journal & Time Analysis."""

from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from database.db import execute_query, fetch_all, fetch_one
from database.queries import (
    VALID_SESSION_STATUSES,
    fetch_study_history,
    save_daily_checkin,
    save_study_session,
)
from services.profile_service import get_profile
from services.subject_service import get_subject, get_topic, list_topics, update_topic_details
from utils.validators import validate_date_range, validate_positive_number

PRODUCTIVITY_LABELS = {
    1: "1 - Very Low",
    2: "2 - Low",
    3: "3 - Average",
    4: "4 - Good",
    5: "5 - Excellent",
}

DATE_FILTER_OPTIONS = (
    "All Records",
    "Today",
    "Last 7 Days",
    "Last 30 Days",
    "This Month",
    "Previous Month",
    "Custom Date Range",
)


def _to_iso_date(value: Optional[Union[date, str]]) -> Optional[str]:
    """Convert a date or string to YYYY-MM-DD."""
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    return text if text else None


def _to_time_str(value: Optional[Union[time, str]]) -> Optional[str]:
    """Convert a time or string to HH:MM."""
    if value is None:
        return None
    if isinstance(value, time):
        return value.strftime("%H:%M")
    text = str(value).strip()
    return text if text else None


def format_minutes_hm(total_minutes: int) -> str:
    """Format minutes as 'X hrs Y mins'."""
    mins = max(0, int(total_minutes))
    hours = mins // 60
    rem = mins % 60
    return f"{hours} hrs {rem} mins"


def calculate_duration_from_times(start_t: time, end_t: time) -> int:
    """Calculate positive duration in minutes between same-day start and end times."""
    if start_t is None or end_t is None:
        raise ValueError("Both Start Time and End Time are required.")
    start_mins = start_t.hour * 60 + start_t.minute
    end_mins = end_t.hour * 60 + end_t.minute
    if end_mins <= start_mins:
        raise ValueError("End Time must be later than Start Time on the same day.")
    return end_mins - start_mins


def calculate_manual_duration(hours: int, minutes: int) -> int:
    """Calculate and validate positive manual duration in minutes."""
    if hours is None or minutes is None:
        raise ValueError("Hours and minutes are required.")
    if hours < 0 or minutes < 0:
        raise ValueError("Duration hours and minutes cannot be negative.")
    total = int(hours) * 60 + int(minutes)
    if total <= 0:
        raise ValueError("Total study duration must be greater than zero.")
    return total


def create_study_session(
    subject_id: int,
    study_date: Union[date, str],
    duration_minutes: Optional[int] = None,
    topic_id: Optional[int] = None,
    start_time: Optional[Union[time, str]] = None,
    end_time: Optional[Union[time, str]] = None,
    study_goal: Optional[str] = None,
    completed_work: Optional[str] = None,
    next_topic: Optional[str] = None,
    productivity_rating: Optional[int] = None,
    status: str = "Completed",
    notes: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Validate and save a study session, updating Not Started topics to In Progress."""
    if get_subject(subject_id, db_path=db_path) is None:
        raise ValueError("Selected subject does not exist.")

    study_date_iso = _to_iso_date(study_date)
    if not study_date_iso:
        raise ValueError("Study Date is required.")

    start_str = _to_time_str(start_time)
    end_str = _to_time_str(end_time)

    if duration_minutes is None:
        if isinstance(start_time, time) and isinstance(end_time, time):
            duration_minutes = calculate_duration_from_times(start_time, end_time)
        else:
            raise ValueError("Study duration is required.")

    ok, msg = validate_positive_number(duration_minutes, "Study Duration", allow_zero=False)
    if not ok:
        raise ValueError(msg)

    if status not in VALID_SESSION_STATUSES:
        raise ValueError(f"Invalid study status: {status}")

    if productivity_rating is not None and (productivity_rating < 1 or productivity_rating > 5):
        raise ValueError("Productivity rating must be between 1 and 5.")

    session_id = save_study_session(
        subject_id=subject_id,
        study_date=study_date_iso,
        duration_minutes=int(duration_minutes),
        topic_id=topic_id,
        start_time=start_str,
        end_time=end_str,
        study_goal=study_goal.strip() if study_goal else None,
        completed_work=completed_work.strip() if completed_work else None,
        next_topic=next_topic.strip() if next_topic else None,
        productivity_rating=productivity_rating,
        status=status,
        notes=notes.strip() if notes else None,
        db_path=db_path,
    )

    # Automatic topic status transition: Not Started -> In Progress (sets start_date if missing)
    if topic_id is not None:
        topic = get_topic(topic_id, db_path=db_path)
        if topic is not None and topic["status"] == "Not Started":
            update_topic_details(
                topic_id=topic_id,
                status="In Progress",
                start_date=topic["start_date"] or study_date_iso,
                db_path=db_path,
            )

    return session_id


def get_study_session(
    session_id: int,
    db_path: Optional[Union[str, Path]] = None,
) -> Optional[Dict[str, Any]]:
    """Fetch a single study session by ID."""
    row = fetch_one(
        "SELECT * FROM study_sessions WHERE id = ?;",
        (session_id,),
        db_path=db_path,
    )
    return dict(row) if row is not None else None


def update_study_session(
    session_id: int,
    subject_id: int,
    study_date: Union[date, str],
    duration_minutes: int,
    topic_id: Optional[int] = None,
    start_time: Optional[Union[time, str]] = None,
    end_time: Optional[Union[time, str]] = None,
    study_goal: Optional[str] = None,
    completed_work: Optional[str] = None,
    next_topic: Optional[str] = None,
    productivity_rating: Optional[int] = None,
    status: str = "Completed",
    notes: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Update an existing study session while preserving created_at."""
    existing = get_study_session(session_id, db_path=db_path)
    if existing is None:
        raise ValueError(f"Study session ID {session_id} does not exist.")

    study_date_iso = _to_iso_date(study_date)
    if not study_date_iso:
        raise ValueError("Study Date is required.")

    if duration_minutes <= 0:
        raise ValueError("Study duration must be greater than zero.")
    if status not in VALID_SESSION_STATUSES:
        raise ValueError(f"Invalid study status: {status}")
    if productivity_rating is not None and (productivity_rating < 1 or productivity_rating > 5):
        raise ValueError("Productivity rating must be between 1 and 5.")

    if topic_id is not None:
        topic = get_topic(topic_id, db_path=db_path)
        if topic is None or int(topic["subject_id"]) != int(subject_id):
            raise ValueError("Selected topic does not belong to the selected subject.")

    execute_query(
        """
        UPDATE study_sessions
        SET subject_id = ?, topic_id = ?, study_date = ?, start_time = ?,
            end_time = ?, duration_minutes = ?, study_goal = ?,
            completed_work = ?, next_topic = ?, productivity_rating = ?,
            status = ?, notes = ?
        WHERE id = ?;
        """,
        (
            subject_id,
            topic_id,
            study_date_iso,
            _to_time_str(start_time),
            _to_time_str(end_time),
            int(duration_minutes),
            study_goal.strip() if study_goal else None,
            completed_work.strip() if completed_work else None,
            next_topic.strip() if next_topic else None,
            productivity_rating,
            status,
            notes.strip() if notes else None,
            session_id,
        ),
        db_path=db_path,
    )
    return session_id


def delete_study_session(
    session_id: int,
    db_path: Optional[Union[str, Path]] = None,
) -> None:
    """Delete a single study session without altering topic statuses or dates."""
    execute_query(
        "DELETE FROM study_sessions WHERE id = ?;",
        (session_id,),
        db_path=db_path,
    )


def get_date_range_for_filter(
    filter_name: str,
    reference_date: Optional[date] = None,
    custom_start: Optional[date] = None,
    custom_end: Optional[date] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """Resolve a named filter into (start_date_iso, end_date_iso)."""
    today = reference_date or date.today()

    if filter_name == "All Records":
        return None, None
    if filter_name == "Today":
        iso = today.isoformat()
        return iso, iso
    if filter_name == "Last 7 Days":
        return (today - timedelta(days=6)).isoformat(), today.isoformat()
    if filter_name == "Last 30 Days":
        return (today - timedelta(days=29)).isoformat(), today.isoformat()
    if filter_name == "This Month":
        return today.replace(day=1).isoformat(), today.isoformat()
    if filter_name == "Previous Month":
        first_this_month = today.replace(day=1)
        last_prev_month = first_this_month - timedelta(days=1)
        first_prev_month = last_prev_month.replace(day=1)
        return first_prev_month.isoformat(), last_prev_month.isoformat()
    if filter_name == "Custom Date Range":
        if custom_start and custom_end:
            ok, msg = validate_date_range(custom_start, custom_end, "From Date", "To Date")
            if not ok:
                raise ValueError(msg)
            return custom_start.isoformat(), custom_end.isoformat()
        return _to_iso_date(custom_start), _to_iso_date(custom_end)

    return None, None


def fetch_sessions(
    start_date: Optional[Union[date, str]] = None,
    end_date: Optional[Union[date, str]] = None,
    subject_id: Optional[int] = None,
    topic_id: Optional[int] = None,
    status: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Fetch study sessions in reverse chronological order with optional filters."""
    rows = fetch_study_history(
        start_date=_to_iso_date(start_date),
        end_date=_to_iso_date(end_date),
        subject_id=subject_id,
        db_path=db_path,
    )
    results = [dict(r) for r in rows]
    if topic_id is not None:
        results = [r for r in results if r.get("topic_id") == topic_id]
    if status is not None and status != "All":
        results = [r for r in results if r.get("status") == status]
    return results


def calculate_total_study_minutes(
    start_date: Optional[Union[date, str]] = None,
    end_date: Optional[Union[date, str]] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Return total study minutes across sessions in the optional date range."""
    sessions = fetch_sessions(start_date=start_date, end_date=end_date, db_path=db_path)
    return sum(int(s["duration_minutes"]) for s in sessions)


def calculate_average_session_duration(sessions: List[Dict[str, Any]]) -> float:
    """Return average session duration in minutes for a list of sessions."""
    if not sessions:
        return 0.0
    total = sum(int(s["duration_minutes"]) for s in sessions)
    return round(total / len(sessions), 1)


def get_today_study_overview(
    target_date: Optional[Union[date, str]] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Compute today's study metrics against the student's daily target."""
    day_iso = _to_iso_date(target_date) or date.today().isoformat()
    today_sessions = fetch_sessions(start_date=day_iso, end_date=day_iso, db_path=db_path)

    studied_minutes = sum(int(s["duration_minutes"]) for s in today_sessions)
    session_count = len(today_sessions)
    completed_count = sum(1 for s in today_sessions if s["status"] == "Completed")

    ratings = [
        int(s["productivity_rating"])
        for s in today_sessions
        if s.get("productivity_rating") is not None
    ]
    avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else None

    profile = get_profile(db_path=db_path)
    target_minutes = int(profile.get("daily_available_minutes") or 0) if profile else 0
    remaining_minutes = max(0, target_minutes - studied_minutes) if target_minutes > 0 else 0
    target_pct = (
        min(100.0, round((studied_minutes / target_minutes) * 100.0, 1))
        if target_minutes > 0
        else 0.0
    )

    return {
        "date": day_iso,
        "has_profile": profile is not None,
        "studied_minutes": studied_minutes,
        "studied_hours": round(studied_minutes / 60.0, 2),
        "session_count": session_count,
        "completed_count": completed_count,
        "avg_productivity_rating": avg_rating,
        "target_minutes": target_minutes,
        "target_hours": round(target_minutes / 60.0, 2),
        "remaining_minutes": remaining_minutes,
        "target_completion_pct": target_pct,
    }


def get_subject_study_summary(
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Aggregate total study time, session count, and average duration per subject."""
    rows = fetch_all(
        """
        SELECT
            sub.id AS subject_id,
            sub.subject_name,
            COALESCE(SUM(s.duration_minutes), 0) AS total_minutes,
            COUNT(s.id) AS session_count
        FROM subjects sub
        LEFT JOIN study_sessions s ON sub.id = s.subject_id
        GROUP BY sub.id, sub.subject_name
        ORDER BY total_minutes DESC, sub.subject_name ASC;
        """,
        db_path=db_path,
    )
    summary: List[Dict[str, Any]] = []
    for row in rows:
        total_mins = int(row["total_minutes"])
        count = int(row["session_count"])
        summary.append(
            {
                "subject_id": int(row["subject_id"]),
                "subject_name": row["subject_name"],
                "total_minutes": total_mins,
                "hours": total_mins // 60,
                "remaining_minutes": total_mins % 60,
                "total_hours_decimal": round(total_mins / 60.0, 2),
                "formatted_time": format_minutes_hm(total_mins),
                "session_count": count,
                "avg_session_minutes": round(total_mins / count, 1) if count > 0 else 0.0,
            }
        )
    return summary


def get_topic_study_summary(
    subject_id: Optional[int] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Aggregate actual study hours and session counts per topic."""
    where_sql = "WHERE t.subject_id = ?" if subject_id is not None else ""
    params = (subject_id,) if subject_id is not None else ()
    rows = fetch_all(
        f"""
        SELECT
            t.id AS topic_id,
            t.subject_id,
            sub.subject_name,
            t.topic_name,
            t.start_date,
            t.completion_date,
            t.status,
            COALESCE(SUM(s.duration_minutes), 0) AS total_minutes,
            COUNT(s.id) AS session_count
        FROM topics t
        JOIN subjects sub ON t.subject_id = sub.id
        LEFT JOIN study_sessions s ON t.id = s.topic_id
        {where_sql}
        GROUP BY t.id
        ORDER BY sub.subject_name ASC, COALESCE(t.sequence_number, 999999) ASC, t.id ASC;
        """,
        params,
        db_path=db_path,
    )
    results: List[Dict[str, Any]] = []
    for row in rows:
        total_mins = int(row["total_minutes"])
        results.append(
            {
                "topic_id": int(row["topic_id"]),
                "subject_id": int(row["subject_id"]),
                "subject_name": row["subject_name"],
                "topic_name": row["topic_name"],
                "start_date": row["start_date"],
                "completion_date": row["completion_date"],
                "status": row["status"],
                "total_minutes": total_mins,
                "total_hours": round(total_mins / 60.0, 2),
                "formatted_time": format_minutes_hm(total_mins),
                "session_count": int(row["session_count"]),
            }
        )
    return results


def get_subject_detailed_learning_journey(
    subject_id: int,
    db_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Return chronological study sessions and topic milestones for a subject."""
    subject = get_subject(subject_id, db_path=db_path)
    if subject is None:
        return {"subject": None, "topics": [], "sessions": []}

    topics = get_topic_study_summary(subject_id=subject_id, db_path=db_path)
    sessions_rows = fetch_all(
        """
        SELECT s.*, t.topic_name
        FROM study_sessions s
        LEFT JOIN topics t ON s.topic_id = t.id
        WHERE s.subject_id = ?
        ORDER BY s.study_date ASC, s.id ASC;
        """,
        (subject_id,),
        db_path=db_path,
    )
    return {
        "subject": subject,
        "topics": topics,
        "sessions": [dict(r) for r in sessions_rows],
    }


def save_checkin(
    checkin_date: Union[date, str],
    goal_completed: bool,
    planned_study_hours: float = 0.0,
    tomorrow_plan: Optional[str] = None,
    productivity_rating: Optional[int] = None,
    notes: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Create or update a daily check-in (unique per date)."""
    date_iso = _to_iso_date(checkin_date)
    if not date_iso:
        raise ValueError("Check-in date is required.")
    if planned_study_hours < 0:
        raise ValueError("Planned study hours cannot be negative.")
    if productivity_rating is not None and (productivity_rating < 1 or productivity_rating > 5):
        raise ValueError("Productivity rating must be between 1 and 5.")

    planned_mins = int(round(float(planned_study_hours) * 60))
    return save_daily_checkin(
        checkin_date=date_iso,
        goal_completed=1 if goal_completed else 0,
        planned_study_minutes=planned_mins,
        tomorrow_plan=tomorrow_plan.strip() if tomorrow_plan else None,
        productivity_rating=productivity_rating,
        notes=notes.strip() if notes else None,
        db_path=db_path,
    )


def get_daily_checkin(
    checkin_date: Union[date, str],
    db_path: Optional[Union[str, Path]] = None,
) -> Optional[Dict[str, Any]]:
    """Fetch the daily check-in for a specific date."""
    date_iso = _to_iso_date(checkin_date)
    row = fetch_one(
        "SELECT * FROM daily_checkins WHERE checkin_date = ?;",
        (date_iso,),
        db_path=db_path,
    )
    return dict(row) if row is not None else None


def list_daily_checkins(
    limit: int = 14,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Fetch recent daily check-ins in reverse chronological order."""
    rows = fetch_all(
        "SELECT * FROM daily_checkins ORDER BY checkin_date DESC LIMIT ?;",
        (limit,),
        db_path=db_path,
    )
    return [dict(r) for r in rows]
