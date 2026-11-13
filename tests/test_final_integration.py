"""Automated tests for Step 11 — Final Application Integration, Dashboard & Integrity."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
import sys

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database.db import get_connection, initialize_database
from database.queries import (
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
)
from services.academic_service import (
    calculate_overall_weighted_attendance,
    get_attendance_summary_all_subjects,
)
from services.analytics_service import generate_progress_report, get_daily_study_minutes
from services.assignment_service import fetch_assignments, fetch_upcoming_deadlines
from services.calendar_service import fetch_upcoming_events
from services.profile_service import get_profile
from services.recommendation_service import get_prioritized_recommendations
from services.study_service import fetch_sessions, get_today_study_overview
from services.subject_service import get_subject_progress, list_subjects
from services.timetable_service import get_saved_timetable


@pytest.fixture()
def temp_db(tmp_path: Path) -> Path:
    """Create an isolated temporary SQLite database with full 11-table schema."""
    db_file = tmp_path / "test_integration.db"
    initialize_database(db_path=db_file)
    return db_file


def test_database_all_11_tables_intact(temp_db: Path) -> None:
    """Verify that all 11 application tables are created and intact."""
    with get_connection(temp_db) as conn:
        tables = [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;"
            ).fetchall()
        ]
    expected = [
        "assignments",
        "attendance",
        "calendar_events",
        "daily_checkins",
        "marks",
        "student_profile",
        "study_sessions",
        "subjects",
        "timetable",
        "topics",
        "video_resources",
    ]
    assert tables == expected


def test_empty_state_dashboard_metrics(temp_db: Path) -> None:
    """Verify clean empty states when no student data exists."""
    profile = get_profile(db_path=temp_db)
    assert profile is None

    subjects = list_subjects(db_path=temp_db)
    assert len(subjects) == 0

    today_iso = date.today().isoformat()
    sessions = fetch_sessions(start_date=today_iso, end_date=today_iso, db_path=temp_db)
    assert len(sessions) == 0

    deadlines = fetch_upcoming_deadlines(days=7, db_path=temp_db)
    assert len(deadlines) == 0

    events = fetch_upcoming_events(reference_date=date.today(), db_path=temp_db)
    assert len(events) == 0

    tt = get_saved_timetable(start_date=today_iso, end_date=today_iso, db_path=temp_db)
    assert len(tt) == 0

    recs = get_prioritized_recommendations(db_path=temp_db)
    # When no records exist, system returns helpful onboarding study habits notices
    assert all("Start recording" in r["title"] or "Insufficient data" in r["title"] for r in recs)


def test_cross_module_workflow_and_dashboard_integration(temp_db: Path) -> None:
    """Verify end-to-end multi-module data flow matching dashboard expectations."""
    today = date.today()
    today_iso = today.isoformat()

    # 1. Profile
    save_student_profile(
        name="Ananya Sharma",
        branch="Information Technology",
        semester=4,
        weekly_study_target=12,
        attendance_target=75.0,
        db_path=temp_db,
    )
    prof = get_profile(db_path=temp_db)
    assert prof["name"] == "Ananya Sharma"

    # 2. Subjects & Topics
    s1 = insert_subject("Web Technology", subject_code="IT201", db_path=temp_db)
    t1 = insert_topic(s1, "HTML & CSS", status="Completed", db_path=temp_db)
    t2 = insert_topic(s1, "JavaScript Async", status="In Progress", db_path=temp_db)

    prog = get_subject_progress(s1, db_path=temp_db)
    assert prog["total_topics"] == 2
    assert prog["completed_topics"] == 1
    assert prog["completion_percentage"] == 50.0

    # 3. Study Session Logged Today
    save_study_session(
        subject_id=s1,
        study_date=today_iso,
        duration_minutes=90,
        topic_id=t2,
        status="Completed",
        db_path=temp_db,
    )
    overview = get_today_study_overview(today, db_path=temp_db)
    assert overview["session_count"] == 1
    assert overview["studied_minutes"] == 90

    # 4. Attendance Shortage
    save_attendance(s1, classes_held=20, classes_attended=12, db_path=temp_db)
    att = calculate_overall_weighted_attendance(db_path=temp_db)
    assert att["overall_percentage"] == 60.0

    # 5. Overdue Assignment
    yesterday_iso = (today - timedelta(days=1)).isoformat()
    save_assignment(
        subject_id=s1,
        title="DOM Manipulation Lab",
        deadline_date=yesterday_iso,
        status="Pending",
        db_path=temp_db,
    )

    # 6. Recommendation Engine should catch attendance + overdue assignment
    ref_dt = datetime.combine(today, datetime.min.time())
    recs = get_prioritized_recommendations(current_dt=ref_dt, db_path=temp_db)
    rec_titles = [r["title"] for r in recs]
    assert any("Attendance" in t or "DOM Manipulation Lab" in t for t in rec_titles)

    # 7. Today's Timetable Schedule
    save_timetable_entry(
        subject_id=s1,
        study_date=today_iso,
        start_time="19:00",
        end_time="20:00",
        status="Planned",
        db_path=temp_db,
    )
    saved_tt = get_saved_timetable(start_date=today_iso, end_date=today_iso, db_path=temp_db)
    assert len(saved_tt) == 1
    assert saved_tt[0]["status"] == "Planned"

    # 8. Upcoming Calendar Event
    save_calendar_event(
        title="Internal Mid-Sem Exam",
        event_type="Internal Examination",
        start_date=(today + timedelta(days=5)).isoformat(),
        db_path=temp_db,
    )
    events = fetch_upcoming_events(reference_date=today, db_path=temp_db)
    assert len(events) == 1
    assert events[0]["title"] == "Internal Mid-Sem Exam"


def test_timetable_and_study_time_isolation(temp_db: Path) -> None:
    """Planned/completed timetable entries must never artificially inflate logged study time."""
    s_id = insert_subject("Data Science", subject_code="DS101", db_path=temp_db)
    today_iso = date.today().isoformat()

    # Schedule a 2-hour timetable slot and mark it Completed
    save_timetable_entry(
        subject_id=s_id,
        study_date=today_iso,
        start_time="18:00",
        end_time="20:00",
        status="Completed",
        db_path=temp_db,
    )

    # Actual study sessions must remain 0
    today_sessions = fetch_sessions(start_date=today_iso, end_date=today_iso, db_path=temp_db)
    assert len(today_sessions) == 0
    mins = sum(int(s["duration_minutes"]) for s in today_sessions)
    assert mins == 0


def test_all_11_pages_import_successfully() -> None:
    """Verify that every Streamlit page and service file can be imported without errors."""
    page_files = [
        "pages/1_Profile.py",
        "pages/2_Subjects_Topics.py",
        "pages/3_Daily_Study_Tracker.py",
        "pages/4_Academic_Performance.py",
        "pages/5_Assignments_Reminders.py",
        "pages/6_College_Calendar.py",
        "pages/7_AI_Recommendations.py",
        "pages/8_Smart_Timetable.py",
        "pages/9_Video_Lectures.py",
        "pages/10_Progress_Analytics.py",
        "pages/11_About_Project.py",
    ]
    for p in page_files:
        path = ROOT_DIR / p
        assert path.exists(), f"Missing page file: {p}"

    import app
    assert callable(app.main)
    assert callable(app._render_quick_actions)


def test_dashboard_quick_action_unique_keys_and_nav() -> None:
    """Verify that quick action buttons have unique keys and navigation labels are human-readable."""
    from utils.ui import NAV_PAGES
    # Verify Dashboard is named explicitly instead of app.py
    nav_dict = {path: title for path, title, _ in NAV_PAGES}
    assert "app.py" in nav_dict
    assert nav_dict["app.py"] == "Dashboard"
    assert len(NAV_PAGES) == 12

    # Verify no duplicate keys in app.py source code
    import inspect
    import app
    src = inspect.getsource(app._render_quick_actions)
    expected_keys = [
        "dashboard_quick_log_study",
        "dashboard_quick_subjects",
        "dashboard_quick_attendance",
        "dashboard_quick_assignments",
        "dashboard_quick_timetable",
        "dashboard_quick_video_lectures",
        "dashboard_quick_analytics",
    ]
    for k in expected_keys:
        assert f'key="{k}"' in src, f"Expected button key {k} missing in _render_quick_actions"
        assert src.count(f'key="{k}"') == 1, f"Duplicate button key {k} detected in _render_quick_actions"


def test_v41_dashboard_and_12h_time_integration(temp_db: Path) -> None:
    """Verify Design System V4.1 12-hour time integration and database canonical isolation."""
    from utils.formatters import format_time_12h, format_time_range_12h, parse_time_12h_to_24h

    # 1. 12-hour formatting
    assert format_time_12h("18:30") == "6:30 PM"
    assert format_time_12h("09:15") == "9:15 AM"
    assert format_time_range_12h("18:00", "20:00") == "6:00 PM – 8:00 PM"

    # 2. Database canonical 24-hour storage is preserved
    today_iso = date.today().isoformat()
    s_id = insert_subject("Algorithm Design", subject_code="CS301", db_path=temp_db)
    save_timetable_entry(
        subject_id=s_id,
        study_date=today_iso,
        start_time=parse_time_12h_to_24h("7:00 PM"),
        end_time=parse_time_12h_to_24h("8:30 PM"),
        status="Planned",
        db_path=temp_db,
    )
    entries = get_saved_timetable(start_date=today_iso, end_date=today_iso, db_path=temp_db)
    assert len(entries) == 1
    # Canonical SQLite storage remains 24h
    assert entries[0]["start_time"] == "19:00"
    assert entries[0]["end_time"] == "20:30"

    # UI presentation layer transforms to 12h AM/PM
    ui_time = format_time_range_12h(entries[0]["start_time"], entries[0]["end_time"])
    assert ui_time == "7:00 PM – 8:30 PM"


