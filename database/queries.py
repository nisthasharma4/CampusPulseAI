"""Reusable parameterized database operations for CampusPulse AI."""

from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Union
import sqlite3

from database.db import execute_query, fetch_all, fetch_one

VALID_SUBJECT_STATUSES = ("Not Started", "In Progress", "Completed")
VALID_TOPIC_STATUSES = ("Not Started", "In Progress", "Completed")
VALID_ASSIGNMENT_STATUSES = ("Pending", "In Progress", "Completed")
VALID_SESSION_STATUSES = ("Completed", "Partially Completed", "Not Completed")
VALID_TIMETABLE_STATUSES = ("Planned", "Completed", "Skipped")
VALID_TIMETABLE_SOURCES = ("Generated", "Manual")
VALID_PRIORITIES = ("Low", "Medium", "High")
VALID_EVENT_TYPES = (
    "Internal Examination",
    "External Examination",
    "Practical Examination",
    "Assignment Submission",
    "Project Submission",
    "Holiday",
    "Workshop",
    "Seminar",
    "Hackathon",
    "Other",
)


def _now_iso() -> str:
    """Return current local timestamp as an ISO-8601 string."""
    return datetime.now().isoformat(timespec="seconds")


def _require_non_empty(value: Optional[str], field_name: str) -> str:
    """Validate that a text value is present and non-empty."""
    if value is None or not str(value).strip():
        raise ValueError(f"{field_name} is required and cannot be empty.")
    return str(value).strip()


def _validate_topic_belongs_to_subject(
    topic_id: Optional[int],
    subject_id: int,
    db_path: Optional[Union[str, Path]] = None,
) -> None:
    """Ensure an optional topic_id exists and belongs to the specified subject_id."""
    if topic_id is None:
        return
    topic = fetch_one(
        "SELECT id, subject_id FROM topics WHERE id = ?;",
        (topic_id,),
        db_path=db_path,
    )
    if topic is None:
        raise ValueError(f"Topic ID {topic_id} does not exist.")
    if int(topic["subject_id"]) != int(subject_id):
        raise ValueError(
            f"Topic ID {topic_id} does not belong to Subject ID {subject_id}."
        )


def save_student_profile(
    name: str,
    branch: Optional[str] = None,
    semester: Optional[int] = None,
    college_name: Optional[str] = None,
    weekly_study_target: Optional[int] = None,
    preferred_start_time: Optional[str] = None,
    preferred_end_time: Optional[str] = None,
    available_days: Optional[str] = None,
    daily_available_minutes: Optional[int] = None,
    session_duration_minutes: Optional[int] = None,
    break_duration_minutes: Optional[int] = None,
    attendance_target: float = 75.0,
    avatar_preset: Optional[str] = None,
    avatar_path: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Create or update the single-user student profile and return its ID."""
    clean_name = _require_non_empty(name, "Student name")
    if attendance_target < 0 or attendance_target > 100:
        raise ValueError("Attendance target must be between 0 and 100.")
    if weekly_study_target is not None and weekly_study_target < 0:
        raise ValueError("Weekly study target cannot be negative.")
    if daily_available_minutes is not None and daily_available_minutes < 0:
        raise ValueError("Daily available minutes cannot be negative.")
    if session_duration_minutes is not None and session_duration_minutes <= 0:
        raise ValueError("Session duration must be greater than zero.")
    if break_duration_minutes is not None and break_duration_minutes < 0:
        raise ValueError("Break duration cannot be negative.")

    now = _now_iso()
    existing = get_student_profile(db_path=db_path)

    # Determine avatar fields (preserve if not explicitly overridden)
    final_avatar_preset = (
        avatar_preset
        if avatar_preset is not None
        else (existing["avatar_preset"] if existing and "avatar_preset" in existing.keys() else None)
    )
    final_avatar_path = (
        avatar_path
        if avatar_path is not None
        else (existing["avatar_path"] if existing and "avatar_path" in existing.keys() else None)
    )

    if existing is None:
        return execute_query(
            """
            INSERT INTO student_profile (
                name, branch, semester, college_name, weekly_study_target,
                preferred_start_time, preferred_end_time, available_days,
                daily_available_minutes, session_duration_minutes,
                break_duration_minutes, attendance_target, avatar_preset,
                avatar_path, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                clean_name,
                branch,
                semester,
                college_name,
                weekly_study_target,
                preferred_start_time,
                preferred_end_time,
                available_days,
                daily_available_minutes,
                session_duration_minutes,
                break_duration_minutes,
                attendance_target,
                final_avatar_preset,
                final_avatar_path,
                now,
                now,
            ),
            db_path=db_path,
        )

    profile_id = int(existing["id"])
    execute_query(
        """
        UPDATE student_profile
        SET name = ?, branch = ?, semester = ?, college_name = ?,
            weekly_study_target = ?, preferred_start_time = ?,
            preferred_end_time = ?, available_days = ?,
            daily_available_minutes = ?, session_duration_minutes = ?,
            break_duration_minutes = ?, attendance_target = ?,
            avatar_preset = ?, avatar_path = ?, updated_at = ?
        WHERE id = ?;
        """,
        (
            clean_name,
            branch,
            semester,
            college_name,
            weekly_study_target,
            preferred_start_time,
            preferred_end_time,
            available_days,
            daily_available_minutes,
            session_duration_minutes,
            break_duration_minutes,
            attendance_target,
            final_avatar_preset,
            final_avatar_path,
            now,
            profile_id,
        ),
        db_path=db_path,
    )
    return profile_id


def update_student_avatar(
    avatar_preset: Optional[str] = None,
    avatar_path: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> bool:
    """Update avatar fields for the student profile."""
    existing = get_student_profile(db_path=db_path)
    if existing is None:
        return False
    profile_id = int(existing["id"])
    now = _now_iso()
    execute_query(
        """
        UPDATE student_profile
        SET avatar_preset = ?, avatar_path = ?, updated_at = ?
        WHERE id = ?;
        """,
        (avatar_preset, avatar_path, now, profile_id),
        db_path=db_path,
    )
    return True


def clear_student_avatar(
    db_path: Optional[Union[str, Path]] = None,
) -> bool:
    """Reset both avatar preset and custom photo path to None."""
    return update_student_avatar(avatar_preset=None, avatar_path=None, db_path=db_path)


def get_student_profile(
    db_path: Optional[Union[str, Path]] = None,
) -> Optional[sqlite3.Row]:
    """Fetch the student profile record, or None if not yet created."""
    return fetch_one(
        "SELECT * FROM student_profile ORDER BY id ASC LIMIT 1;",
        db_path=db_path,
    )


def insert_subject(
    subject_name: str,
    subject_code: Optional[str] = None,
    semester: Optional[int] = None,
    start_date: Optional[str] = None,
    target_completion_date: Optional[str] = None,
    completion_date: Optional[str] = None,
    status: str = "Not Started",
    notes: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Insert a new subject and return its ID."""
    clean_name = _require_non_empty(subject_name, "Subject name")
    if status not in VALID_SUBJECT_STATUSES:
        raise ValueError(f"Invalid subject status: {status}")

    now = _now_iso()
    return execute_query(
        """
        INSERT INTO subjects (
            subject_name, subject_code, semester, start_date,
            target_completion_date, completion_date, status, notes,
            created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            clean_name,
            subject_code,
            semester,
            start_date,
            target_completion_date,
            completion_date,
            status,
            notes,
            now,
            now,
        ),
        db_path=db_path,
    )


def fetch_all_subjects(
    db_path: Optional[Union[str, Path]] = None,
) -> List[sqlite3.Row]:
    """Return all subjects ordered by name."""
    return fetch_all(
        "SELECT * FROM subjects ORDER BY subject_name ASC, id ASC;",
        db_path=db_path,
    )


def insert_topic(
    subject_id: int,
    topic_name: str,
    sequence_number: Optional[int] = None,
    start_date: Optional[str] = None,
    target_date: Optional[str] = None,
    completion_date: Optional[str] = None,
    estimated_hours: Optional[float] = None,
    status: str = "Not Started",
    notes: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Insert a syllabus topic under a subject and return its ID."""
    clean_name = _require_non_empty(topic_name, "Topic name")
    if status not in VALID_TOPIC_STATUSES:
        raise ValueError(f"Invalid topic status: {status}")
    if estimated_hours is not None and estimated_hours < 0:
        raise ValueError("Estimated hours cannot be negative.")

    now = _now_iso()
    return execute_query(
        """
        INSERT INTO topics (
            subject_id, topic_name, sequence_number, start_date,
            target_date, completion_date, estimated_hours, status,
            notes, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            subject_id,
            clean_name,
            sequence_number,
            start_date,
            target_date,
            completion_date,
            estimated_hours,
            status,
            notes,
            now,
            now,
        ),
        db_path=db_path,
    )


def fetch_topics_by_subject(
    subject_id: int,
    db_path: Optional[Union[str, Path]] = None,
) -> List[sqlite3.Row]:
    """Return all topics for a given subject ordered by sequence_number."""
    return fetch_all(
        """
        SELECT * FROM topics
        WHERE subject_id = ?
        ORDER BY COALESCE(sequence_number, 999999) ASC, id ASC;
        """,
        (subject_id,),
        db_path=db_path,
    )


def update_topic(
    topic_id: int,
    topic_name: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    target_date: Optional[str] = None,
    completion_date: Optional[str] = None,
    estimated_hours: Optional[float] = None,
    notes: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Update topic fields without modifying or deleting historical study sessions."""
    existing = fetch_one(
        "SELECT * FROM topics WHERE id = ?;",
        (topic_id,),
        db_path=db_path,
    )
    if existing is None:
        raise ValueError(f"Topic ID {topic_id} does not exist.")

    new_name = (
        _require_non_empty(topic_name, "Topic name")
        if topic_name is not None
        else existing["topic_name"]
    )
    new_status = status if status is not None else existing["status"]
    if new_status not in VALID_TOPIC_STATUSES:
        raise ValueError(f"Invalid topic status: {new_status}")

    new_est = (
        estimated_hours if estimated_hours is not None else existing["estimated_hours"]
    )
    if new_est is not None and new_est < 0:
        raise ValueError("Estimated hours cannot be negative.")

    execute_query(
        """
        UPDATE topics
        SET topic_name = ?, status = ?, start_date = ?, target_date = ?,
            completion_date = ?, estimated_hours = ?, notes = ?, updated_at = ?
        WHERE id = ?;
        """,
        (
            new_name,
            new_status,
            start_date if start_date is not None else existing["start_date"],
            target_date if target_date is not None else existing["target_date"],
            completion_date
            if completion_date is not None
            else existing["completion_date"],
            new_est,
            notes if notes is not None else existing["notes"],
            _now_iso(),
            topic_id,
        ),
        db_path=db_path,
    )
    return topic_id


def save_attendance(
    subject_id: int,
    classes_held: int,
    classes_attended: int,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Create or update the aggregate attendance record for a subject."""
    if classes_held < 0 or classes_attended < 0:
        raise ValueError("Attendance counts cannot be negative.")
    if classes_attended > classes_held:
        raise ValueError("Classes attended cannot exceed classes held.")

    now = _now_iso()
    existing = fetch_one(
        "SELECT id FROM attendance WHERE subject_id = ?;",
        (subject_id,),
        db_path=db_path,
    )
    if existing is None:
        return execute_query(
            """
            INSERT INTO attendance (subject_id, classes_held, classes_attended, updated_at)
            VALUES (?, ?, ?, ?);
            """,
            (subject_id, classes_held, classes_attended, now),
            db_path=db_path,
        )

    attendance_id = int(existing["id"])
    execute_query(
        """
        UPDATE attendance
        SET classes_held = ?, classes_attended = ?, updated_at = ?
        WHERE id = ?;
        """,
        (classes_held, classes_attended, now, attendance_id),
        db_path=db_path,
    )
    return attendance_id


def save_marks(
    subject_id: int,
    assessment_type: str,
    marks_obtained: float,
    maximum_marks: float,
    assessment_date: Optional[str] = None,
    notes: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Insert an assessment marks record for a subject."""
    clean_type = _require_non_empty(assessment_type, "Assessment type")
    if marks_obtained < 0:
        raise ValueError("Marks obtained cannot be negative.")
    if maximum_marks <= 0:
        raise ValueError("Maximum marks must be greater than zero.")
    if marks_obtained > maximum_marks:
        raise ValueError("Marks obtained cannot exceed maximum marks.")

    return execute_query(
        """
        INSERT INTO marks (
            subject_id, assessment_type, marks_obtained,
            maximum_marks, assessment_date, notes, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """,
        (
            subject_id,
            clean_type,
            marks_obtained,
            maximum_marks,
            assessment_date,
            notes,
            _now_iso(),
        ),
        db_path=db_path,
    )


def save_assignment(
    subject_id: int,
    title: str,
    deadline_date: str,
    description: Optional[str] = None,
    assigned_date: Optional[str] = None,
    deadline_time: Optional[str] = None,
    reminder_at: Optional[str] = None,
    priority: str = "Medium",
    status: str = "Pending",
    completed_at: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Insert a new assignment record and return its ID."""
    clean_title = _require_non_empty(title, "Assignment title")
    clean_deadline = _require_non_empty(deadline_date, "Deadline date")
    if priority not in VALID_PRIORITIES:
        raise ValueError(f"Invalid priority: {priority}")
    if status not in VALID_ASSIGNMENT_STATUSES:
        raise ValueError(f"Invalid assignment status: {status}")

    now = _now_iso()
    return execute_query(
        """
        INSERT INTO assignments (
            subject_id, title, description, assigned_date, deadline_date,
            deadline_time, reminder_at, priority, status, completed_at,
            created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            subject_id,
            clean_title,
            description,
            assigned_date,
            clean_deadline,
            deadline_time,
            reminder_at,
            priority,
            status,
            completed_at,
            now,
            now,
        ),
        db_path=db_path,
    )


def save_calendar_event(
    title: str,
    event_type: str,
    start_date: str,
    end_date: Optional[str] = None,
    start_time: Optional[str] = None,
    description: Optional[str] = None,
    reminder_at: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Insert a college academic calendar event and return its ID."""
    clean_title = _require_non_empty(title, "Event title")
    clean_start = _require_non_empty(start_date, "Start date")
    if event_type not in VALID_EVENT_TYPES:
        raise ValueError(f"Invalid event type: {event_type}")

    now = _now_iso()
    return execute_query(
        """
        INSERT INTO calendar_events (
            title, event_type, start_date, end_date, start_time,
            description, reminder_at, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            clean_title,
            event_type,
            clean_start,
            end_date,
            start_time,
            description,
            reminder_at,
            now,
            now,
        ),
        db_path=db_path,
    )


def save_study_session(
    subject_id: int,
    study_date: str,
    duration_minutes: int,
    topic_id: Optional[int] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    study_goal: Optional[str] = None,
    completed_work: Optional[str] = None,
    next_topic: Optional[str] = None,
    productivity_rating: Optional[int] = None,
    status: str = "Completed",
    notes: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Insert a study session record after validating duration, rating, status, and topic."""
    clean_date = _require_non_empty(study_date, "Study date")
    if duration_minutes <= 0:
        raise ValueError("Study duration must be greater than zero.")
    if productivity_rating is not None and (
        productivity_rating < 1 or productivity_rating > 5
    ):
        raise ValueError("Productivity rating must be between 1 and 5.")
    if status not in VALID_SESSION_STATUSES:
        raise ValueError(f"Invalid session status: {status}")

    _validate_topic_belongs_to_subject(topic_id, subject_id, db_path=db_path)

    return execute_query(
        """
        INSERT INTO study_sessions (
            subject_id, topic_id, study_date, start_time, end_time,
            duration_minutes, study_goal, completed_work, next_topic,
            productivity_rating, status, notes, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            subject_id,
            topic_id,
            clean_date,
            start_time,
            end_time,
            duration_minutes,
            study_goal,
            completed_work,
            next_topic,
            productivity_rating,
            status,
            notes,
            _now_iso(),
        ),
        db_path=db_path,
    )


def fetch_study_history(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    subject_id: Optional[int] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> List[sqlite3.Row]:
    """Fetch study sessions optionally filtered by date range and subject."""
    clauses: List[str] = []
    params: List[Any] = []

    if start_date is not None:
        clauses.append("s.study_date >= ?")
        params.append(start_date)
    if end_date is not None:
        clauses.append("s.study_date <= ?")
        params.append(end_date)
    if subject_id is not None:
        clauses.append("s.subject_id = ?")
        params.append(subject_id)

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"""
        SELECT
            s.*,
            sub.subject_name,
            t.topic_name
        FROM study_sessions s
        JOIN subjects sub ON s.subject_id = sub.id
        LEFT JOIN topics t ON s.topic_id = t.id
        {where_sql}
        ORDER BY s.study_date DESC, s.id DESC;
    """
    return fetch_all(query, tuple(params), db_path=db_path)


def save_daily_checkin(
    checkin_date: str,
    goal_completed: int = 0,
    planned_study_minutes: Optional[int] = None,
    tomorrow_plan: Optional[str] = None,
    productivity_rating: Optional[int] = None,
    notes: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Create or update a daily check-in for a specific date."""
    clean_date = _require_non_empty(checkin_date, "Check-in date")
    if goal_completed not in (0, 1):
        raise ValueError("goal_completed must be 0 or 1.")
    if planned_study_minutes is not None and planned_study_minutes < 0:
        raise ValueError("Planned study minutes cannot be negative.")
    if productivity_rating is not None and (
        productivity_rating < 1 or productivity_rating > 5
    ):
        raise ValueError("Productivity rating must be between 1 and 5.")

    now = _now_iso()
    existing = fetch_one(
        "SELECT id FROM daily_checkins WHERE checkin_date = ?;",
        (clean_date,),
        db_path=db_path,
    )
    if existing is None:
        return execute_query(
            """
            INSERT INTO daily_checkins (
                checkin_date, goal_completed, planned_study_minutes,
                tomorrow_plan, productivity_rating, notes, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                clean_date,
                goal_completed,
                planned_study_minutes,
                tomorrow_plan,
                productivity_rating,
                notes,
                now,
                now,
            ),
            db_path=db_path,
        )

    checkin_id = int(existing["id"])
    execute_query(
        """
        UPDATE daily_checkins
        SET goal_completed = ?, planned_study_minutes = ?, tomorrow_plan = ?,
            productivity_rating = ?, notes = ?, updated_at = ?
        WHERE id = ?;
        """,
        (
            goal_completed,
            planned_study_minutes,
            tomorrow_plan,
            productivity_rating,
            notes,
            now,
            checkin_id,
        ),
        db_path=db_path,
    )
    return checkin_id


def save_timetable_entry(
    subject_id: int,
    study_date: str,
    start_time: str,
    end_time: str,
    topic_id: Optional[int] = None,
    session_title: Optional[str] = None,
    priority: str = "Medium",
    status: str = "Planned",
    source: str = "Generated",
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Insert a timetable session entry and return its ID."""
    clean_date = _require_non_empty(study_date, "Study date")
    clean_start = _require_non_empty(start_time, "Start time")
    clean_end = _require_non_empty(end_time, "End time")
    if priority not in VALID_PRIORITIES:
        raise ValueError(f"Invalid priority: {priority}")
    if status not in VALID_TIMETABLE_STATUSES:
        raise ValueError(f"Invalid timetable status: {status}")
    if source not in VALID_TIMETABLE_SOURCES:
        raise ValueError(f"Invalid timetable source: {source}")

    _validate_topic_belongs_to_subject(topic_id, subject_id, db_path=db_path)

    now = _now_iso()
    return execute_query(
        """
        INSERT INTO timetable (
            subject_id, topic_id, study_date, start_time, end_time,
            session_title, priority, status, source, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            subject_id,
            topic_id,
            clean_date,
            clean_start,
            clean_end,
            session_title,
            priority,
            status,
            source,
            now,
            now,
        ),
        db_path=db_path,
    )


def save_video_resource(
    subject_id: int,
    title: str,
    video_url: str,
    topic_id: Optional[int] = None,
    channel_name: Optional[str] = None,
    notes: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Insert a saved video resource and return its ID."""
    clean_title = _require_non_empty(title, "Video title")
    clean_url = _require_non_empty(video_url, "Video URL")
    _validate_topic_belongs_to_subject(topic_id, subject_id, db_path=db_path)

    return execute_query(
        """
        INSERT INTO video_resources (
            subject_id, topic_id, title, channel_name, video_url, notes, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """,
        (
            subject_id,
            topic_id,
            clean_title,
            channel_name,
            clean_url,
            notes,
            _now_iso(),
        ),
        db_path=db_path,
    )
