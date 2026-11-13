"""Unit tests for Academic Performance, Attendance, Marks & Weak Subjects (Step 5)."""

import pytest

from database.db import initialize_database
from services.academic_service import (
    analyze_weak_subjects,
    calculate_assessment_percentage,
    calculate_attendance_percentage,
    calculate_missed_classes,
    calculate_overall_academic_average,
    calculate_overall_weighted_attendance,
    calculate_required_additional_classes,
    create_marks_record,
    delete_marks_record,
    fetch_marks_records,
    get_academic_overview,
    get_attendance_by_subject,
    get_subject_marks_summary,
    identify_low_attendance_subjects,
    update_marks_record,
    upsert_attendance,
)
from services.profile_service import save_profile
from services.subject_service import create_subject


@pytest.fixture()
def temp_db(tmp_path):
    """Provide a clean initialized temporary SQLite database."""
    db_file = tmp_path / "test_step5.db"
    assert initialize_database(db_file) is True
    return db_file


def test_attendance_create_update_percentage_and_zero_classes(temp_db):
    sid = create_subject("DSA", semester=3, db_path=temp_db)

    # Zero classes conducted
    upsert_attendance(sid, classes_held=0, classes_attended=0, db_path=temp_db)
    assert calculate_attendance_percentage(0, 0) is None

    # Update attendance
    upsert_attendance(sid, classes_held=20, classes_attended=16, db_path=temp_db)
    rec = get_attendance_by_subject(sid, db_path=temp_db)
    assert rec["classes_held"] == 20
    assert rec["classes_attended"] == 16
    assert calculate_attendance_percentage(20, 16) == 80.0
    assert calculate_missed_classes(20, 16) == 4


def test_weighted_overall_attendance(temp_db):
    s1 = create_subject("DSA", semester=3, db_path=temp_db)
    s2 = create_subject("DBMS", semester=3, db_path=temp_db)

    # Subject 1: 10/10 = 100%, Subject 2: 20/40 = 50%
    # Simple average would be 75%, but weighted overall is 30/50 = 60%
    upsert_attendance(s1, classes_held=10, classes_attended=10, db_path=temp_db)
    upsert_attendance(s2, classes_held=40, classes_attended=20, db_path=temp_db)

    overall = calculate_overall_weighted_attendance(db_path=temp_db)
    assert overall["total_classes_held"] == 50
    assert overall["total_classes_attended"] == 30
    assert overall["total_classes_missed"] == 20
    assert overall["overall_percentage"] == 60.0


def test_required_additional_classes_and_edge_cases():
    # 12/20 = 60%, target 75% -> (0.75*20 - 12)/(1 - 0.75) = 3/0.25 = 12 classes
    res = calculate_required_additional_classes(20, 12, 75.0)
    assert res["status"] == "classes_needed"
    assert res["required_classes"] == 12

    # Already reached target
    reached = calculate_required_additional_classes(20, 16, 75.0)
    assert reached["status"] == "target_reached"
    assert reached["required_classes"] == 0

    # 100% target edge case with missed class
    edge_100 = calculate_required_additional_classes(10, 9, 100.0)
    assert edge_100["status"] == "unreachable_100"
    assert edge_100["required_classes"] is None

    # No classes conducted
    no_cls = calculate_required_additional_classes(0, 0, 75.0)
    assert no_cls["status"] == "no_classes"


def test_invalid_attendance_rejected(temp_db):
    sid = create_subject("Java", semester=3, db_path=temp_db)

    with pytest.raises(ValueError):
        upsert_attendance(sid, classes_held=10, classes_attended=11, db_path=temp_db)

    with pytest.raises(ValueError):
        upsert_attendance(sid, classes_held=-5, classes_attended=0, db_path=temp_db)


def test_marks_crud_and_weighted_averages(temp_db):
    sid = create_subject("Operating Systems", semester=4, db_path=temp_db)
    s2 = create_subject("Maths", semester=4, db_path=temp_db)

    assert calculate_assessment_percentage(18, 25) == 72.0

    m1 = create_marks_record(sid, "Quiz", 8, 10, "2026-11-05", db_path=temp_db)
    m2 = create_marks_record(sid, "Internal Assessment", 32, 40, "2026-11-10", db_path=temp_db)

    records = fetch_marks_records(subject_id=sid, db_path=temp_db)
    assert len(records) == 2

    # Weighted average for OS: (8 + 32) / (10 + 40) = 40 / 50 = 80.0%
    summary = {m["subject_name"]: m for m in get_subject_marks_summary(db_path=temp_db)}
    assert summary["Operating Systems"]["weighted_percentage"] == 80.0
    assert summary["Maths"]["weighted_percentage"] is None

    # Update mark
    update_marks_record(m1, sid, "Quiz", 10, 10, "2026-11-05", db_path=temp_db)
    assert calculate_overall_academic_average(db_path=temp_db) == 84.0

    # Delete mark
    delete_marks_record(m1, db_path=temp_db)
    assert len(fetch_marks_records(subject_id=sid, db_path=temp_db)) == 1
    assert calculate_overall_academic_average(db_path=temp_db) == 80.0

    # Invalid marks rejected
    with pytest.raises(ValueError):
        create_marks_record(sid, "Test", 30, 20, db_path=temp_db)


def test_weak_subject_identification_and_academic_overview(temp_db):
    save_profile(name="Aarav", semester=3, attendance_target=75.0, db_path=temp_db)

    s_both = create_subject("DBMS", semester=3, db_path=temp_db)
    s_low_marks = create_subject("Discrete Math", semester=3, db_path=temp_db)
    s_low_att = create_subject("Java", semester=3, db_path=temp_db)
    s_good = create_subject("DSA", semester=3, db_path=temp_db)
    s_no_marks = create_subject("Ethics", semester=3, db_path=temp_db)

    # DBMS: 45% marks & 68% attendance -> both low
    create_marks_record(s_both, "Internal Assessment", 45, 100, db_path=temp_db)
    upsert_attendance(s_both, 25, 17, db_path=temp_db)

    # Discrete Math: 50% marks & 90% attendance -> low marks
    create_marks_record(s_low_marks, "Test", 10, 20, db_path=temp_db)
    upsert_attendance(s_low_marks, 20, 18, db_path=temp_db)

    # Java: 85% marks & 60% attendance -> low attendance
    create_marks_record(s_low_att, "Quiz", 17, 20, db_path=temp_db)
    upsert_attendance(s_low_att, 20, 12, db_path=temp_db)

    # DSA: 88% marks & 85% attendance -> Satisfactory
    create_marks_record(s_good, "Internal Assessment", 44, 50, db_path=temp_db)
    upsert_attendance(s_good, 20, 17, db_path=temp_db)

    # Ethics: no marks, good attendance -> Insufficient Data
    upsert_attendance(s_no_marks, 10, 9, db_path=temp_db)

    analysis = {a["subject_name"]: a for a in analyze_weak_subjects(marks_threshold=60.0, db_path=temp_db)}
    assert analysis["DBMS"]["performance_status"] == "Needs Attention"
    assert "both below" in analysis["DBMS"]["reason"].lower()
    assert analysis["Discrete Math"]["performance_status"] == "Needs Attention"
    assert analysis["Java"]["performance_status"] == "Needs Attention"
    assert analysis["DSA"]["performance_status"] == "Satisfactory"
    assert analysis["Ethics"]["performance_status"] == "Insufficient Data"

    low_att = identify_low_attendance_subjects(db_path=temp_db)
    assert {s["subject_name"] for s in low_att} == {"DBMS", "Java"}

    overview = get_academic_overview(marks_threshold=60.0, db_path=temp_db)
    assert overview["total_subjects"] == 5
    assert overview["subjects_needing_attention"] == 3
    assert overview["total_assessments"] == 4
