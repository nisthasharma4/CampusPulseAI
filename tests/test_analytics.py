"""Automated tests for Step 10 — Progress Analytics, Performance Reports & Data Export."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import sys

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database.db import initialize_database
from database.queries import (
    insert_subject,
    insert_topic,
    save_assignment,
    save_attendance,
    save_daily_checkin,
    save_marks,
    save_student_profile,
    save_study_session,
    save_timetable_entry,
)
from services.analytics_service import (
    calculate_study_streaks,
    export_study_history,
    export_subject_summary,
    export_topic_summary,
    generate_progress_report,
    get_academic_marks_summary,
    get_assignment_analytics,
    get_current_attendance_summary,
    get_daily_productivity_summary,
    get_daily_study_minutes,
    get_date_range,
    get_monthly_study_summary,
    get_study_summary,
    get_subject_completion_summary,
    get_subject_study_summary,
    get_timetable_analytics,
    get_topic_completion_duration,
    get_topic_study_summary,
    get_weekly_study_summary,
)


@pytest.fixture()
def temp_db(tmp_path: Path) -> Path:
    """Create an isolated temporary SQLite database with full schema."""
    db_file = tmp_path / "test_analytics.db"
    initialize_database(db_path=db_file)
    return db_file


def _seed_basic_data(db_path: Path) -> dict:
    save_student_profile(
        name="Aarav",
        branch="Computer Science",
        semester=4,
        college_name="VIT",
        weekly_study_target=10,
        attendance_target=75.0,
        db_path=db_path,
    )
    s1 = insert_subject(
        subject_name="Data Structures",
        subject_code="CS201",
        start_date="2026-02-01",
        completion_date="2026-02-28",
        status="Completed",
        db_path=db_path,
    )
    s2 = insert_subject(
        subject_name="Database Systems",
        subject_code="CS202",
        start_date="2026-02-15",
        status="In Progress",
        db_path=db_path,
    )
    t1 = insert_topic(
        subject_id=s1,
        topic_name="Binary Trees",
        start_date="2026-02-01",
        completion_date="2026-02-10",
        estimated_hours=5.0,
        status="Completed",
        db_path=db_path,
    )
    t2 = insert_topic(
        subject_id=s1,
        topic_name="Graphs",
        start_date="2026-02-11",
        completion_date="2026-02-20",
        estimated_hours=6.0,
        status="Completed",
        db_path=db_path,
    )
    t3 = insert_topic(
        subject_id=s2,
        topic_name="Normalization",
        start_date="2026-02-16",
        estimated_hours=4.0,
        status="In Progress",
        db_path=db_path,
    )

    # Study sessions on consecutive days to test streaks and aggregations
    save_study_session(
        subject_id=s1,
        study_date="2026-02-26",
        duration_minutes=60,
        topic_id=t1,
        status="Completed",
        productivity_rating=5,
        db_path=db_path,
    )
    save_study_session(
        subject_id=s1,
        study_date="2026-02-27",
        duration_minutes=90,
        topic_id=t2,
        status="Completed",
        productivity_rating=4,
        db_path=db_path,
    )
    save_study_session(
        subject_id=s2,
        study_date="2026-02-28",
        duration_minutes=120,
        topic_id=t3,
        status="Partially Completed",
        productivity_rating=3,
        db_path=db_path,
    )

    # Checkins
    save_daily_checkin(
        checkin_date="2026-02-27",
        productivity_rating=4,
        goal_completed=1,
        db_path=db_path,
    )
    save_daily_checkin(
        checkin_date="2026-02-28",
        productivity_rating=3,
        goal_completed=0,
        db_path=db_path,
    )

    # Marks
    save_marks(s1, "Midsem", 25.0, 30.0, assessment_date="2026-02-20", db_path=db_path)
    save_marks(s1, "Quiz", 8.0, 10.0, assessment_date="2026-02-22", db_path=db_path)
    save_marks(s2, "Midsem", 15.0, 30.0, assessment_date="2026-02-25", db_path=db_path)

    # Attendance
    save_attendance(s1, classes_held=20, classes_attended=18, db_path=db_path)
    save_attendance(s2, classes_held=20, classes_attended=13, db_path=db_path)

    # Assignments
    save_assignment(
        subject_id=s1,
        title="Tree Lab",
        assigned_date="2026-02-10",
        deadline_date="2026-02-20",
        status="Completed",
        db_path=db_path,
    )
    save_assignment(
        subject_id=s2,
        title="SQL Practice",
        assigned_date="2026-02-20",
        deadline_date="2026-03-05",
        status="Pending",
        db_path=db_path,
    )

    # Timetable
    save_timetable_entry(
        subject_id=s1,
        study_date="2026-02-26",
        start_time="18:00",
        end_time="19:00",
        status="Completed",
        db_path=db_path,
    )
    save_timetable_entry(
        subject_id=s2,
        study_date="2026-02-27",
        start_time="19:00",
        end_time="20:30",
        status="Skipped",
        db_path=db_path,
    )
    save_timetable_entry(
        subject_id=s2,
        study_date="2026-02-28",
        start_time="18:00",
        end_time="19:00",
        status="Planned",
        db_path=db_path,
    )

    return {
        "s1": s1,
        "s2": s2,
        "t1": t1,
        "t2": t2,
        "t3": t3,
    }


def test_date_range_presets_and_custom_validation() -> None:
    ref = date(2026, 3, 15)  # Sunday
    s, e = get_date_range("Today", reference_date=ref)
    assert s == "2026-03-15"
    assert e == "2026-03-15"

    s_7, e_7 = get_date_range("Last 7 Days", reference_date=ref)
    assert s_7 == "2026-03-09"
    assert e_7 == "2026-03-15"

    s_w, e_w = get_date_range("This Week", reference_date=ref)
    assert s_w == "2026-03-09"  # Monday
    assert e_w == "2026-03-15"  # Sunday

    s_m, e_m = get_date_range("This Month", reference_date=ref)
    assert s_m == "2026-03-01"
    assert e_m == "2026-03-31"

    s_all, e_all = get_date_range("All Time")
    assert s_all is None
    assert e_all is None

    with pytest.raises(ValueError):
        get_date_range(
            "Custom Date Range",
            custom_start=date(2026, 3, 20),
            custom_end=date(2026, 3, 10),
        )


def test_daily_weekly_and_monthly_study_summaries(temp_db: Path) -> None:
    _seed_basic_data(temp_db)
    summary = get_study_summary(start_date="2026-02-26", end_date="2026-02-28", db_path=temp_db)
    assert summary["total_sessions"] == 3
    assert summary["total_minutes"] == 270
    assert summary["total_hours"] == 4.5
    assert summary["completed_sessions"] == 2
    assert summary["partially_completed_sessions"] == 1
    assert summary["distinct_study_days"] == 3
    assert summary["average_daily_study_hours"] == 1.5

    daily = get_daily_study_minutes("2026-02-26", "2026-02-28", fill_missing_days=True, db_path=temp_db)
    assert len(daily) == 3
    assert daily[0]["study_date"] == "2026-02-26"
    assert daily[0]["minutes"] == 60

    weekly = get_weekly_study_summary(db_path=temp_db)
    assert len(weekly) == 1
    assert weekly[0]["total_minutes"] == 270

    monthly = get_monthly_study_summary(db_path=temp_db)
    assert len(monthly) == 1
    assert monthly[0]["month_key"] == "2026-02"
    assert monthly[0]["total_minutes"] == 270


def test_custom_date_range_inclusive_filtering_and_empty_range(temp_db: Path) -> None:
    _seed_basic_data(temp_db)
    # Range covering only 27th
    s_only = get_study_summary("2026-02-27", "2026-02-27", db_path=temp_db)
    assert s_only["total_sessions"] == 1
    assert s_only["total_minutes"] == 90

    # Out-of-bounds date range
    s_empty = get_study_summary("2026-01-01", "2026-01-10", db_path=temp_db)
    assert s_empty["total_sessions"] == 0
    assert s_empty["total_minutes"] == 0
    assert s_empty["average_daily_study_hours"] == 0.0


def test_subject_wise_study_hours_and_distribution(temp_db: Path) -> None:
    ids = _seed_basic_data(temp_db)
    subj_data = get_subject_study_summary(db_path=temp_db)
    assert len(subj_data) == 2

    s1_row = next(r for r in subj_data if r["subject_id"] == ids["s1"])
    s2_row = next(r for r in subj_data if r["subject_id"] == ids["s2"])

    assert s1_row["total_minutes"] == 150  # 60 + 90
    assert s1_row["session_count"] == 2
    assert s2_row["total_minutes"] == 120
    assert s2_row["session_count"] == 1
    assert round(s1_row["study_time_percentage"] + s2_row["study_time_percentage"], 0) == 100.0


def test_topic_wise_study_hours_and_deleted_topic_preservation(temp_db: Path) -> None:
    ids = _seed_basic_data(temp_db)
    # Insert a session referencing topic_id=None (simulating deleted topic ON DELETE SET NULL)
    save_study_session(
        subject_id=ids["s1"],
        study_date="2026-02-28",
        duration_minutes=45,
        topic_id=None,
        status="Completed",
        db_path=temp_db,
    )

    t_data = get_topic_study_summary(subject_id=ids["s1"], db_path=temp_db)
    hist_entry = next((t for t in t_data if t["topic_id"] is None), None)
    assert hist_entry is not None
    assert hist_entry["topic_name"] == "Historical session — topic no longer available"
    assert hist_entry["total_minutes"] == 45


def test_topic_and_subject_completion_duration_analysis(temp_db: Path) -> None:
    ids = _seed_basic_data(temp_db)
    t_comp = get_topic_completion_duration(db_path=temp_db)
    assert len(t_comp) == 2
    t1_row = next(r for r in t_comp if r["topic_id"] == ids["t1"])
    assert t1_row["calendar_days_taken"] == 10  # Feb 01 to Feb 10
    assert t1_row["actual_study_hours"] == 1.0  # 60 mins
    assert t1_row["estimated_hours"] == 5.0
    assert t1_row["hours_variance"] == -4.0

    s_comp = get_subject_completion_summary(db_path=temp_db)
    assert len(s_comp) == 2
    s1_row = next(r for r in s_comp if r["subject_id"] == ids["s1"])
    assert s1_row["calendar_days_taken"] == 28  # Feb 01 to Feb 28
    assert s1_row["syllabus_completion_percentage"] == 100.0
    assert s1_row["total_study_hours"] == 2.5  # 150 mins


def test_study_streaks_calculation(temp_db: Path) -> None:
    _seed_basic_data(temp_db)
    # Sessions are on 2026-02-26, 2026-02-27, 2026-02-28 (3 consecutive days)
    streaks = calculate_study_streaks(reference_date=date(2026, 2, 28), db_path=temp_db)
    assert streaks["longest_streak_days"] == 3
    assert streaks["current_streak_days"] == 3
    assert streaks["streak_active_today"] is True

    # When evaluated a day later (2026-03-01 without study), streak is still active from yesterday
    streaks_mar1 = calculate_study_streaks(reference_date=date(2026, 3, 1), db_path=temp_db)
    assert streaks_mar1["current_streak_days"] == 3
    assert streaks_mar1["streak_active_today"] is False

    # Two days later, current streak resets to 0
    streaks_mar3 = calculate_study_streaks(reference_date=date(2026, 3, 3), db_path=temp_db)
    assert streaks_mar3["current_streak_days"] == 0
    assert streaks_mar3["longest_streak_days"] == 3


def test_productivity_and_checkin_summary(temp_db: Path) -> None:
    _seed_basic_data(temp_db)
    prod = get_daily_productivity_summary(db_path=temp_db)
    assert prod["checkin_count"] == 2
    assert prod["completed_goals"] == 1
    assert prod["goal_completion_rate"] == 50.0
    assert prod["average_checkin_rating"] == 3.5  # (4 + 3) / 2
    assert prod["session_rating_count"] == 3
    assert prod["average_session_rating"] == 4.0  # (5 + 4 + 3) / 3


def test_academic_marks_weighted_and_attendance_snapshot(temp_db: Path) -> None:
    _seed_basic_data(temp_db)
    marks = get_academic_marks_summary(db_path=temp_db)
    assert marks["assessment_count"] == 3
    # Total obtained = 25 + 8 + 15 = 48, Total max = 30 + 10 + 30 = 70 => 48/70 = 68.57%
    assert marks["total_marks_obtained"] == 48.0
    assert marks["total_maximum_marks"] == 70.0
    assert round(marks["overall_weighted_percentage"], 2) == 68.57

    att = get_current_attendance_summary(db_path=temp_db)
    assert att["total_classes_held"] == 40
    assert att["total_classes_attended"] == 31
    assert att["total_missed_classes"] == 9
    # Weighted attendance = 31 / 40 = 77.5%
    assert att["overall_attendance_percentage"] == 77.5
    assert att["is_snapshot"] is True


def test_assignment_and_timetable_analytics(temp_db: Path) -> None:
    _seed_basic_data(temp_db)
    # Ref date: 2026-03-01. Tree Lab was due 2026-02-20 and is Completed (not overdue). SQL Practice due 2026-03-05 (pending).
    asgn = get_assignment_analytics(current_date=date(2026, 3, 1), db_path=temp_db)
    assert asgn["total_assignments"] == 2
    assert asgn["completed_assignments"] == 1
    assert asgn["pending_assignments"] == 1
    assert asgn["overdue_assignments"] == 0
    assert asgn["completion_percentage"] == 50.0

    tt = get_timetable_analytics(db_path=temp_db)
    assert tt["total_scheduled_sessions"] == 3
    assert tt["completed_sessions"] == 1
    assert tt["skipped_sessions"] == 1
    assert tt["planned_sessions"] == 1
    assert round(tt["completion_percentage"], 1) == 33.3
    assert tt["scheduled_hours"] == 3.5  # 60 + 90 + 60 = 210 mins = 3.5h


def test_csv_exports_and_empty_database(temp_db: Path) -> None:
    _seed_basic_data(temp_db)
    study_csv = export_study_history(db_path=temp_db)
    assert len(study_csv) == 3
    assert "Duration (Hours)" in study_csv[0]

    subj_csv = export_subject_summary(db_path=temp_db)
    assert len(subj_csv) == 2

    topic_csv = export_topic_summary(db_path=temp_db)
    assert len(topic_csv) == 3

    rep = generate_progress_report(reference_date=date(2026, 2, 28), db_path=temp_db)
    assert rep["student_name"] == "Aarav"
    assert rep["overview"]["total_study_hours"] == 4.5
    assert rep["overview"]["overall_syllabus_completion_pct"] == 66.7
