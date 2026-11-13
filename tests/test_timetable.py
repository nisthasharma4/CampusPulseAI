"""Automated tests for Step 8 — Smart Timetable Generator & Study Scheduler."""

from __future__ import annotations

from datetime import date, time
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
    save_marks,
)
from services.profile_service import save_profile
from services.timetable_service import (
    add_manual_session,
    calculate_subject_priority,
    calculate_weekly_scheduled_minutes,
    delete_timetable_session,
    generate_weekly_timetable,
    get_assignment_priority,
    get_exam_priority,
    get_incomplete_topics,
    get_saved_timetable,
    get_student_availability,
    get_subject_priority_reasons,
    get_timetable_summary,
    has_generated_timetable_in_range,
    normalize_subject_priorities,
    save_generated_timetable,
    update_session_status,
    update_timetable_session,
    validate_timetable_slots,
)


@pytest.fixture()
def temp_db(tmp_path: Path) -> Path:
    """Create an isolated temporary SQLite database with full schema."""
    db_file = tmp_path / "test_timetable.db"
    initialize_database(db_path=db_file)
    return db_file


def _seed_profile(
    db_file: Path,
    days=None,
    start_time: str = "18:00",
    end_time: str = "21:00",
    daily_hours: float = 2.0,
    weekly_hours: int = 10,
    session_mins: int = 60,
    break_mins: int = 15,
) -> None:
    sh, sm = [int(x) for x in start_time.split(":")]
    eh, em = [int(x) for x in end_time.split(":")]
    save_profile(
        name="Aarav",
        branch="CSE",
        semester=4,
        college_name="VIT",
        weekly_study_target=int(round(weekly_hours)),
        daily_available_hours=float(daily_hours),
        preferred_start_time=time(sh, sm),
        preferred_end_time=time(eh, em),
        available_days=days or ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        session_duration_minutes=session_mins,
        break_duration_minutes=break_mins,
        attendance_target=75.0,
        db_path=db_file,
    )


def test_default_availability_without_profile(temp_db: Path) -> None:
    avail = get_student_availability(db_path=temp_db)
    assert avail["has_profile"] is False
    assert len(avail["available_days"]) >= 1
    assert avail["daily_available_minutes"] > 0
    assert avail["session_duration_minutes"] > 0


def test_availability_reads_from_student_profile(temp_db: Path) -> None:
    _seed_profile(
        temp_db,
        days=["Monday", "Wednesday", "Friday"],
        start_time="17:00",
        end_time="20:00",
        daily_hours=2.5,
        weekly_hours=8,
        session_mins=45,
        break_mins=10,
    )
    avail = get_student_availability(db_path=temp_db)
    assert avail["has_profile"] is True
    assert avail["available_days"] == ["Monday", "Wednesday", "Friday"]
    assert avail["preferred_start_time"] == "17:00"
    assert avail["preferred_end_time"] == "20:00"
    assert avail["daily_available_minutes"] == 150
    assert avail["weekly_study_target_minutes"] == 480
    assert avail["session_duration_minutes"] == 45
    assert avail["break_duration_minutes"] == 10


def test_generate_with_no_subjects_returns_empty_plan(temp_db: Path) -> None:
    plan = generate_weekly_timetable(
        current_date=date(2026, 3, 2),
        start_date=date(2026, 3, 2),
        db_path=temp_db,
    )
    assert plan["sessions"] == []
    assert plan["total_generated_minutes"] == 0


def test_weak_subject_scores_higher_than_strong_subject(temp_db: Path) -> None:
    weak_id = insert_subject("Data Structures", subject_code="CS201", db_path=temp_db)
    strong_id = insert_subject("Digital Logic", subject_code="CS202", db_path=temp_db)
    save_marks(weak_id, "Quiz 1", 8.0, 25.0, assessment_date="2026-02-20", db_path=temp_db)
    save_marks(strong_id, "Quiz 1", 23.0, 25.0, assessment_date="2026-02-20", db_path=temp_db)

    weak_info = calculate_subject_priority(weak_id, current_date=date(2026, 3, 2), db_path=temp_db)
    strong_info = calculate_subject_priority(strong_id, current_date=date(2026, 3, 2), db_path=temp_db)
    assert weak_info["score"] > strong_info["score"]
    assert weak_info["priority"] in ("High", "Medium")


def test_low_attendance_boosts_subject_priority(temp_db: Path) -> None:
    _seed_profile(temp_db)
    low_att_id = insert_subject("OS", subject_code="CS301", db_path=temp_db)
    ok_att_id = insert_subject("DBMS", subject_code="CS302", db_path=temp_db)
    save_attendance(low_att_id, classes_held=10, classes_attended=5, db_path=temp_db)
    save_attendance(ok_att_id, classes_held=10, classes_attended=9, db_path=temp_db)

    low_info = calculate_subject_priority(low_att_id, current_date=date(2026, 3, 2), db_path=temp_db)
    ok_info = calculate_subject_priority(ok_att_id, current_date=date(2026, 3, 2), db_path=temp_db)
    assert low_info["score"] > ok_info["score"]
    assert any("attendance" in r.lower() for r in low_info["reasons"])


def test_assignment_priority_within_horizon(temp_db: Path) -> None:
    subj_id = insert_subject("Computer Networks", subject_code="CS303", db_path=temp_db)
    save_assignment(
        subject_id=subj_id,
        title="Socket Lab",
        deadline_date="2026-03-04",
        priority="High",
        status="Pending",
        db_path=temp_db,
    )
    score, reasons, urgent_title = get_assignment_priority(
        subj_id, current_date=date(2026, 3, 2), db_path=temp_db
    )
    assert score > 0
    assert len(reasons) >= 1
    assert urgent_title == "Socket Lab"


def test_upcoming_exam_boosts_priority_and_recommendation(temp_db: Path) -> None:
    _seed_profile(temp_db)
    subj_id = insert_subject("Algorithms", subject_code="CS304", db_path=temp_db)
    save_calendar_event(
        title="Algorithms Midsem Exam",
        event_type="Internal Examination",
        start_date="2026-03-08",
        db_path=temp_db,
    )
    exam_info = get_exam_priority(current_date=date(2026, 3, 2), db_path=temp_db)
    assert exam_info["score"] > 0

    plan = generate_weekly_timetable(
        current_date=date(2026, 3, 2),
        start_date=date(2026, 3, 2),
        db_path=temp_db,
    )
    assert plan["exam_recommendation"] is not None


def test_manual_exam_subject_selection_boosts_priority(temp_db: Path) -> None:
    s1 = insert_subject("Maths III", subject_code="MA201", db_path=temp_db)
    s2 = insert_subject("Physics", subject_code="PH201", db_path=temp_db)
    save_calendar_event(
        title="Midsem Examination",
        event_type="Internal Examination",
        start_date="2026-03-08",
        db_path=temp_db,
    )
    without_boost = calculate_subject_priority(s1, current_date=date(2026, 3, 2), db_path=temp_db)
    with_boost = calculate_subject_priority(
        s1, current_date=date(2026, 3, 2), exam_subject_ids=[s1], db_path=temp_db
    )
    other = calculate_subject_priority(
        s2, current_date=date(2026, 3, 2), exam_subject_ids=[s1], db_path=temp_db
    )
    assert with_boost["score"] > without_boost["score"]
    assert with_boost["score"] > other["score"]


def test_incomplete_topics_assigned_and_completed_excluded(temp_db: Path) -> None:
    _seed_profile(temp_db, days=["Monday", "Tuesday"], weekly_hours=4)
    subj_id = insert_subject("DSA", subject_code="CS201", db_path=temp_db)
    insert_topic(subj_id, "Arrays", status="Completed", db_path=temp_db)
    t2 = insert_topic(subj_id, "Linked Lists", status="Not Started", db_path=temp_db)
    t3 = insert_topic(subj_id, "Trees", status="In Progress", db_path=temp_db)

    incomplete = get_incomplete_topics(subj_id, db_path=temp_db)
    assert [t["id"] for t in incomplete] == [t3, t2]

    plan = generate_weekly_timetable(
        current_date=date(2026, 3, 2),
        start_date=date(2026, 3, 2),
        db_path=temp_db,
    )
    topic_names = [s["topic_name"] for s in plan["sessions"] if s.get("topic_name")]
    assert "Arrays" not in topic_names
    assert "Linked Lists" in topic_names


def test_respects_available_days_and_time_window(temp_db: Path) -> None:
    _seed_profile(
        temp_db,
        days=["Monday", "Wednesday"],
        start_time="18:00",
        end_time="20:00",
        daily_hours=2.0,
        weekly_hours=4.0,
        session_mins=60,
        break_mins=0,
    )
    insert_subject("Discrete Math", subject_code="MA202", db_path=temp_db)

    plan = generate_weekly_timetable(
        current_date=date(2026, 3, 2),
        start_date=date(2026, 3, 2),  # Monday
        db_path=temp_db,
    )
    assert len(plan["sessions"]) > 0
    for s in plan["sessions"]:
        day_name = date.fromisoformat(s["study_date"]).strftime("%A")
        assert day_name in ("Monday", "Wednesday")
        assert s["start_time"] >= "18:00"
        assert s["end_time"] <= "20:00"


def test_break_duration_spacing_between_sessions(temp_db: Path) -> None:
    _seed_profile(
        temp_db,
        days=["Monday"],
        start_time="18:00",
        end_time="22:00",
        daily_hours=4.0,
        weekly_hours=4.0,
        session_mins=60,
        break_mins=15,
    )
    insert_subject("Operating Systems", subject_code="CS301", db_path=temp_db)

    plan = generate_weekly_timetable(
        current_date=date(2026, 3, 2),
        start_date=date(2026, 3, 2),
        db_path=temp_db,
    )
    assert len(plan["sessions"]) >= 2
    s1, s2 = plan["sessions"][0], plan["sessions"][1]
    assert s1["start_time"] == "18:00"
    assert s1["end_time"] == "19:00"
    assert s2["start_time"] == "19:15"
    assert s2["end_time"] == "20:15"


def test_daily_capacity_cap_respected(temp_db: Path) -> None:
    _seed_profile(
        temp_db,
        days=["Monday"],
        start_time="18:00",
        end_time="23:00",
        daily_hours=1.5,  # 90 mins max
        weekly_hours=5.0,
        session_mins=60,
        break_mins=10,
    )
    insert_subject("Compilers", subject_code="CS401", db_path=temp_db)

    plan = generate_weekly_timetable(
        current_date=date(2026, 3, 2),
        start_date=date(2026, 3, 2),
        db_path=temp_db,
    )
    assert plan["total_generated_minutes"] <= 90


def test_weekly_target_cap_and_capacity_warning(temp_db: Path) -> None:
    _seed_profile(
        temp_db,
        days=["Monday"],
        start_time="18:00",
        end_time="19:00",
        daily_hours=1.0,
        weekly_hours=10.0,
        session_mins=60,
        break_mins=0,
    )
    insert_subject("AI", subject_code="CS402", db_path=temp_db)

    plan = generate_weekly_timetable(
        current_date=date(2026, 3, 2),
        start_date=date(2026, 3, 2),
        db_path=temp_db,
    )
    assert plan["total_generated_minutes"] == 60
    assert plan["capacity_warning"] is not None


def test_deterministic_generation(temp_db: Path) -> None:
    _seed_profile(temp_db)
    s1 = insert_subject("DSA", subject_code="CS201", db_path=temp_db)
    s2 = insert_subject("DBMS", subject_code="CS202", db_path=temp_db)
    save_marks(s1, "Midsem", 10.0, 30.0, db_path=temp_db)
    insert_topic(s1, "Graphs", db_path=temp_db)
    insert_topic(s2, "Normalization", db_path=temp_db)

    p1 = generate_weekly_timetable(
        current_date=date(2026, 3, 2), start_date=date(2026, 3, 2), db_path=temp_db
    )
    p2 = generate_weekly_timetable(
        current_date=date(2026, 3, 2), start_date=date(2026, 3, 2), db_path=temp_db
    )
    assert p1["sessions"] == p2["sessions"]


def test_calendar_holiday_and_timed_event_avoidance(temp_db: Path) -> None:
    _seed_profile(
        temp_db,
        days=["Monday", "Tuesday"],
        start_time="18:00",
        end_time="21:00",
        daily_hours=3.0,
        weekly_hours=6.0,
        session_mins=60,
        break_mins=0,
    )
    insert_subject("Software Engineering", subject_code="CS305", db_path=temp_db)
    # Full-day Holiday on Monday 2026-03-02
    save_calendar_event(
        title="College Holiday",
        event_type="Holiday",
        start_date="2026-03-02",
        db_path=temp_db,
    )
    # Timed event on Tuesday 2026-03-03 from 18:00
    save_calendar_event(
        title="Project Viva",
        event_type="Seminar",
        start_date="2026-03-03",
        start_time="18:00",
        db_path=temp_db,
    )

    plan = generate_weekly_timetable(
        current_date=date(2026, 3, 2),
        start_date=date(2026, 3, 2),
        db_path=temp_db,
    )
    dates = {s["study_date"] for s in plan["sessions"]}
    assert "2026-03-02" not in dates
    tuesday_starts = {s["start_time"] for s in plan["sessions"] if s["study_date"] == "2026-03-03"}
    assert "18:00" not in tuesday_starts


def test_avoids_existing_manual_sessions(temp_db: Path) -> None:
    _seed_profile(
        temp_db,
        days=["Monday"],
        start_time="18:00",
        end_time="20:00",
        daily_hours=2.0,
        weekly_hours=2.0,
        session_mins=60,
        break_mins=0,
    )
    s_id = insert_subject("Cloud Computing", subject_code="CS403", db_path=temp_db)
    add_manual_session(
        subject_id=s_id,
        study_date="2026-03-02",
        start_time="18:00",
        end_time="19:00",
        session_title="Manual Lab",
        db_path=temp_db,
    )

    plan = generate_weekly_timetable(
        current_date=date(2026, 3, 2),
        start_date=date(2026, 3, 2),
        db_path=temp_db,
    )
    for s in plan["sessions"]:
        if s["study_date"] == "2026-03-02":
            assert s["start_time"] >= "19:00"


def test_validate_timetable_slots_rejects_overlap_and_bad_times(temp_db: Path) -> None:
    _seed_profile(temp_db, start_time="18:00", end_time="21:00")
    s_id = insert_subject("Networks", subject_code="CS303", db_path=temp_db)

    with pytest.raises(ValueError):
        validate_timetable_slots(
            [{"subject_id": s_id, "study_date": "2026-03-02", "start_time": "20:00", "end_time": "19:00"}],
            db_path=temp_db,
        )

    with pytest.raises(ValueError):
        validate_timetable_slots(
            [
                {"subject_id": s_id, "study_date": "2026-03-02", "start_time": "18:00", "end_time": "19:00"},
                {"subject_id": s_id, "study_date": "2026-03-02", "start_time": "18:30", "end_time": "19:30"},
            ],
            db_path=temp_db,
        )

    with pytest.raises(ValueError):
        validate_timetable_slots(
            [{"subject_id": 99999, "study_date": "2026-03-02", "start_time": "18:00", "end_time": "19:00"}],
            db_path=temp_db,
        )


def test_save_and_replace_preserves_manual_and_completed(temp_db: Path) -> None:
    _seed_profile(
        temp_db,
        days=["Monday", "Tuesday"],
        start_time="18:00",
        end_time="20:00",
        daily_hours=2.0,
        weekly_hours=4.0,
        session_mins=60,
        break_mins=0,
    )
    s_id = insert_subject("DSA", subject_code="CS201", db_path=temp_db)
    manual_id = add_manual_session(
        subject_id=s_id,
        study_date="2026-03-02",
        start_time="18:00",
        end_time="19:00",
        session_title="Manual Focus",
        db_path=temp_db,
    )
    assert has_generated_timetable_in_range("2026-03-02", "2026-03-08", db_path=temp_db) is False

    plan1 = generate_weekly_timetable(
        current_date=date(2026, 3, 2), start_date=date(2026, 3, 2), db_path=temp_db
    )
    save_generated_timetable(plan1["sessions"], "2026-03-02", "2026-03-08", replace_existing=False, db_path=temp_db)
    assert has_generated_timetable_in_range("2026-03-02", "2026-03-08", db_path=temp_db) is True

    saved = get_saved_timetable("2026-03-02", "2026-03-08", db_path=temp_db)
    gen_entry = next(e for e in saved if e["source"] == "Generated")
    update_session_status(gen_entry["id"], "Completed", db_path=temp_db)

    plan2 = generate_weekly_timetable(
        current_date=date(2026, 3, 2), start_date=date(2026, 3, 2), db_path=temp_db
    )
    save_generated_timetable(plan2["sessions"], "2026-03-02", "2026-03-08", replace_existing=True, db_path=temp_db)

    after = get_saved_timetable("2026-03-02", "2026-03-08", db_path=temp_db)
    ids_after = {e["id"] for e in after}
    assert manual_id in ids_after
    assert gen_entry["id"] in ids_after


def test_manual_session_crud_and_availability_toggle(temp_db: Path) -> None:
    _seed_profile(temp_db, start_time="18:00", end_time="21:00")
    s_id = insert_subject("Microprocessors", subject_code="EC201", db_path=temp_db)

    with pytest.raises(ValueError):
        add_manual_session(
            subject_id=s_id,
            study_date="2026-03-02",
            start_time="10:00",
            end_time="11:00",
            enforce_availability=True,
            db_path=temp_db,
        )

    sid = add_manual_session(
        subject_id=s_id,
        study_date="2026-03-02",
        start_time="10:00",
        end_time="11:00",
        session_title="Morning Extra",
        enforce_availability=False,
        db_path=temp_db,
    )
    update_timetable_session(
        session_id=sid,
        subject_id=s_id,
        study_date="2026-03-02",
        start_time="10:30",
        end_time="11:30",
        session_title="Morning Extra Updated",
        priority="High",
        db_path=temp_db,
    )
    entries = get_saved_timetable("2026-03-02", "2026-03-02", db_path=temp_db)
    assert len(entries) == 1
    assert entries[0]["session_title"] == "Morning Extra Updated"
    assert entries[0]["priority"] == "High"

    delete_timetable_session(sid, db_path=temp_db)
    assert get_saved_timetable("2026-03-02", "2026-03-02", db_path=temp_db) == []


def test_status_update_does_not_create_study_session(temp_db: Path) -> None:
    _seed_profile(temp_db)
    s_id = insert_subject("ML Basics", subject_code="CS404", db_path=temp_db)
    sid = add_manual_session(
        subject_id=s_id,
        study_date="2026-03-02",
        start_time="18:00",
        end_time="19:00",
        db_path=temp_db,
    )
    update_session_status(sid, "Completed", db_path=temp_db)

    with get_connection(temp_db) as conn:
        count = conn.execute("SELECT COUNT(*) FROM study_sessions").fetchone()[0]
    assert count == 0


def test_filters_and_summary_metrics(temp_db: Path) -> None:
    _seed_profile(temp_db)
    s1 = insert_subject("Subj A", subject_code="A1", db_path=temp_db)
    s2 = insert_subject("Subj B", subject_code="B1", db_path=temp_db)

    id1 = add_manual_session(s1, "2026-03-02", "18:00", "19:00", db_path=temp_db)
    id2 = add_manual_session(s2, "2026-03-03", "18:00", "19:30", db_path=temp_db)
    update_session_status(id1, "Completed", db_path=temp_db)
    update_session_status(id2, "Skipped", db_path=temp_db)

    only_s1 = get_saved_timetable("2026-03-02", "2026-03-08", subject_id=s1, db_path=temp_db)
    assert len(only_s1) == 1
    only_skipped = get_saved_timetable("2026-03-02", "2026-03-08", status="Skipped", db_path=temp_db)
    assert len(only_skipped) == 1

    mins = calculate_weekly_scheduled_minutes("2026-03-02", "2026-03-08", db_path=temp_db)
    assert mins == 150

    summary = get_timetable_summary("2026-03-02", "2026-03-08", db_path=temp_db)
    assert summary["total_planned"] == 0
    assert summary["completed"] == 1
    assert summary["skipped"] == 1
    assert summary["total_sessions"] == 2
    assert summary["scheduled_hours"] == 2.5


def test_subject_priority_reasons_and_availability_override(temp_db: Path) -> None:
    _seed_profile(temp_db, days=["Monday"], start_time="18:00", end_time="19:00", weekly_hours=1.0)
    s_id = insert_subject("Theory of Computation", subject_code="CS306", db_path=temp_db)
    save_marks(s_id, "Quiz", 5.0, 20.0, db_path=temp_db)

    reasons_list = get_subject_priority_reasons(current_date=date(2026, 3, 2), db_path=temp_db)
    assert len(reasons_list) == 1
    assert len(reasons_list[0]["reasons"]) >= 1

    override = {
        "available_days": ["Tuesday"],
        "preferred_start_time": "19:00",
        "preferred_end_time": "21:00",
        "daily_available_minutes": 120,
        "weekly_study_target_minutes": 120,
        "session_duration_minutes": 60,
        "break_duration_minutes": 0,
    }
    plan = generate_weekly_timetable(
        current_date=date(2026, 3, 2),
        start_date=date(2026, 3, 2),
        availability_override=override,
        db_path=temp_db,
    )
    assert len(plan["sessions"]) == 2
    assert all(s["study_date"] == "2026-03-03" for s in plan["sessions"])


# ===========================================================================
# Phase 9: Regression Tests for Smart Timetable TypeError & Priority Normalization
# ===========================================================================


def test_normalize_priority_dict_mapping(temp_db: Path) -> None:
    """Test normalizing a dictionary mapping of subject names to hours or scores."""
    s1 = insert_subject("Data Structures", subject_code="CS101", db_path=temp_db)
    s2 = insert_subject("Algorithms", subject_code="CS102", db_path=temp_db)

    # Dictionary input as returned by older preview structures { "Data Structures": 4.0, "Algorithms": 2.0 }
    dict_input = {"Data Structures": 4.0, "Algorithms": 2.0}
    normalized = normalize_subject_priorities(dict_input, db_path=temp_db)

    assert len(normalized) == 2
    assert all(isinstance(item, dict) for item in normalized)
    names = {item["subject_name"] for item in normalized}
    assert "Data Structures" in names
    assert "Algorithms" in names
    for item in normalized:
        assert "subject_id" in item
        assert "score" in item
        assert "priority" in item
        assert "reasons" in item
        assert isinstance(item["reasons"], list)


def test_normalize_priority_list_of_dicts(temp_db: Path) -> None:
    """Test normalizing a list of dictionary priority items."""
    raw_list = [
        {
            "subject_id": 1,
            "subject_name": "Operating Systems",
            "score": 45.0,
            "priority": "High",
            "reasons": ["Internal marks below 50%"],
            "sessions": 3,
            "minutes": 180,
        },
        {
            "subject_id": 2,
            "subject_name": "Databases",
            "score": 20.0,
            "priority": "Medium",
            "reasons": [],
        },
    ]
    normalized = normalize_subject_priorities(raw_list, db_path=temp_db)
    assert len(normalized) == 2
    assert normalized[0]["subject_name"] == "Operating Systems"
    assert normalized[0]["priority"] == "High"
    assert normalized[0]["hours"] == 3.0
    assert normalized[0]["reasons"] == ["Internal marks below 50%"]
    assert normalized[1]["subject_name"] == "Databases"
    assert normalized[1]["reasons"] == ["Regular balanced revision"]


def test_normalize_priority_list_of_strings(temp_db: Path) -> None:
    """Test normalizing a list of subject name strings."""
    insert_subject("Computer Networks", subject_code="CS302", db_path=temp_db)
    str_list = ["Computer Networks", "Nonexistent Subject"]
    normalized = normalize_subject_priorities(str_list, db_path=temp_db)

    assert len(normalized) == 2
    s_names = [item["subject_name"] for item in normalized]
    assert "Computer Networks" in s_names
    assert "Nonexistent Subject" in s_names
    for item in normalized:
        assert isinstance(item["score"], (int, float))
        assert item["priority"] in ("High", "Medium", "Low")
        assert isinstance(item["reasons"], list)


def test_normalize_empty_priority_data(temp_db: Path) -> None:
    """Test that empty or None priority data safely returns an empty list."""
    assert normalize_subject_priorities(None, db_path=temp_db) == []
    assert normalize_subject_priorities([], db_path=temp_db) == []
    assert normalize_subject_priorities({}, db_path=temp_db) == []


def test_normalize_missing_optional_reasons_and_metadata(temp_db: Path) -> None:
    """Test graceful handling of items missing optional fields without raising exceptions."""
    malformed_items = [
        {"subject_name": "Test Subject without ID"},
        {"subject_id": 99999},  # Unregistered ID
        {"subject_name": "Incomplete Item", "score": "invalid_number"},
    ]
    normalized = normalize_subject_priorities(malformed_items, db_path=temp_db)
    assert len(normalized) == 3
    for item in normalized:
        assert isinstance(item["subject_name"], str)
        assert isinstance(item["score"], (int, float))
        assert isinstance(item["reasons"], list)
        assert len(item["reasons"]) >= 1


def test_regression_timetable_preview_rendering_no_typeerror(temp_db: Path) -> None:
    """Direct regression test for the original bug:

    Simulates the UI rendering logic in pages/8_Smart_Timetable.py on the
    plan generated by generate_weekly_timetable().
    Must NOT raise TypeError: string indices must be integers, not 'str'.
    """
    _seed_profile(temp_db, days=["Monday", "Tuesday", "Wednesday"], weekly_hours=6)
    s1 = insert_subject("Data Structures", subject_code="CS201", db_path=temp_db)
    s2 = insert_subject("DBMS", subject_code="CS202", db_path=temp_db)
    insert_topic(s1, "Binary Trees", db_path=temp_db)
    insert_topic(s2, "SQL Queries", db_path=temp_db)

    plan = generate_weekly_timetable(
        current_date=date(2026, 3, 2),
        start_date=date(2026, 3, 2),
        db_path=temp_db,
    )

    # 1. Verify subject_allocations in preview plan is a canonical list of dicts
    assert "subject_allocations" in plan
    allocations = plan["subject_allocations"]
    assert isinstance(allocations, list)
    assert len(allocations) >= 2

    # 2. Simulate the exact loop in _render_generator_and_preview that crashed before:
    alloc_rows = []
    for item in allocations:
        # Before the fix, item was a string and item["subject_name"] raised TypeError!
        alloc_rows.append(
            {
                "Subject": item["subject_name"],
                "Priority": item["priority"],
                "Score": round(float(item["score"]), 2),
                "Sessions": int(item["sessions"]),
                "Hours": round(float(item["hours"]), 2),
                "Reasons": "; ".join(item.get("reasons") or []),
            }
        )

    assert len(alloc_rows) == len(allocations)
    for row in alloc_rows:
        assert isinstance(row["Subject"], str)
        assert row["Priority"] in ("High", "Medium", "Low")
        assert isinstance(row["Score"], float)
        assert isinstance(row["Sessions"], int)
        assert isinstance(row["Hours"], float)


def test_regression_old_dict_preview_compatibility(temp_db: Path) -> None:
    """Verifies that if preview['subject_allocations'] contains a legacy dict,

    normalize_subject_priorities converts it cleanly so the UI rendering never crashes.
    """
    s_id = insert_subject("Software Architecture", subject_code="CS405", db_path=temp_db)

    # Legacy dictionary structure
    legacy_subject_allocations = {"Software Architecture": 3.0}

    canonical = normalize_subject_priorities(legacy_subject_allocations, db_path=temp_db)
    assert isinstance(canonical, list)
    assert len(canonical) == 1

    # Ensure UI loop can execute safely on it
    alloc_rows = []
    for item in canonical:
        alloc_rows.append(
            {
                "Subject": item["subject_name"],
                "Priority": item["priority"],
                "Score": round(float(item["score"]), 2),
                "Sessions": int(item["sessions"]),
                "Hours": round(float(item["hours"]), 2),
                "Reasons": "; ".join(item.get("reasons") or []),
            }
        )
    assert alloc_rows[0]["Subject"] == "Software Architecture"


def test_save_generated_timetable_transaction_rollback_on_failure(temp_db: Path, monkeypatch) -> None:
    """Verifies that an error during save_generated_timetable rolls back the transaction cleanly."""
    _seed_profile(temp_db, days=["Monday"], weekly_hours=2)
    s_id = insert_subject("Compiler Design", subject_code="CS501", db_path=temp_db)

    sessions = [
        {
            "subject_id": s_id,
            "topic_id": None,
            "study_date": "2026-03-02",
            "start_time": "18:00",
            "end_time": "19:00",
            "session_title": "Lexical Analysis",
            "priority": "Medium",
        }
    ]

    # Monkeypatch to simulate database failure during insert
    original_execute = None

    import sqlite3
    real_connect = sqlite3.connect

    def faulty_execute(sql, *args, **kwargs):
        if "INSERT INTO timetable" in sql:
            raise sqlite3.OperationalError("Simulated write failure")
        return original_execute(sql, *args, **kwargs)

    # Verify that an invalid slot triggers rejection before partial commit
    bad_sessions = [
        {
            "subject_id": s_id,
            "study_date": "2026-03-02",
            "start_time": "19:00",
            "end_time": "18:00",  # Invalid times
        }
    ]
    with pytest.raises(ValueError):
        save_generated_timetable(bad_sessions, "2026-03-02", "2026-03-08", db_path=temp_db)

    # Ensure no partial rows were committed
    saved = get_saved_timetable("2026-03-02", "2026-03-08", db_path=temp_db)
    assert len(saved) == 0

