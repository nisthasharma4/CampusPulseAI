"""Transparent Rule-Based AI Recommendation Engine for CampusPulse AI."""

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from services.academic_service import (
    fetch_marks_records,
    get_attendance_summary_all_subjects,
    get_attendance_target,
    get_subject_marks_summary,
)
from services.assignment_service import fetch_assignments
from services.profile_service import get_profile
from services.study_service import fetch_sessions, get_topic_study_summary, list_daily_checkins
from services.subject_service import get_subject_progress, list_subjects, list_topics
from utils.config import (
    MARKS_WEAK_THRESHOLD,
    PRODUCTIVITY_MIN_RECORDS,
    RECOMMENDATION_PRIORITY_SCORES,
    TOPIC_OVERDUE_WARNING,
    WEEKLY_STUDY_WARNING_RATIO,
)

PRIORITY_LABELS = (
    "High Priority",
    "Medium Priority",
    "Low Priority",
    "Positive Progress",
)

CATEGORY_LABELS = (
    "Academic",
    "Attendance",
    "Assignments",
    "Study Habits",
    "Topics and Syllabus",
)


def _make_rec(
    rec_id: str,
    category: str,
    title: str,
    description: str,
    reason: str,
    suggested_action: str,
    priority: str,
    priority_score: int,
    generated_at: str,
    target_page: str,
    related_subject_id: Optional[int] = None,
    related_assignment_id: Optional[int] = None,
    related_topic_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Build a standardized recommendation dictionary."""
    return {
        "id": rec_id,
        "category": category,
        "title": title,
        "description": description,
        "reason": reason,
        "suggested_action": suggested_action,
        "priority": priority,
        "priority_score": priority_score,
        "related_subject_id": related_subject_id,
        "related_assignment_id": related_assignment_id,
        "related_topic_id": related_topic_id,
        "target_page": target_page,
        "generated_at": generated_at,
    }


def _current_week_bounds(ref_date: date) -> tuple[date, date]:
    """Return Monday and Sunday dates of the week containing ref_date."""
    monday = ref_date - timedelta(days=ref_date.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def get_student_academic_summary(
    current_dt: Optional[datetime] = None,
    marks_threshold: float = MARKS_WEAK_THRESHOLD,
    db_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Collect a unified snapshot of real academic, study, and deadline metrics."""
    now = current_dt or datetime.now()
    profile = get_profile(db_path=db_path)
    subjects = list_subjects(db_path=db_path)
    att_summary = get_attendance_summary_all_subjects(db_path=db_path)
    marks_summary = get_subject_marks_summary(db_path=db_path)
    assignments = fetch_assignments(current_dt=now, db_path=db_path)

    week_start, week_end = _current_week_bounds(now.date())
    week_sessions = fetch_sessions(
        start_date=week_start, end_date=week_end, db_path=db_path
    )
    all_sessions = fetch_sessions(db_path=db_path)
    week_hours = round(
        sum(int(s["duration_minutes"]) for s in week_sessions) / 60.0, 2
    )
    weekly_target = (
        int(profile.get("weekly_study_target") or 0) if profile else 0
    )

    return {
        "has_profile": profile is not None,
        "total_subjects": len(subjects),
        "attendance_target": get_attendance_target(db_path=db_path),
        "marks_threshold": float(marks_threshold),
        "attendance_summary": att_summary,
        "marks_summary": marks_summary,
        "assignments": assignments,
        "week_hours": week_hours,
        "weekly_target": weekly_target,
        "total_sessions": len(all_sessions),
    }


def generate_academic_recommendations(
    current_dt: Optional[datetime] = None,
    marks_threshold: float = MARKS_WEAK_THRESHOLD,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Generate rule-based recommendations from subject-wise internal marks."""
    now = current_dt or datetime.now()
    gen_at = now.isoformat(timespec="seconds")
    marks_summary = get_subject_marks_summary(db_path=db_path)
    recs: List[Dict[str, Any]] = []

    for item in marks_summary:
        sid = item["subject_id"]
        sname = item["subject_name"]
        avg = item["weighted_percentage"]

        if avg is None:
            recs.append(
                _make_rec(
                    rec_id=f"academic-missing-{sid}",
                    category="Academic",
                    title=f"{sname}: Insufficient assessment information",
                    description=f"No assessment marks have been recorded for {sname} yet.",
                    reason="At least one recorded assessment is required to evaluate academic performance.",
                    suggested_action="Record quiz or internal assessment marks in Academic Performance.",
                    priority="Low Priority",
                    priority_score=RECOMMENDATION_PRIORITY_SCORES["general_study_improvement"],
                    generated_at=gen_at,
                    target_page="pages/4_Academic_Performance.py",
                    related_subject_id=sid,
                )
            )
            continue

        if avg < marks_threshold:
            recs.append(
                _make_rec(
                    rec_id=f"academic-low-{sid}",
                    category="Academic",
                    title=f"Your {sname} performance is below the configured academic target.",
                    description=f"Weighted marks average in {sname} is {avg:.1f}% (threshold: {marks_threshold:.0f}%).",
                    reason=f"{sname} weighted average ({avg:.1f}%) is below {marks_threshold:.0f}%.",
                    suggested_action="Spend additional time revising the subject and practise important questions.",
                    priority="High Priority",
                    priority_score=RECOMMENDATION_PRIORITY_SCORES["low_academic_marks"],
                    generated_at=gen_at,
                    target_page="pages/4_Academic_Performance.py",
                    related_subject_id=sid,
                )
            )
        else:
            recs.append(
                _make_rec(
                    rec_id=f"academic-good-{sid}",
                    category="Academic",
                    title=f"{sname}: Satisfactory academic performance",
                    description=f"Weighted marks average in {sname} is {avg:.1f}%, meeting the {marks_threshold:.0f}% target.",
                    reason=f"{sname} weighted average ({avg:.1f}%) is at or above {marks_threshold:.0f}%.",
                    suggested_action="Keep maintaining your current revision schedule.",
                    priority="Positive Progress",
                    priority_score=RECOMMENDATION_PRIORITY_SCORES["positive_progress"],
                    generated_at=gen_at,
                    target_page="pages/4_Academic_Performance.py",
                    related_subject_id=sid,
                )
            )

        # Dated performance trend comparison when >= 2 dated assessments exist
        dated_records = [
            r
            for r in fetch_marks_records(subject_id=sid, db_path=db_path)
            if r.get("assessment_date")
        ]
        if len(dated_records) >= 2:
            dated_sorted = sorted(dated_records, key=lambda r: (r["assessment_date"], r["id"]))
            earliest_pct = dated_sorted[0]["percentage"]
            latest_pct = dated_sorted[-1]["percentage"]
            if latest_pct - earliest_pct >= 5.0:
                recs.append(
                    _make_rec(
                        rec_id=f"academic-trend-up-{sid}",
                        category="Academic",
                        title=f"{sname}: Marks are improving",
                        description=f"Recent assessment ({latest_pct:.1f}%) improved compared to earlier ({earliest_pct:.1f}%).",
                        reason="Comparing dated assessment records shows an upward trend.",
                        suggested_action="Continue your current study approach for this subject.",
                        priority="Positive Progress",
                        priority_score=RECOMMENDATION_PRIORITY_SCORES["positive_progress"],
                        generated_at=gen_at,
                        target_page="pages/4_Academic_Performance.py",
                        related_subject_id=sid,
                    )
                )

    return recs


def generate_attendance_recommendations(
    current_dt: Optional[datetime] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Generate rule-based attendance recommendations using academic_service."""
    now = current_dt or datetime.now()
    gen_at = now.isoformat(timespec="seconds")
    target = get_attendance_target(db_path=db_path)
    att_summary = get_attendance_summary_all_subjects(target_percent=target, db_path=db_path)
    recs: List[Dict[str, Any]] = []

    for item in att_summary:
        sid = item["subject_id"]
        sname = item["subject_name"]
        pct = item["attendance_percentage"]
        status = item["status"]

        if pct is None:
            continue

        if status == "Needs Improvement":
            recs.append(
                _make_rec(
                    rec_id=f"attendance-low-{sid}",
                    category="Attendance",
                    title=f"Your {sname} attendance is {pct:.1f}%, below your configured target of {target:.0f}%.",
                    description=f"Attended {item['classes_attended']} of {item['classes_held']} classes. {item['required_info']['message']}",
                    reason=f"Attendance ({pct:.1f}%) is below your {target:.0f}% target.",
                    suggested_action="Attend upcoming classes regularly.",
                    priority="High Priority",
                    priority_score=RECOMMENDATION_PRIORITY_SCORES["attendance_below_target"],
                    generated_at=gen_at,
                    target_page="pages/4_Academic_Performance.py",
                    related_subject_id=sid,
                )
            )
        elif status == "Close to Target":
            recs.append(
                _make_rec(
                    rec_id=f"attendance-close-{sid}",
                    category="Attendance",
                    title=f"{sname} attendance ({pct:.1f}%) is close to your {target:.0f}% target.",
                    description=f"Attended {item['classes_attended']} of {item['classes_held']} classes.",
                    reason="Attendance is within the warning buffer above your target.",
                    suggested_action="Maintain consistent attendance to avoid falling below the required level.",
                    priority="Medium Priority",
                    priority_score=RECOMMENDATION_PRIORITY_SCORES["attendance_close_to_target"],
                    generated_at=gen_at,
                    target_page="pages/4_Academic_Performance.py",
                    related_subject_id=sid,
                )
            )
        elif status == "Good":
            recs.append(
                _make_rec(
                    rec_id=f"attendance-good-{sid}",
                    category="Attendance",
                    title=f"{sname}: Good attendance ({pct:.1f}%)",
                    description=f"Above your {target:.0f}% attendance target.",
                    reason=f"Attended {item['classes_attended']} of {item['classes_held']} classes.",
                    suggested_action="Keep attending classes consistently.",
                    priority="Positive Progress",
                    priority_score=RECOMMENDATION_PRIORITY_SCORES["positive_progress"],
                    generated_at=gen_at,
                    target_page="pages/4_Academic_Performance.py",
                    related_subject_id=sid,
                )
            )

    return recs


def generate_assignment_recommendations(
    current_dt: Optional[datetime] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Generate priority recommendations for incomplete assignments."""
    now = current_dt or datetime.now()
    gen_at = now.isoformat(timespec="seconds")
    assignments = fetch_assignments(current_dt=now, db_path=db_path)
    recs: List[Dict[str, Any]] = []

    for item in assignments:
        if item["status"] == "Completed":
            continue

        aid = int(item["id"])
        sid = int(item["subject_id"])
        title = item["title"]
        sname = item["subject_name"]
        state = item["reminder_state"]
        days_rem = item["days_remaining"]
        cat = state["category"]

        if cat == "Overdue":
            recs.append(
                _make_rec(
                    rec_id=f"assign-overdue-{aid}",
                    category="Assignments",
                    title=f"Overdue assignment: {title} ({sname})",
                    description=f"Deadline was {item['deadline_date']}.",
                    reason="This assignment has passed its submission deadline and is still incomplete.",
                    suggested_action="Complete and submit this assignment immediately.",
                    priority="High Priority",
                    priority_score=RECOMMENDATION_PRIORITY_SCORES["overdue_assignment"],
                    generated_at=gen_at,
                    target_page="pages/5_Assignments_Reminders.py",
                    related_subject_id=sid,
                    related_assignment_id=aid,
                )
            )
        elif cat == "Due Today":
            recs.append(
                _make_rec(
                    rec_id=f"assign-today-{aid}",
                    category="Assignments",
                    title=f"Your {title} ({sname}) is due today.",
                    description=f"Submission deadline: {item['deadline_date']} {item.get('deadline_time') or ''}.",
                    reason="Assignment deadline is today.",
                    suggested_action="Prioritize completing the remaining work today.",
                    priority="High Priority",
                    priority_score=RECOMMENDATION_PRIORITY_SCORES["assignment_due_today"],
                    generated_at=gen_at,
                    target_page="pages/5_Assignments_Reminders.py",
                    related_subject_id=sid,
                    related_assignment_id=aid,
                )
            )
        elif 1 <= days_rem <= 2:
            due_word = "tomorrow" if days_rem == 1 else "in 2 days"
            recs.append(
                _make_rec(
                    rec_id=f"assign-soon-{aid}",
                    category="Assignments",
                    title=f"Your {title} ({sname}) is due {due_word}.",
                    description=f"Deadline: {item['deadline_date']} ({item['priority']} Priority).",
                    reason=f"Only {days_rem} day(s) remaining before submission.",
                    suggested_action="Prioritize completing the remaining work before the deadline.",
                    priority="Medium Priority",
                    priority_score=RECOMMENDATION_PRIORITY_SCORES["assignment_due_soon"],
                    generated_at=gen_at,
                    target_page="pages/5_Assignments_Reminders.py",
                    related_subject_id=sid,
                    related_assignment_id=aid,
                )
            )
        elif 3 <= days_rem <= 7:
            recs.append(
                _make_rec(
                    rec_id=f"assign-week-{aid}",
                    category="Assignments",
                    title=f"Upcoming assignment: {title} ({sname}) due in {days_rem} days.",
                    description=f"Deadline: {item['deadline_date']}.",
                    reason="Assignment deadline is within the next 7 days.",
                    suggested_action="Plan a study block this week to finish it comfortably.",
                    priority="Low Priority",
                    priority_score=RECOMMENDATION_PRIORITY_SCORES["assignment_due_week"],
                    generated_at=gen_at,
                    target_page="pages/5_Assignments_Reminders.py",
                    related_subject_id=sid,
                    related_assignment_id=aid,
                )
            )

    return recs


def generate_study_recommendations(
    current_dt: Optional[datetime] = None,
    marks_threshold: float = MARKS_WEAK_THRESHOLD,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Analyze weekly study consistency and weak-subject study focus."""
    now = current_dt or datetime.now()
    gen_at = now.isoformat(timespec="seconds")
    recs: List[Dict[str, Any]] = []

    all_sessions = fetch_sessions(db_path=db_path)
    if not all_sessions:
        recs.append(
            _make_rec(
                rec_id="study-no-records",
                category="Study Habits",
                title="Start recording study sessions to receive personalized study insights.",
                description="No study sessions have been logged yet.",
                reason="Study consistency analysis requires at least one recorded study session.",
                suggested_action="Log your first study session in Daily Study Tracker.",
                priority="Low Priority",
                priority_score=RECOMMENDATION_PRIORITY_SCORES["general_study_improvement"],
                generated_at=gen_at,
                target_page="pages/3_Daily_Study_Tracker.py",
            )
        )
        return recs

    week_start, week_end = _current_week_bounds(now.date())
    week_sessions = fetch_sessions(start_date=week_start, end_date=week_end, db_path=db_path)
    week_hours = round(sum(int(s["duration_minutes"]) for s in week_sessions) / 60.0, 2)

    profile = get_profile(db_path=db_path)
    weekly_target = int(profile.get("weekly_study_target") or 0) if profile else 0

    if weekly_target > 0:
        if week_hours >= weekly_target:
            recs.append(
                _make_rec(
                    rec_id="study-weekly-met",
                    category="Study Habits",
                    title=f"Weekly study target achieved ({week_hours:.1f} / {weekly_target} hrs)!",
                    description="You have met or exceeded your weekly study goal.",
                    reason=f"Logged {week_hours:.1f} hours during the current Monday–Sunday week.",
                    suggested_action="Keep up the steady pace and review completed topics.",
                    priority="Positive Progress",
                    priority_score=RECOMMENDATION_PRIORITY_SCORES["positive_progress"],
                    generated_at=gen_at,
                    target_page="pages/3_Daily_Study_Tracker.py",
                )
            )
        elif week_hours < weekly_target * WEEKLY_STUDY_WARNING_RATIO:
            recs.append(
                _make_rec(
                    rec_id="study-weekly-low",
                    category="Study Habits",
                    title=f"You have completed {week_hours:.1f} study hours this week against your {weekly_target}-hour target.",
                    description="Current weekly study progress is below 70% of your weekly target.",
                    reason=f"Logged {week_hours:.1f} hours vs {weekly_target} hours target.",
                    suggested_action="Try adding a consistent daily study session.",
                    priority="Medium Priority",
                    priority_score=RECOMMENDATION_PRIORITY_SCORES["weekly_study_below_target"],
                    generated_at=gen_at,
                    target_page="pages/3_Daily_Study_Tracker.py",
                )
            )

    # Combined weak subject study recommendation (marks + attendance + weekly hours)
    marks_by_subj = {m["subject_id"]: m for m in get_subject_marks_summary(db_path=db_path)}
    att_by_subj = {a["subject_id"]: a for a in get_attendance_summary_all_subjects(db_path=db_path)}
    att_target = get_attendance_target(db_path=db_path)

    for sid, m in marks_by_subj.items():
        sname = m["subject_name"]
        avg = m["weighted_percentage"]
        att = att_by_subj.get(sid, {}).get("attendance_percentage")

        low_marks = avg is not None and avg < marks_threshold
        low_att = att is not None and att < att_target
        if not (low_marks and low_att):
            continue

        subj_week_mins = sum(
            int(s["duration_minutes"])
            for s in week_sessions
            if int(s["subject_id"]) == sid
        )
        subj_week_hrs = round(subj_week_mins / 60.0, 2)
        reason_parts = [
            f"assessment performance ({avg:.1f}%) and attendance ({att:.1f}%) are below target"
        ]
        if subj_week_hrs < 2.0:
            reason_parts.append(f"recent weekly study time is limited ({subj_week_hrs:.1f} hrs)")

        recs.append(
            _make_rec(
                rec_id=f"study-weak-combined-{sid}",
                category="Study Habits",
                title=f"{sname} requires additional attention.",
                description=f"Marks: {avg:.1f}%, Attendance: {att:.1f}%, Study time this week: {subj_week_hrs:.1f} hrs.",
                reason="Your " + ", while your ".join(reason_parts) + ".",
                suggested_action=f"Prioritize {sname} revision and schedule additional practice sessions.",
                priority="High Priority",
                priority_score=RECOMMENDATION_PRIORITY_SCORES["weak_subject_combined"],
                generated_at=gen_at,
                target_page="pages/3_Daily_Study_Tracker.py",
                related_subject_id=sid,
            )
        )

    return recs


def generate_topic_recommendations(
    current_dt: Optional[datetime] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Analyze syllabus topics for overdue dates, over-budget hours, or completion."""
    now = current_dt or datetime.now()
    today_iso = now.date().isoformat()
    gen_at = now.isoformat(timespec="seconds")
    subjects = list_subjects(db_path=db_path)
    topic_hours_map = {
        t["topic_id"]: t["total_hours"]
        for t in get_topic_study_summary(db_path=db_path)
    }
    recs: List[Dict[str, Any]] = []

    for subj in subjects:
        sid = int(subj["id"])
        sname = subj["subject_name"]
        topics = list_topics(sid, db_path=db_path)

        if not topics:
            recs.append(
                _make_rec(
                    rec_id=f"topic-empty-{sid}",
                    category="Topics and Syllabus",
                    title=f"Add syllabus topics for {sname}",
                    description=f"No syllabus topics have been entered for {sname} yet.",
                    reason="Topic-level tracking requires syllabus topics.",
                    suggested_action="Add syllabus topics in Subjects & Topics.",
                    priority="Low Priority",
                    priority_score=RECOMMENDATION_PRIORITY_SCORES["general_study_improvement"],
                    generated_at=gen_at,
                    target_page="pages/2_Subjects_Topics.py",
                    related_subject_id=sid,
                )
            )
            continue

        prog = get_subject_progress(sid, db_path=db_path)
        if prog["total_topics"] > 0 and prog["completed_topics"] == prog["total_topics"]:
            recs.append(
                _make_rec(
                    rec_id=f"topic-all-done-{sid}",
                    category="Topics and Syllabus",
                    title=f"All {prog['total_topics']} topics in {sname} are completed!",
                    description=f"100% syllabus completion achieved for {sname}.",
                    reason="Every recorded topic in this subject has status Completed.",
                    suggested_action="Focus on mock tests and past-paper revision.",
                    priority="Positive Progress",
                    priority_score=RECOMMENDATION_PRIORITY_SCORES["positive_progress"],
                    generated_at=gen_at,
                    target_page="pages/2_Subjects_Topics.py",
                    related_subject_id=sid,
                )
            )

        for topic in topics:
            tid = int(topic["id"])
            tname = topic["topic_name"]
            if topic["status"] == "Completed":
                continue

            if (
                TOPIC_OVERDUE_WARNING
                and topic.get("target_date")
                and topic["target_date"] < today_iso
            ):
                recs.append(
                    _make_rec(
                        rec_id=f"topic-overdue-{tid}",
                        category="Topics and Syllabus",
                        title=f"Your {tname} topic ({sname}) has passed its planned completion date.",
                        description=f"Planned completion was {topic['target_date']}.",
                        reason="Topic is still incomplete after its planned target date.",
                        suggested_action="Review the remaining content and set a realistic new completion target.",
                        priority="Medium Priority",
                        priority_score=RECOMMENDATION_PRIORITY_SCORES["topic_past_target"],
                        generated_at=gen_at,
                        target_page="pages/2_Subjects_Topics.py",
                        related_subject_id=sid,
                        related_topic_id=tid,
                    )
                )

            est = topic.get("estimated_hours") or 0.0
            actual = topic_hours_map.get(tid, 0.0)
            if topic["status"] == "In Progress" and est > 0 and actual > est:
                recs.append(
                    _make_rec(
                        rec_id=f"topic-overhours-{tid}",
                        category="Topics and Syllabus",
                        title=f"{tname} ({sname}) is taking longer than estimated.",
                        description=f"Logged {actual:.1f} hrs against an estimate of {est:.1f} hrs.",
                        reason="Actual study hours exceed estimated hours while topic is still In Progress.",
                        suggested_action="Break the remaining work into smaller focused practice sessions.",
                        priority="Low Priority",
                        priority_score=RECOMMENDATION_PRIORITY_SCORES["topic_revision_needed"],
                        generated_at=gen_at,
                        target_page="pages/2_Subjects_Topics.py",
                        related_subject_id=sid,
                        related_topic_id=tid,
                    )
                )

    return recs


def generate_productivity_insights(
    current_dt: Optional[datetime] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Analyze daily check-ins and study session ratings when sufficient data exists."""
    now = current_dt or datetime.now()
    gen_at = now.isoformat(timespec="seconds")
    checkins = list_daily_checkins(limit=14, db_path=db_path)

    if len(checkins) < PRODUCTIVITY_MIN_RECORDS:
        return [
            _make_rec(
                rec_id="productivity-insufficient",
                category="Study Habits",
                title="Insufficient data for daily productivity trends",
                description=f"Complete at least {PRODUCTIVITY_MIN_RECORDS} daily check-ins to unlock productivity trend insights.",
                reason=f"Currently {len(checkins)} daily check-in(s) recorded.",
                suggested_action="Submit daily check-ins in Daily Study Tracker.",
                priority="Low Priority",
                priority_score=RECOMMENDATION_PRIORITY_SCORES["general_study_improvement"],
                generated_at=gen_at,
                target_page="pages/3_Daily_Study_Tracker.py",
            )
        ]

    recs: List[Dict[str, Any]] = []
    # Checkins are ordered DESC; reverse to chronological order
    chronological = list(reversed(checkins))
    rated = [c["productivity_rating"] for c in chronological if c.get("productivity_rating") is not None]
    if len(rated) >= PRODUCTIVITY_MIN_RECORDS:
        mid = len(rated) // 2
        early_avg = sum(rated[:mid]) / len(rated[:mid])
        recent_avg = sum(rated[mid:]) / len(rated[mid:])
        if recent_avg - early_avg >= 0.4:
            recs.append(
                _make_rec(
                    rec_id="productivity-trend-up",
                    category="Study Habits",
                    title="Your recorded daily productivity has improved.",
                    description=f"Recent average rating ({recent_avg:.1f}/5) is higher than earlier ({early_avg:.1f}/5).",
                    reason="Daily check-in productivity ratings show a positive upward trend.",
                    suggested_action="Keep following the study routine that worked well this week.",
                    priority="Positive Progress",
                    priority_score=RECOMMENDATION_PRIORITY_SCORES["positive_progress"],
                    generated_at=gen_at,
                    target_page="pages/3_Daily_Study_Tracker.py",
                )
            )

    goal_rate = sum(1 for c in checkins if c.get("goal_completed")) / len(checkins)
    if goal_rate < 0.5:
        recs.append(
            _make_rec(
                rec_id="productivity-low-goals",
                category="Study Habits",
                title="Your daily study goals have not been completed consistently.",
                description=f"Daily goals were marked completed on {int(goal_rate * 100)}% of recent check-ins.",
                reason="Goal completion rate across recent check-ins is below 50%.",
                suggested_action="Set smaller and more achievable daily targets.",
                priority="Medium Priority",
                priority_score=RECOMMENDATION_PRIORITY_SCORES["general_study_improvement"] + 25,
                generated_at=gen_at,
                target_page="pages/3_Daily_Study_Tracker.py",
            )
        )

    return recs


def get_prioritized_recommendations(
    current_dt: Optional[datetime] = None,
    marks_threshold: float = MARKS_WEAK_THRESHOLD,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Aggregate, deduplicate, and sort all rule-based recommendations."""
    raw = (
        generate_assignment_recommendations(current_dt=current_dt, db_path=db_path)
        + generate_attendance_recommendations(current_dt=current_dt, db_path=db_path)
        + generate_academic_recommendations(
            current_dt=current_dt, marks_threshold=marks_threshold, db_path=db_path
        )
        + generate_study_recommendations(
            current_dt=current_dt, marks_threshold=marks_threshold, db_path=db_path
        )
        + generate_topic_recommendations(current_dt=current_dt, db_path=db_path)
        + generate_productivity_insights(current_dt=current_dt, db_path=db_path)
    )

    deduped: Dict[str, Dict[str, Any]] = {}
    for rec in raw:
        if rec["id"] not in deduped:
            deduped[rec["id"]] = rec

    ordered = list(deduped.values())
    ordered.sort(key=lambda r: (-int(r["priority_score"]), r["title"]))
    return ordered


def calculate_overall_progress_status(
    current_dt: Optional[datetime] = None,
    marks_threshold: float = MARKS_WEAK_THRESHOLD,
    db_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Compute a transparent overall progress status from real database records."""
    summary = get_student_academic_summary(
        current_dt=current_dt, marks_threshold=marks_threshold, db_path=db_path
    )

    if summary["total_subjects"] == 0:
        return {
            "status": "Insufficient Data",
            "reasons": ["No subjects have been added yet."],
            "disclaimer": "Informational rule-based status only; not an official university grade.",
        }

    recorded_att = [
        a["attendance_percentage"]
        for a in summary["attendance_summary"]
        if a["attendance_percentage"] is not None
    ]
    recorded_marks = [
        m["weighted_percentage"]
        for m in summary["marks_summary"]
        if m["weighted_percentage"] is not None
    ]

    if not recorded_att and not recorded_marks and summary["total_sessions"] == 0:
        return {
            "status": "Insufficient Data",
            "reasons": [
                "Subjects exist, but no attendance, marks, or study sessions have been recorded yet."
            ],
            "disclaimer": "Informational rule-based status only; not an official university grade.",
        }

    issues: List[str] = []
    positives: List[str] = []

    att_target = summary["attendance_target"]
    low_att = [p for p in recorded_att if p < att_target]
    if low_att:
        issues.append(f"{len(low_att)} subject(s) have attendance below {att_target:.0f}%.")
    elif recorded_att:
        positives.append(f"All recorded subjects meet the {att_target:.0f}% attendance target.")

    low_marks = [m for m in recorded_marks if m < marks_threshold]
    if low_marks:
        issues.append(f"{len(low_marks)} subject(s) have marks below {marks_threshold:.0f}%.")
    elif recorded_marks:
        positives.append(f"All assessed subjects meet the {marks_threshold:.0f}% marks threshold.")

    overdue_count = sum(
        1 for a in summary["assignments"] if a["reminder_state"]["category"] == "Overdue"
    )
    if overdue_count > 0:
        issues.append(f"{overdue_count} assignment(s) are currently overdue.")

    if summary["weekly_target"] > 0:
        if summary["week_hours"] >= summary["weekly_target"]:
            positives.append(
                f"Weekly study target achieved ({summary['week_hours']:.1f}/{summary['weekly_target']} hrs)."
            )
        elif summary["week_hours"] < summary["weekly_target"] * WEEKLY_STUDY_WARNING_RATIO:
            issues.append(
                f"Weekly study hours ({summary['week_hours']:.1f} hrs) are below target ({summary['weekly_target']} hrs)."
            )

    if len(issues) >= 2 or overdue_count > 0 or len(low_att) > 0 or len(low_marks) > 0:
        status = "Needs Attention"
    elif len(issues) == 0 and len(positives) >= 2:
        status = "Excellent Progress"
    else:
        status = "Good Progress"

    return {
        "status": status,
        "reasons": issues + positives if (issues or positives) else ["Steady academic activity recorded."],
        "disclaimer": "Informational rule-based status only; not an official university grade.",
    }
