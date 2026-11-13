"""Progress Analytics, Performance Reports, and CSV Data Export page."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database.db import initialize_database
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
from services.subject_service import list_subjects
from utils.config import ANALYTICS_DATE_FILTERS, APP_NAME, STYLES_PATH
from utils.ui import load_css, render_sidebar

st.set_page_config(
    page_title=f"Progress Analytics | {APP_NAME}",
    page_icon="📊",
    layout="wide",
)


def _render_date_filter_selector() -> tuple[str, Optional[str], Optional[str]]:
    """Render top-level date range selection toolbar and return (filter_name, start_iso, end_iso)."""
    col1, col2, col3 = st.columns([2, 1.5, 1.5])
    with col1:
        filter_name = st.selectbox(
            "Analytics Time Period",
            options=list(ANALYTICS_DATE_FILTERS),
            index=2,  # Default to Last 30 Days
            key="analytics_period_filter",
        )

    custom_start: Optional[date] = None
    custom_end: Optional[date] = None
    if filter_name == "Custom Date Range":
        with col2:
            custom_start = st.date_input(
                "Start Date",
                value=date.today() - timedelta(days=14),
                key="analytics_custom_start",
            )
        with col3:
            custom_end = st.date_input(
                "End Date",
                value=date.today(),
                key="analytics_custom_end",
            )
        if custom_start and custom_end and custom_start > custom_end:
            st.error("Start Date cannot be later than End Date.")
            return filter_name, None, None

    start_iso, end_iso = get_date_range(
        filter_name=filter_name,
        custom_start=custom_start,
        custom_end=custom_end,
    )

    if start_iso and end_iso:
        st.caption(
            f"Active analysis period: **{start_iso}** to **{end_iso}** (inclusive). "
            "Syllabus completion and current attendance snapshot reflect your overall academic status."
        )
    else:
        st.caption("Active analysis period: **All Recorded Time**.")

    return filter_name, start_iso, end_iso


def _render_overall_overview(report: Dict[str, Any]) -> None:
    """Display top-level summary metrics cards."""
    ov = report["overview"]
    ss = report["study_summary"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Study Hours", f"{ov['total_study_hours']:.1f} hrs")
    c2.metric("Daily Average", f"{ov['average_daily_study_hours']:.1f} hrs/day")
    c3.metric("Study Sessions", ss["total_sessions"])
    c4.metric("Completed Topics (Period)", ov["completed_topics_in_period"])

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Active Subjects", ov["active_subjects_count"])
    c6.metric("Overall Syllabus Completion", f"{ov['overall_syllabus_completion_pct']}%")
    c7.metric("Assignment Completion", f"{ov['assignment_completion_pct']}%")
    c8.metric("Current Study Streak", f"{ov['current_streak_days']} days", f"Max: {ov['longest_streak_days']}d")


def _render_study_time_tab(start_iso: Optional[str], end_iso: Optional[str]) -> None:
    """Render daily, weekly, and monthly study hours charts."""
    st.subheader("Study Time Trends")

    daily = get_daily_study_minutes(start_iso, end_iso, fill_missing_days=True)
    weekly = get_weekly_study_summary(start_iso, end_iso)
    monthly = get_monthly_study_summary(start_iso, end_iso)

    if not daily or sum(d["minutes"] for d in daily) == 0:
        st.info("No recorded study sessions in the selected period. Start logging your study sessions to view trends.")
        return

    # Daily study line chart
    df_daily = pd.DataFrame(daily)
    fig_daily = px.line(
        df_daily,
        x="study_date",
        y="hours",
        markers=True,
        title="Daily Recorded Study Hours",
        labels={"study_date": "Date", "hours": "Study Hours"},
    )
    fig_daily.update_traces(line_color="#36594A", hovertemplate="%{x}: %{y:.2f} hrs<extra></extra>")
    fig_daily.update_layout(
        height=350,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="system-ui, sans-serif", color="#292C28"),
        xaxis=dict(showgrid=False, linecolor="#93897B"),
        yaxis=dict(gridcolor="#D8D0C5", linecolor="#93897B"),
    )
    st.plotly_chart(fig_daily, use_container_width=True)

    c_w, c_m = st.columns(2)
    with c_w:
        if weekly:
            df_w = pd.DataFrame(weekly)
            fig_w = px.bar(
                df_w,
                x="week_label",
                y="hours",
                title="Weekly Study Hours",
                labels={"week_label": "Week", "hours": "Hours"},
                text_auto=".1f",
            )
            fig_w.update_traces(marker_color="#9D563A")
            fig_w.update_layout(
                height=320,
                margin=dict(l=20, r=20, t=40, b=20),
                xaxis_tickangle=-30,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="system-ui, sans-serif", color="#292C28"),
                xaxis=dict(showgrid=False, linecolor="#93897B"),
                yaxis=dict(gridcolor="#D8D0C5", linecolor="#93897B"),
            )
            st.plotly_chart(fig_w, use_container_width=True)
    with c_m:
        if monthly:
            df_m = pd.DataFrame(monthly)
            fig_m = px.bar(
                df_m,
                x="month_label",
                y="hours",
                title="Monthly Study Hours",
                labels={"month_label": "Month", "hours": "Hours"},
                text_auto=".1f",
            )
            fig_m.update_traces(marker_color="#36594A")
            fig_m.update_layout(
                height=320,
                margin=dict(l=20, r=20, t=40, b=20),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="system-ui, sans-serif", color="#292C28"),
                xaxis=dict(showgrid=False, linecolor="#93897B"),
                yaxis=dict(gridcolor="#D8D0C5", linecolor="#93897B"),
            )
            st.plotly_chart(fig_m, use_container_width=True)


def _render_subject_tab(start_iso: Optional[str], end_iso: Optional[str]) -> None:
    """Render subject-wise study time bar charts and distribution."""
    st.subheader("Subject-Wise Study Time Analysis")
    data = get_subject_study_summary(start_iso, end_iso)
    if not data:
        st.info("No subjects found. Add subjects in Subjects & Topics.")
        return

    df = pd.DataFrame(data)
    col1, col2 = st.columns([3, 2])
    with col1:
        fig_bar = px.bar(
            df,
            x="subject_name",
            y="total_hours",
            title="Total Study Hours by Subject",
            labels={"subject_name": "Subject", "total_hours": "Study Hours"},
            text_auto=".1f",
        )
        fig_bar.update_traces(marker_color="#36594A")
        fig_bar.update_layout(
            height=350,
            margin=dict(l=20, r=20, t=40, b=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="system-ui, sans-serif", color="#292C28"),
            xaxis=dict(showgrid=False, linecolor="#93897B"),
            yaxis=dict(gridcolor="#D8D0C5", linecolor="#93897B"),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with col2:
        df_active = df[df["total_minutes"] > 0]
        if not df_active.empty:
            fig_pie = px.pie(
                df_active,
                names="subject_name",
                values="total_minutes",
                title="Study Time Distribution",
                hole=0.4,
                color_discrete_sequence=["#36594A", "#9D563A", "#355C78", "#875514", "#5C5A50"],
            )
            fig_pie.update_layout(
                height=350,
                margin=dict(l=20, r=20, t=40, b=20),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="system-ui, sans-serif", color="#292C28"),
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No recorded study hours for subjects in this period.")

    st.dataframe(
        df[
            [
                "subject_name",
                "total_hours",
                "session_count",
                "avg_session_minutes",
                "study_time_percentage",
            ]
        ].rename(
            columns={
                "subject_name": "Subject",
                "total_hours": "Total Hours",
                "session_count": "Sessions",
                "avg_session_minutes": "Avg Mins/Session",
                "study_time_percentage": "% of Study Time",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )


def _render_topic_tab(subjects: List[Dict[str, Any]], start_iso: Optional[str], end_iso: Optional[str]) -> None:
    """Render topic-wise study time and completion durations."""
    st.subheader("Topic-Wise Study & Completion Analysis")
    subject_map = {s["id"]: s["subject_name"] for s in subjects}

    filter_subj = st.selectbox(
        "Filter by Subject",
        options=[None] + [s["id"] for s in subjects],
        format_func=lambda sid: "All Subjects" if sid is None else subject_map.get(sid, f"Subject {sid}"),
        key="topic_analytics_subj_filter",
    )

    t_data = get_topic_study_summary(filter_subj, start_iso, end_iso)
    if not t_data:
        st.info("No syllabus topics found for this selection.")
    else:
        df_top = pd.DataFrame(t_data)
        fig_top = px.bar(
            df_top,
            x="topic_name",
            y="total_hours",
            color="status",
            title="Actual Study Hours by Topic",
            labels={"topic_name": "Topic", "total_hours": "Hours", "status": "Status"},
            text_auto=".1f",
        )
        fig_top.update_layout(height=350, margin=dict(l=20, r=20, t=40, b=20), xaxis_tickangle=-30)
        st.plotly_chart(fig_top, use_container_width=True)

    st.markdown("#### Completed Topics — Duration Comparison")
    st.caption("Compares calendar days elapsed between start and completion dates against actual logged study hours.")
    durations = get_topic_completion_duration(filter_subj)
    if not durations:
        st.info("No completed topics with recorded duration data yet.")
    else:
        df_dur = pd.DataFrame(durations)
        st.dataframe(
            df_dur[
                [
                    "topic_name",
                    "subject_name",
                    "start_date",
                    "completion_date",
                    "calendar_days_taken",
                    "actual_study_hours",
                    "estimated_hours",
                    "hours_variance",
                ]
            ].rename(
                columns={
                    "topic_name": "Topic",
                    "subject_name": "Subject",
                    "start_date": "Start Date",
                    "completion_date": "Completed Date",
                    "calendar_days_taken": "Calendar Days",
                    "actual_study_hours": "Actual Study Hours",
                    "estimated_hours": "Estimated Hours",
                    "hours_variance": "Variance (hrs)",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )


def _render_consistency_productivity_tab(start_iso: Optional[str], end_iso: Optional[str]) -> None:
    """Render streaks, check-in completion, and productivity charts."""
    st.subheader("Study Consistency & Daily Productivity")

    streaks = calculate_study_streaks()
    prod = get_daily_productivity_summary(start_iso, end_iso)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Longest Study Streak", f"{streaks['longest_streak_days']} days")
    c2.metric("Current Study Streak", f"{streaks['current_streak_days']} days")
    c3.metric(
        "Daily Goal Completion Rate",
        f"{prod['goal_completion_rate']}%" if prod["goal_completion_rate"] is not None else "No check-ins",
    )
    c4.metric(
        "Avg Productivity Rating",
        f"{prod['average_checkin_rating']}/5" if prod["average_checkin_rating"] is not None else "N/A",
    )

    st.caption(
        "Note: Study-recording streaks measure recorded study days in SQLite, not proof of actual productivity. "
        "Daily check-in ratings and individual session ratings are evaluated separately."
    )

    trend = prod.get("daily_trend") or []
    if trend:
        df_trend = pd.DataFrame(trend)
        fig_prod = go.Figure()
        if "checkin_rating" in df_trend.columns and df_trend["checkin_rating"].notna().any():
            fig_prod.add_trace(
                go.Scatter(
                    x=df_trend["date"],
                    y=df_trend["checkin_rating"],
                    mode="lines+markers",
                    name="Daily Check-in Rating",
                    line=dict(color="#0d9488"),
                )
            )
        if "session_rating_avg" in df_trend.columns and df_trend["session_rating_avg"].notna().any():
            fig_prod.add_trace(
                go.Scatter(
                    x=df_trend["date"],
                    y=df_trend["session_rating_avg"],
                    mode="lines+markers",
                    name="Study Session Rating (Avg)",
                    line=dict(color="#7c3aed", dash="dot"),
                )
            )
        fig_prod.update_layout(
            title="Daily Productivity Ratings (1–5 Scale)",
            yaxis=dict(range=[0.5, 5.5], dtick=1),
            height=320,
            margin=dict(l=20, r=20, t=40, b=20),
        )
        st.plotly_chart(fig_prod, use_container_width=True)
    else:
        st.info("No productivity ratings recorded in this period. Add ratings during study sessions or daily check-ins.")


def _render_academic_attendance_tab(start_iso: Optional[str], end_iso: Optional[str]) -> None:
    """Render academic marks analysis and aggregate attendance snapshot."""
    st.subheader("Academic Marks & Attendance Snapshot")

    marks = get_academic_marks_summary(start_date=start_iso, end_date=end_iso)
    att = get_current_attendance_summary()

    att_pct = att["overall_attendance_percentage"]
    att_label = f"{att_pct:.1f}%" if att_pct is not None else "N/A"
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Overall Weighted Marks", f"{marks['overall_weighted_percentage']:.1f}%")
    m2.metric("Assessments Recorded", marks["assessment_count"])
    m3.metric("Overall Attendance", att_label, f"Target: {att['attendance_target']}%")
    m4.metric("Missed Classes", att["total_missed_classes"])

    st.markdown("#### Subject-Wise Marks & Assessment Types")
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        if marks["subject_marks_summary"]:
            df_sm = pd.DataFrame(marks["subject_marks_summary"])
            fig_sm = px.bar(
                df_sm,
                x="subject_name",
                y="weighted_percentage",
                title="Subject-Wise Marks Average (%)",
                text_auto=".1f",
            )
            fig_sm.update_traces(marker_color="#36594A")
            fig_sm.update_layout(
                height=320,
                yaxis_range=[0, 100],
                margin=dict(l=20, r=20, t=40, b=20),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="system-ui, sans-serif", color="#292C28"),
                xaxis=dict(showgrid=False, linecolor="#93897B"),
                yaxis=dict(gridcolor="#D8D0C5", linecolor="#93897B"),
            )
            st.plotly_chart(fig_sm, use_container_width=True)
        else:
            st.info("No marks records found for this period.")

    with col_m2:
        if marks["type_summary"]:
            df_tm = pd.DataFrame(marks["type_summary"])
            fig_tm = px.bar(
                df_tm,
                x="assessment_type",
                y="weighted_percentage",
                title="Marks by Assessment Type (%)",
                text_auto=".1f",
            )
            fig_tm.update_traces(marker_color="#9D563A")
            fig_tm.update_layout(
                height=320,
                yaxis_range=[0, 100],
                margin=dict(l=20, r=20, t=40, b=20),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="system-ui, sans-serif", color="#292C28"),
                xaxis=dict(showgrid=False, linecolor="#93897B"),
                yaxis=dict(gridcolor="#D8D0C5", linecolor="#93897B"),
            )
            st.plotly_chart(fig_tm, use_container_width=True)

    st.markdown("#### Current Attendance Snapshot")
    st.info(att["limitation_note"])
    if att["subject_attendance"]:
        df_att = pd.DataFrame(att["subject_attendance"])
        st.dataframe(
            df_att[
                [
                    "subject_name",
                    "classes_held",
                    "classes_attended",
                    "missed_classes",
                    "attendance_percentage",
                    "status",
                ]
            ].rename(
                columns={
                    "subject_name": "Subject",
                    "classes_held": "Classes Held",
                    "classes_attended": "Classes Attended",
                    "missed_classes": "Missed",
                    "attendance_percentage": "Attendance %",
                    "status": "Status",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )


def _render_assignments_timetable_tab(start_iso: Optional[str], end_iso: Optional[str]) -> None:
    """Render assignment status breakdown and timetable scheduling vs completion."""
    st.subheader("Assignments & Timetable Completion")

    assign = get_assignment_analytics(start_date=start_iso, end_date=end_iso)
    tt = get_timetable_analytics(start_date=start_iso, end_date=end_iso)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Assignments Summary")
        a1, a2, a3 = st.columns(3)
        a1.metric("Assignments", assign["total_assignments"])
        a2.metric("Completed", assign["completed_assignments"])
        a3.metric("Overdue", assign["overdue_assignments"])

        if assign["total_assignments"] > 0:
            df_as = pd.DataFrame(
                [
                    {"Status": "Completed", "Count": assign["completed_assignments"]},
                    {"Status": "In Progress", "Count": assign["in_progress_assignments"]},
                    {"Status": "Pending", "Count": assign["pending_assignments"]},
                ]
            )
            fig_as = px.pie(
                df_as,
                names="Status",
                values="Count",
                hole=0.45,
                title="Assignment Status Distribution",
            )
            fig_as.update_layout(height=280, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_as, use_container_width=True)
        else:
            st.info("No assignments recorded in this period.")

    with col2:
        st.markdown("#### Timetable Performance")
        t1, t2, t3 = st.columns(3)
        t1.metric("Scheduled Sessions", tt["total_scheduled_sessions"])
        t2.metric("Completed", tt["completed_sessions"])
        t3.metric("Timetable Completion", f"{tt['completion_percentage']}%")

        st.caption(
            "Note: Timetable scheduled time is distinct from actual study session time. "
            "Planned sessions do not count as study time unless logged in the Study Tracker."
        )

        if tt["total_scheduled_sessions"] > 0:
            df_tt = pd.DataFrame(
                [
                    {"Status": "Completed", "Count": tt["completed_sessions"]},
                    {"Status": "Planned", "Count": tt["planned_sessions"]},
                    {"Status": "Skipped", "Count": tt["skipped_sessions"]},
                ]
            )
            fig_tt = px.pie(
                df_tt,
                names="Status",
                values="Count",
                hole=0.45,
                title="Timetable Sessions Status",
            )
            fig_tt.update_layout(height=280, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_tt, use_container_width=True)
        else:
            st.info("No timetable sessions scheduled in this period.")


def _render_custom_report_and_export_tab(
    report: Dict[str, Any], start_iso: Optional[str], end_iso: Optional[str]
) -> None:
    """Render printable student progress report view and CSV downloads."""
    st.subheader("Progress Report & CSV Data Export")

    with st.container(border=True):
        st.markdown(f"## {report['report_title']}")
        st.caption(
            f"Student: **{report['student_name']}** | "
            f"Period: **{report['start_date'] or 'All Time'}** to **{report['end_date'] or 'Present'}** | "
            f"Generated: **{report['generated_at']}**"
        )
        st.markdown("---")

        r1, r2, r3, r4 = st.columns(4)
        r1.markdown(f"**Total Study Time:**  \n{report['study_summary']['formatted_study_time']}")
        r2.markdown(f"**Study Sessions:**  \n{report['study_summary']['total_sessions']}")
        r3.markdown(f"**Syllabus Completion:**  \n{report['overview']['overall_syllabus_completion_pct']}%")
        r4.markdown(f"**Weighted Marks:**  \n{report['academic']['overall_weighted_percentage']:.1f}%")

    st.markdown("### CSV Report Downloads")
    st.caption("Export your actual stored records for the selected period into CSV files.")

    c1, c2, c3 = st.columns(3)
    with c1:
        study_rows = export_study_history(start_iso, end_iso)
        st.download_button(
            "Download Study History CSV",
            data=pd.DataFrame(study_rows).to_csv(index=False).encode("utf-8"),
            file_name="campuspulse_study_history.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with c2:
        subj_rows = export_subject_summary(start_iso, end_iso)
        st.download_button(
            "Download Subject Summary CSV",
            data=pd.DataFrame(subj_rows).to_csv(index=False).encode("utf-8"),
            file_name="campuspulse_subject_summary.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with c3:
        topic_rows = export_topic_summary(start_date=start_iso, end_date=end_iso)
        st.download_button(
            "Download Topic Summary CSV",
            data=pd.DataFrame(topic_rows).to_csv(index=False).encode("utf-8"),
            file_name="campuspulse_topic_summary.csv",
            mime="text/csv",
            use_container_width=True,
        )

    c4, c5, c6 = st.columns(3)
    with c4:
        st.download_button(
            "Download Assessments CSV",
            data=pd.DataFrame(report["academic"]["history"]).to_csv(index=False).encode("utf-8"),
            file_name="campuspulse_assessment_history.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with c5:
        st.download_button(
            "Download Assignments CSV",
            data=pd.DataFrame(report["assignments"]["assignments"]).to_csv(index=False).encode("utf-8"),
            file_name="campuspulse_assignment_summary.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with c6:
        st.download_button(
            "Download Timetable History CSV",
            data=pd.DataFrame(report["timetable"]["sessions"]).to_csv(index=False).encode("utf-8"),
            file_name="campuspulse_timetable_history.csv",
            mime="text/csv",
            use_container_width=True,
        )


def main() -> None:
    """Render the Progress Analytics Dashboard page."""
    load_css(STYLES_PATH)
    db_ready = initialize_database()
    render_sidebar(db_ready=db_ready)

    st.title("Student Progress Analytics & Performance Reports")
    st.caption(
        "Comprehensive, multi-period analytics evaluating study consistency, subject and topic progress, "
        "academic assessments, attendance snapshots, and assignment performance."
    )

    subjects = list_subjects()
    if not subjects:
        st.warning("Please add your subjects first in Subjects & Topics to see performance analytics.")
        return

    filter_name, start_iso, end_iso = _render_date_filter_selector()

    report = generate_progress_report(start_date=start_iso, end_date=end_iso)
    _render_overall_overview(report)

    tab_study, tab_subj, tab_topic, tab_cons, tab_acad, tab_asgn, tab_rep = st.tabs(
        [
            "Study Time Analytics",
            "Subject Analytics",
            "Topic Analytics",
            "Consistency & Productivity",
            "Marks & Attendance",
            "Assignments & Timetable",
            "Custom Report & Export",
        ]
    )

    with tab_study:
        _render_study_time_tab(start_iso, end_iso)
    with tab_subj:
        _render_subject_tab(start_iso, end_iso)
    with tab_topic:
        _render_topic_tab(subjects, start_iso, end_iso)
    with tab_cons:
        _render_consistency_productivity_tab(start_iso, end_iso)
    with tab_acad:
        _render_academic_attendance_tab(start_iso, end_iso)
    with tab_asgn:
        _render_assignments_timetable_tab(start_iso, end_iso)
    with tab_rep:
        _render_custom_report_and_export_tab(report, start_iso, end_iso)


if __name__ == "__main__":
    main()
