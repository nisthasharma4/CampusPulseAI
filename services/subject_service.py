"""Business logic for Subject Management, Topic Tracking & Learning Timeline."""

from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from database.db import execute_query, fetch_all, fetch_one
from database.queries import (
    VALID_SUBJECT_STATUSES,
    VALID_TOPIC_STATUSES,
    fetch_all_subjects,
    fetch_topics_by_subject,
    insert_subject,
    insert_topic,
)
from utils.validators import (
    validate_date_range,
    validate_non_empty_text,
    validate_positive_number,
)


def _today_iso() -> str:
    """Return today's date as YYYY-MM-DD."""
    return date.today().isoformat()


def _now_iso() -> str:
    """Return current local timestamp as ISO-8601 string."""
    return datetime.now().isoformat(timespec="seconds")


def _to_iso_date(value: Optional[Union[date, str]]) -> Optional[str]:
    """Convert a date or non-empty string into YYYY-MM-DD, or return None."""
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    return text if text else None


def _parse_iso_date(value: Optional[str]) -> Optional[date]:
    """Parse a YYYY-MM-DD string into a date object, or return None."""
    if not value:
        return None
    return date.fromisoformat(str(value).strip())


# ---------------------------------------------------------------------------
# Subject Operations
# ---------------------------------------------------------------------------


def list_subjects(
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Return all subjects as a list of dictionaries."""
    return [dict(row) for row in fetch_all_subjects(db_path=db_path)]


def get_subject(
    subject_id: int,
    db_path: Optional[Union[str, Path]] = None,
) -> Optional[Dict[str, Any]]:
    """Return a single subject by ID, or None if not found."""
    row = fetch_one(
        "SELECT * FROM subjects WHERE id = ?;",
        (subject_id,),
        db_path=db_path,
    )
    return dict(row) if row is not None else None


def _check_duplicate_subject(
    subject_name: str,
    semester: Optional[int],
    exclude_subject_id: Optional[int] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> None:
    """Raise ValueError if a subject with the same name and semester already exists."""
    clean_name = subject_name.strip().lower()
    rows = fetch_all(
        "SELECT id, subject_name, semester FROM subjects;",
        db_path=db_path,
    )
    for row in rows:
        if exclude_subject_id is not None and int(row["id"]) == int(exclude_subject_id):
            continue
        existing_name = (row["subject_name"] or "").strip().lower()
        existing_sem = row["semester"]
        if existing_name == clean_name and existing_sem == semester:
            sem_label = f"Semester {semester}" if semester is not None else "no semester"
            raise ValueError(
                f"Subject '{subject_name.strip()}' already exists for {sem_label}."
            )


def create_subject(
    subject_name: str,
    subject_code: Optional[str] = None,
    semester: Optional[int] = None,
    start_date: Optional[Union[date, str]] = None,
    target_completion_date: Optional[Union[date, str]] = None,
    status: str = "Not Started",
    notes: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Validate and create a new college subject."""
    ok, msg = validate_non_empty_text(subject_name, "Subject Name")
    if not ok:
        raise ValueError(msg)

    if status not in VALID_SUBJECT_STATUSES:
        raise ValueError(f"Invalid subject status: {status}")

    if semester is not None:
        ok, msg = validate_positive_number(semester, "Semester", allow_zero=False)
        if not ok or int(semester) != semester:
            raise ValueError("Semester must be a positive whole number.")
        semester = int(semester)

    _check_duplicate_subject(subject_name, semester, db_path=db_path)

    start_iso = _to_iso_date(start_date)
    target_iso = _to_iso_date(target_completion_date)

    if start_iso and target_iso:
        ok, msg = validate_date_range(
            _parse_iso_date(start_iso),
            _parse_iso_date(target_iso),
            "Subject Starting Date",
            "Target Completion Date",
        )
        if not ok:
            raise ValueError(msg)

    completion_iso = None
    if status == "In Progress" and not start_iso:
        start_iso = _today_iso()
    elif status == "Completed":
        if not start_iso:
            start_iso = _today_iso()
        completion_iso = _today_iso()

    return insert_subject(
        subject_name=subject_name.strip(),
        subject_code=subject_code.strip() if subject_code else None,
        semester=semester,
        start_date=start_iso,
        target_completion_date=target_iso,
        completion_date=completion_iso,
        status=status,
        notes=notes.strip() if notes else None,
        db_path=db_path,
    )


def update_subject(
    subject_id: int,
    subject_name: str,
    subject_code: Optional[str] = None,
    semester: Optional[int] = None,
    start_date: Optional[Union[date, str]] = None,
    target_completion_date: Optional[Union[date, str]] = None,
    completion_date: Optional[Union[date, str]] = None,
    status: str = "Not Started",
    notes: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Validate and update an existing subject while preserving historical dates."""
    existing = get_subject(subject_id, db_path=db_path)
    if existing is None:
        raise ValueError(f"Subject ID {subject_id} does not exist.")

    ok, msg = validate_non_empty_text(subject_name, "Subject Name")
    if not ok:
        raise ValueError(msg)

    if status not in VALID_SUBJECT_STATUSES:
        raise ValueError(f"Invalid subject status: {status}")

    if semester is not None:
        ok, msg = validate_positive_number(semester, "Semester", allow_zero=False)
        if not ok or int(semester) != semester:
            raise ValueError("Semester must be a positive whole number.")
        semester = int(semester)

    _check_duplicate_subject(
        subject_name, semester, exclude_subject_id=subject_id, db_path=db_path
    )

    new_start = (
        _to_iso_date(start_date) if start_date is not None else existing["start_date"]
    )
    new_target = (
        _to_iso_date(target_completion_date)
        if target_completion_date is not None
        else existing["target_completion_date"]
    )
    new_completion = (
        _to_iso_date(completion_date)
        if completion_date is not None
        else existing["completion_date"]
    )

    if new_start and new_target:
        ok, msg = validate_date_range(
            _parse_iso_date(new_start),
            _parse_iso_date(new_target),
            "Subject Starting Date",
            "Target Completion Date",
        )
        if not ok:
            raise ValueError(msg)

    old_status = existing["status"]
    if old_status != "In Progress" and status == "In Progress" and not new_start:
        new_start = _today_iso()
    elif old_status != "Completed" and status == "Completed":
        if not new_start:
            new_start = _today_iso()
        if completion_date is None:
            new_completion = _today_iso()

    execute_query(
        """
        UPDATE subjects
        SET subject_name = ?, subject_code = ?, semester = ?,
            start_date = ?, target_completion_date = ?, completion_date = ?,
            status = ?, notes = ?, updated_at = ?
        WHERE id = ?;
        """,
        (
            subject_name.strip(),
            subject_code.strip() if subject_code else None,
            semester,
            new_start,
            new_target,
            new_completion,
            status,
            notes.strip() if notes else None,
            _now_iso(),
            subject_id,
        ),
        db_path=db_path,
    )
    return subject_id


def delete_subject(
    subject_id: int,
    db_path: Optional[Union[str, Path]] = None,
) -> None:
    """Delete a subject (and cascade dependent records per database foreign keys)."""
    execute_query(
        "DELETE FROM subjects WHERE id = ?;",
        (subject_id,),
        db_path=db_path,
    )


# ---------------------------------------------------------------------------
# Topic Operations & Automatic Date Tracking
# ---------------------------------------------------------------------------


def list_topics(
    subject_id: int,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Return all topics for a subject ordered by sequence_number."""
    return [dict(row) for row in fetch_topics_by_subject(subject_id, db_path=db_path)]


def get_topic(
    topic_id: int,
    db_path: Optional[Union[str, Path]] = None,
) -> Optional[Dict[str, Any]]:
    """Return a single topic by ID, or None if not found."""
    row = fetch_one(
        "SELECT * FROM topics WHERE id = ?;",
        (topic_id,),
        db_path=db_path,
    )
    return dict(row) if row is not None else None


def get_next_sequence_number(
    subject_id: int,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Return the next suggested positive sequence number for a subject's topic."""
    row = fetch_one(
        "SELECT COALESCE(MAX(sequence_number), 0) AS max_seq FROM topics WHERE subject_id = ?;",
        (subject_id,),
        db_path=db_path,
    )
    return int(row["max_seq"]) + 1 if row else 1


def create_topic(
    subject_id: int,
    topic_name: str,
    sequence_number: Optional[int] = None,
    start_date: Optional[Union[date, str]] = None,
    target_date: Optional[Union[date, str]] = None,
    estimated_hours: Optional[float] = 0.0,
    status: str = "Not Started",
    notes: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Validate and add a new topic under a subject."""
    if get_subject(subject_id, db_path=db_path) is None:
        raise ValueError(f"Subject ID {subject_id} does not exist.")

    ok, msg = validate_non_empty_text(topic_name, "Topic Name")
    if not ok:
        raise ValueError(msg)

    if status not in VALID_TOPIC_STATUSES:
        raise ValueError(f"Invalid topic status: {status}")

    if sequence_number is None:
        seq = get_next_sequence_number(subject_id, db_path=db_path)
    else:
        ok, msg = validate_positive_number(
            sequence_number, "Sequence Number", allow_zero=False
        )
        if not ok or int(sequence_number) != sequence_number:
            raise ValueError("Sequence Number must be a positive whole number.")
        seq = int(sequence_number)

    if estimated_hours is not None:
        ok, msg = validate_positive_number(
            estimated_hours, "Estimated Study Hours", allow_zero=True
        )
        if not ok:
            raise ValueError(msg)
        estimated_hours = float(estimated_hours)

    start_iso = _to_iso_date(start_date)
    target_iso = _to_iso_date(target_date)

    if start_iso and target_iso:
        ok, msg = validate_date_range(
            _parse_iso_date(start_iso),
            _parse_iso_date(target_iso),
            "Topic Start Date",
            "Planned Completion Date",
        )
        if not ok:
            raise ValueError(msg)

    completion_iso = None
    if status == "In Progress" and not start_iso:
        start_iso = _today_iso()
    elif status == "Completed":
        if not start_iso:
            start_iso = _today_iso()
        completion_iso = _today_iso()

    return insert_topic(
        subject_id=subject_id,
        topic_name=topic_name.strip(),
        sequence_number=seq,
        start_date=start_iso,
        target_date=target_iso,
        completion_date=completion_iso,
        estimated_hours=estimated_hours,
        status=status,
        notes=notes.strip() if notes else None,
        db_path=db_path,
    )


def update_topic_details(
    topic_id: int,
    topic_name: Optional[str] = None,
    sequence_number: Optional[int] = None,
    start_date: Optional[Union[date, str]] = None,
    target_date: Optional[Union[date, str]] = None,
    completion_date: Optional[Union[date, str]] = None,
    estimated_hours: Optional[float] = None,
    status: Optional[str] = None,
    notes: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Update a topic while enforcing automatic date tracking and preserving history."""
    existing = get_topic(topic_id, db_path=db_path)
    if existing is None:
        raise ValueError(f"Topic ID {topic_id} does not exist.")

    new_name = existing["topic_name"]
    if topic_name is not None:
        ok, msg = validate_non_empty_text(topic_name, "Topic Name")
        if not ok:
            raise ValueError(msg)
        new_name = topic_name.strip()

    new_seq = existing["sequence_number"]
    if sequence_number is not None:
        ok, msg = validate_positive_number(
            sequence_number, "Sequence Number", allow_zero=False
        )
        if not ok or int(sequence_number) != sequence_number:
            raise ValueError("Sequence Number must be a positive whole number.")
        new_seq = int(sequence_number)

    new_est = existing["estimated_hours"]
    if estimated_hours is not None:
        ok, msg = validate_positive_number(
            estimated_hours, "Estimated Study Hours", allow_zero=True
        )
        if not ok:
            raise ValueError(msg)
        new_est = float(estimated_hours)

    old_status = existing["status"]
    new_status = status if status is not None else old_status
    if new_status not in VALID_TOPIC_STATUSES:
        raise ValueError(f"Invalid topic status: {new_status}")

    # Preserve existing dates unless manually overridden or triggered by a status transition
    new_start = (
        _to_iso_date(start_date) if start_date is not None else existing["start_date"]
    )
    new_target = (
        _to_iso_date(target_date) if target_date is not None else existing["target_date"]
    )
    new_completion = (
        _to_iso_date(completion_date)
        if completion_date is not None
        else existing["completion_date"]
    )

    if old_status == "Not Started" and new_status == "In Progress":
        if not new_start:
            new_start = _today_iso()
    elif old_status != "Completed" and new_status == "Completed":
        if not new_start:
            new_start = _today_iso()
        if completion_date is None:
            new_completion = _today_iso()
    # When reopening a Completed topic or editing without changing status,
    # existing historical start_date and completion_date remain preserved.

    if new_start and new_target:
        ok, msg = validate_date_range(
            _parse_iso_date(new_start),
            _parse_iso_date(new_target),
            "Topic Start Date",
            "Planned Completion Date",
        )
        if not ok:
            raise ValueError(msg)

    new_notes = notes.strip() if notes is not None else existing["notes"]

    execute_query(
        """
        UPDATE topics
        SET topic_name = ?, sequence_number = ?, start_date = ?, target_date = ?,
            completion_date = ?, estimated_hours = ?, status = ?, notes = ?,
            updated_at = ?
        WHERE id = ?;
        """,
        (
            new_name,
            new_seq,
            new_start,
            new_target,
            new_completion,
            new_est,
            new_status,
            new_notes,
            _now_iso(),
            topic_id,
        ),
        db_path=db_path,
    )
    return topic_id


def change_topic_status(
    topic_id: int,
    new_status: str,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Convenience helper to transition a topic's status with automatic date rules."""
    return update_topic_details(topic_id=topic_id, status=new_status, db_path=db_path)


def delete_topic(
    topic_id: int,
    db_path: Optional[Union[str, Path]] = None,
) -> None:
    """Delete a topic while preserving historical study_sessions (topic_id -> NULL)."""
    execute_query(
        "DELETE FROM topics WHERE id = ?;",
        (topic_id,),
        db_path=db_path,
    )


# ---------------------------------------------------------------------------
# Progress & Learning Journey Calculations
# ---------------------------------------------------------------------------


def get_subject_progress(
    subject_id: int,
    db_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Calculate topic counts and completion percentage for a subject."""
    topics = list_topics(subject_id, db_path=db_path)
    total_topics = len(topics)
    completed_topics = sum(1 for t in topics if t["status"] == "Completed")
    in_progress_topics = sum(1 for t in topics if t["status"] == "In Progress")
    pending_topics = total_topics - completed_topics
    completion_pct = (
        round((completed_topics / total_topics) * 100.0, 1)
        if total_topics > 0
        else 0.0
    )

    return {
        "total_topics": total_topics,
        "completed_topics": completed_topics,
        "in_progress_topics": in_progress_topics,
        "pending_topics": pending_topics,
        "completion_percentage": completion_pct,
    }


def get_subject_learning_journey(
    subject_id: int,
    db_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Return subject start date and ordered topic timeline with actual study hours."""
    subject = get_subject(subject_id, db_path=db_path)
    if subject is None:
        return {"subject": None, "topics": []}

    topics = list_topics(subject_id, db_path=db_path)
    hours_rows = fetch_all(
        """
        SELECT topic_id, COALESCE(SUM(duration_minutes), 0) AS total_minutes
        FROM study_sessions
        WHERE subject_id = ? AND topic_id IS NOT NULL
        GROUP BY topic_id;
        """,
        (subject_id,),
        db_path=db_path,
    )
    hours_by_topic = {
        int(row["topic_id"]): round(float(row["total_minutes"]) / 60.0, 2)
        for row in hours_rows
    }

    timeline_topics: List[Dict[str, Any]] = []
    for topic in topics:
        item = dict(topic)
        item["actual_study_hours"] = hours_by_topic.get(int(topic["id"]), 0.0)
        timeline_topics.append(item)

    return {
        "subject": subject,
        "topics": timeline_topics,
    }
