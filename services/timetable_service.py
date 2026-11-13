"""Deterministic Rule-Based Smart Timetable Generator & Scheduler."""

from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from database.db import execute_query, fetch_all, fetch_one, get_connection
from database.queries import (
    VALID_PRIORITIES,
    VALID_TIMETABLE_STATUSES,
    save_timetable_entry,
)
from services.academic_service import (
    get_attendance_summary_all_subjects,
    get_attendance_target,
    get_subject_marks_summary,
)
from services.assignment_service import fetch_assignments
from services.calendar_service import fetch_events_by_date_range
from services.profile_service import DAYS_OF_WEEK, get_profile
from services.study_service import fetch_sessions
from services.subject_service import get_subject, get_topic, list_subjects, list_topics
from utils.config import (
    DEFAULT_BREAK_MINUTES,
    DEFAULT_STUDY_SESSION_MINUTES,
    DEFAULT_TIMED_EVENT_BLOCK_MINUTES,
    EXAM_PRIORITY_DAYS,
    SUBJECT_PRIORITY_WEIGHTS,
    TIMETABLE_HORIZON_DAYS,
)
from utils.validators import validate_non_empty_text

EXAM_EVENT_TYPES = (
    "Internal Examination",
    "External Examination",
    "Practical Examination",
)


def _now_iso() -> str:
    """Return current local timestamp as ISO-8601 string."""
    return datetime.now().isoformat(timespec="seconds")


def _time_to_minutes(t_val: Union[time, str]) -> int:
    """Convert a time object or 'HH:MM' string to minutes since midnight."""
    if isinstance(t_val, time):
        return t_val.hour * 60 + t_val.minute
    parts = str(t_val).strip().split(":")
    return int(parts[0]) * 60 + int(parts[1])


def _minutes_to_hhmm(mins: int) -> str:
    """Convert minutes since midnight to 'HH:MM'."""
    h = mins // 60
    m = mins % 60
    return f"{h:02d}:{m:02d}"


def _to_iso_date(val: Union[date, str]) -> str:
    """Convert date or string to YYYY-MM-DD."""
    if isinstance(val, date) and not isinstance(val, datetime):
        return val.isoformat()
    return str(val).strip()


def _intervals_overlap(s1: int, e1: int, s2: int, e2: int) -> bool:
    """Return True if [s1, e1) and [s2, e2) overlap."""
    return s1 < e2 and s2 < e1


def get_student_availability(
    db_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Load study availability preferences from student_profile with safe defaults."""
    profile = get_profile(db_path=db_path)
    if profile is None:
        return {
            "has_profile": False,
            "available_days": list(DAYS_OF_WEEK[:5]),
            "preferred_start_time": "18:00",
            "preferred_end_time": "21:00",
            "daily_available_minutes": 120,
            "weekly_study_target_minutes": 600,
            "session_duration_minutes": DEFAULT_STUDY_SESSION_MINUTES,
            "break_duration_minutes": DEFAULT_BREAK_MINUTES,
        }

    days = profile.get("available_days_list") or []
    daily_mins = int(profile.get("daily_available_minutes") or 120)
    weekly_hrs = int(profile.get("weekly_study_target") or 10)
    session_mins = int(
        profile.get("session_duration_minutes") or DEFAULT_STUDY_SESSION_MINUTES
    )
    break_mins = int(
        profile.get("break_duration_minutes")
        if profile.get("break_duration_minutes") is not None
        else DEFAULT_BREAK_MINUTES
    )

    return {
        "has_profile": True,
        "available_days": days,
        "preferred_start_time": profile.get("preferred_start_time") or "18:00",
        "preferred_end_time": profile.get("preferred_end_time") or "21:00",
        "daily_available_minutes": daily_mins,
        "weekly_study_target_minutes": weekly_hrs * 60,
        "session_duration_minutes": session_mins,
        "break_duration_minutes": break_mins,
    }


def get_incomplete_topics(
    subject_id: int,
    current_date: Optional[date] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Return incomplete topics ordered by overdue date, In Progress status, and sequence."""
    today_iso = (current_date or date.today()).isoformat()
    topics = list_topics(subject_id, db_path=db_path)
    incomplete = [t for t in topics if t["status"] != "Completed"]

    def _sort_key(t: Dict[str, Any]) -> tuple:
        target = t.get("target_date") or "9999-12-31"
        is_overdue = 0 if (t.get("target_date") and t["target_date"] < today_iso) else 1
        in_prog_rank = 0 if t["status"] == "In Progress" else 1
        seq = t.get("sequence_number") or 999999
        return (is_overdue, in_prog_rank, target, seq, t["id"])

    incomplete.sort(key=_sort_key)
    return incomplete


def get_assignment_priority(
    subject_id: int,
    current_date: Optional[date] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> Tuple[int, List[str], Optional[str]]:
    """Calculate assignment urgency score, reasons, and most urgent title for a subject."""
    ref_date = current_date or date.today()
    ref_dt = datetime.combine(ref_date, time(12, 0))
    assignments = fetch_assignments(
        subject_id=subject_id, current_dt=ref_dt, db_path=db_path
    )

    best_score = 0
    reasons: List[str] = []
    urgent_title: Optional[str] = None

    for item in assignments:
        if item["status"] == "Completed":
            continue
        days_rem = item["days_remaining"]
        score = 0
        reason = None

        if days_rem < 0:
            score = SUBJECT_PRIORITY_WEIGHTS["assignment_overdue"]
            reason = f"Assignment '{item['title']}' is overdue"
        elif days_rem <= 1:
            score = SUBJECT_PRIORITY_WEIGHTS["assignment_due_1_day"]
            reason = f"Assignment '{item['title']}' is due within 1 day"
        elif days_rem <= 3:
            score = SUBJECT_PRIORITY_WEIGHTS["assignment_due_3_days"]
            reason = f"Assignment '{item['title']}' is due within 3 days"
        elif days_rem <= 7:
            score = SUBJECT_PRIORITY_WEIGHTS["assignment_due_7_days"]
            reason = f"Assignment '{item['title']}' is due within 7 days"

        if score > 0 and reason:
            reasons.append(reason)
            if score > best_score:
                best_score = score
                urgent_title = item["title"]

    return best_score, reasons, urgent_title


def get_exam_priority(
    current_date: Optional[date] = None,
    exam_subject_ids: Optional[List[int]] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Check upcoming examination events within EXAM_PRIORITY_DAYS."""
    ref_date = current_date or date.today()
    end_date = ref_date + timedelta(days=EXAM_PRIORITY_DAYS)
    events = fetch_events_by_date_range(ref_date, end_date, db_path=db_path)
    exams = [e for e in events if e["event_type"] in EXAM_EVENT_TYPES]

    if not exams:
        return {
            "score": 0,
            "nearest_exam": None,
            "exam_subject_ids": set(exam_subject_ids or []),
            "general_recommendation": None,
        }

    nearest = exams[0]
    days_until = (date.fromisoformat(nearest["start_date"]) - ref_date).days
    if days_until <= 3:
        score = SUBJECT_PRIORITY_WEIGHTS["exam_within_3_days"]
    elif days_until <= 7:
        score = SUBJECT_PRIORITY_WEIGHTS["exam_within_7_days"]
    else:
        score = SUBJECT_PRIORITY_WEIGHTS["exam_within_14_days"]

    selected_ids = set(exam_subject_ids or [])
    general_rec = None
    if not selected_ids:
        general_rec = (
            f"Upcoming '{nearest['title']}' ({nearest['event_type']}) on {nearest['start_date']}. "
            "Select priority exam subjects to focus revision sessions."
        )

    return {
        "score": score,
        "nearest_exam": nearest,
        "exam_subject_ids": selected_ids,
        "general_recommendation": general_rec,
    }


def calculate_subject_priority(
    subject_id: int,
    current_date: Optional[date] = None,
    exam_subject_ids: Optional[List[int]] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Calculate explainable priority score, label, and reasons for a subject."""
    ref_date = current_date or date.today()
    subj = get_subject(subject_id, db_path=db_path)
    if subj is None:
        raise ValueError(f"Subject ID {subject_id} does not exist.")

    score = 0
    reasons: List[str] = []

    # A. Marks performance
    marks_map = {
        m["subject_id"]: m for m in get_subject_marks_summary(db_path=db_path)
    }
    avg_marks = marks_map.get(subject_id, {}).get("weighted_percentage")
    if avg_marks is not None:
        if avg_marks < 40:
            score += SUBJECT_PRIORITY_WEIGHTS["marks_below_40"]
            reasons.append(f"Internal marks ({avg_marks:.1f}%) are critically low (<40%)")
        elif avg_marks < 50:
            score += SUBJECT_PRIORITY_WEIGHTS["marks_40_to_50"]
            reasons.append(f"Internal marks ({avg_marks:.1f}%) are below 50%")
        elif avg_marks < 60:
            score += SUBJECT_PRIORITY_WEIGHTS["marks_50_to_60"]
            reasons.append(f"Internal marks ({avg_marks:.1f}%) are below 60%")
        elif avg_marks < 75:
            score += SUBJECT_PRIORITY_WEIGHTS["marks_60_to_75"]
            reasons.append(f"Internal marks ({avg_marks:.1f}%) can be improved (<75%)")

    # B. Attendance
    att_target = get_attendance_target(db_path=db_path)
    att_map = {
        a["subject_id"]: a
        for a in get_attendance_summary_all_subjects(
            target_percent=att_target, db_path=db_path
        )
    }
    att_info = att_map.get(subject_id, {})
    att_pct = att_info.get("attendance_percentage")
    if att_pct is not None:
        if att_pct < att_target:
            score += SUBJECT_PRIORITY_WEIGHTS["attendance_below_target"]
            reasons.append(
                f"Attendance ({att_pct:.1f}%) is below your {att_target:.0f}% target"
            )
        elif att_pct <= att_target + 5.0:
            score += SUBJECT_PRIORITY_WEIGHTS["attendance_close_to_target"]
            reasons.append(
                f"Attendance ({att_pct:.1f}%) is close to your {att_target:.0f}% target"
            )

    # C. Topic progress
    incomplete = get_incomplete_topics(subject_id, current_date=ref_date, db_path=db_path)
    today_iso = ref_date.isoformat()
    has_overdue_topic = any(
        t.get("target_date") and t["target_date"] < today_iso for t in incomplete
    )
    has_in_prog = any(t["status"] == "In Progress" for t in incomplete)
    if has_overdue_topic:
        score += SUBJECT_PRIORITY_WEIGHTS["topic_overdue"]
        reasons.append("Has incomplete topic(s) past target completion date")
    elif has_in_prog:
        score += SUBJECT_PRIORITY_WEIGHTS["topic_in_progress"]
        reasons.append("Has in-progress syllabus topic(s)")

    # D. Assignment deadlines
    assign_score, assign_reasons, urgent_assign = get_assignment_priority(
        subject_id, current_date=ref_date, db_path=db_path
    )
    score += assign_score
    reasons.extend(assign_reasons)

    # E. Examination priority (explicitly selected subjects only)
    exam_info = get_exam_priority(
        current_date=ref_date, exam_subject_ids=exam_subject_ids, db_path=db_path
    )
    if subject_id in exam_info["exam_subject_ids"] and exam_info["score"] > 0:
        score += exam_info["score"]
        nearest = exam_info["nearest_exam"]
        reasons.append(
            f"Selected as priority for upcoming {nearest['event_type']} ({nearest['start_date']})"
        )

    # F. Recent study activity (only if student has logged sessions overall)
    all_sessions = fetch_sessions(db_path=db_path)
    if all_sessions:
        week_ago = ref_date - timedelta(days=6)
        recent_subj = fetch_sessions(
            start_date=week_ago, end_date=ref_date, subject_id=subject_id, db_path=db_path
        )
        recent_mins = sum(int(s["duration_minutes"]) for s in recent_subj)
        if recent_mins < 60:
            score += SUBJECT_PRIORITY_WEIGHTS["low_recent_study"]
            reasons.append("Limited study time recorded in the last 7 days")

    if score >= 40:
        priority_label = "High"
    elif score >= 15:
        priority_label = "Medium"
    else:
        priority_label = "Low"

    if not reasons:
        reasons.append("Regular balanced revision")

    return {
        "subject_id": subject_id,
        "subject_name": subj["subject_name"],
        "score": score,
        "priority": priority_label,
        "reasons": reasons,
        "urgent_assignment": urgent_assign,
    }


def get_subject_priority_reasons(
    current_date: Optional[date] = None,
    exam_subject_ids: Optional[List[int]] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Return sorted priority breakdown for all active subjects."""
    subjects = [
        s for s in list_subjects(db_path=db_path) if s["status"] != "Completed"
    ]
    results = [
        calculate_subject_priority(
            int(s["id"]),
            current_date=current_date,
            exam_subject_ids=exam_subject_ids,
            db_path=db_path,
        )
        for s in subjects
    ]
    results.sort(key=lambda r: (-r["score"], r["subject_name"].lower()))
    return results


def normalize_subject_priorities(
    priority_data: Any,
    subjects: Optional[List[Dict[str, Any]]] = None,
    sessions: Optional[List[Dict[str, Any]]] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Normalize any subject priority or allocation data into a canonical list of presentation dicts.

    Canonical output format per subject:
    {
        "subject_id": int,
        "subject_name": str,
        "score": float,
        "priority": str ("High" | "Medium" | "Low"),
        "reasons": List[str],
        "sessions": int,
        "minutes": int,
        "hours": float,
    }
    """
    if priority_data is None:
        return []

    # Prepare subjects lookup maps
    if subjects is None:
        try:
            subjects = list_subjects(db_path=db_path)
        except Exception:
            subjects = []

    id_map: Dict[int, Dict[str, Any]] = {
        int(s["id"]): s for s in (subjects or []) if "id" in s
    }
    name_map: Dict[str, Dict[str, Any]] = {
        str(s["subject_name"]).strip().lower(): s for s in (subjects or []) if "subject_name" in s
    }

    # Pre-calculate session statistics if session list is provided
    sess_counts: Dict[int, int] = {}
    sess_mins: Dict[int, int] = {}
    sess_counts_by_name: Dict[str, int] = {}
    sess_mins_by_name: Dict[str, int] = {}

    if sessions and isinstance(sessions, list):
        for s in sessions:
            if isinstance(s, dict):
                sid = s.get("subject_id")
                sname = str(s.get("subject_name") or "").strip().lower()
                dur = int(s.get("duration_minutes") or 0)
                if sid is not None:
                    try:
                        sid_int = int(sid)
                        sess_counts[sid_int] = sess_counts.get(sid_int, 0) + 1
                        sess_mins[sid_int] = sess_mins.get(sid_int, 0) + dur
                    except (ValueError, TypeError):
                        pass
                if sname:
                    sess_counts_by_name[sname] = sess_counts_by_name.get(sname, 0) + 1
                    sess_mins_by_name[sname] = sess_mins_by_name.get(sname, 0) + dur

    raw_items: List[Any] = []
    if isinstance(priority_data, dict):
        if "subject_name" in priority_data or "subject_id" in priority_data:
            raw_items = [priority_data]
        else:
            for k, v in priority_data.items():
                raw_items.append((k, v))
    elif isinstance(priority_data, (list, tuple, set)):
        raw_items = list(priority_data)
    else:
        return []

    if not raw_items:
        return []

    normalized: List[Dict[str, Any]] = []

    for item in raw_items:
        sid: Optional[int] = None
        sname: Optional[str] = None
        score: float = 0.0
        priority_label: Optional[str] = None
        reasons: List[str] = []
        item_sessions: Optional[int] = None
        item_minutes: Optional[int] = None

        if isinstance(item, tuple) and len(item) == 2:
            key, val = item
            if isinstance(key, int) or (isinstance(key, str) and key.isdigit()):
                sid = int(key)
                if sid in id_map:
                    sname = id_map[sid]["subject_name"]
            else:
                sname = str(key).strip()
                k_lower = sname.lower()
                if k_lower in name_map:
                    sid = int(name_map[k_lower]["id"])
                    sname = name_map[k_lower]["subject_name"]

            if isinstance(val, dict):
                score = float(val.get("score") or 0.0)
                priority_label = val.get("priority")
                if isinstance(val.get("reasons"), list):
                    reasons = [str(r) for r in val["reasons"] if r]
                item_sessions = val.get("sessions")
                item_minutes = val.get("minutes")
            elif isinstance(val, (int, float)):
                if sid and sid in id_map:
                    try:
                        p_calc = calculate_subject_priority(sid, db_path=db_path)
                        score = float(p_calc.get("score") or 0.0)
                        priority_label = p_calc.get("priority")
                        reasons = p_calc.get("reasons") or []
                    except Exception:
                        score = float(val)
                else:
                    score = float(val)

        elif isinstance(item, str):
            sname = item.strip()
            k_lower = sname.lower()
            if k_lower in name_map:
                sid = int(name_map[k_lower]["id"])
                sname = name_map[k_lower]["subject_name"]
                try:
                    p_calc = calculate_subject_priority(sid, db_path=db_path)
                    score = float(p_calc.get("score") or 0.0)
                    priority_label = p_calc.get("priority")
                    reasons = p_calc.get("reasons") or []
                except Exception:
                    score = 0.0
            else:
                score = 0.0

        elif isinstance(item, dict):
            raw_sid = item.get("subject_id")
            if raw_sid is not None:
                try:
                    sid = int(raw_sid)
                except (ValueError, TypeError):
                    sid = None

            sname = item.get("subject_name")
            if not sname and sid and sid in id_map:
                sname = id_map[sid]["subject_name"]
            elif sname and not sid:
                k_lower = str(sname).strip().lower()
                if k_lower in name_map:
                    sid = int(name_map[k_lower]["id"])
                    sname = name_map[k_lower]["subject_name"]

            raw_score = item.get("score")
            if raw_score is not None:
                try:
                    score = float(raw_score)
                except (ValueError, TypeError):
                    score = 0.0
            elif sid and sid in id_map:
                try:
                    p_calc = calculate_subject_priority(sid, db_path=db_path)
                    score = float(p_calc.get("score") or 0.0)
                    priority_label = p_calc.get("priority")
                    reasons = p_calc.get("reasons") or []
                except Exception:
                    score = 0.0

            if not priority_label and item.get("priority"):
                priority_label = str(item["priority"])

            if not reasons and isinstance(item.get("reasons"), list):
                reasons = [str(r) for r in item["reasons"] if r]

            item_sessions = item.get("sessions")
            item_minutes = item.get("minutes")

        else:
            continue

        if not sname and not sid:
            continue

        final_sname = sname or f"Subject {sid}"
        final_sid = sid if sid is not None else 0

        if not priority_label:
            if score >= 40:
                priority_label = "High"
            elif score >= 15:
                priority_label = "Medium"
            else:
                priority_label = "Low"

        if item_sessions is not None:
            final_sessions = int(item_sessions)
        elif final_sid and final_sid in sess_counts:
            final_sessions = sess_counts[final_sid]
        elif final_sname.strip().lower() in sess_counts_by_name:
            final_sessions = sess_counts_by_name[final_sname.strip().lower()]
        else:
            final_sessions = 0

        if item_minutes is not None:
            final_minutes = int(item_minutes)
        elif final_sid and final_sid in sess_mins:
            final_minutes = sess_mins[final_sid]
        elif final_sname.strip().lower() in sess_mins_by_name:
            final_minutes = sess_mins_by_name[final_sname.strip().lower()]
        else:
            final_minutes = 0

        final_hours = round(final_minutes / 60.0, 2)

        if not reasons:
            reasons = ["Regular balanced revision"]

        normalized.append(
            {
                "subject_id": final_sid,
                "subject_name": final_sname,
                "score": round(score, 2),
                "priority": priority_label,
                "reasons": reasons,
                "sessions": final_sessions,
                "minutes": final_minutes,
                "hours": final_hours,
            }
        )

    normalized.sort(key=lambda r: (-r["score"], r["subject_name"].lower()))
    return normalized


def _subtract_blocked_intervals(
    window_start: int,
    window_end: int,
    blocked: List[Tuple[int, int]],
) -> List[Tuple[int, int]]:
    """Return sorted free [start, end) intervals within [window_start, window_end)."""
    free = [(window_start, window_end)]
    for b_start, b_end in blocked:
        next_free: List[Tuple[int, int]] = []
        for f_start, f_end in free:
            if not _intervals_overlap(f_start, f_end, b_start, b_end):
                next_free.append((f_start, f_end))
            else:
                if f_start < b_start:
                    next_free.append((f_start, b_start))
                if b_end < f_end:
                    next_free.append((b_end, f_end))
        free = next_free
    return [(s, e) for s, e in free if e > s]


def generate_weekly_timetable(
    current_date: Optional[date] = None,
    start_date: Optional[date] = None,
    availability_override: Optional[Dict[str, Any]] = None,
    exam_subject_ids: Optional[List[int]] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Generate a deterministic, constraint-safe weekly study timetable preview."""
    today = current_date or date.today()
    horizon_start = max(today, start_date or today)
    horizon_end = horizon_start + timedelta(days=TIMETABLE_HORIZON_DAYS - 1)

    avail = get_student_availability(db_path=db_path)
    if availability_override:
        avail.update(availability_override)

    available_days = set(avail.get("available_days") or [])
    win_start = _time_to_minutes(avail["preferred_start_time"])
    win_end = _time_to_minutes(avail["preferred_end_time"])
    daily_limit = int(avail["daily_available_minutes"])
    weekly_target = int(avail["weekly_study_target_minutes"])
    session_len = int(avail["session_duration_minutes"])
    break_len = int(avail["break_duration_minutes"])

    if win_end <= win_start:
        raise ValueError("Preferred end time must be after preferred start time.")
    if session_len <= 0:
        raise ValueError("Session duration must be greater than zero.")

    priorities = get_subject_priority_reasons(
        current_date=today, exam_subject_ids=exam_subject_ids, db_path=db_path
    )
    exam_info = get_exam_priority(
        current_date=today, exam_subject_ids=exam_subject_ids, db_path=db_path
    )

    empty_result = {
        "start_date": horizon_start.isoformat(),
        "end_date": horizon_end.isoformat(),
        "sessions": [],
        "total_generated_minutes": 0,
        "weekly_target_minutes": weekly_target,
        "remaining_target_minutes": weekly_target,
        "available_capacity_minutes": 0,
        "unscheduled_target_minutes": weekly_target,
        "capacity_warning": None,
        "subject_allocations": [],
        "subject_allocations_dict": {},
        "subject_priorities": priorities,
        "exam_recommendation": exam_info["general_recommendation"],
    }

    if not available_days:
        empty_result["capacity_warning"] = "No available study days selected."
        return empty_result
    if not priorities:
        empty_result["capacity_warning"] = (
            "No active subjects found. Add subjects (not marked Completed) to generate a timetable."
        )
        return empty_result
    if daily_limit <= 0 or weekly_target <= 0:
        empty_result["capacity_warning"] = (
            "Daily available minutes and weekly study target must be greater than zero."
        )
        return empty_result

    # Load existing manual/completed sessions and calendar events in the horizon
    existing_saved = get_saved_timetable(
        start_date=horizon_start, end_date=horizon_end, db_path=db_path
    )
    events = fetch_events_by_date_range(horizon_start, horizon_end, db_path=db_path)

    # Prepare topic queues per subject
    topic_queues: Dict[int, List[Dict[str, Any]]] = {
        p["subject_id"]: get_incomplete_topics(
            p["subject_id"], current_date=today, db_path=db_path
        )
        for p in priorities
    }
    topic_cursors: Dict[int, int] = {p["subject_id"]: 0 for p in priorities}
    subject_session_counts: Dict[int, int] = {p["subject_id"]: 0 for p in priorities}

    # Build weighted rotation queue: High priority gets 3 slots per cycle, Medium 2, Low 1
    weighted_queue: List[Dict[str, Any]] = []
    for p in priorities:
        reps = 3 if p["priority"] == "High" else (2 if p["priority"] == "Medium" else 1)
        for _ in range(reps):
            weighted_queue.append(p)
    queue_idx = 0

    generated_sessions: List[Dict[str, Any]] = []
    total_generated = 0

    for offset in range(TIMETABLE_HORIZON_DAYS):
        if total_generated >= weekly_target:
            break
        day_date = horizon_start + timedelta(days=offset)
        day_iso = day_date.isoformat()
        day_name = day_date.strftime("%A")

        if day_name not in available_days:
            continue

        # Check full-day calendar events
        day_events = [
            e
            for e in events
            if e["start_date"] <= day_iso <= (e.get("end_date") or e["start_date"])
        ]
        if any(not e.get("start_time") for e in day_events):
            continue

        # Blocked intervals from preserved Manual or Completed sessions + timed events
        blocked: List[Tuple[int, int]] = []
        existing_day_minutes = 0
        for ex in existing_saved:
            if ex["study_date"] == day_iso:
                # Preserve Manual and Completed entries as unavailable slots
                if ex["source"] == "Manual" or ex["status"] == "Completed":
                    s_m = _time_to_minutes(ex["start_time"])
                    e_m = _time_to_minutes(ex["end_time"])
                    blocked.append((s_m, e_m))
                    existing_day_minutes += max(0, e_m - s_m)

        for ev in day_events:
            if ev.get("start_time"):
                ev_s = _time_to_minutes(ev["start_time"])
                ev_e = ev_s + DEFAULT_TIMED_EVENT_BLOCK_MINUTES
                blocked.append((ev_s, ev_e))

        day_remaining_cap = max(0, daily_limit - existing_day_minutes)
        free_intervals = _subtract_blocked_intervals(win_start, win_end, blocked)
        used_subjects_today: set[int] = set()

        for f_start, f_end in free_intervals:
            cursor = f_start
            while cursor + session_len <= f_end:
                if total_generated + session_len > weekly_target:
                    break
                if day_remaining_cap < session_len:
                    break

                # Pick next subject from weighted queue, preferring one not yet scheduled today
                chosen = None
                for attempt in range(len(weighted_queue)):
                    cand = weighted_queue[(queue_idx + attempt) % len(weighted_queue)]
                    if cand["subject_id"] not in used_subjects_today or len(priorities) == 1:
                        chosen = cand
                        queue_idx = (queue_idx + attempt + 1) % len(weighted_queue)
                        break
                if chosen is None:
                    chosen = weighted_queue[queue_idx % len(weighted_queue)]
                    queue_idx = (queue_idx + 1) % len(weighted_queue)

                sid = chosen["subject_id"]
                used_subjects_today.add(sid)
                subject_session_counts[sid] += 1

                # Pick topic or urgent assignment title
                t_list = topic_queues[sid]
                topic_id = None
                topic_name = None
                if t_list:
                    t_idx = topic_cursors[sid] % len(t_list)
                    topic_obj = t_list[t_idx]
                    topic_id = int(topic_obj["id"])
                    topic_name = topic_obj["topic_name"]
                    topic_cursors[sid] += 1

                if chosen.get("urgent_assignment") and subject_session_counts[sid] == 1:
                    sess_title = f"Assignment: {chosen['urgent_assignment']}"
                elif topic_name:
                    sess_title = f"{chosen['subject_name']} — {topic_name}"
                else:
                    sess_title = f"{chosen['subject_name']} — General Revision"

                generated_sessions.append(
                    {
                        "subject_id": sid,
                        "subject_name": chosen["subject_name"],
                        "topic_id": topic_id,
                        "topic_name": topic_name,
                        "study_date": day_iso,
                        "day_name": day_name,
                        "start_time": _minutes_to_hhmm(cursor),
                        "end_time": _minutes_to_hhmm(cursor + session_len),
                        "duration_minutes": session_len,
                        "session_title": sess_title,
                        "priority": chosen["priority"],
                        "status": "Planned",
                        "source": "Generated",
                    }
                )

                total_generated += session_len
                day_remaining_cap -= session_len
                cursor += session_len + break_len

    # Calculate total feasible capacity across the horizon for capacity transparency
    total_feasible_capacity = 0
    for offset in range(TIMETABLE_HORIZON_DAYS):
        day_date = horizon_start + timedelta(days=offset)
        day_iso = day_date.isoformat()
        day_name = day_date.strftime("%A")

        if day_name not in available_days:
            continue

        day_events = [
            e
            for e in events
            if e["start_date"] <= day_iso <= (e.get("end_date") or e["start_date"])
        ]
        if any(not e.get("start_time") for e in day_events):
            continue

        blocked_cap: List[Tuple[int, int]] = []
        ex_mins = 0
        for ex in existing_saved:
            if ex["study_date"] == day_iso:
                if ex["source"] == "Manual" or ex["status"] == "Completed":
                    s_m = _time_to_minutes(ex["start_time"])
                    e_m = _time_to_minutes(ex["end_time"])
                    blocked_cap.append((s_m, e_m))
                    ex_mins += max(0, e_m - s_m)

        for ev in day_events:
            if ev.get("start_time"):
                ev_s = _time_to_minutes(ev["start_time"])
                ev_e = ev_s + DEFAULT_TIMED_EVENT_BLOCK_MINUTES
                blocked_cap.append((ev_s, ev_e))

        day_cap = max(0, daily_limit - ex_mins)
        day_free = _subtract_blocked_intervals(win_start, win_end, blocked_cap)
        for f_s, f_e in day_free:
            cur = f_s
            while cur + session_len <= f_e and day_cap >= session_len:
                total_feasible_capacity += session_len
                day_cap -= session_len
                cur += session_len + break_len

    remaining_target = max(0, weekly_target - total_generated)
    capacity_warning = None
    if remaining_target > 0:
        if total_feasible_capacity < weekly_target:
            capacity_warning = (
                f"Generated {total_generated // 60}h {total_generated % 60}m out of your "
                f"{weekly_target // 60}h {weekly_target % 60}m weekly target due to daily/break/event capacity. "
                f"Your selected study days and time window allow at most {total_feasible_capacity // 60}h {total_feasible_capacity % 60}m this week."
            )
        else:
            capacity_warning = (
                f"Generated {total_generated // 60}h {total_generated % 60}m out of your "
                f"{weekly_target // 60}h {weekly_target % 60}m weekly target due to daily/break/event capacity."
            )

    canonical_allocations = normalize_subject_priorities(
        priorities,
        sessions=generated_sessions,
        db_path=db_path,
    )

    allocations_dict = {
        item["subject_name"]: item["hours"]
        for item in canonical_allocations
    }

    return {
        "start_date": horizon_start.isoformat(),
        "end_date": horizon_end.isoformat(),
        "sessions": generated_sessions,
        "total_generated_minutes": total_generated,
        "weekly_target_minutes": weekly_target,
        "remaining_target_minutes": remaining_target,
        "available_capacity_minutes": total_feasible_capacity,
        "unscheduled_target_minutes": remaining_target,
        "capacity_warning": capacity_warning,
        "subject_allocations": canonical_allocations,
        "subject_allocations_dict": allocations_dict,
        "subject_priorities": priorities,
        "exam_recommendation": exam_info["general_recommendation"],
    }


def validate_timetable_slots(
    slots: List[Dict[str, Any]],
    db_path: Optional[Union[str, Path]] = None,
) -> None:
    """Validate that a list of timetable slots has valid times, relationships, and no overlaps."""
    by_day: Dict[str, List[Tuple[int, int]]] = {}
    for slot in slots:
        s_mins = _time_to_minutes(slot["start_time"])
        e_mins = _time_to_minutes(slot["end_time"])
        if e_mins <= s_mins:
            raise ValueError("Session end time must be later than start time.")
        if get_subject(slot["subject_id"], db_path=db_path) is None:
            raise ValueError(f"Subject ID {slot['subject_id']} does not exist.")
        if slot.get("topic_id") is not None:
            t = get_topic(slot["topic_id"], db_path=db_path)
            if t is None or int(t["subject_id"]) != int(slot["subject_id"]):
                raise ValueError("Selected topic does not belong to the selected subject.")

        day = slot["study_date"]
        for ex_s, ex_e in by_day.get(day, []):
            if _intervals_overlap(s_mins, e_mins, ex_s, ex_e):
                raise ValueError(f"Overlapping sessions detected on {day}.")
        by_day.setdefault(day, []).append((s_mins, e_mins))


def get_saved_timetable(
    start_date: Optional[Union[date, str]] = None,
    end_date: Optional[Union[date, str]] = None,
    subject_id: Optional[int] = None,
    status: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Fetch saved timetable sessions joined with subject and topic names."""
    clauses: List[str] = []
    params: List[Any] = []
    if start_date is not None:
        clauses.append("tt.study_date >= ?")
        params.append(_to_iso_date(start_date))
    if end_date is not None:
        clauses.append("tt.study_date <= ?")
        params.append(_to_iso_date(end_date))
    if subject_id is not None:
        clauses.append("tt.subject_id = ?")
        params.append(subject_id)
    if status is not None and status != "All":
        clauses.append("tt.status = ?")
        params.append(status)

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = fetch_all(
        f"""
        SELECT tt.*, s.subject_name, t.topic_name
        FROM timetable tt
        JOIN subjects s ON tt.subject_id = s.id
        LEFT JOIN topics t ON tt.topic_id = t.id
        {where_sql}
        ORDER BY tt.study_date ASC, tt.start_time ASC, tt.id ASC;
        """,
        tuple(params),
        db_path=db_path,
    )
    return [dict(r) for r in rows]


def has_generated_timetable_in_range(
    start_date: Union[date, str],
    end_date: Union[date, str],
    db_path: Optional[Union[str, Path]] = None,
) -> bool:
    """Return True if any Generated timetable entries already exist in the date range."""
    row = fetch_one(
        """
        SELECT id FROM timetable
        WHERE study_date >= ? AND study_date <= ? AND source = 'Generated'
        LIMIT 1;
        """,
        (_to_iso_date(start_date), _to_iso_date(end_date)),
        db_path=db_path,
    )
    return row is not None


def save_generated_timetable(
    sessions: List[Dict[str, Any]],
    start_date: Union[date, str],
    end_date: Union[date, str],
    replace_existing: bool = False,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Save generated timetable sessions atomically, preserving Manual and Completed entries."""
    start_iso = _to_iso_date(start_date)
    end_iso = _to_iso_date(end_date)

    if not replace_existing and has_generated_timetable_in_range(
        start_iso, end_iso, db_path=db_path
    ):
        raise ValueError(
            "A generated timetable already exists for this date range. Confirm replacement to overwrite it."
        )

    validate_timetable_slots(sessions, db_path=db_path)

    conn = get_connection(db_path)
    try:
        conn.execute("BEGIN;")
        if replace_existing:
            conn.execute(
                """
                DELETE FROM timetable
                WHERE study_date >= ? AND study_date <= ?
                  AND source = 'Generated' AND status != 'Completed';
                """,
                (start_iso, end_iso),
            )

        existing_rows = conn.execute(
            """
            SELECT study_date, start_time, end_time FROM timetable
            WHERE study_date >= ? AND study_date <= ?;
            """,
            (start_iso, end_iso),
        ).fetchall()

        now = _now_iso()
        inserted = 0
        for s in sessions:
            s_m = _time_to_minutes(s["start_time"])
            e_m = _time_to_minutes(s["end_time"])
            conflict = any(
                ex["study_date"] == s["study_date"]
                and _intervals_overlap(
                    s_m, e_m, _time_to_minutes(ex["start_time"]), _time_to_minutes(ex["end_time"])
                )
                for ex in existing_rows
            )
            if conflict:
                continue

            conn.execute(
                """
                INSERT INTO timetable (
                    subject_id, topic_id, study_date, start_time, end_time,
                    session_title, priority, status, source, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 'Planned', 'Generated', ?, ?);
                """,
                (
                    s["subject_id"],
                    s.get("topic_id"),
                    s["study_date"],
                    s["start_time"],
                    s["end_time"],
                    s.get("session_title"),
                    s.get("priority", "Medium"),
                    now,
                    now,
                ),
            )
            inserted += 1

        conn.commit()
        return inserted
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _check_overlap_with_saved(
    study_date_iso: str,
    start_hhmm: str,
    end_hhmm: str,
    exclude_id: Optional[int] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> None:
    """Raise ValueError if [start_hhmm, end_hhmm) overlaps an existing saved session."""
    s_m = _time_to_minutes(start_hhmm)
    e_m = _time_to_minutes(end_hhmm)
    day_sessions = get_saved_timetable(
        start_date=study_date_iso, end_date=study_date_iso, db_path=db_path
    )
    for ex in day_sessions:
        if exclude_id is not None and int(ex["id"]) == int(exclude_id):
            continue
        if _intervals_overlap(
            s_m, e_m, _time_to_minutes(ex["start_time"]), _time_to_minutes(ex["end_time"])
        ):
            raise ValueError(
                f"Time slot {start_hhmm}–{end_hhmm} overlaps with existing session "
                f"'{ex.get('session_title') or ex['subject_name']}' ({ex['start_time']}–{ex['end_time']})."
            )


def add_manual_session(
    subject_id: int,
    study_date: Union[date, str],
    start_time: Union[time, str],
    end_time: Union[time, str],
    topic_id: Optional[int] = None,
    session_title: Optional[str] = None,
    priority: str = "Medium",
    enforce_availability: bool = True,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Validate and add a manual timetable session."""
    if get_subject(subject_id, db_path=db_path) is None:
        raise ValueError("Selected subject does not exist.")
    if priority not in VALID_PRIORITIES:
        raise ValueError(f"Invalid priority: {priority}")

    date_iso = _to_iso_date(study_date)
    s_m = _time_to_minutes(start_time)
    e_m = _time_to_minutes(end_time)
    if e_m <= s_m:
        raise ValueError("End time must be later than start time.")

    start_hhmm = _minutes_to_hhmm(s_m)
    end_hhmm = _minutes_to_hhmm(e_m)

    if enforce_availability:
        avail = get_student_availability(db_path=db_path)
        win_s = _time_to_minutes(avail["preferred_start_time"])
        win_e = _time_to_minutes(avail["preferred_end_time"])
        if s_m < win_s or e_m > win_e:
            raise ValueError(
                f"Manual session ({start_hhmm}–{end_hhmm}) falls outside your availability window "
                f"({avail['preferred_start_time']}–{avail['preferred_end_time']})."
            )

    _check_overlap_with_saved(date_iso, start_hhmm, end_hhmm, db_path=db_path)

    clean_title = session_title.strip() if session_title and session_title.strip() else None
    return save_timetable_entry(
        subject_id=subject_id,
        study_date=date_iso,
        start_time=start_hhmm,
        end_time=end_hhmm,
        topic_id=topic_id,
        session_title=clean_title,
        priority=priority,
        status="Planned",
        source="Manual",
        db_path=db_path,
    )


def update_timetable_session(
    session_id: int,
    subject_id: int,
    study_date: Union[date, str],
    start_time: Union[time, str],
    end_time: Union[time, str],
    topic_id: Optional[int] = None,
    session_title: Optional[str] = None,
    priority: str = "Medium",
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Edit a saved timetable session, converting Generated source to Manual."""
    existing = fetch_one(
        "SELECT * FROM timetable WHERE id = ?;", (session_id,), db_path=db_path
    )
    if existing is None:
        raise ValueError(f"Timetable session ID {session_id} does not exist.")
    if existing["status"] == "Completed":
        raise ValueError("Completed timetable sessions are protected and cannot be edited.")
    if get_subject(subject_id, db_path=db_path) is None:
        raise ValueError("Selected subject does not exist.")
    if topic_id is not None:
        t = get_topic(topic_id, db_path=db_path)
        if t is None or int(t["subject_id"]) != int(subject_id):
            raise ValueError("Selected topic does not belong to the selected subject.")

    date_iso = _to_iso_date(study_date)
    s_m = _time_to_minutes(start_time)
    e_m = _time_to_minutes(end_time)
    if e_m <= s_m:
        raise ValueError("End time must be later than start time.")

    start_hhmm = _minutes_to_hhmm(s_m)
    end_hhmm = _minutes_to_hhmm(e_m)
    _check_overlap_with_saved(
        date_iso, start_hhmm, end_hhmm, exclude_id=session_id, db_path=db_path
    )

    execute_query(
        """
        UPDATE timetable
        SET subject_id = ?, topic_id = ?, study_date = ?, start_time = ?,
            end_time = ?, session_title = ?, priority = ?, source = 'Manual',
            updated_at = ?
        WHERE id = ?;
        """,
        (
            subject_id,
            topic_id,
            date_iso,
            start_hhmm,
            end_hhmm,
            session_title.strip() if session_title else None,
            priority,
            _now_iso(),
            session_id,
        ),
        db_path=db_path,
    )
    return session_id


def delete_timetable_session(
    session_id: int,
    db_path: Optional[Union[str, Path]] = None,
) -> None:
    """Delete a timetable session (protects Completed sessions)."""
    existing = fetch_one(
        "SELECT status FROM timetable WHERE id = ?;", (session_id,), db_path=db_path
    )
    if existing is not None and existing["status"] == "Completed":
        raise ValueError("Completed timetable sessions are protected and cannot be deleted.")
    execute_query("DELETE FROM timetable WHERE id = ?;", (session_id,), db_path=db_path)


def update_session_status(
    session_id: int,
    new_status: str,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Update a timetable session's status (does not auto-create study_sessions)."""
    if new_status not in VALID_TIMETABLE_STATUSES:
        raise ValueError(f"Invalid timetable status: {new_status}")
    execute_query(
        "UPDATE timetable SET status = ?, updated_at = ? WHERE id = ?;",
        (new_status, _now_iso(), session_id),
        db_path=db_path,
    )
    return session_id


def calculate_weekly_scheduled_minutes(
    start_date: Union[date, str],
    end_date: Union[date, str],
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Return total scheduled minutes in the given date range."""
    sessions = get_saved_timetable(
        start_date=start_date, end_date=end_date, db_path=db_path
    )
    return sum(
        max(0, _time_to_minutes(s["end_time"]) - _time_to_minutes(s["start_time"]))
        for s in sessions
    )


def get_timetable_summary(
    start_date: Union[date, str],
    end_date: Union[date, str],
    db_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Return summary counts and scheduled hours for a week."""
    sessions = get_saved_timetable(
        start_date=start_date, end_date=end_date, db_path=db_path
    )
    total_mins = calculate_weekly_scheduled_minutes(
        start_date=start_date, end_date=end_date, db_path=db_path
    )
    return {
        "total_planned": sum(1 for s in sessions if s["status"] == "Planned"),
        "completed": sum(1 for s in sessions if s["status"] == "Completed"),
        "skipped": sum(1 for s in sessions if s["status"] == "Skipped"),
        "total_sessions": len(sessions),
        "scheduled_hours": round(total_mins / 60.0, 2),
    }
