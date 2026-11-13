"""Business logic for Attendance, Internal Marks, Weak Subject Detection & Analytics."""

from datetime import date
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from database.db import execute_query, fetch_all, fetch_one
from database.queries import save_attendance, save_marks
from services.profile_service import get_profile
from services.subject_service import get_subject
from utils.config import (
    ATTENDANCE_TARGET,
    ATTENDANCE_WARNING_BUFFER,
    MARKS_WEAK_THRESHOLD,
)
from utils.validators import validate_non_empty_text

ASSESSMENT_TYPES = (
    "Internal Assessment",
    "Quiz",
    "Assignment",
    "Practical",
    "Test",
    "Other",
)


def _to_iso_date(value: Optional[Union[date, str]]) -> Optional[str]:
    """Convert date or string to YYYY-MM-DD."""
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    if not text:
        return None
    date.fromisoformat(text)
    return text


# ---------------------------------------------------------------------------
# Attendance Operations
# ---------------------------------------------------------------------------


def get_attendance_target(db_path: Optional[Union[str, Path]] = None) -> float:
    """Return the student's configured attendance target percentage."""
    profile = get_profile(db_path=db_path)
    if profile and profile.get("attendance_target") is not None:
        return float(profile["attendance_target"])
    return float(ATTENDANCE_TARGET)


def upsert_attendance(
    subject_id: int,
    classes_held: int,
    classes_attended: int,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Validate and save/update aggregate attendance for a subject."""
    if get_subject(subject_id, db_path=db_path) is None:
        raise ValueError("Selected subject does not exist.")
    return save_attendance(
        subject_id=subject_id,
        classes_held=int(classes_held),
        classes_attended=int(classes_attended),
        db_path=db_path,
    )


def get_attendance_by_subject(
    subject_id: int,
    db_path: Optional[Union[str, Path]] = None,
) -> Optional[Dict[str, Any]]:
    """Fetch the attendance record for a single subject."""
    row = fetch_one(
        "SELECT * FROM attendance WHERE subject_id = ?;",
        (subject_id,),
        db_path=db_path,
    )
    return dict(row) if row is not None else None


def calculate_attendance_percentage(
    classes_held: int,
    classes_attended: int,
) -> Optional[float]:
    """Calculate attendance percentage safely; returns None when classes_held is 0."""
    if classes_held < 0 or classes_attended < 0 or classes_attended > classes_held:
        raise ValueError("Invalid attendance counts.")
    if classes_held == 0:
        return None
    return round((classes_attended / classes_held) * 100.0, 2)


def calculate_missed_classes(classes_held: int, classes_attended: int) -> int:
    """Return number of missed classes."""
    if classes_held < 0 or classes_attended < 0 or classes_attended > classes_held:
        raise ValueError("Invalid attendance counts.")
    return int(classes_held - classes_attended)


def calculate_required_additional_classes(
    classes_held: int,
    classes_attended: int,
    target_percent: float,
) -> Dict[str, Any]:
    """Calculate consecutive classes needed to reach target_percent."""
    if classes_held < 0 or classes_attended < 0 or classes_attended > classes_held:
        raise ValueError("Invalid attendance counts.")
    if target_percent < 0 or target_percent > 100:
        raise ValueError("Attendance target must be between 0 and 100.")

    if classes_held == 0:
        return {
            "status": "no_classes",
            "required_classes": None,
            "message": "No attendance recorded yet.",
        }

    current_pct = (classes_attended / classes_held) * 100.0
    if current_pct + 1e-9 >= target_percent:
        return {
            "status": "target_reached",
            "required_classes": 0,
            "message": "You have already reached your attendance target.",
        }

    if target_percent >= 100.0:
        return {
            "status": "unreachable_100",
            "required_classes": None,
            "message": (
                "Target is 100%, and because at least one class was missed, "
                "no finite number of additional classes will restore 100% attendance."
            ),
        }

    t_dec = target_percent / 100.0
    numerator = (t_dec * classes_held) - classes_attended
    denominator = 1.0 - t_dec
    needed = max(0, int(math.ceil(round(numerator / denominator, 9))))
    return {
        "status": "classes_needed",
        "required_classes": needed,
        "message": f"Attend {needed} consecutive class(es) to reach {target_percent:.0f}%.",
    }


def get_attendance_summary_all_subjects(
    target_percent: Optional[float] = None,
    warning_buffer: float = ATTENDANCE_WARNING_BUFFER,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Return subject-wise attendance summary with statuses and required classes."""
    target = (
        float(target_percent)
        if target_percent is not None
        else get_attendance_target(db_path=db_path)
    )
    rows = fetch_all(
        """
        SELECT
            sub.id AS subject_id,
            sub.subject_name,
            COALESCE(a.classes_held, 0) AS classes_held,
            COALESCE(a.classes_attended, 0) AS classes_attended,
            a.updated_at
        FROM subjects sub
        LEFT JOIN attendance a ON sub.id = a.subject_id
        ORDER BY sub.subject_name ASC, sub.id ASC;
        """,
        db_path=db_path,
    )

    results: List[Dict[str, Any]] = []
    for row in rows:
        held = int(row["classes_held"])
        attended = int(row["classes_attended"])
        missed = calculate_missed_classes(held, attended)
        pct = calculate_attendance_percentage(held, attended)
        req = calculate_required_additional_classes(held, attended, target)

        if pct is None:
            status = "No Data"
        elif pct < target:
            status = "Needs Improvement"
        elif pct < target + warning_buffer:
            status = "Close to Target"
        else:
            status = "Good"

        results.append(
            {
                "subject_id": int(row["subject_id"]),
                "subject_name": row["subject_name"],
                "classes_held": held,
                "classes_attended": attended,
                "missed_classes": missed,
                "attendance_percentage": pct,
                "status": status,
                "required_info": req,
            }
        )
    return results


def calculate_overall_weighted_attendance(
    db_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Calculate weighted overall attendance from total attended and held classes."""
    row = fetch_one(
        """
        SELECT
            COALESCE(SUM(classes_held), 0) AS total_held,
            COALESCE(SUM(classes_attended), 0) AS total_attended
        FROM attendance;
        """,
        db_path=db_path,
    )
    total_held = int(row["total_held"]) if row else 0
    total_attended = int(row["total_attended"]) if row else 0
    total_missed = max(0, total_held - total_attended)
    pct = calculate_attendance_percentage(total_held, total_attended)

    return {
        "total_classes_held": total_held,
        "total_classes_attended": total_attended,
        "total_classes_missed": total_missed,
        "overall_percentage": pct,
    }


def identify_low_attendance_subjects(
    target_percent: Optional[float] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Return subjects whose recorded attendance is below target."""
    summary = get_attendance_summary_all_subjects(
        target_percent=target_percent, db_path=db_path
    )
    return [s for s in summary if s["status"] == "Needs Improvement"]


# ---------------------------------------------------------------------------
# Marks & Assessment Operations
# ---------------------------------------------------------------------------


def calculate_assessment_percentage(
    marks_obtained: float, maximum_marks: float
) -> float:
    """Calculate percentage for a single assessment."""
    if marks_obtained < 0:
        raise ValueError("Marks obtained cannot be negative.")
    if maximum_marks <= 0:
        raise ValueError("Maximum marks must be greater than zero.")
    if marks_obtained > maximum_marks:
        raise ValueError("Marks obtained cannot exceed maximum marks.")
    return round((marks_obtained / maximum_marks) * 100.0, 2)


def create_marks_record(
    subject_id: int,
    assessment_type: str,
    marks_obtained: float,
    maximum_marks: float,
    assessment_date: Optional[Union[date, str]] = None,
    notes: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Validate and insert an assessment marks record."""
    if get_subject(subject_id, db_path=db_path) is None:
        raise ValueError("Selected subject does not exist.")
    ok, msg = validate_non_empty_text(assessment_type, "Assessment Type")
    if not ok:
        raise ValueError(msg)

    date_iso = _to_iso_date(assessment_date)
    return save_marks(
        subject_id=subject_id,
        assessment_type=assessment_type.strip(),
        marks_obtained=float(marks_obtained),
        maximum_marks=float(maximum_marks),
        assessment_date=date_iso,
        notes=notes.strip() if notes else None,
        db_path=db_path,
    )


def update_marks_record(
    mark_id: int,
    subject_id: int,
    assessment_type: str,
    marks_obtained: float,
    maximum_marks: float,
    assessment_date: Optional[Union[date, str]] = None,
    notes: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Validate and update an existing marks record."""
    existing = fetch_one(
        "SELECT id FROM marks WHERE id = ?;", (mark_id,), db_path=db_path
    )
    if existing is None:
        raise ValueError(f"Marks record ID {mark_id} does not exist.")
    if get_subject(subject_id, db_path=db_path) is None:
        raise ValueError("Selected subject does not exist.")

    ok, msg = validate_non_empty_text(assessment_type, "Assessment Type")
    if not ok:
        raise ValueError(msg)
    calculate_assessment_percentage(float(marks_obtained), float(maximum_marks))

    execute_query(
        """
        UPDATE marks
        SET subject_id = ?, assessment_type = ?, marks_obtained = ?,
            maximum_marks = ?, assessment_date = ?, notes = ?
        WHERE id = ?;
        """,
        (
            subject_id,
            assessment_type.strip(),
            float(marks_obtained),
            float(maximum_marks),
            _to_iso_date(assessment_date),
            notes.strip() if notes else None,
            mark_id,
        ),
        db_path=db_path,
    )
    return mark_id


def delete_marks_record(
    mark_id: int,
    db_path: Optional[Union[str, Path]] = None,
) -> None:
    """Delete a marks record by ID."""
    execute_query("DELETE FROM marks WHERE id = ?;", (mark_id,), db_path=db_path)


def fetch_marks_records(
    subject_id: Optional[int] = None,
    assessment_type: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Fetch marks records with optional subject and assessment_type filters."""
    clauses: List[str] = []
    params: List[Any] = []
    if subject_id is not None:
        clauses.append("m.subject_id = ?")
        params.append(subject_id)
    if assessment_type is not None and assessment_type != "All":
        clauses.append("m.assessment_type = ?")
        params.append(assessment_type)

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = fetch_all(
        f"""
        SELECT m.*, sub.subject_name
        FROM marks m
        JOIN subjects sub ON m.subject_id = sub.id
        {where_sql}
        ORDER BY COALESCE(m.assessment_date, '') DESC, m.id DESC;
        """,
        tuple(params),
        db_path=db_path,
    )
    results: List[Dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["percentage"] = calculate_assessment_percentage(
            float(item["marks_obtained"]), float(item["maximum_marks"])
        )
        results.append(item)
    return results


def get_subject_marks_summary(
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Calculate weighted average marks per subject."""
    rows = fetch_all(
        """
        SELECT
            sub.id AS subject_id,
            sub.subject_name,
            COUNT(m.id) AS total_assessments,
            COALESCE(SUM(m.marks_obtained), 0.0) AS total_obtained,
            COALESCE(SUM(m.maximum_marks), 0.0) AS total_maximum
        FROM subjects sub
        LEFT JOIN marks m ON sub.id = m.subject_id
        GROUP BY sub.id, sub.subject_name
        ORDER BY sub.subject_name ASC, sub.id ASC;
        """,
        db_path=db_path,
    )
    results: List[Dict[str, Any]] = []
    for row in rows:
        total_max = float(row["total_maximum"])
        total_obt = float(row["total_obtained"])
        weighted_pct = round((total_obt / total_max) * 100.0, 2) if total_max > 0 else None
        results.append(
            {
                "subject_id": int(row["subject_id"]),
                "subject_name": row["subject_name"],
                "total_assessments": int(row["total_assessments"]),
                "total_obtained": round(total_obt, 2),
                "total_maximum": round(total_max, 2),
                "weighted_percentage": weighted_pct,
            }
        )
    return results


def calculate_overall_academic_average(
    db_path: Optional[Union[str, Path]] = None,
) -> Optional[float]:
    """Calculate weighted average marks across all recorded assessments."""
    row = fetch_one(
        """
        SELECT
            COALESCE(SUM(marks_obtained), 0.0) AS sum_obt,
            COALESCE(SUM(maximum_marks), 0.0) AS sum_max
        FROM marks;
        """,
        db_path=db_path,
    )
    if not row or float(row["sum_max"]) <= 0:
        return None
    return round((float(row["sum_obt"]) / float(row["sum_max"])) * 100.0, 2)


# ---------------------------------------------------------------------------
# Weak Subject Identification & Overview Analytics
# ---------------------------------------------------------------------------


def analyze_weak_subjects(
    marks_threshold: float = MARKS_WEAK_THRESHOLD,
    attendance_target: Optional[float] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Identify weak subjects based on weighted marks and attendance targets."""
    target_att = (
        float(attendance_target)
        if attendance_target is not None
        else get_attendance_target(db_path=db_path)
    )
    marks_list = {
        m["subject_id"]: m for m in get_subject_marks_summary(db_path=db_path)
    }
    att_list = get_attendance_summary_all_subjects(
        target_percent=target_att, db_path=db_path
    )

    analysis: List[Dict[str, Any]] = []
    for att in att_list:
        sid = att["subject_id"]
        marks_info = marks_list.get(sid, {})
        avg_marks = marks_info.get("weighted_percentage")
        att_pct = att["attendance_percentage"]

        low_marks = avg_marks is not None and avg_marks < marks_threshold
        low_att = att_pct is not None and att_pct < target_att

        if low_marks and low_att:
            perf_status = "Needs Attention"
            reason = (
                "Your assessment performance and attendance are both below the configured targets."
            )
        elif low_marks:
            perf_status = "Needs Attention"
            reason = (
                f"Weighted marks ({avg_marks:.1f}%) are below the {marks_threshold:.0f}% threshold."
            )
        elif low_att:
            perf_status = "Needs Attention"
            reason = (
                f"Attendance ({att_pct:.1f}%) is below your {target_att:.0f}% target."
            )
        elif avg_marks is None:
            perf_status = "Insufficient Data"
            reason = "Insufficient assessment data."
        else:
            perf_status = "Satisfactory"
            reason = "Meeting academic performance and attendance targets."

        analysis.append(
            {
                "subject_id": sid,
                "subject_name": att["subject_name"],
                "average_marks": avg_marks,
                "attendance_percentage": att_pct,
                "performance_status": perf_status,
                "reason": reason,
            }
        )
    return analysis


def get_academic_overview(
    marks_threshold: float = MARKS_WEAK_THRESHOLD,
    db_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Return top-level academic overview KPIs from real SQLite data."""
    overall_att = calculate_overall_weighted_attendance(db_path=db_path)
    overall_marks = calculate_overall_academic_average(db_path=db_path)
    weak_analysis = analyze_weak_subjects(
        marks_threshold=marks_threshold, db_path=db_path
    )
    marks_rows = fetch_marks_records(db_path=db_path)

    needing_attention = sum(
        1 for item in weak_analysis if item["performance_status"] == "Needs Attention"
    )

    return {
        "total_subjects": len(weak_analysis),
        "overall_attendance": overall_att["overall_percentage"],
        "overall_marks_average": overall_marks,
        "subjects_needing_attention": needing_attention,
        "total_assessments": len(marks_rows),
    }


def get_attendance_chart_data(
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Prepare subject-wise attendance data for Plotly charts."""
    summary = get_attendance_summary_all_subjects(db_path=db_path)
    return [s for s in summary if s["attendance_percentage"] is not None]


def get_marks_chart_data(
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Prepare subject-wise weighted marks data for Plotly charts."""
    summary = get_subject_marks_summary(db_path=db_path)
    return [m for m in summary if m["weighted_percentage"] is not None]


def get_combined_performance_data(
    marks_threshold: float = MARKS_WEAK_THRESHOLD,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Prepare combined attendance + marks data for scatter/comparison charts."""
    analysis = analyze_weak_subjects(
        marks_threshold=marks_threshold, db_path=db_path
    )
    return [
        a
        for a in analysis
        if a["average_marks"] is not None and a["attendance_percentage"] is not None
    ]
