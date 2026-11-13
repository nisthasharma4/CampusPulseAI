"""Unit tests for the Rule-Based AI Recommendation Engine (Step 7)."""

from datetime import datetime, time
import pytest

from database.db import initialize_database
from services.academic_service import create_marks_record, upsert_attendance
from services.assignment_service import create_assignment
from services.profile_service import save_profile
from services.recommendation_service import (
    calculate_overall_progress_status,
    generate_academic_recommendations,
    generate_assignment_recommendations,
    generate_attendance_recommendations,
    generate_productivity_insights,
    generate_study_recommendations,
    generate_topic_recommendations,
    get_prioritized_recommendations,
)
from services.study_service import create_study_session, save_checkin
from services.subject_service import create_subject, create_topic

FIXED_NOW = datetime(2026, 11, 12, 15, 0, 0)  # Thursday


@pytest.fixture()
def temp_db(tmp_path):
    """Provide a clean initialized temporary SQLite database."""
    db_file = tmp_path / "test_step7.db"
    assert initialize_database(db_file) is True
    return db_file


def test_empty_database_and_insufficient_data(temp_db):
    status = calculate_overall_progress_status(current_dt=FIXED_NOW, db_path=temp_db)
    assert status["status"] == "Insufficient Data"

    recs = get_prioritized_recommendations(current_dt=FIXED_NOW, db_path=temp_db)
    rec_ids = {r["id"] for r in recs}
    assert "study-no-records" in rec_ids
    assert "productivity-insufficient" in rec_ids


def test_academic_marks_recommendations_and_configurable_threshold(temp_db):
    s_low = create_subject("DBMS", semester=3, db_path=temp_db)
    s_good = create_subject("DSA", semester=3, db_path=temp_db)
    s_none = create_subject("Ethics", semester=3, db_path=temp_db)

    create_marks_record(s_low, "Quiz", 4, 10, "2026-11-01", db_path=temp_db)
    create_marks_record(s_low, "Test", 11, 20, "2026-11-10", db_path=temp_db)  # 15/30 = 50%
    create_marks_record(s_good, "Test", 17, 20, "2026-11-10", db_path=temp_db)  # 85%

    recs = generate_academic_recommendations(
        current_dt=FIXED_NOW, marks_threshold=60.0, db_path=temp_db
    )
    by_id = {r["id"]: r for r in recs}

    assert by_id[f"academic-low-{s_low}"]["priority"] == "High Priority"
    assert by_id[f"academic-good-{s_good}"]["priority"] == "Positive Progress"
    assert "Insufficient assessment information" in by_id[f"academic-missing-{s_none}"]["title"]
    assert f"academic-trend-up-{s_low}" in by_id

    # Configurable threshold: lowering threshold to 45% turns DBMS into Positive Progress
    recs_custom = generate_academic_recommendations(
        current_dt=FIXED_NOW, marks_threshold=45.0, db_path=temp_db
    )
    assert f"academic-good-{s_low}" in {r["id"] for r in recs_custom}


def test_attendance_recommendations(temp_db):
    save_profile(name="Aarav", semester=3, attendance_target=75.0, db_path=temp_db)
    s_low = create_subject("DBMS", semester=3, db_path=temp_db)
    s_good = create_subject("DSA", semester=3, db_path=temp_db)

    upsert_attendance(s_low, 25, 17, db_path=temp_db)  # 68%
    upsert_attendance(s_good, 20, 18, db_path=temp_db)  # 90%

    recs = {r["id"]: r for r in generate_attendance_recommendations(current_dt=FIXED_NOW, db_path=temp_db)}
    assert recs[f"attendance-low-{s_low}"]["priority"] == "High Priority"
    assert recs[f"attendance-good-{s_good}"]["priority"] == "Positive Progress"


def test_assignment_recommendations_and_completed_suppression(temp_db):
    sid = create_subject("Java", semester=3, db_path=temp_db)
    a_over = create_assignment(sid, "Lab 1", "2026-11-10", db_path=temp_db)
    a_today = create_assignment(sid, "Lab 2", "2026-11-12", deadline_time=time(23, 59), db_path=temp_db)
    a_soon = create_assignment(sid, "Lab 3", "2026-11-13", db_path=temp_db)
    a_done = create_assignment(sid, "Lab 0", "2026-11-09", status="Completed", db_path=temp_db)

    recs = {r["id"]: r for r in generate_assignment_recommendations(current_dt=FIXED_NOW, db_path=temp_db)}
    assert recs[f"assign-overdue-{a_over}"]["priority"] == "High Priority"
    assert recs[f"assign-today-{a_today}"]["priority"] == "High Priority"
    assert recs[f"assign-soon-{a_soon}"]["priority"] == "Medium Priority"
    assert f"assign-overdue-{a_done}" not in recs


def test_study_consistency_weekly_target_and_weak_subject_combined(temp_db):
    save_profile(
        name="Aarav", semester=3, weekly_study_target=12, attendance_target=75.0, db_path=temp_db
    )
    sid = create_subject("DBMS", semester=3, db_path=temp_db)
    create_marks_record(sid, "Internal Assessment", 45, 100, db_path=temp_db)
    upsert_attendance(sid, 25, 17, db_path=temp_db)

    # 2 hours logged in current week (2026-11-09..2026-11-15) against 12h target (< 70%)
    create_study_session(sid, "2026-11-11", 120, db_path=temp_db)
    recs_low = {r["id"]: r for r in generate_study_recommendations(current_dt=FIXED_NOW, db_path=temp_db)}
    assert "study-weekly-low" in recs_low
    assert f"study-weak-combined-{sid}" in recs_low

    # Add 10 more hours -> 12h total -> meets weekly target
    create_study_session(sid, "2026-11-12", 600, db_path=temp_db)
    recs_met = {r["id"]: r for r in generate_study_recommendations(current_dt=FIXED_NOW, db_path=temp_db)}
    assert "study-weekly-met" in recs_met
    assert "study-weekly-low" not in recs_met


def test_topic_recommendations_overdue_and_completed(temp_db):
    s1 = create_subject("DSA", semester=3, db_path=temp_db)
    s2 = create_subject("OS", semester=3, db_path=temp_db)

    t_over = create_topic(
        s1, "Linked Lists", target_date="2026-11-10", estimated_hours=2.0, status="In Progress", db_path=temp_db
    )
    create_study_session(s1, "2026-11-11", 180, topic_id=t_over, db_path=temp_db)  # 3h > 2h est

    create_topic(s2, "Processes", status="Completed", db_path=temp_db)

    recs = {r["id"]: r for r in generate_topic_recommendations(current_dt=FIXED_NOW, db_path=temp_db)}
    assert f"topic-overdue-{t_over}" in recs
    assert f"topic-overhours-{t_over}" in recs
    assert f"topic-all-done-{s2}" in recs


def test_productivity_insights_and_insufficient_data(temp_db):
    # Fewer than 4 check-ins -> insufficient data
    save_checkin("2026-11-10", True, 2.0, productivity_rating=3, db_path=temp_db)
    insuff = generate_productivity_insights(current_dt=FIXED_NOW, db_path=temp_db)
    assert len(insuff) == 1
    assert insuff[0]["id"] == "productivity-insufficient"

    # Add 3 more check-ins showing upward rating trend & low goal completion
    save_checkin("2026-11-08", False, 2.0, productivity_rating=2, db_path=temp_db)
    save_checkin("2026-11-09", False, 2.0, productivity_rating=2, db_path=temp_db)
    save_checkin("2026-11-11", False, 2.0, productivity_rating=5, db_path=temp_db)
    save_checkin("2026-11-12", False, 2.0, productivity_rating=5, db_path=temp_db)

    insights = {r["id"]: r for r in generate_productivity_insights(current_dt=FIXED_NOW, db_path=temp_db)}
    assert "productivity-trend-up" in insights
    assert "productivity-low-goals" in insights


def test_priority_sorting_deduplication_and_overall_status(temp_db):
    save_profile(name="Aarav", semester=3, weekly_study_target=10, attendance_target=75.0, db_path=temp_db)
    sid = create_subject("DSA", semester=3, db_path=temp_db)
    create_marks_record(sid, "Internal Assessment", 85, 100, db_path=temp_db)
    upsert_attendance(sid, 20, 18, db_path=temp_db)
    create_study_session(sid, "2026-11-12", 600, db_path=temp_db)  # 10 hrs

    status = calculate_overall_progress_status(current_dt=FIXED_NOW, db_path=temp_db)
    assert status["status"] == "Excellent Progress"

    # Add overdue assignment -> status becomes Needs Attention, sorted first (score 100)
    create_assignment(sid, "Overdue Lab", "2026-11-10", db_path=temp_db)
    recs = get_prioritized_recommendations(current_dt=FIXED_NOW, db_path=temp_db)
    scores = [r["priority_score"] for r in recs]
    assert scores == sorted(scores, reverse=True)
    assert recs[0]["priority_score"] == 100
    assert len({r["id"] for r in recs}) == len(recs)
    assert calculate_overall_progress_status(current_dt=FIXED_NOW, db_path=temp_db)["status"] == "Needs Attention"
