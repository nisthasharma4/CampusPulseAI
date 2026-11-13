"""Unit tests for Daily Study Tracker, Study Journal & Time Analysis (Step 4)."""

from datetime import date, time
import pytest

from database.db import fetch_all, initialize_database
from services.study_service import (
    calculate_average_session_duration,
    calculate_duration_from_times,
    calculate_manual_duration,
    calculate_total_study_minutes,
    create_study_session,
    delete_study_session,
    fetch_sessions,
    get_daily_checkin,
    get_date_range_for_filter,
    get_study_session,
    get_subject_study_summary,
    get_today_study_overview,
    get_topic_study_summary,
    save_checkin,
    update_study_session,
)
from services.subject_service import (
    change_topic_status,
    create_subject,
    create_topic,
    get_topic,
    update_topic_details,
)


@pytest.fixture()
def temp_db(tmp_path):
    """Provide a clean initialized temporary SQLite database."""
    db_file = tmp_path / "test_step4.db"
    assert initialize_database(db_file) is True
    return db_file


def test_duration_calculations_and_rejections():
    assert calculate_duration_from_times(time(18, 0), time(20, 0)) == 120
    assert calculate_manual_duration(1, 30) == 90

    with pytest.raises(ValueError):
        calculate_duration_from_times(time(20, 0), time(18, 0))

    with pytest.raises(ValueError):
        calculate_duration_from_times(time(18, 0), time(18, 0))

    with pytest.raises(ValueError):
        calculate_manual_duration(-1, 30)

    with pytest.raises(ValueError):
        calculate_manual_duration(0, 0)


def test_study_session_crud_and_persistence(temp_db):
    sid = create_subject("DSA", semester=3, db_path=temp_db)
    tid = create_topic(sid, "Arrays", db_path=temp_db)

    sess_id = create_study_session(
        subject_id=sid,
        topic_id=tid,
        study_date="2026-11-12",
        start_time=time(18, 0),
        end_time=time(20, 0),
        duration_minutes=120,
        study_goal="Master array rotations",
        completed_work="Solved 5 problems",
        next_topic="Linked Lists",
        productivity_rating=5,
        status="Completed",
        db_path=temp_db,
    )
    assert sess_id > 0

    fetched = get_study_session(sess_id, db_path=temp_db)
    assert fetched is not None
    assert fetched["duration_minutes"] == 120
    original_created_at = fetched["created_at"]

    # Edit session
    update_study_session(
        session_id=sess_id,
        subject_id=sid,
        topic_id=tid,
        study_date="2026-11-12",
        duration_minutes=90,
        start_time=time(18, 0),
        end_time=time(19, 30),
        completed_work="Solved 4 problems",
        productivity_rating=4,
        status="Partially Completed",
        db_path=temp_db,
    )
    updated = get_study_session(sess_id, db_path=temp_db)
    assert updated["duration_minutes"] == 90
    assert updated["created_at"] == original_created_at

    # Delete session
    delete_study_session(sess_id, db_path=temp_db)
    assert get_study_session(sess_id, db_path=temp_db) is None

    # Re-create and verify persistence across re-initialization
    sess_id_2 = create_study_session(
        subject_id=sid,
        topic_id=tid,
        study_date="2026-11-12",
        duration_minutes=60,
        db_path=temp_db,
    )
    assert initialize_database(temp_db) is True
    assert get_study_session(sess_id_2, db_path=temp_db)["duration_minutes"] == 60


def test_negative_duration_and_invalid_session_rejected(temp_db):
    sid = create_subject("DBMS", semester=3, db_path=temp_db)

    with pytest.raises(ValueError):
        create_study_session(sid, "2026-11-12", duration_minutes=0, db_path=temp_db)

    with pytest.raises(ValueError):
        create_study_session(sid, "2026-11-12", duration_minutes=-45, db_path=temp_db)


def test_subject_and_topic_study_time_aggregations(temp_db):
    s1 = create_subject("DSA", semester=3, db_path=temp_db)
    s2 = create_subject("Java", semester=3, db_path=temp_db)
    t1 = create_topic(s1, "Arrays", db_path=temp_db)
    t2 = create_topic(s1, "Trees", db_path=temp_db)

    create_study_session(s1, "2026-11-10", 90, topic_id=t1, db_path=temp_db)
    create_study_session(s1, "2026-11-11", 60, topic_id=t1, db_path=temp_db)
    create_study_session(s2, "2026-11-12", 45, db_path=temp_db)

    subj_summary = {r["subject_name"]: r for r in get_subject_study_summary(db_path=temp_db)}
    assert subj_summary["DSA"]["total_minutes"] == 150
    assert subj_summary["DSA"]["hours"] == 2
    assert subj_summary["DSA"]["remaining_minutes"] == 30
    assert subj_summary["DSA"]["session_count"] == 2
    assert subj_summary["Java"]["total_minutes"] == 45

    topic_summary = {r["topic_name"]: r for r in get_topic_study_summary(subject_id=s1, db_path=temp_db)}
    assert topic_summary["Arrays"]["total_hours"] == 2.5
    assert topic_summary["Trees"]["total_hours"] == 0.0

    all_sessions = fetch_sessions(db_path=temp_db)
    assert calculate_total_study_minutes(db_path=temp_db) == 195
    assert calculate_average_session_duration(all_sessions) == 65.0


def test_date_range_filtering_and_reverse_chronological_sorting(temp_db):
    sid = create_subject("OS", semester=4, db_path=temp_db)
    create_study_session(sid, "2026-11-01", 60, db_path=temp_db)
    create_study_session(sid, "2026-11-10", 60, db_path=temp_db)
    create_study_session(sid, "2026-11-12", 60, db_path=temp_db)

    sessions = fetch_sessions(db_path=temp_db)
    dates = [s["study_date"] for s in sessions]
    assert dates == ["2026-11-12", "2026-11-10", "2026-11-01"]

    s_iso, e_iso = get_date_range_for_filter("Last 7 Days", reference_date=date(2026, 11, 12))
    filtered = fetch_sessions(start_date=s_iso, end_date=e_iso, db_path=temp_db)
    assert [s["study_date"] for s in filtered] == ["2026-11-12", "2026-11-10"]

    overview = get_today_study_overview(target_date="2026-11-12", db_path=temp_db)
    assert overview["studied_minutes"] == 60
    assert overview["session_count"] == 1


def test_daily_checkin_create_and_update_without_duplication(temp_db):
    c1 = save_checkin(
        checkin_date="2026-11-12",
        goal_completed=False,
        planned_study_hours=2.0,
        tomorrow_plan="Linked Lists",
        productivity_rating=3,
        db_path=temp_db,
    )
    row1 = get_daily_checkin("2026-11-12", db_path=temp_db)
    orig_created_at = row1["created_at"]

    c2 = save_checkin(
        checkin_date="2026-11-12",
        goal_completed=True,
        planned_study_hours=2.5,
        tomorrow_plan="Stacks & Queues",
        productivity_rating=5,
        db_path=temp_db,
    )
    assert c2 == c1
    rows = fetch_all("SELECT * FROM daily_checkins;", db_path=temp_db)
    assert len(rows) == 1
    assert rows[0]["goal_completed"] == 1
    assert rows[0]["created_at"] == orig_created_at


def test_automatic_topic_status_and_date_preservation_with_sessions(temp_db):
    sid = create_subject("Algorithms", semester=4, db_path=temp_db)
    t_new = create_topic(sid, "Greedy", status="Not Started", db_path=temp_db)
    t_existing = create_topic(
        sid, "DP", start_date="2026-11-01", status="In Progress", db_path=temp_db
    )
    t_done = create_topic(sid, "Sorting", status="Completed", db_path=temp_db)
    change_topic_status(t_done, "Completed", db_path=temp_db)
    done_comp_date = get_topic(t_done, db_path=temp_db)["completion_date"]

    # First session on Not Started topic -> In Progress + start_date = study_date
    create_study_session(sid, "2026-11-12", 60, topic_id=t_new, db_path=temp_db)
    t_new_after = get_topic(t_new, db_path=temp_db)
    assert t_new_after["status"] == "In Progress"
    assert t_new_after["start_date"] == "2026-11-12"

    # Session on topic with existing start_date -> preserves existing start_date
    create_study_session(sid, "2026-11-12", 60, topic_id=t_existing, db_path=temp_db)
    assert get_topic(t_existing, db_path=temp_db)["start_date"] == "2026-11-01"

    # Revision session on Completed topic -> stays Completed and preserves completion_date
    create_study_session(sid, "2026-11-12", 45, topic_id=t_done, db_path=temp_db)
    t_done_after = get_topic(t_done, db_path=temp_db)
    assert t_done_after["status"] == "Completed"
    assert t_done_after["completion_date"] == done_comp_date

    # Historical sessions remain available after topic edits
    update_topic_details(t_new, topic_name="Greedy Algorithms", db_path=temp_db)
    sessions = fetch_sessions(subject_id=sid, topic_id=t_new, db_path=temp_db)
    assert len(sessions) == 1
    assert sessions[0]["topic_name"] == "Greedy Algorithms"
