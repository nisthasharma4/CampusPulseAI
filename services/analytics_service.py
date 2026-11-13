"""Business logic, aggregations, and data exports for Step 10 Progress Analytics."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from database.db import fetch_all, fetch_one
from services.academic_service import (
    calculate_overall_academic_average,
    calculate_overall_weighted_attendance,
    get_attendance_summary_all_subjects,
    get_attendance_target,
    get_subject_marks_summary,
)
from services.profile_service import get_profile
from services.study_service import fetch_sessions, format_minutes_hm
from services.subject_service import get_subject_progress, list_subjects
from utils.validators import validate_date_range


def _to_iso_date(value: Optional[Union[date, str]]) -> Optional[str]:
    """Convert date or non-empty string to YYYY-MM-DD, or return None."""
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    return text if text else None


def _parse_iso_date(value: Optional[str]) -> Optional[date]:
    """Parse YYYY-MM-DD string into date object, or return None."""
    if not value:
        return None
    return date.fromisoformat(str(value).strip()[:10])


def get_date_range(
    filter_name: str,
    reference_date: Optional[date] = None,
    custom_start: Optional[date] = None,
    custom_end: Optional[date] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """Resolve a date filter preset into inclusive ISO-8601 (start_date, end_date) strings."""
    today = reference_date or date.today()

    if filter_name == "All Time":
        return None, None
    if filter_name == "Today":
        iso = today.isoformat()
        return iso, iso
    if filter_name == "Last 7 Days":
        return (today - timedelta(days=6)).isoformat(), today.isoformat()
    if filter_name == "Last 30 Days":
        return (today - timedelta(days=29)).isoformat(), today.isoformat()
    if filter_name == "This Week":
        # Monday to Sunday calendar week
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        return monday.isoformat(), sunday.isoformat()
    if filter_name == "Previous Week":
        last_monday = today - timedelta(days=today.weekday() + 7)
        last_sunday = last_monday + timedelta(days=6)
        return last_monday.isoformat(), last_sunday.isoformat()
    if filter_name == "This Month":
        first_day = today.replace(day=1)
        # End of current month
        next_month = (first_day + timedelta(days=32)).replace(day=1)
        last_day = next_month - timedelta(days=1)
        return first_day.isoformat(), last_day.isoformat()
    if filter_name == "Previous Month":
        first_this = today.replace(day=1)
        last_prev = first_this - timedelta(days=1)
        first_prev = last_prev.replace(day=1)
        return first_prev.isoformat(), last_prev.isoformat()
    if filter_name == "Last 3 Months":
        return (today - timedelta(days=90)).isoformat(), today.isoformat()
    if filter_name == "Custom Date Range":
        if custom_start and custom_end:
            ok, msg = validate_date_range(custom_start, custom_end, "Start Date", "End Date")
            if not ok:
                raise ValueError(msg)
            return custom_start.isoformat(), custom_end.isoformat()
        return _to_iso_date(custom_start), _to_iso_date(custom_end)

    return None, None


def get_study_summary(
    start_date: Optional[Union[date, str]] = None,
    end_date: Optional[Union[date, str]] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Calculate overall study metrics for sessions within the inclusive date range."""
    s_iso = _to_iso_date(start_date)
    e_iso = _to_iso_date(end_date)
    sessions = fetch_sessions(start_date=s_iso, end_date=e_iso, db_path=db_path)

    total_sessions = len(sessions)
    total_minutes = sum(int(s["duration_minutes"]) for s in sessions)
    avg_minutes = round(total_minutes / total_sessions, 1) if total_sessions > 0 else 0.0

    completed_sessions = sum(1 for s in sessions if s.get("status") == "Completed")
    partially_completed = sum(1 for s in sessions if s.get("status") == "Partially Completed")
    not_completed = sum(1 for s in sessions if s.get("status") == "Not Completed")

    distinct_study_days = len({s["study_date"] for s in sessions if s.get("study_date")})

    # Average daily study hours across active days
    avg_daily_hours = (
        round((total_minutes / 60.0) / distinct_study_days, 2)
        if distinct_study_days > 0
        else 0.0
    )

    return {
        "start_date": s_iso,
        "end_date": e_iso,
        "total_sessions": total_sessions,
        "completed_sessions": completed_sessions,
        "partially_completed_sessions": partially_completed,
        "not_completed_sessions": not_completed,
        "total_minutes": total_minutes,
        "total_hours": round(total_minutes / 60.0, 2),
        "formatted_study_time": format_minutes_hm(total_minutes),
        "average_session_minutes": avg_minutes,
        "distinct_study_days": distinct_study_days,
        "average_daily_study_hours": avg_daily_hours,
    }


def get_daily_study_minutes(
    start_date: Optional[Union[date, str]] = None,
    end_date: Optional[Union[date, str]] = None,
    fill_missing_days: bool = True,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Return day-by-day recorded study minutes, optionally filling 0-hour days in date range."""
    s_iso = _to_iso_date(start_date)
    e_iso = _to_iso_date(end_date)
    sessions = fetch_sessions(start_date=s_iso, end_date=e_iso, db_path=db_path)

    daily_totals: Dict[str, int] = {}
    daily_counts: Dict[str, int] = {}
    for s in sessions:
        dt = s.get("study_date")
        if not dt:
            continue
        daily_totals[dt] = daily_totals.get(dt, 0) + int(s["duration_minutes"])
        daily_counts[dt] = daily_counts.get(dt, 0) + 1

    if fill_missing_days and s_iso and e_iso:
        s_d = _parse_iso_date(s_iso)
        e_d = _parse_iso_date(e_iso)
        if s_d and e_d and s_d <= e_d:
            cur = s_d
            # Limit fill range to maximum 180 days to avoid UI blow-up
            if (e_d - s_d).days <= 180:
                while cur <= e_d:
                    cur_iso = cur.isoformat()
                    if cur_iso not in daily_totals:
                        daily_totals[cur_iso] = 0
                        daily_counts[cur_iso] = 0
                    cur += timedelta(days=1)

    results: List[Dict[str, Any]] = []
    for dt in sorted(daily_totals.keys()):
        mins = daily_totals[dt]
        results.append(
            {
                "study_date": dt,
                "minutes": mins,
                "hours": round(mins / 60.0, 2),
                "sessions_count": daily_counts.get(dt, 0),
            }
        )
    return results


def get_weekly_study_summary(
    start_date: Optional[Union[date, str]] = None,
    end_date: Optional[Union[date, str]] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Aggregate recorded study time by calendar week (Monday–Sunday)."""
    s_iso = _to_iso_date(start_date)
    e_iso = _to_iso_date(end_date)
    sessions = fetch_sessions(start_date=s_iso, end_date=e_iso, db_path=db_path)

    weeks: Dict[str, Dict[str, Any]] = {}
    for s in sessions:
        dt_str = s.get("study_date")
        if not dt_str:
            continue
        d = _parse_iso_date(dt_str)
        if not d:
            continue
        mon = d - timedelta(days=d.weekday())
        sun = mon + timedelta(days=6)
        label = f"Week {mon.strftime('%b %d')}–{sun.strftime('%b %d, %Y')}"
        key = mon.isoformat()

        if key not in weeks:
            weeks[key] = {
                "week_start": mon.isoformat(),
                "week_end": sun.isoformat(),
                "week_label": label,
                "total_minutes": 0,
                "sessions_count": 0,
            }
        weeks[key]["total_minutes"] += int(s["duration_minutes"])
        weeks[key]["sessions_count"] += 1

    results: List[Dict[str, Any]] = []
    for key in sorted(weeks.keys()):
        w = weeks[key]
        results.append(
            {
                "week_start": w["week_start"],
                "week_end": w["week_end"],
                "week_label": w["week_label"],
                "total_minutes": w["total_minutes"],
                "hours": round(w["total_minutes"] / 60.0, 2),
                "sessions_count": w["sessions_count"],
            }
        )
    return results


def get_monthly_study_summary(
    start_date: Optional[Union[date, str]] = None,
    end_date: Optional[Union[date, str]] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Aggregate recorded study time by calendar month."""
    s_iso = _to_iso_date(start_date)
    e_iso = _to_iso_date(end_date)
    sessions = fetch_sessions(start_date=s_iso, end_date=e_iso, db_path=db_path)

    months: Dict[str, Dict[str, Any]] = {}
    for s in sessions:
        dt_str = s.get("study_date")
        if not dt_str:
            continue
        d = _parse_iso_date(dt_str)
        if not d:
            continue
        key = d.strftime("%Y-%m")
        label = d.strftime("%B %Y")
        if key not in months:
            months[key] = {
                "month_key": key,
                "month_label": label,
                "total_minutes": 0,
                "sessions_count": 0,
            }
        months[key]["total_minutes"] += int(s["duration_minutes"])
        months[key]["sessions_count"] += 1

    results: List[Dict[str, Any]] = []
    for key in sorted(months.keys()):
        m = months[key]
        results.append(
            {
                "month_key": m["month_key"],
                "month_label": m["month_label"],
                "total_minutes": m["total_minutes"],
                "hours": round(m["total_minutes"] / 60.0, 2),
                "sessions_count": m["sessions_count"],
            }
        )
    return results


def get_subject_study_summary(
    start_date: Optional[Union[date, str]] = None,
    end_date: Optional[Union[date, str]] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Aggregate study time and session counts per subject, including 0-hour subjects."""
    s_iso = _to_iso_date(start_date)
    e_iso = _to_iso_date(end_date)
    subjects = list_subjects(db_path=db_path)
    sessions = fetch_sessions(start_date=s_iso, end_date=e_iso, db_path=db_path)

    by_subj: Dict[int, Dict[str, int]] = {}
    total_all_minutes = 0
    for s in sessions:
        sid = int(s["subject_id"])
        mins = int(s["duration_minutes"])
        total_all_minutes += mins
        if sid not in by_subj:
            by_subj[sid] = {"minutes": 0, "count": 0}
        by_subj[sid]["minutes"] += mins
        by_subj[sid]["count"] += 1

    results: List[Dict[str, Any]] = []
    for subj in subjects:
        sid = int(subj["id"])
        stat = by_subj.get(sid, {"minutes": 0, "count": 0})
        mins = stat["minutes"]
        cnt = stat["count"]
        pct = round((mins / total_all_minutes) * 100, 1) if total_all_minutes > 0 else 0.0
        results.append(
            {
                "subject_id": sid,
                "subject_name": subj["subject_name"],
                "subject_code": subj.get("subject_code"),
                "total_minutes": mins,
                "total_hours": round(mins / 60.0, 2),
                "formatted_time": format_minutes_hm(mins),
                "session_count": cnt,
                "avg_session_minutes": round(mins / cnt, 1) if cnt > 0 else 0.0,
                "study_time_percentage": pct,
            }
        )
    results.sort(key=lambda x: (x["total_minutes"], x["subject_name"]), reverse=True)
    return results


def get_topic_study_summary(
    subject_id: Optional[int] = None,
    start_date: Optional[Union[date, str]] = None,
    end_date: Optional[Union[date, str]] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Aggregate actual study hours per topic, preserving historical sessions with NULL topic_id."""
    s_iso = _to_iso_date(start_date)
    e_iso = _to_iso_date(end_date)
    sessions = fetch_sessions(
        start_date=s_iso, end_date=e_iso, subject_id=subject_id, db_path=db_path
    )

    where_topic = "WHERE t.subject_id = ?" if subject_id is not None else ""
    topic_rows = fetch_all(
        f"""
        SELECT
            t.id AS topic_id,
            t.subject_id,
            s.subject_name,
            t.topic_name,
            t.start_date,
            t.completion_date,
            t.status,
            t.estimated_hours
        FROM topics t
        JOIN subjects s ON t.subject_id = s.id
        {where_topic}
        ORDER BY s.subject_name ASC, COALESCE(t.sequence_number, 999999) ASC, t.id ASC;
        """,
        (subject_id,) if subject_id is not None else (),
        db_path=db_path,
    )

    topic_stats: Dict[Optional[int], Dict[str, Any]] = {}
    for r in topic_rows:
        tid = int(r["topic_id"])
        topic_stats[tid] = {
            "topic_id": tid,
            "subject_id": int(r["subject_id"]),
            "subject_name": r["subject_name"],
            "topic_name": r["topic_name"],
            "start_date": r["start_date"],
            "completion_date": r["completion_date"],
            "status": r["status"],
            "estimated_hours": r["estimated_hours"],
            "total_minutes": 0,
            "session_count": 0,
        }

    null_topic_mins = 0
    null_topic_count = 0
    for s in sessions:
        tid = s.get("topic_id")
        mins = int(s["duration_minutes"])
        if tid is None:
            null_topic_mins += mins
            null_topic_count += 1
        elif tid in topic_stats:
            topic_stats[tid]["total_minutes"] += mins
            topic_stats[tid]["session_count"] += 1

    results: List[Dict[str, Any]] = []
    for item in topic_stats.values():
        mins = item["total_minutes"]
        results.append(
            {
                "topic_id": item["topic_id"],
                "subject_id": item["subject_id"],
                "subject_name": item["subject_name"],
                "topic_name": item["topic_name"],
                "start_date": item["start_date"],
                "completion_date": item["completion_date"],
                "status": item["status"],
                "estimated_hours": item["estimated_hours"],
                "total_minutes": mins,
                "total_hours": round(mins / 60.0, 2),
                "formatted_time": format_minutes_hm(mins),
                "session_count": item["session_count"],
            }
        )

    if null_topic_count > 0:
        results.append(
            {
                "topic_id": None,
                "subject_id": subject_id,
                "subject_name": "Multiple / Filtered" if subject_id is None else "Selected Subject",
                "topic_name": "Historical session — topic no longer available",
                "start_date": None,
                "completion_date": None,
                "status": "Historical",
                "estimated_hours": None,
                "total_minutes": null_topic_mins,
                "total_hours": round(null_topic_mins / 60.0, 2),
                "formatted_time": format_minutes_hm(null_topic_mins),
                "session_count": null_topic_count,
            }
        )

    return results


def get_topic_completion_duration(
    subject_id: Optional[int] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Compare calendar completion duration vs actual study hours for completed topics."""
    where_sql = "WHERE t.status = 'Completed'"
    params: List[Any] = []
    if subject_id is not None:
        where_sql += " AND t.subject_id = ?"
        params.append(subject_id)

    rows = fetch_all(
        f"""
        SELECT
            t.id AS topic_id,
            t.subject_id,
            s.subject_name,
            t.topic_name,
            t.start_date,
            t.completion_date,
            t.estimated_hours,
            COALESCE(SUM(ss.duration_minutes), 0) AS actual_minutes
        FROM topics t
        JOIN subjects s ON t.subject_id = s.id
        LEFT JOIN study_sessions ss ON t.id = ss.topic_id
        {where_sql}
        GROUP BY t.id
        ORDER BY t.completion_date DESC, t.id DESC;
        """,
        tuple(params),
        db_path=db_path,
    )

    results: List[Dict[str, Any]] = []
    for r in rows:
        start_d = _parse_iso_date(r["start_date"])
        comp_d = _parse_iso_date(r["completion_date"])
        days_taken: Optional[int] = None
        if start_d and comp_d:
            days_taken = max((comp_d - start_d).days + 1, 1)

        act_mins = int(r["actual_minutes"])
        act_hours = round(act_mins / 60.0, 2)
        est_hours = float(r["estimated_hours"]) if r["estimated_hours"] is not None else None

        results.append(
            {
                "topic_id": int(r["topic_id"]),
                "subject_id": int(r["subject_id"]),
                "subject_name": r["subject_name"],
                "topic_name": r["topic_name"],
                "start_date": r["start_date"],
                "completion_date": r["completion_date"],
                "calendar_days_taken": days_taken,
                "actual_study_minutes": act_mins,
                "actual_study_hours": act_hours,
                "estimated_hours": est_hours,
                "hours_variance": round(act_hours - est_hours, 2) if est_hours is not None else None,
            }
        )
    return results


def get_subject_completion_summary(
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Calculate syllabus completion percentage, calendar days, and total study hours per subject."""
    subjects = list_subjects(db_path=db_path)
    results: List[Dict[str, Any]] = []

    for s in subjects:
        sid = int(s["id"])
        prog = get_subject_progress(sid, db_path=db_path)
        start_d = _parse_iso_date(s.get("start_date"))
        comp_d = _parse_iso_date(s.get("completion_date"))
        days_taken: Optional[int] = None
        if start_d and comp_d:
            days_taken = max((comp_d - start_d).days + 1, 1)

        # Sum of actual study minutes for this subject
        act_mins_row = fetch_one(
            "SELECT COALESCE(SUM(duration_minutes), 0) FROM study_sessions WHERE subject_id = ?;",
            (sid,),
            db_path=db_path,
        )
        total_mins = int(act_mins_row[0]) if act_mins_row else 0

        results.append(
            {
                "subject_id": sid,
                "subject_name": s["subject_name"],
                "subject_code": s.get("subject_code"),
                "status": s.get("status") or "Not Started",
                "start_date": s.get("start_date"),
                "completion_date": s.get("completion_date"),
                "calendar_days_taken": days_taken,
                "total_topics": prog["total_topics"],
                "completed_topics": prog["completed_topics"],
                "in_progress_topics": prog["in_progress_topics"],
                "pending_topics": prog["pending_topics"],
                "syllabus_completion_percentage": prog["completion_percentage"],
                "total_study_minutes": total_mins,
                "total_study_hours": round(total_mins / 60.0, 2),
            }
        )
    return results


def calculate_study_streaks(
    reference_date: Optional[date] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Calculate longest and current consecutive study-recording streaks from distinct study dates."""
    today = reference_date or date.today()
    rows = fetch_all(
        "SELECT DISTINCT study_date FROM study_sessions ORDER BY study_date ASC;",
        db_path=db_path,
    )
    distinct_dates = [
        _parse_iso_date(r["study_date"])
        for r in rows
        if r["study_date"] and _parse_iso_date(r["study_date"])
    ]
    distinct_dates = [d for d in distinct_dates if d is not None and d <= today]

    if not distinct_dates:
        return {
            "longest_streak_days": 0,
            "current_streak_days": 0,
            "total_study_recording_days": 0,
            "streak_active_today": False,
        }

    # Calculate longest streak
    longest = 1
    current_run = 1
    for i in range(1, len(distinct_dates)):
        if (distinct_dates[i] - distinct_dates[i - 1]).days == 1:
            current_run += 1
            if current_run > longest:
                longest = current_run
        elif (distinct_dates[i] - distinct_dates[i - 1]).days > 1:
            current_run = 1

    # Calculate current streak ending today or yesterday
    date_set = set(distinct_dates)
    streak_active_today = today in date_set
    current_streak = 0
    anchor = today if streak_active_today else today - timedelta(days=1)

    while anchor in date_set:
        current_streak += 1
        anchor -= timedelta(days=1)

    return {
        "longest_streak_days": longest,
        "current_streak_days": current_streak,
        "total_study_recording_days": len(distinct_dates),
        "streak_active_today": streak_active_today,
    }


def get_daily_productivity_summary(
    start_date: Optional[Union[date, str]] = None,
    end_date: Optional[Union[date, str]] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Calculate separate productivity statistics for daily check-ins and individual study sessions."""
    s_iso = _to_iso_date(start_date)
    e_iso = _to_iso_date(end_date)

    where_ci = "WHERE 1=1"
    ci_params: List[Any] = []
    if s_iso:
        where_ci += " AND checkin_date >= ?"
        ci_params.append(s_iso)
    if e_iso:
        where_ci += " AND checkin_date <= ?"
        ci_params.append(e_iso)

    ci_rows = fetch_all(
        f"SELECT * FROM daily_checkins {where_ci} ORDER BY checkin_date ASC;",
        tuple(ci_params),
        db_path=db_path,
    )
    sessions = fetch_sessions(start_date=s_iso, end_date=e_iso, db_path=db_path)

    # Check-in ratings
    ci_ratings = [r["productivity_rating"] for r in ci_rows if r["productivity_rating"] is not None]
    avg_ci_rating = round(sum(ci_ratings) / len(ci_ratings), 2) if ci_ratings else None
    completed_goals = sum(1 for r in ci_rows if r["goal_completed"])
    incomplete_goals = len(ci_rows) - completed_goals
    goal_completion_rate = (
        round((completed_goals / len(ci_rows)) * 100, 1) if ci_rows else None
    )

    # Study session ratings
    sess_ratings = [
        s["productivity_rating"] for s in sessions if s.get("productivity_rating") is not None
    ]
    avg_sess_rating = round(sum(sess_ratings) / len(sess_ratings), 2) if sess_ratings else None

    # Daily trend combining distinct dates
    by_date: Dict[str, Dict[str, Any]] = {}
    for r in ci_rows:
        dt = r["checkin_date"]
        by_date.setdefault(dt, {})["checkin_rating"] = r["productivity_rating"]

    for s in sessions:
        dt = s.get("study_date")
        if not dt:
            continue
        pr = s.get("productivity_rating")
        if pr is not None:
            bucket = by_date.setdefault(dt, {})
            bucket.setdefault("session_ratings", []).append(pr)

    daily_trend: List[Dict[str, Any]] = []
    for dt in sorted(by_date.keys()):
        b = by_date[dt]
        s_rates = b.get("session_ratings") or []
        s_avg = round(sum(s_rates) / len(s_rates), 1) if s_rates else None
        daily_trend.append(
            {
                "date": dt,
                "checkin_rating": b.get("checkin_rating"),
                "session_rating_avg": s_avg,
            }
        )

    return {
        "checkin_count": len(ci_rows),
        "average_checkin_rating": avg_ci_rating,
        "completed_goals": completed_goals,
        "incomplete_goals": incomplete_goals,
        "goal_completion_rate": goal_completion_rate,
        "session_rating_count": len(sess_ratings),
        "average_session_rating": avg_sess_rating,
        "daily_trend": daily_trend,
    }


def get_academic_marks_summary(
    subject_id: Optional[int] = None,
    start_date: Optional[Union[date, str]] = None,
    end_date: Optional[Union[date, str]] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Calculate weighted academic marks summary, assessment type breakdowns, and chronologic history."""
    s_iso = _to_iso_date(start_date)
    e_iso = _to_iso_date(end_date)

    where_sql = "WHERE 1=1"
    params: List[Any] = []
    if subject_id is not None:
        where_sql += " AND m.subject_id = ?"
        params.append(subject_id)
    if s_iso:
        where_sql += " AND m.assessment_date >= ?"
        params.append(s_iso)
    if e_iso:
        where_sql += " AND m.assessment_date <= ?"
        params.append(e_iso)

    rows = fetch_all(
        f"""
        SELECT
            m.*,
            s.subject_name,
            s.subject_code
        FROM marks m
        JOIN subjects s ON m.subject_id = s.id
        {where_sql}
        ORDER BY m.assessment_date ASC, m.id ASC;
        """,
        tuple(params),
        db_path=db_path,
    )

    total_obtained = sum(float(r["marks_obtained"]) for r in rows)
    total_max = sum(float(r["maximum_marks"]) for r in rows)
    overall_pct = round((total_obtained / total_max) * 100, 2) if total_max > 0 else 0.0

    # Group by assessment type
    by_type: Dict[str, Dict[str, float]] = {}
    for r in rows:
        atype = r["assessment_type"]
        stat = by_type.setdefault(atype, {"obtained": 0.0, "max": 0.0, "count": 0})
        stat["obtained"] += float(r["marks_obtained"])
        stat["max"] += float(r["maximum_marks"])
        stat["count"] += 1

    type_summary: List[Dict[str, Any]] = []
    for atype, stat in sorted(by_type.items()):
        pct = round((stat["obtained"] / stat["max"]) * 100, 2) if stat["max"] > 0 else 0.0
        type_summary.append(
            {
                "assessment_type": atype,
                "assessment_count": stat["count"],
                "marks_obtained": round(stat["obtained"], 2),
                "maximum_marks": round(stat["max"], 2),
                "weighted_percentage": pct,
            }
        )

    history: List[Dict[str, Any]] = []
    for r in rows:
        pct = (
            round((float(r["marks_obtained"]) / float(r["maximum_marks"])) * 100, 2)
            if float(r["maximum_marks"]) > 0
            else 0.0
        )
        history.append(
            {
                "id": int(r["id"]),
                "subject_id": int(r["subject_id"]),
                "subject_name": r["subject_name"],
                "assessment_type": r["assessment_type"],
                "marks_obtained": float(r["marks_obtained"]),
                "maximum_marks": float(r["maximum_marks"]),
                "percentage": pct,
                "assessment_date": r["assessment_date"],
                "notes": r["notes"],
            }
        )

    # Subject-wise marks summary
    subj_summary = get_subject_marks_summary(db_path=db_path)
    if subject_id is not None:
        subj_summary = [s for s in subj_summary if s["subject_id"] == subject_id]

    return {
        "assessment_count": len(rows),
        "total_marks_obtained": round(total_obtained, 2),
        "total_maximum_marks": round(total_max, 2),
        "overall_weighted_percentage": overall_pct,
        "type_summary": type_summary,
        "history": history,
        "subject_marks_summary": subj_summary,
    }


def get_current_attendance_summary(
    db_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Return the current aggregate attendance snapshot and weighted overall percentage."""
    summary_list = get_attendance_summary_all_subjects(db_path=db_path)
    weighted_res = calculate_overall_weighted_attendance(db_path=db_path)
    target = get_attendance_target(db_path=db_path)
    total_held = sum(item["classes_held"] for item in summary_list)
    total_attended = sum(item["classes_attended"] for item in summary_list)
    total_missed = sum(item["missed_classes"] for item in summary_list)
    weighted_pct = (
        weighted_res["overall_percentage"]
        if isinstance(weighted_res, dict)
        else float(weighted_res)
    )

    return {
        "attendance_target": target,
        "overall_attendance_percentage": weighted_pct,
        "total_classes_held": total_held,
        "total_classes_attended": total_attended,
        "total_missed_classes": total_missed,
        "subject_attendance": summary_list,
        "is_snapshot": True,
        "limitation_note": (
            "Current database stores aggregate subject attendance counts. "
            "Metrics reflect the current recorded snapshot, not historical daily attendance."
        ),
    }


def get_assignment_analytics(
    start_date: Optional[Union[date, str]] = None,
    end_date: Optional[Union[date, str]] = None,
    current_date: Optional[date] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Calculate period-specific assignment creation/completion metrics and current overdue summary."""
    s_iso = _to_iso_date(start_date)
    e_iso = _to_iso_date(end_date)
    ref_d = current_date or date.today()
    ref_iso = ref_d.isoformat()

    where_sql = "WHERE 1=1"
    params: List[Any] = []
    if s_iso:
        # Use assigned_date when available, falling back to deadline_date
        where_sql += " AND COALESCE(a.assigned_date, a.deadline_date) >= ?"
        params.append(s_iso)
    if e_iso:
        where_sql += " AND COALESCE(a.assigned_date, a.deadline_date) <= ?"
        params.append(e_iso)

    rows = fetch_all(
        f"""
        SELECT
            a.*,
            s.subject_name
        FROM assignments a
        JOIN subjects s ON a.subject_id = s.id
        {where_sql}
        ORDER BY a.deadline_date ASC, a.id ASC;
        """,
        tuple(params),
        db_path=db_path,
    )

    total_assignments = len(rows)
    completed = sum(1 for r in rows if r["status"] == "Completed")
    in_progress = sum(1 for r in rows if r["status"] == "In Progress")
    pending = sum(1 for r in rows if r["status"] == "Pending")

    # Overdue assignments are pending/in-progress with deadline_date < current_date
    overdue = sum(
        1
        for r in rows
        if r["status"] != "Completed" and r["deadline_date"] < ref_iso
    )

    completion_pct = (
        round((completed / total_assignments) * 100, 1) if total_assignments > 0 else 0.0
    )

    # Subject-wise assignment breakdown
    by_subj: Dict[str, Dict[str, int]] = {}
    for r in rows:
        sname = r["subject_name"]
        stat = by_subj.setdefault(sname, {"total": 0, "completed": 0, "pending": 0})
        stat["total"] += 1
        if r["status"] == "Completed":
            stat["completed"] += 1
        else:
            stat["pending"] += 1

    subject_breakdown: List[Dict[str, Any]] = [
        {"subject_name": k, **v} for k, v in sorted(by_subj.items())
    ]

    return {
        "total_assignments": total_assignments,
        "completed_assignments": completed,
        "in_progress_assignments": in_progress,
        "pending_assignments": pending,
        "overdue_assignments": overdue,
        "completion_percentage": completion_pct,
        "subject_breakdown": subject_breakdown,
        "assignments": [dict(r) for r in rows],
    }


def get_timetable_analytics(
    start_date: Optional[Union[date, str]] = None,
    end_date: Optional[Union[date, str]] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Calculate timetable scheduling vs completion metrics for sessions in the date range."""
    s_iso = _to_iso_date(start_date)
    e_iso = _to_iso_date(end_date)

    where_sql = "WHERE 1=1"
    params: List[Any] = []
    if s_iso:
        where_sql += " AND t.study_date >= ?"
        params.append(s_iso)
    if e_iso:
        where_sql += " AND t.study_date <= ?"
        params.append(e_iso)

    rows = fetch_all(
        f"""
        SELECT
            t.*,
            s.subject_name
        FROM timetable t
        JOIN subjects s ON t.subject_id = s.id
        {where_sql}
        ORDER BY t.study_date ASC, t.start_time ASC;
        """,
        tuple(params),
        db_path=db_path,
    )

    total_sessions = len(rows)
    completed = sum(1 for r in rows if r["status"] == "Completed")
    skipped = sum(1 for r in rows if r["status"] == "Skipped")
    planned = sum(1 for r in rows if r["status"] == "Planned")

    completion_pct = (
        round((completed / total_sessions) * 100, 1) if total_sessions > 0 else 0.0
    )

    # Calculate scheduled minutes (from start_time and end_time)
    def _slot_mins(st: str, et: str) -> int:
        sh, sm = [int(x) for x in st.split(":")]
        eh, em = [int(x) for x in et.split(":")]
        return max((eh * 60 + em) - (sh * 60 + sm), 0)

    total_scheduled_mins = sum(_slot_mins(r["start_time"], r["end_time"]) for r in rows)

    # Subject-wise timetable stats
    by_subj: Dict[str, Dict[str, int]] = {}
    for r in rows:
        sname = r["subject_name"]
        stat = by_subj.setdefault(
            sname, {"scheduled": 0, "completed": 0, "skipped": 0, "planned": 0}
        )
        stat["scheduled"] += 1
        st = r["status"]
        if st == "Completed":
            stat["completed"] += 1
        elif st == "Skipped":
            stat["skipped"] += 1
        else:
            stat["planned"] += 1

    subject_breakdown = [
        {"subject_name": k, **v} for k, v in sorted(by_subj.items())
    ]

    return {
        "total_scheduled_sessions": total_sessions,
        "completed_sessions": completed,
        "skipped_sessions": skipped,
        "planned_sessions": planned,
        "completion_percentage": completion_pct,
        "scheduled_minutes": total_scheduled_mins,
        "scheduled_hours": round(total_scheduled_mins / 60.0, 2),
        "subject_breakdown": subject_breakdown,
        "sessions": [dict(r) for r in rows],
    }


def generate_progress_report(
    start_date: Optional[Union[date, str]] = None,
    end_date: Optional[Union[date, str]] = None,
    reference_date: Optional[date] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Compile a comprehensive progress report bundle for the selected date range."""
    s_iso = _to_iso_date(start_date)
    e_iso = _to_iso_date(end_date)
    ref_d = reference_date or date.today()

    profile = get_profile(db_path=db_path)
    student_name = profile["name"] if profile else "Student"

    study_summary = get_study_summary(s_iso, e_iso, db_path=db_path)
    daily_study = get_daily_study_minutes(s_iso, e_iso, fill_missing_days=True, db_path=db_path)
    subject_study = get_subject_study_summary(s_iso, e_iso, db_path=db_path)
    topic_study = get_topic_study_summary(start_date=s_iso, end_date=e_iso, db_path=db_path)
    topic_completion = get_topic_completion_duration(db_path=db_path)
    subject_completion = get_subject_completion_summary(db_path=db_path)
    streaks = calculate_study_streaks(reference_date=ref_d, db_path=db_path)
    productivity = get_daily_productivity_summary(s_iso, e_iso, db_path=db_path)
    academic = get_academic_marks_summary(start_date=s_iso, end_date=e_iso, db_path=db_path)
    attendance = get_current_attendance_summary(db_path=db_path)
    assignments = get_assignment_analytics(s_iso, e_iso, current_date=ref_d, db_path=db_path)
    timetable = get_timetable_analytics(s_iso, e_iso, db_path=db_path)

    # Count topics completed within selected date range
    topics_in_period = 0
    for tc in topic_completion:
        if tc["completion_date"]:
            if (not s_iso or tc["completion_date"] >= s_iso) and (
                not e_iso or tc["completion_date"] <= e_iso
            ):
                topics_in_period += 1

    # Overall syllabus completion across all active subjects
    total_syllabus_topics = sum(sc["total_topics"] for sc in subject_completion)
    total_completed_topics = sum(sc["completed_topics"] for sc in subject_completion)
    overall_syllabus_pct = (
        round((total_completed_topics / total_syllabus_topics) * 100, 1)
        if total_syllabus_topics > 0
        else 0.0
    )

    # Weekly target progress (only for current calendar week or full 7-day ranges)
    weekly_target_hours = float(profile["weekly_study_target"]) if profile else 14.0
    weekly_progress_pct = (
        round((study_summary["total_hours"] / weekly_target_hours) * 100, 1)
        if weekly_target_hours > 0
        else 0.0
    )

    return {
        "report_title": "CampusPulse AI — Student Progress Report",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "student_name": student_name,
        "start_date": s_iso,
        "end_date": e_iso,
        "overview": {
            "total_study_hours": study_summary["total_hours"],
            "average_daily_study_hours": study_summary["average_daily_study_hours"],
            "total_study_sessions": study_summary["total_sessions"],
            "completed_topics_in_period": topics_in_period,
            "active_subjects_count": len(subject_completion),
            "overall_syllabus_completion_pct": overall_syllabus_pct,
            "assignment_completion_pct": assignments["completion_percentage"],
            "weekly_target_progress_pct": weekly_progress_pct,
            "longest_streak_days": streaks["longest_streak_days"],
            "current_streak_days": streaks["current_streak_days"],
        },
        "study_summary": study_summary,
        "daily_study": daily_study,
        "subject_study": subject_study,
        "topic_study": topic_study,
        "topic_completion": topic_completion,
        "subject_completion": subject_completion,
        "streaks": streaks,
        "productivity": productivity,
        "academic": academic,
        "attendance": attendance,
        "assignments": assignments,
        "timetable": timetable,
    }


# ---------------------------------------------------------------------------
# Data Exports (CSV)
# ---------------------------------------------------------------------------


def export_study_history(
    start_date: Optional[Union[date, str]] = None,
    end_date: Optional[Union[date, str]] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Return study history sessions formatted for CSV export."""
    sessions = fetch_sessions(start_date=start_date, end_date=end_date, db_path=db_path)
    rows: List[Dict[str, Any]] = []
    for s in sessions:
        rows.append(
            {
                "Session ID": s["id"],
                "Study Date": s["study_date"],
                "Subject": s.get("subject_name", ""),
                "Topic": s.get("topic_name") or "General",
                "Duration (Minutes)": s["duration_minutes"],
                "Duration (Hours)": round(s["duration_minutes"] / 60.0, 2),
                "Start Time": s.get("start_time") or "",
                "End Time": s.get("end_time") or "",
                "Status": s.get("status") or "",
                "Productivity Rating": s.get("productivity_rating") or "",
                "Study Goal": s.get("study_goal") or "",
                "Completed Work": s.get("completed_work") or "",
                "Next Topic": s.get("next_topic") or "",
                "Notes": s.get("notes") or "",
            }
        )
    return rows


def export_subject_summary(
    start_date: Optional[Union[date, str]] = None,
    end_date: Optional[Union[date, str]] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Return subject-wise study and completion summary for CSV export."""
    items = get_subject_study_summary(start_date, end_date, db_path=db_path)
    rows: List[Dict[str, Any]] = []
    for item in items:
        rows.append(
            {
                "Subject ID": item["subject_id"],
                "Subject Name": item["subject_name"],
                "Subject Code": item.get("subject_code") or "",
                "Total Study Minutes": item["total_minutes"],
                "Total Study Hours": item["total_hours"],
                "Session Count": item["session_count"],
                "Average Session Minutes": item["avg_session_minutes"],
                "Study Time Percentage": f"{item['study_time_percentage']}%",
            }
        )
    return rows


def export_topic_summary(
    subject_id: Optional[int] = None,
    start_date: Optional[Union[date, str]] = None,
    end_date: Optional[Union[date, str]] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Return topic-wise study time summary for CSV export."""
    items = get_topic_study_summary(subject_id, start_date, end_date, db_path=db_path)
    rows: List[Dict[str, Any]] = []
    for item in items:
        rows.append(
            {
                "Topic ID": item["topic_id"] if item["topic_id"] is not None else "Historical",
                "Subject": item["subject_name"],
                "Topic Name": item["topic_name"],
                "Status": item["status"],
                "Start Date": item.get("start_date") or "",
                "Completion Date": item.get("completion_date") or "",
                "Total Study Minutes": item["total_minutes"],
                "Total Study Hours": item["total_hours"],
                "Session Count": item["session_count"],
            }
        )
    return rows
