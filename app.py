"""Main entry point and Central Productivity Dashboard for CampusPulse AI (Design System V4)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
import html
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database.db import initialize_database
from services.academic_service import (
    calculate_overall_weighted_attendance,
    get_attendance_summary_all_subjects,
    get_attendance_target,
)
from services.analytics_service import get_daily_study_minutes, get_subject_study_summary
from services.assignment_service import fetch_assignments, fetch_upcoming_deadlines
from services.calendar_service import fetch_upcoming_events
from services.profile_service import get_profile
from services.recommendation_service import get_prioritized_recommendations
from services.study_service import (
    fetch_sessions,
    format_minutes_hm,
    get_daily_checkin,
    get_today_study_overview,
)
from services.subject_service import get_subject_progress, list_subjects
from services.timetable_service import get_saved_timetable
from utils.avatars import get_avatar_html
from utils.config import (
    APP_DESCRIPTION,
    APP_ICON,
    APP_NAME,
    APP_SUBTITLE,
    APP_TAGLINE,
    DEV_STATUS,
    STYLES_PATH,
)
from utils.formatters import format_time_12h, format_time_range_12h
from utils.ui import (
    get_greeting_for_hour,
    load_css,
    render_empty_state,
    render_enhanced_metric_card,
    render_page_header,
    render_section_header,
    render_sidebar,
    render_status_badge,
    render_subject_card,
)


def _render_welcome_section(profile: Optional[Dict[str, Any]]) -> None:
    """Render personalized welcome hero with student avatar and date metadata."""
    now = datetime.now()
    greeting_prefix = get_greeting_for_hour(now.hour)
    today_str = now.strftime("%A, %d %B %Y")

    if profile and profile.get("name"):
        name = profile["name"]
        greeting = f"{greeting_prefix}, {name}!"
        branch = profile.get("branch") or "Engineering"
        semester = profile.get("semester")
        sem_str = f"Semester {semester}" if semester else ""
        college = profile.get("college_name") or "CampusPulse AI Academy"
        meta_items = [branch, sem_str, college]
        meta_line = " • ".join(item for item in meta_items if item)
        avatar_html = get_avatar_html(profile, size=74, border=True)
    else:
        greeting = f"{greeting_prefix} & Welcome to CampusPulse AI!"
        meta_line = "Your personal intelligent academic workspace"
        avatar_html = get_avatar_html(None, size=74, border=True)

    st.markdown(
        f"""
        <div class="cp-welcome-card">
            <div style="display: flex; align-items: center; gap: 1.4rem; flex-wrap: wrap;">
                <div>{avatar_html}</div>
                <div style="flex: 1; min-width: 260px;">
                    <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.25rem;">
                        <span class="cp-welcome-eyebrow">🎓 {APP_NAME} • Dashboard</span>
                        <span style="font-size: 0.82rem; font-weight: 600; color: var(--cp-muted);">{today_str}</span>
                    </div>
                    <h1 style="margin: 0 0 0.35rem 0; font-size: 1.95rem; color: var(--cp-midnight); font-weight: 750;">{html.escape(greeting)}</h1>
                    <p class="cp-welcome-subtitle" style="margin: 0 0 0.45rem 0;">{html.escape(meta_line)}</p>
                    <p class="cp-welcome-tagline">Plan Smarter. Study Better. Track Your Growth.</p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_academic_summary_cards(
    today_iso: str,
    monday_iso: str,
    sunday_iso: str,
    subjects: List[Dict[str, Any]],
) -> None:
    """Display the top-level academic and study KPI summary metrics."""
    # 1. Today's study hours
    today_sessions = fetch_sessions(start_date=today_iso, end_date=today_iso)
    today_mins = sum(int(s["duration_minutes"]) for s in today_sessions)
    today_hrs = round(today_mins / 60.0, 1)

    # 2. Weekly study hours
    week_sessions = fetch_sessions(start_date=monday_iso, end_date=sunday_iso)
    week_mins = sum(int(s["duration_minutes"]) for s in week_sessions)
    week_hrs = round(week_mins / 60.0, 1)

    # 3 & 4. Subject and syllabus completion metrics
    total_active_subjects = len(subjects)
    total_topics = 0
    total_completed_topics = 0
    for subj in subjects:
        prog = get_subject_progress(subj["id"])
        total_topics += prog["total_topics"]
        total_completed_topics += prog["completed_topics"]

    overall_syllabus_pct = (
        round((total_completed_topics / total_topics) * 100.0, 1)
        if total_topics > 0
        else 0.0
    )

    # 5. Overall attendance
    att_summary = calculate_overall_weighted_attendance()
    att_pct = (
        att_summary["overall_percentage"]
        if isinstance(att_summary, dict) and att_summary.get("overall_percentage") is not None
        else None
    )
    att_label = f"{att_pct:.1f}%" if att_pct is not None else "No Records"

    # 6. Assignment metrics
    all_assignments = fetch_assignments()
    pending_count = sum(1 for a in all_assignments if a["status"] != "Completed")

    c1, c2, c3 = st.columns(3)
    with c1:
        render_enhanced_metric_card(
            label="Today's Study",
            value=f"{today_hrs} hrs",
            delta=f"{len(today_sessions)} session(s) logged",
            accent_color="#5C559A",
            icon="⏱️",
            help_text="Total study hours logged today",
        )
    with c2:
        render_enhanced_metric_card(
            label="This Week's Study",
            value=f"{week_hrs} hrs",
            delta="Current week (Mon–Sun)",
            accent_color="#C87863",
            icon="📈",
            help_text="Study hours logged across the active week",
        )
    with c3:
        render_enhanced_metric_card(
            label="Active Subjects",
            value=str(total_active_subjects),
            delta=f"{total_topics} topics tracked",
            accent_color="#6B8B7F",
            icon="📚",
            help_text="Subjects currently active in your syllabus",
        )

    st.markdown("<div style='margin-top: 0.65rem;'></div>", unsafe_allow_html=True)
    c4, c5, c6 = st.columns(3)
    with c4:
        render_enhanced_metric_card(
            label="Syllabus Progress",
            value=f"{overall_syllabus_pct}%" if total_topics > 0 else "0.0%",
            delta=f"{total_completed_topics}/{total_topics} topics completed" if total_topics > 0 else "No topics yet",
            accent_color="#5C559A",
            icon="🎯",
            help_text="Overall percentage of topics marked completed",
        )
    with c5:
        render_enhanced_metric_card(
            label="Pending Assignments",
            value=str(pending_count),
            delta="Deadlines requiring action",
            accent_color="#E9B67D",
            icon="📌",
            help_text="Assignments not yet completed",
        )
    with c6:
        render_enhanced_metric_card(
            label="Overall Attendance",
            value=att_label,
            delta="Target: 75% minimum",
            accent_color="#38684F",
            icon="🎓",
            help_text="Weighted college class attendance rate",
        )


def _render_schedule_and_today_study(today_iso: str) -> None:
    """Render Today's Timetable Schedule alongside Today's Recorded Study Summary."""
    col_sched, col_study = st.columns([1.2, 1], gap="medium")

    with col_sched:
        render_section_header("🗓️ Today's Study Schedule", "Planned slots generated by the timetable engine")
        today_tt = get_saved_timetable(start_date=today_iso, end_date=today_iso)

        if not today_tt:
            with st.container(border=True):
                render_empty_state("No Study Scheduled Today", "You have no timetable sessions planned for today.", "🗓️")
                if st.button("Generate or Open Timetable", key="tt_open_btn", type="primary"):
                    st.switch_page("pages/8_Smart_Timetable.py")
        else:
            with st.container(border=True):
                for item in today_tt:
                    time_range = format_time_range_12h(item.get("start_time"), item.get("end_time"))
                    subj_name = html.escape(item.get("subject_name") or "Subject")
                    top_name = html.escape(item.get("topic_name") or "")
                    top_html = f" • <span style='color: var(--cp-muted); font-size: 0.88rem;'>{top_name}</span>" if top_name else ""
                    sess_title = html.escape(item.get("session_title") or "Study Session")
                    prio = item.get("priority") or "Medium"
                    p_color = "danger" if prio == "High" else "warning" if prio == "Medium" else "info"
                    status = item.get("status") or "Planned"
                    s_color = "success" if status == "Completed" else "warning" if status == "In Progress" else "neutral"

                    st.markdown(
                        f"""
                        <div class="cp-schedule-item">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 0.5rem; margin-bottom: 4px;">
                                <div>
                                    <span class="cp-time-badge">⏰ {time_range}</span>
                                    <span style="font-weight: 700; color: var(--cp-midnight); margin-left: 8px;">{subj_name}</span>{top_html}
                                </div>
                                <div style="display: flex; gap: 4px;">
                                    {render_status_badge(prio, p_color)}
                                    {render_status_badge(status, s_color)}
                                </div>
                            </div>
                            <div style="font-size: 0.85rem; color: var(--cp-muted);">{sess_title}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
                if st.button("Manage Timetable", key="tt_manage_btn", type="secondary"):
                    st.switch_page("pages/8_Smart_Timetable.py")

    with col_study:
        render_section_header("⏱️ Today's Recorded Study", "Actual study time tracked via the study logger")
        overview = get_today_study_overview()
        checkin = get_daily_checkin(today_iso)

        with st.container(border=True):
            r1, r2 = st.columns(2)
            r1.metric("Actual Logged", f"{overview['studied_hours']} hrs")
            r2.metric("Sessions Logged", overview["session_count"])

            st.markdown("---")
            rem_text = f"{overview['remaining_minutes']} mins remaining" if overview["remaining_minutes"] > 0 else "Daily target met! 🎉"
            st.caption(f"Target: **{overview['target_hours']} hrs/day** • {rem_text}")

            target_mins = max(1, int(overview['target_hours'] * 60))
            current_mins = int(overview['studied_hours'] * 60)
            progress_ratio = min(1.0, current_mins / target_mins)
            st.progress(progress_ratio)

            if checkin and checkin.get("productivity_rating"):
                stars = "⭐" * int(checkin["productivity_rating"])
                st.caption(f"Today's Productivity Rating: **{checkin['productivity_rating']} / 5** {stars}")
            else:
                st.caption("No daily check-in recorded for today.")

            st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
            if st.button("Open Study Tracker", key="dash_open_study", type="secondary"):
                st.switch_page("pages/3_Daily_Study_Tracker.py")


def _render_deadlines_and_calendar() -> None:
    """Render Upcoming Assignment Deadlines and Upcoming College Calendar Events."""
    col_asgn, col_cal = st.columns([1.2, 1], gap="medium")
    today = date.today()

    with col_asgn:
        render_section_header("📌 Upcoming Assignment Deadlines", "Submissions and coursework due within 14 days")
        upcoming_asgns = fetch_upcoming_deadlines(days=14)

        if not upcoming_asgns:
            with st.container(border=True):
                render_empty_state("All Caught Up!", "No pending assignments due within the next 14 days.", "🎉")
        else:
            with st.container(border=True):
                for item in upcoming_asgns[:5]:
                    rem_d = item.get("days_remaining")
                    if rem_d is not None and rem_d < 0:
                        urgency_cls = "urgent"
                        rem_badge = render_status_badge("OVERDUE", "danger")
                    elif rem_d == 0:
                        urgency_cls = "urgent"
                        rem_badge = render_status_badge("Due Today", "warning")
                    elif rem_d is not None and rem_d <= 2:
                        urgency_cls = "urgent"
                        rem_badge = render_status_badge(f"{rem_d}d left", "warning")
                    elif rem_d is not None and rem_d <= 5:
                        urgency_cls = "soon"
                        rem_badge = render_status_badge(f"{rem_d}d left", "info")
                    else:
                        urgency_cls = "normal"
                        rem_badge = render_status_badge(f"{rem_d}d left", "neutral")

                    p_color = "danger" if item["priority"] == "High" else "warning" if item["priority"] == "Medium" else "info"
                    p_badge = render_status_badge(item["priority"], p_color)

                    time_fmt = format_time_12h(item.get("deadline_time"))
                    time_str = f" at {time_fmt}" if time_fmt != "—" else ""
                    due_str = f"Due: <strong>{item['deadline_date']}</strong>{time_str}"
                    title_esc = html.escape(item["title"])
                    subj_esc = html.escape(item.get("subject_name") or "Subject")

                    st.markdown(
                        f"""
                        <div class="cp-assignment-card {urgency_cls}">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 0.5rem; margin-bottom: 4px;">
                                <div>
                                    <strong style="color: var(--cp-midnight); font-size: 0.96rem;">{title_esc}</strong>
                                    <span style="font-size: 0.82rem; color: var(--cp-muted); margin-left: 6px;">({subj_esc})</span>
                                </div>
                                <div style="display: flex; gap: 4px;">
                                    {p_badge} {rem_badge}
                                </div>
                            </div>
                            <div style="font-size: 0.84rem; color: var(--cp-muted);">{due_str}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
                if st.button("View All Assignments", key="dash_view_asgn", type="secondary"):
                    st.switch_page("pages/5_Assignments_Reminders.py")

    with col_cal:
        render_section_header("📅 Upcoming College Events", "Important university dates and holidays")
        events = fetch_upcoming_events(reference_date=today)

        if not events:
            with st.container(border=True):
                render_empty_state("No Upcoming Events", "No calendar events scheduled in the next 30 days.", "📅")
        else:
            with st.container(border=True):
                for ev in events[:4]:
                    try:
                        ev_dt = datetime.strptime(ev["start_date"], "%Y-%m-%d")
                        mon_str = ev_dt.strftime("%b").upper()
                        day_str = str(ev_dt.day)
                    except Exception:
                        mon_str = "CAL"
                        day_str = "--"

                    ev_type = ev.get("event_type", "Event")
                    type_cls = "exam" if "exam" in ev_type.lower() else "holiday" if "holiday" in ev_type.lower() else ""

                    time_fmt = format_time_12h(ev.get("start_time"))
                    time_str = f" • ⏰ {time_fmt}" if time_fmt != "—" else ""

                    title_esc = html.escape(ev["title"])
                    st.markdown(
                        f"""
                        <div class="cp-event-card">
                            <div class="cp-event-date-box {type_cls}">
                                <span class="month">{mon_str}</span>
                                <span class="day">{day_str}</span>
                            </div>
                            <div style="flex: 1; min-width: 0;">
                                <div style="font-weight: 700; color: var(--cp-midnight); font-size: 0.94rem; margin-bottom: 2px;">{title_esc}</div>
                                <div style="font-size: 0.82rem; color: var(--cp-muted);">
                                    <span class="cp-badge cp-badge-neutral" style="padding: 1px 6px; font-size: 0.72rem;">{ev_type}</span>
                                    <span style="margin-left: 4px;">{ev['start_date']}{time_str}</span>
                                </div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
                if st.button("Open Calendar", key="dash_view_cal", type="secondary"):
                    st.switch_page("pages/6_College_Calendar.py")


def _render_recommendations_and_weekly_chart(
    monday_iso: str,
    sunday_iso: str,
    profile: Optional[Dict[str, Any]],
) -> None:
    """Render top rule-based AI recommendations alongside interactive weekly study hours chart."""
    col_rec, col_chart = st.columns([1.2, 1], gap="medium")

    with col_rec:
        render_section_header("🧠 Top AI Study Recommendations", "Actionable personalized guidance from the rules engine")
        recs = get_prioritized_recommendations()

        if not recs:
            with st.container(border=True):
                render_empty_state("Optimal Progress!", "No urgent study warnings or overdue tasks identified right now.", "🌟")
        else:
            with st.container(border=True):
                top_rec = recs[0]
                top_badge = render_status_badge(
                    top_rec['priority'],
                    "danger" if top_rec['priority'] == "High Priority"
                    else "warning" if top_rec['priority'] == "Medium Priority"
                    else "success" if top_rec['priority'] == "Positive Progress"
                    else "info"
                )
                st.markdown(
                    f"""
                    <div class="cp-rec-featured-card">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                            <span style="font-size: 0.76rem; font-weight: 750; text-transform: uppercase; letter-spacing: 0.06em; color: var(--cp-terracotta);">⭐ Priority Insight</span>
                            {top_badge}
                        </div>
                        <div style="font-weight: 750; font-size: 1.05rem; color: var(--cp-midnight); margin-bottom: 4px;">{html.escape(top_rec['title'])}</div>
                        <div style="font-size: 0.88rem; color: var(--cp-text); line-height: 1.45; margin-bottom: 8px;">{html.escape(top_rec['reason'])}</div>
                        <div style="font-size: 0.84rem; font-weight: 600; color: var(--cp-primary); background: #FAF7FE; border-left: 3px solid var(--cp-primary); padding: 4px 8px; border-radius: 4px;">
                            👉 {html.escape(top_rec['suggested_action'])}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                for item in recs[1:3]:
                    p_badge = render_status_badge(
                        item['priority'],
                        "danger" if item['priority'] == "High Priority"
                        else "warning" if item['priority'] == "Medium Priority"
                        else "success" if item['priority'] == "Positive Progress"
                        else "info"
                    )
                    p_border = "#9A4147" if item['priority'] == "High Priority" else "#925B1F" if item['priority'] == "Medium Priority" else "#5C559A"
                    st.markdown(
                        f"""
                        <div class="cp-rec-card" style="border-left: 4px solid {p_border};">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                                <strong style="color: var(--cp-midnight); font-size: 0.94rem;">{html.escape(item['title'])}</strong>
                                {p_badge}
                            </div>
                            <div style="font-size: 0.86rem; color: var(--cp-muted); margin-bottom: 6px; line-height: 1.4;">{html.escape(item['reason'])}</div>
                            <div style="font-size: 0.82rem; color: var(--cp-midnight); font-weight: 550;">👉 Action: {html.escape(item['suggested_action'])}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
                if st.button("View All Recommendations", key="dash_all_recs", type="secondary"):
                    st.switch_page("pages/7_AI_Recommendations.py")

    with col_chart:
        render_section_header("📈 Weekly Study Progress", "Visual breakdown of study hours this week")
        weekly_daily = get_daily_study_minutes(
            start_date=monday_iso,
            end_date=sunday_iso,
            fill_missing_days=True,
        )

        target_hrs = float(profile["weekly_study_target"]) if profile else 14.0
        total_week_mins = sum(d["minutes"] for d in weekly_daily)
        total_week_hrs = round(total_week_mins / 60.0, 1)

        with st.container(border=True):
            st.caption(f"Logged This Week: **{total_week_hrs} / {target_hrs} hrs target** (Mon–Sun)")
            if weekly_daily:
                df = pd.DataFrame(weekly_daily)
                df["day_name"] = df["study_date"].apply(
                    lambda d: datetime.strptime(d, "%Y-%m-%d").strftime("%a")
                )
                fig = px.bar(
                    df,
                    x="day_name",
                    y="hours",
                    text_auto=".1f",
                    labels={"day_name": "Day", "hours": "Hours"},
                )
                fig.update_traces(
                    marker_color="#5C559A",
                    marker_line_color="#48427D",
                    marker_line_width=1,
                )
                fig.update_layout(
                    height=250,
                    margin=dict(l=10, r=10, t=20, b=10),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Inter, system-ui, sans-serif", color="#282536"),
                    xaxis=dict(showgrid=False, linecolor="#DCD8E4"),
                    yaxis=dict(gridcolor="#ECE8F2", linecolor="#DCD8E4"),
                )
                st.plotly_chart(fig, use_container_width=True)

            if st.button("Explore Full Analytics", key="dash_open_analytics", type="secondary"):
                st.switch_page("pages/10_Progress_Analytics.py")


def _render_subject_progress_summary(subjects: List[Dict[str, Any]]) -> None:
    """Render Subject-wise Learning Progress overview using visual progress cards."""
    render_section_header("📚 Subject Syllabus Progress", "Syllabus completion status across enrolled subjects")

    if not subjects:
        with st.container(border=True):
            render_empty_state("No Subjects Added", "Add your college subjects to start tracking your syllabus.", "📚")
            if st.button("Add Subjects Now", key="dash_add_subjs", type="primary"):
                st.switch_page("pages/2_Subjects_Topics.py")
        return

    subject_study_map = {}
    try:
        study_summary = get_subject_study_summary()
        for item in study_summary:
            subject_study_map[item["subject_id"]] = item.get("total_hours", item.get("hours", 0.0))
    except Exception:
        pass

    with st.container(border=True):
        cols = st.columns(3)
        for idx, s in enumerate(subjects):
            col = cols[idx % 3]
            prog = get_subject_progress(s["id"])
            hrs = subject_study_map.get(s["id"], 0.0)

            with col:
                render_subject_card(
                    subject=s,
                    progress=prog,
                    study_hours=hrs,
                )

        st.markdown("<div style='margin-top: 0.75rem;'></div>", unsafe_allow_html=True)
        if st.button("Manage Subjects & Topics", key="dash_manage_subjs", type="secondary"):
            st.switch_page("pages/2_Subjects_Topics.py")


def _render_quick_actions() -> None:
    """Render one-click direct navigation quick action pills at the bottom of the dashboard."""
    render_section_header("⚡ Quick Actions", "Direct shortcuts to key productivity workspaces")

    # Row 1: 4 primary and secondary actions
    r1_c1, r1_c2, r1_c3, r1_c4 = st.columns(4)
    with r1_c1:
        if st.button("⏱️ Log Study", use_container_width=True, type="primary", key="dashboard_quick_log_study"):
            st.switch_page("pages/3_Daily_Study_Tracker.py")
    with r1_c2:
        if st.button("📚 Subjects", use_container_width=True, type="secondary", key="dashboard_quick_subjects"):
            st.switch_page("pages/2_Subjects_Topics.py")
    with r1_c3:
        if st.button("📝 Attendance", use_container_width=True, type="secondary", key="dashboard_quick_attendance"):
            st.switch_page("pages/4_Academic_Performance.py")
    with r1_c4:
        if st.button("📌 Assignments", use_container_width=True, type="secondary", key="dashboard_quick_assignments"):
            st.switch_page("pages/5_Assignments_Reminders.py")

    # Row 2: 3 complementary workspace actions
    st.markdown("<div style='margin-top: 0.35rem;'></div>", unsafe_allow_html=True)
    r2_c1, r2_c2, r2_c3 = st.columns(3)
    with r2_c1:
        if st.button("🗓️ Timetable", use_container_width=True, type="secondary", key="dashboard_quick_timetable"):
            st.switch_page("pages/8_Smart_Timetable.py")
    with r2_c2:
        if st.button("🎥 Video Lectures", use_container_width=True, type="secondary", key="dashboard_quick_video_lectures"):
            st.switch_page("pages/9_Video_Lectures.py")
    with r2_c3:
        if st.button("📊 Analytics", use_container_width=True, type="secondary", key="dashboard_quick_analytics"):
            st.switch_page("pages/10_Progress_Analytics.py")


def main() -> None:
    """Main dashboard entry point for CampusPulse AI."""
    st.set_page_config(
        page_title=f"Dashboard | {APP_NAME}",
        page_icon=APP_ICON,
        layout="wide",
    )

    load_css(STYLES_PATH)
    db_ready = initialize_database()
    render_sidebar(db_ready=db_ready)

    today = date.today()
    today_iso = today.isoformat()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    monday_iso = monday.isoformat()
    sunday_iso = sunday.isoformat()

    profile = get_profile()
    subjects = list_subjects()

    # 1. TOP: Personalized welcome greeting with student avatar
    _render_welcome_section(profile)

    # 2. SUMMARY: Key academic summary KPI metrics
    _render_academic_summary_cards(today_iso, monday_iso, sunday_iso, subjects)

    # 3. MIDDLE: Today's schedule and recorded study, upcoming deadlines & college events
    _render_schedule_and_today_study(today_iso)
    _render_deadlines_and_calendar()

    # 4. LOWER: Weekly study progress, subject progress, and top AI recommendations
    _render_recommendations_and_weekly_chart(monday_iso, sunday_iso, profile)
    _render_subject_progress_summary(subjects)

    # 5. BOTTOM: Quick Actions
    _render_quick_actions()


if __name__ == "__main__":
    main()
