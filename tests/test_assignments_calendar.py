"""Unit tests for Assignment Manager, Deadline Reminders & College Calendar (Step 6)."""

from datetime import date, datetime, time
import pytest

from database.db import initialize_database
from services.assignment_service import (
    calculate_assignment_completion_percentage,
    calculate_reminder_state,
    create_assignment,
    delete_assignment,
    fetch_active_reminders,
    fetch_assignments,
    fetch_overdue_assignments,
    fetch_upcoming_deadlines,
    get_assignment,
    get_assignment_overview,
    mark_assignment_completed,
    update_assignment,
)
from services.calendar_service import (
    create_calendar_event,
    delete_calendar_event,
    fetch_all_events,
    fetch_events_by_date_range,
    fetch_events_by_month,
    fetch_events_by_type,
    fetch_upcoming_events,
    get_calendar_event,
    get_combined_upcoming_schedule,
    update_calendar_event,
)
from services.subject_service import create_subject


@pytest.fixture()
def temp_db(tmp_path):
    """Provide a clean initialized temporary SQLite database."""
    db_file = tmp_path / "test_step6.db"
    assert initialize_database(db_file) is True
    return db_file


# ---------------------------------------------------------------------------
# Assignment & Reminder Tests
# ---------------------------------------------------------------------------


def test_assignment_crud_and_completion_preservation(temp_db):
    sid = create_subject("DBMS", semester=3, db_path=temp_db)
    aid = create_assignment(
        subject_id=sid,
        title="ER Diagram Assignment",
        deadline_date="2026-11-20",
        assigned_date="2026-11-10",
        deadline_time=time(17, 0),
        reminder_at=datetime(2026, 11, 19, 10, 0),
        priority="High",
        status="Pending",
        db_path=temp_db,
    )
    row = get_assignment(aid, db_path=temp_db)
    assert row is not None
    assert row["title"] == "ER Diagram Assignment"
    orig_assigned = row["assigned_date"]
    orig_created = row["created_at"]

    # Mark Completed -> sets completed_at and preserves assigned_date & created_at
    mark_assignment_completed(aid, db_path=temp_db)
    comp_row = get_assignment(aid, db_path=temp_db)
    assert comp_row["status"] == "Completed"
    assert comp_row["completed_at"] is not None
    assert comp_row["assigned_date"] == orig_assigned
    assert comp_row["created_at"] == orig_created
    orig_completed_at = comp_row["completed_at"]

    # Edit without changing status -> preserves completed_at
    update_assignment(
        assignment_id=aid,
        subject_id=sid,
        title="ER Diagram Assignment (Revised)",
        deadline_date="2026-11-20",
        status="Completed",
        db_path=temp_db,
    )
    assert get_assignment(aid, db_path=temp_db)["completed_at"] == orig_completed_at

    # Reopen -> clears completed_at
    update_assignment(
        assignment_id=aid,
        subject_id=sid,
        title="ER Diagram Assignment (Revised)",
        deadline_date="2026-11-20",
        status="In Progress",
        db_path=temp_db,
    )
    assert get_assignment(aid, db_path=temp_db)["completed_at"] is None

    # Delete
    delete_assignment(aid, db_path=temp_db)
    assert get_assignment(aid, db_path=temp_db) is None


def test_assignment_reminder_classifications_and_suppression(temp_db):
    sid = create_subject("DSA", semester=3, db_path=temp_db)
    fixed_now = datetime(2026, 11, 12, 14, 0, 0)

    a_overdue = create_assignment(
        sid, "Overdue Task", "2026-11-11", deadline_time=time(23, 59), db_path=temp_db
    )
    a_today = create_assignment(
        sid, "Today Task", "2026-11-12", deadline_time=time(20, 0), db_path=temp_db
    )
    a_soon = create_assignment(
        sid, "Soon Task", "2026-11-14", db_path=temp_db
    )
    a_upcoming = create_assignment(
        sid, "Upcoming Task", "2026-11-25", reminder_at=datetime(2026, 11, 12, 9, 0), db_path=temp_db
    )
    a_done = create_assignment(
        sid, "Done Task", "2026-11-10", status="Completed", db_path=temp_db
    )

    assert calculate_reminder_state(get_assignment(a_overdue, db_path=temp_db), fixed_now)["category"] == "Overdue"
    assert calculate_reminder_state(get_assignment(a_today, db_path=temp_db), fixed_now)["category"] == "Due Today"
    assert calculate_reminder_state(get_assignment(a_soon, db_path=temp_db), fixed_now)["category"] == "Due Soon"

    up_state = calculate_reminder_state(get_assignment(a_upcoming, db_path=temp_db), fixed_now)
    assert up_state["category"] == "Upcoming"
    assert up_state["reminder_triggered"] is True

    done_state = calculate_reminder_state(get_assignment(a_done, db_path=temp_db), fixed_now)
    assert done_state["category"] == "Completed"
    assert done_state["reminder_triggered"] is False

    # Active reminders suppress Completed, include Overdue/Today/Soon + triggered Upcoming
    active_ids = {r["id"] for r in fetch_active_reminders(current_dt=fixed_now, db_path=temp_db)}
    assert active_ids == {a_overdue, a_today, a_soon, a_upcoming}

    # Sorting by nearest deadline
    all_sorted = fetch_assignments(current_dt=fixed_now, db_path=temp_db)
    assert [a["deadline_date"] for a in all_sorted] == [
        "2026-11-10",
        "2026-11-11",
        "2026-11-12",
        "2026-11-14",
        "2026-11-25",
    ]

    assert len(fetch_overdue_assignments(current_dt=fixed_now, db_path=temp_db)) == 1
    assert len(fetch_upcoming_deadlines(days=3, current_dt=fixed_now, db_path=temp_db)) == 2
    assert calculate_assignment_completion_percentage(db_path=temp_db) == 20.0

    overview = get_assignment_overview(current_dt=fixed_now, db_path=temp_db)
    assert overview["total"] == 5
    assert overview["overdue"] == 1
    assert overview["due_today"] == 1
    assert overview["completed"] == 1


def test_invalid_assignment_dates_and_reminders_rejected(temp_db):
    sid = create_subject("Java", semester=3, db_path=temp_db)

    with pytest.raises(ValueError):
        create_assignment(
            sid, "Invalid Dates", deadline_date="2026-11-10", assigned_date="2026-11-15", db_path=temp_db
        )

    with pytest.raises(ValueError):
        create_assignment(
            sid,
            "Invalid Reminder",
            deadline_date="2026-11-15",
            deadline_time=time(17, 0),
            reminder_at=datetime(2026, 11, 15, 18, 0),
            db_path=temp_db,
        )


# ---------------------------------------------------------------------------
# College Calendar & Combined Schedule Tests
# ---------------------------------------------------------------------------


def test_calendar_event_crud_and_filters(temp_db):
    e1 = create_calendar_event(
        title="Mid-Sem Exam",
        event_type="Internal Examination",
        start_date="2026-11-20",
        end_date="2026-11-24",
        start_time=time(9, 30),
        description="Core subjects",
        db_path=temp_db,
    )
    e2 = create_calendar_event(
        title="Annual Hackathon",
        event_type="Hackathon",
        start_date="2026-12-05",
        db_path=temp_db,
    )

    assert get_calendar_event(e1, db_path=temp_db)["title"] == "Mid-Sem Exam"
    assert len(fetch_all_events(db_path=temp_db)) == 2

    # Edit event
    update_calendar_event(
        event_id=e1,
        title="Mid-Sem Exam (Updated)",
        event_type="Internal Examination",
        start_date="2026-11-21",
        end_date="2026-11-25",
        db_path=temp_db,
    )
    assert get_calendar_event(e1, db_path=temp_db)["title"] == "Mid-Sem Exam (Updated)"

    # Monthly & type filtering
    nov_events = fetch_events_by_month(2026, 11, db_path=temp_db)
    assert len(nov_events) == 1
    assert nov_events[0]["id"] == e1

    hackathons = fetch_events_by_type("Hackathon", db_path=temp_db)
    assert len(hackathons) == 1
    assert hackathons[0]["id"] == e2

    range_events = fetch_events_by_date_range("2026-11-01", "2026-12-31", db_path=temp_db)
    assert [e["id"] for e in range_events] == [e1, e2]

    upcoming = fetch_upcoming_events(reference_date="2026-11-26", db_path=temp_db)
    assert [e["id"] for e in upcoming] == [e2]

    delete_calendar_event(e2, db_path=temp_db)
    assert get_calendar_event(e2, db_path=temp_db) is None


def test_invalid_calendar_event_date_range_rejected(temp_db):
    with pytest.raises(ValueError):
        create_calendar_event(
            title="Bad Event",
            event_type="Workshop",
            start_date="2026-11-20",
            end_date="2026-11-18",
            db_path=temp_db,
        )


def test_combined_upcoming_schedule(temp_db):
    sid = create_subject("OS", semester=4, db_path=temp_db)
    create_assignment(sid, "OS Lab 1", "2026-11-15", priority="High", db_path=temp_db)
    create_assignment(sid, "OS Completed", "2026-11-14", status="Completed", db_path=temp_db)
    create_calendar_event("OS Practical", "Practical Examination", "2026-11-18", db_path=temp_db)

    combined = get_combined_upcoming_schedule(reference_date="2026-11-12", db_path=temp_db)
    # Completed assignment is excluded; pending assignment + event are sorted chronologically
    assert len(combined) == 2
    assert combined[0]["title"] == "OS Lab 1"
    assert combined[0]["source_type"] == "Assignment Deadline"
    assert combined[1]["title"] == "OS Practical"
    assert combined[1]["source_type"] == "College Event"
