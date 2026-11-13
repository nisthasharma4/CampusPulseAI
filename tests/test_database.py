"""Comprehensive unit tests for CampusPulse AI SQLite database and schema."""

import sqlite3
import pytest

from database.db import (
    execute_query,
    fetch_all,
    fetch_one,
    get_connection,
    initialize_database,
    table_exists,
)
from database.queries import (
    fetch_all_subjects,
    fetch_study_history,
    fetch_topics_by_subject,
    get_student_profile,
    insert_subject,
    insert_topic,
    save_assignment,
    save_attendance,
    save_calendar_event,
    save_daily_checkin,
    save_marks,
    save_student_profile,
    save_study_session,
    save_timetable_entry,
    save_video_resource,
    update_topic,
)
from database.schema import REQUIRED_TABLES, SCHEMA_VERSION, get_schema_version


@pytest.fixture()
def temp_db(tmp_path):
    """Provide an initialized temporary SQLite database path for each test."""
    db_file = tmp_path / "test_campuspulse.db"
    assert initialize_database(db_file) is True
    return db_file


def test_database_initialization_and_all_11_tables_exist(temp_db):
    assert temp_db.exists()
    assert len(REQUIRED_TABLES) == 11
    for table in REQUIRED_TABLES:
        assert table_exists(table, db_path=temp_db) is True

    conn = get_connection(temp_db)
    try:
        assert get_schema_version(conn) == SCHEMA_VERSION
    finally:
        conn.close()


def test_repeated_initialization_does_not_fail_or_drop_data(temp_db):
    subject_id = insert_subject("Data Structures", subject_code="CS201", db_path=temp_db)
    assert initialize_database(temp_db) is True
    subjects = fetch_all_subjects(db_path=temp_db)
    assert len(subjects) == 1
    assert subjects[0]["id"] == subject_id


def test_foreign_keys_are_enabled(temp_db):
    conn = get_connection(temp_db)
    try:
        fk_status = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
        assert fk_status == 1
    finally:
        conn.close()


def test_student_profile_insert_and_retrieve(temp_db):
    profile_id = save_student_profile(
        name="Aarav Sharma",
        branch="Computer Science",
        semester=3,
        college_name="ABC Institute of Technology",
        weekly_study_target=18,
        preferred_start_time="18:00",
        preferred_end_time="21:00",
        available_days="Monday,Tuesday,Wednesday,Thursday,Friday",
        daily_available_minutes=120,
        session_duration_minutes=60,
        break_duration_minutes=10,
        attendance_target=75.0,
        db_path=temp_db,
    )
    assert profile_id > 0
    profile = get_student_profile(db_path=temp_db)
    assert profile is not None
    assert profile["name"] == "Aarav Sharma"
    assert profile["semester"] == 3


def test_subject_and_topic_insert_and_retrieve(temp_db):
    subject_id = insert_subject(
        subject_name="Data Structures and Algorithms",
        subject_code="CS301",
        semester=3,
        start_date="2026-11-01",
        status="In Progress",
        db_path=temp_db,
    )
    topic_id = insert_topic(
        subject_id=subject_id,
        topic_name="Arrays",
        sequence_number=1,
        start_date="2026-11-02",
        estimated_hours=4.0,
        status="In Progress",
        db_path=temp_db,
    )
    subjects = fetch_all_subjects(db_path=temp_db)
    topics = fetch_topics_by_subject(subject_id, db_path=temp_db)
    assert len(subjects) == 1
    assert len(topics) == 1
    assert topics[0]["id"] == topic_id
    assert topics[0]["topic_name"] == "Arrays"


def test_attendance_insert_and_update(temp_db):
    subject_id = insert_subject("DBMS", db_path=temp_db)
    att_id = save_attendance(subject_id, classes_held=20, classes_attended=17, db_path=temp_db)
    assert att_id > 0

    att_id_2 = save_attendance(subject_id, classes_held=22, classes_attended=19, db_path=temp_db)
    assert att_id_2 == att_id
    row = fetch_one("SELECT * FROM attendance WHERE subject_id = ?;", (subject_id,), db_path=temp_db)
    assert row["classes_held"] == 22
    assert row["classes_attended"] == 19


def test_marks_assignment_calendar_checkin_timetable_video_insert(temp_db):
    subject_id = insert_subject("Operating Systems", db_path=temp_db)
    topic_id = insert_topic(subject_id, "CPU Scheduling", db_path=temp_db)

    marks_id = save_marks(
        subject_id=subject_id,
        assessment_type="Internal Assessment",
        marks_obtained=24.5,
        maximum_marks=30.0,
        assessment_date="2026-11-10",
        db_path=temp_db,
    )
    assert marks_id > 0

    assignment_id = save_assignment(
        subject_id=subject_id,
        title="Process Scheduling Lab",
        deadline_date="2026-11-20",
        priority="High",
        status="Pending",
        db_path=temp_db,
    )
    assert assignment_id > 0

    event_id = save_calendar_event(
        title="Mid-Sem Exam",
        event_type="Internal Examination",
        start_date="2026-11-25",
        end_date="2026-11-30",
        db_path=temp_db,
    )
    assert event_id > 0

    checkin_id = save_daily_checkin(
        checkin_date="2026-11-12",
        goal_completed=1,
        planned_study_minutes=120,
        tomorrow_plan="Revise Deadlocks",
        productivity_rating=4,
        db_path=temp_db,
    )
    assert checkin_id > 0

    tt_id = save_timetable_entry(
        subject_id=subject_id,
        topic_id=topic_id,
        study_date="2026-11-13",
        start_time="18:00",
        end_time="19:00",
        session_title="OS - CPU Scheduling",
        priority="High",
        status="Planned",
        source="Generated",
        db_path=temp_db,
    )
    assert tt_id > 0

    video_id = save_video_resource(
        subject_id=subject_id,
        topic_id=topic_id,
        title="CPU Scheduling Algorithms",
        channel_name="Gate Smashers",
        video_url="https://www.youtube.com/watch?v=example",
        db_path=temp_db,
    )
    assert video_id > 0


def test_study_session_insert_and_retrieve(temp_db):
    subject_id = insert_subject("Computer Networks", db_path=temp_db)
    topic_id = insert_topic(subject_id, "OSI Model", db_path=temp_db)

    session_id = save_study_session(
        subject_id=subject_id,
        topic_id=topic_id,
        study_date="2026-11-12",
        start_time="18:00",
        end_time="19:30",
        duration_minutes=90,
        study_goal="Understand 7 layers",
        completed_work="Finished layers 1-5",
        productivity_rating=5,
        status="Completed",
        db_path=temp_db,
    )
    assert session_id > 0

    history = fetch_study_history(
        start_date="2026-11-01",
        end_date="2026-11-30",
        subject_id=subject_id,
        db_path=temp_db,
    )
    assert len(history) == 1
    assert history[0]["duration_minutes"] == 90
    assert history[0]["subject_name"] == "Computer Networks"
    assert history[0]["topic_name"] == "OSI Model"


def test_invalid_marks_rejected(temp_db):
    subject_id = insert_subject("Discrete Math", db_path=temp_db)

    with pytest.raises(ValueError):
        save_marks(subject_id, "Quiz", -2, 10, db_path=temp_db)

    with pytest.raises(ValueError):
        save_marks(subject_id, "Quiz", 12, 10, db_path=temp_db)

    with pytest.raises(ValueError):
        save_marks(subject_id, "Quiz", 0, 0, db_path=temp_db)

    # Also verify SQLite CHECK constraint directly
    with pytest.raises(sqlite3.IntegrityError):
        execute_query(
            "INSERT INTO marks (subject_id, assessment_type, marks_obtained, maximum_marks) VALUES (?, ?, ?, ?);",
            (subject_id, "Quiz", 25, 20),
            db_path=temp_db,
        )


def test_invalid_attendance_rejected(temp_db):
    subject_id = insert_subject("Java", db_path=temp_db)

    with pytest.raises(ValueError):
        save_attendance(subject_id, classes_held=10, classes_attended=12, db_path=temp_db)

    with pytest.raises(ValueError):
        save_attendance(subject_id, classes_held=-1, classes_attended=0, db_path=temp_db)

    with pytest.raises(sqlite3.IntegrityError):
        execute_query(
            "INSERT INTO attendance (subject_id, classes_held, classes_attended) VALUES (?, ?, ?);",
            (subject_id, 10, 15),
            db_path=temp_db,
        )


def test_negative_or_zero_study_duration_rejected(temp_db):
    subject_id = insert_subject("Python", db_path=temp_db)

    with pytest.raises(ValueError):
        save_study_session(subject_id, "2026-11-12", duration_minutes=0, db_path=temp_db)

    with pytest.raises(ValueError):
        save_study_session(subject_id, "2026-11-12", duration_minutes=-30, db_path=temp_db)

    with pytest.raises(sqlite3.IntegrityError):
        execute_query(
            "INSERT INTO study_sessions (subject_id, study_date, duration_minutes) VALUES (?, ?, ?);",
            (subject_id, "2026-11-12", -15),
            db_path=temp_db,
        )


def test_invalid_productivity_rating_rejected(temp_db):
    subject_id = insert_subject("Software Engineering", db_path=temp_db)

    with pytest.raises(ValueError):
        save_study_session(subject_id, "2026-11-12", 60, productivity_rating=6, db_path=temp_db)

    with pytest.raises(ValueError):
        save_daily_checkin("2026-11-12", goal_completed=1, productivity_rating=0, db_path=temp_db)

    with pytest.raises(sqlite3.IntegrityError):
        execute_query(
            "INSERT INTO study_sessions (subject_id, study_date, duration_minutes, productivity_rating) VALUES (?, ?, ?, ?);",
            (subject_id, "2026-11-12", 45, 7),
            db_path=temp_db,
        )


def test_foreign_key_violations_rejected(temp_db):
    non_existent_subject_id = 9999
    with pytest.raises(sqlite3.IntegrityError):
        insert_topic(non_existent_subject_id, "Orphan Topic", db_path=temp_db)

    with pytest.raises(sqlite3.IntegrityError):
        save_marks(non_existent_subject_id, "Quiz", 8, 10, db_path=temp_db)

    # Cross-subject topic_id mismatch is also rejected
    subj_a = insert_subject("Subject A", db_path=temp_db)
    subj_b = insert_subject("Subject B", db_path=temp_db)
    topic_a = insert_topic(subj_a, "Topic A1", db_path=temp_db)
    with pytest.raises(ValueError):
        save_study_session(subj_b, "2026-11-12", 60, topic_id=topic_a, db_path=temp_db)


def test_historical_study_records_preserved_after_topic_update_and_delete(temp_db):
    subject_id = insert_subject("DSA", db_path=temp_db)
    topic_id = insert_topic(subject_id, "Linked Lists", status="In Progress", db_path=temp_db)

    save_study_session(
        subject_id=subject_id,
        topic_id=topic_id,
        study_date="2026-11-12",
        duration_minutes=120,
        status="Completed",
        db_path=temp_db,
    )

    # Update topic name and mark completed
    update_topic(
        topic_id=topic_id,
        topic_name="Singly & Doubly Linked Lists",
        status="Completed",
        completion_date="2026-11-14",
        db_path=temp_db,
    )

    history_after_update = fetch_study_history(subject_id=subject_id, db_path=temp_db)
    assert len(history_after_update) == 1
    assert history_after_update[0]["duration_minutes"] == 120
    assert history_after_update[0]["topic_name"] == "Singly & Doubly Linked Lists"

    # Even if the topic is deleted, the study session remains (topic_id becomes NULL)
    execute_query("DELETE FROM topics WHERE id = ?;", (topic_id,), db_path=temp_db)
    history_after_delete = fetch_study_history(subject_id=subject_id, db_path=temp_db)
    assert len(history_after_delete) == 1
    assert history_after_delete[0]["duration_minutes"] == 120
    assert history_after_delete[0]["topic_id"] is None
