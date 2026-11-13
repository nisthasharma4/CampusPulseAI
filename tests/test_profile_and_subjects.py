"""Unit tests for Student Profile, Subject Management, and Topic Tracking (Step 3)."""

from datetime import date, time
import pytest

from database.db import fetch_all, initialize_database
from database.queries import fetch_study_history, save_study_session
from services.profile_service import get_profile, save_profile
from services.subject_service import (
    change_topic_status,
    create_subject,
    create_topic,
    delete_subject,
    delete_topic,
    get_subject,
    get_subject_learning_journey,
    get_subject_progress,
    get_topic,
    list_subjects,
    list_topics,
    update_subject,
    update_topic_details,
)


@pytest.fixture()
def temp_db(tmp_path):
    """Provide a clean initialized temporary SQLite database."""
    db_file = tmp_path / "test_step3.db"
    assert initialize_database(db_file) is True
    return db_file


def test_profile_create_update_and_prevent_duplicates(temp_db):
    pid1 = save_profile(
        name="Aarav Sharma",
        college_name="ABC Engineering College",
        branch="CSE",
        semester=3,
        weekly_study_target=16,
        daily_available_hours=2.5,
        preferred_start_time=time(18, 0),
        preferred_end_time=time(21, 0),
        available_days=["Monday", "Wednesday", "Friday"],
        session_duration_minutes=60,
        break_duration_minutes=10,
        attendance_target=80.0,
        db_path=temp_db,
    )
    created = get_profile(db_path=temp_db)
    assert created is not None
    assert created["name"] == "Aarav Sharma"
    assert created["daily_available_minutes"] == 150
    original_created_at = created["created_at"]

    # Update profile — must reuse same row and preserve created_at
    pid2 = save_profile(
        name="Aarav S.",
        college_name="ABC Engineering College",
        branch="Computer Science",
        semester=4,
        weekly_study_target=20,
        daily_available_hours=3.0,
        preferred_start_time=time(17, 30),
        preferred_end_time=time(21, 0),
        available_days=["Monday", "Tuesday", "Wednesday", "Thursday"],
        session_duration_minutes=50,
        break_duration_minutes=10,
        attendance_target=75.0,
        db_path=temp_db,
    )
    assert pid2 == pid1
    all_rows = fetch_all("SELECT * FROM student_profile;", db_path=temp_db)
    assert len(all_rows) == 1
    assert all_rows[0]["name"] == "Aarav S."
    assert all_rows[0]["semester"] == 4
    assert all_rows[0]["created_at"] == original_created_at


def test_invalid_profile_rejected(temp_db):
    with pytest.raises(ValueError):
        save_profile(name="   ", db_path=temp_db)

    with pytest.raises(ValueError):
        save_profile(
            name="Aarav",
            preferred_start_time=time(21, 0),
            preferred_end_time=time(18, 0),
            db_path=temp_db,
        )

    with pytest.raises(ValueError):
        save_profile(name="Aarav", attendance_target=110.0, db_path=temp_db)


def test_subject_create_edit_and_status_changes(temp_db):
    sid = create_subject(
        subject_name="Data Structures and Algorithms",
        subject_code="CS301",
        semester=3,
        status="Not Started",
        db_path=temp_db,
    )
    subj = get_subject(sid, db_path=temp_db)
    assert subj["status"] == "Not Started"
    assert subj["start_date"] is None

    # Mark In Progress -> auto-records start_date
    update_subject(
        subject_id=sid,
        subject_name="Data Structures and Algorithms",
        subject_code="CS301",
        semester=3,
        status="In Progress",
        db_path=temp_db,
    )
    subj = get_subject(sid, db_path=temp_db)
    assert subj["start_date"] == date.today().isoformat()

    # Mark Completed -> auto-records completion_date and preserves start_date
    update_subject(
        subject_id=sid,
        subject_name="Data Structures and Algorithms",
        subject_code="CS301",
        semester=3,
        status="Completed",
        db_path=temp_db,
    )
    subj = get_subject(sid, db_path=temp_db)
    assert subj["completion_date"] == date.today().isoformat()
    assert subj["start_date"] == date.today().isoformat()


def test_invalid_and_duplicate_subject_rejected(temp_db):
    with pytest.raises(ValueError):
        create_subject(subject_name="  ", semester=3, db_path=temp_db)

    with pytest.raises(ValueError):
        create_subject(
            subject_name="DBMS",
            semester=3,
            start_date=date(2026, 11, 20),
            target_completion_date=date(2026, 11, 10),
            db_path=temp_db,
        )

    create_subject(subject_name="DBMS", semester=3, db_path=temp_db)
    with pytest.raises(ValueError):
        create_subject(subject_name="dbms", semester=3, db_path=temp_db)


def test_topic_create_edit_auto_dates_and_preservation(temp_db):
    sid = create_subject("Algorithms", semester=3, db_path=temp_db)
    tid = create_topic(
        subject_id=sid,
        topic_name="Divide and Conquer",
        sequence_number=1,
        estimated_hours=4.0,
        status="Not Started",
        db_path=temp_db,
    )
    topic = get_topic(tid, db_path=temp_db)
    assert topic["subject_id"] == sid
    assert topic["start_date"] is None
    assert topic["completion_date"] is None

    # Not Started -> In Progress sets start_date automatically
    change_topic_status(tid, "In Progress", db_path=temp_db)
    topic = get_topic(tid, db_path=temp_db)
    assert topic["start_date"] == date.today().isoformat()

    # Manually set an earlier historical start_date and edit notes without changing status
    update_topic_details(
        topic_id=tid,
        start_date=date(2026, 11, 1),
        notes="Read CLRS Ch 4",
        db_path=temp_db,
    )
    topic = get_topic(tid, db_path=temp_db)
    assert topic["start_date"] == "2026-11-01"

    # Mark Completed -> sets completion_date and preserves original start_date
    change_topic_status(tid, "Completed", db_path=temp_db)
    topic = get_topic(tid, db_path=temp_db)
    assert topic["start_date"] == "2026-11-01"
    assert topic["completion_date"] == date.today().isoformat()

    # Reopen Completed topic -> preserves historical completion_date
    change_topic_status(tid, "In Progress", db_path=temp_db)
    topic = get_topic(tid, db_path=temp_db)
    assert topic["status"] == "In Progress"
    assert topic["completion_date"] == date.today().isoformat()


def test_invalid_topic_data_rejected(temp_db):
    sid = create_subject("Operating Systems", semester=4, db_path=temp_db)

    with pytest.raises(ValueError):
        create_topic(sid, "   ", db_path=temp_db)

    with pytest.raises(ValueError):
        create_topic(sid, "Deadlocks", estimated_hours=-2.0, db_path=temp_db)

    with pytest.raises(ValueError):
        create_topic(sid, "Deadlocks", sequence_number=0, db_path=temp_db)

    with pytest.raises(ValueError):
        create_topic(
            sid,
            "Deadlocks",
            start_date=date(2026, 11, 15),
            target_date=date(2026, 11, 10),
            db_path=temp_db,
        )


def test_subject_progress_and_learning_journey(temp_db):
    sid = create_subject("DSA", semester=3, start_date="2026-11-12", db_path=temp_db)

    # Zero topics edge case
    empty_prog = get_subject_progress(sid, db_path=temp_db)
    assert empty_prog["total_topics"] == 0
    assert empty_prog["completion_percentage"] == 0.0

    t1 = create_topic(sid, "Arrays", sequence_number=1, status="Completed", db_path=temp_db)
    t2 = create_topic(sid, "Linked Lists", sequence_number=2, status="In Progress", db_path=temp_db)
    create_topic(sid, "Stacks", sequence_number=3, status="Not Started", db_path=temp_db)
    create_topic(sid, "Queues", sequence_number=4, status="Not Started", db_path=temp_db)

    prog = get_subject_progress(sid, db_path=temp_db)
    assert prog["total_topics"] == 4
    assert prog["completed_topics"] == 1
    assert prog["in_progress_topics"] == 1
    assert prog["pending_topics"] == 3
    assert prog["completion_percentage"] == 25.0

    journey = get_subject_learning_journey(sid, db_path=temp_db)
    assert journey["subject"]["start_date"] == "2026-11-12"
    assert len(journey["topics"]) == 4
    assert journey["topics"][0]["id"] == t1
    assert journey["topics"][0]["actual_study_hours"] == 0.0
    assert journey["topics"][1]["id"] == t2


def test_subject_and_topic_deletion_behavior(temp_db):
    sid = create_subject("Computer Networks", semester=5, db_path=temp_db)
    tid = create_topic(sid, "TCP/IP", db_path=temp_db)

    save_study_session(
        subject_id=sid,
        topic_id=tid,
        study_date="2026-11-12",
        duration_minutes=60,
        status="Completed",
        db_path=temp_db,
    )

    # Deleting a topic preserves study_sessions (topic_id becomes NULL)
    delete_topic(tid, db_path=temp_db)
    assert list_topics(sid, db_path=temp_db) == []
    history = fetch_study_history(subject_id=sid, db_path=temp_db)
    assert len(history) == 1
    assert history[0]["topic_id"] is None

    # Deleting a subject removes the subject and its dependent records
    delete_subject(sid, db_path=temp_db)
    assert list_subjects(db_path=temp_db) == []
