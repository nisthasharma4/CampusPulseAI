"""Daily Study Tracker, Study Journal & Learning History page for CampusPulse AI."""

from datetime import date, time
from pathlib import Path
import sys
from typing import Optional
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database.db import initialize_database
from database.queries import VALID_SESSION_STATUSES
from services.study_service import (
    DATE_FILTER_OPTIONS,
    PRODUCTIVITY_LABELS,
    calculate_duration_from_times,
    calculate_manual_duration,
    create_study_session,
    delete_study_session,
    fetch_sessions,
    format_minutes_hm,
    get_daily_checkin,
    get_date_range_for_filter,
    get_subject_detailed_learning_journey,
    get_subject_study_summary,
    get_today_study_overview,
    get_topic_study_summary,
    list_daily_checkins,
    save_checkin,
    update_study_session,
)
from services.subject_service import list_subjects, list_topics
from utils.config import APP_NAME, STYLES_PATH
from utils.formatters import format_time_12h, format_time_range_12h
from utils.ui import load_css, render_sidebar


def _parse_time_or_default(value: Optional[str], fallback: time) -> time:
    """Parse HH:MM string into a time object."""
    if not value:
        return fallback
    try:
        parts = str(value).split(":")
        return time(int(parts[0]), int(parts[1]))
    except (ValueError, IndexError):
        return fallback


def _format_display_date(value: Optional[str], fallback: str = "—") -> str:
    """Format YYYY-MM-DD into '12 November 2026'."""
    if not value:
        return fallback
    try:
        return date.fromisoformat(value).strftime("%d %B %Y")
    except ValueError:
        return str(value)


def _render_today_overview() -> None:
    """Render Today's Study Overview KPI cards."""
    overview = get_today_study_overview()
    st.subheader(f"📊 Today's Study Overview ({_format_display_date(overview['date'])})")

    if not overview["has_profile"]:
        st.info(
            "No student profile found yet. Visit **My Profile** in the sidebar to set your daily study target."
        )

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Today's Study", format_minutes_hm(overview["studied_minutes"]))
    c2.metric("Sessions", overview["session_count"])
    c3.metric("Completed", overview["completed_count"])
    c4.metric(
        "Avg Productivity",
        f"{overview['avg_productivity_rating']}/5"
        if overview["avg_productivity_rating"] is not None
        else "N/A",
    )
    c5.metric(
        "Daily Target",
        format_minutes_hm(overview["target_minutes"]) if overview["target_minutes"] > 0 else "Not Set",
    )
    c6.metric(
        "Remaining",
        format_minutes_hm(overview["remaining_minutes"]) if overview["target_minutes"] > 0 else "—",
    )

    if overview["target_minutes"] > 0:
        st.progress(overview["target_completion_pct"] / 100.0)
        st.caption(f"Daily Target Completion: {overview['target_completion_pct']:.1f}%")

    if overview["session_count"] == 0:
        st.markdown(
            """
            <div class="onboarding-card">
                <h3>📝 No Study Sessions Recorded Today</h3>
                <p>Use the <strong>Add Study Session</strong> tab below to log what you studied today.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_add_session_tab(subjects: list) -> None:
    """Render the interactive Add Study Session form."""
    if not subjects:
        st.warning("No subjects found. Please add at least one subject in **Subjects & Topics** first.")
        return

    subject_map = {
        f"{s['subject_name']}" + (f" ({s['subject_code']})" if s.get("subject_code") else ""): int(s["id"])
        for s in subjects
    }

    col_sel1, col_sel2, col_sel3 = st.columns(3)
    with col_sel1:
        selected_subj_label = st.selectbox(
            "Select Subject *", options=list(subject_map.keys()), key="add_sess_subj"
        )
        subject_id = subject_map[selected_subj_label]

    topics = list_topics(subject_id)
    topic_options = {"General Subject Study (No specific topic)": None}
    for t in topics:
        seq = f"#{t['sequence_number']} " if t.get("sequence_number") else ""
        topic_options[f"{seq}{t['topic_name']} ({t['status']})"] = int(t["id"])

    with col_sel2:
        selected_topic_label = st.selectbox(
            "Select Topic (Optional)", options=list(topic_options.keys()), key="add_sess_topic"
        )
        topic_id = topic_options[selected_topic_label]

    with col_sel3:
        duration_method = st.radio(
            "Duration Entry Method",
            options=["Start & End Time", "Manual Duration"],
            horizontal=True,
            key="add_sess_dur_method",
        )

    with st.form("add_study_session_form", clear_on_submit=True):
        study_date = st.date_input("Study Date *", value=date.today(), max_value=date.today())

        start_t = None
        end_t = None
        manual_hrs = 1
        manual_mins = 0

        if duration_method == "Start & End Time":
            tc1, tc2 = st.columns(2)
            with tc1:
                start_t = st.time_input("Study Start Time *", value=time(18, 0))
            with tc2:
                end_t = st.time_input("Study End Time *", value=time(19, 0))
        else:
            mc1, mc2 = st.columns(2)
            with mc1:
                manual_hrs = st.number_input("Hours", min_value=0, max_value=16, value=1, step=1)
            with mc2:
                manual_mins = st.number_input("Minutes", min_value=0, max_value=59, value=0, step=5)

        study_goal = st.text_input("What was your study goal today?", placeholder="e.g., Complete Arrays practice problems")
        completed_work = st.text_area("What did you complete?", height=70, placeholder="e.g., Solved 5 array rotation problems")
        next_topic = st.text_input("What will you study next?", placeholder="e.g., Linked Lists basics")

        sc1, sc2 = st.columns(2)
        with sc1:
            status = st.selectbox("Study Status *", options=list(VALID_SESSION_STATUSES))
        with sc2:
            rating_options = [None, 1, 2, 3, 4, 5]
            rating = st.selectbox(
                "Productivity Rating (Optional)",
                options=rating_options,
                format_func=lambda x: "Not Rated" if x is None else PRODUCTIVITY_LABELS[x],
            )

        notes = st.text_area("Personal Notes (Optional)", height=60)

        if st.form_submit_button("💾 Save Study Session", type="primary", use_container_width=True):
            try:
                if duration_method == "Start & End Time":
                    duration_mins = calculate_duration_from_times(start_t, end_t)
                else:
                    duration_mins = calculate_manual_duration(int(manual_hrs), int(manual_mins))

                create_study_session(
                    subject_id=subject_id,
                    study_date=study_date,
                    duration_minutes=duration_mins,
                    topic_id=topic_id,
                    start_time=start_t,
                    end_time=end_t,
                    study_goal=study_goal,
                    completed_work=completed_work,
                    next_topic=next_topic,
                    productivity_rating=rating,
                    status=status,
                    notes=notes,
                )
                st.session_state["study_msg"] = (
                    f"Study session saved ({format_minutes_hm(duration_mins)})!"
                )
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))


def _render_checkin_tab() -> None:
    """Render the Daily Check-in form and recent check-ins."""
    col_form, col_recent = st.columns([1.1, 1], gap="large")

    with col_form:
        checkin_date = st.date_input("Check-in Date", value=date.today(), key="checkin_date_picker")
        existing = get_daily_checkin(checkin_date)

        default_planned = (
            round((existing.get("planned_study_minutes") or 0) / 60.0, 1)
            if existing
            else 2.0
        )
        default_goal_done = bool(existing.get("goal_completed")) if existing else False
        default_rating = int(existing.get("productivity_rating") or 3) if existing else 4
        default_tomorrow = existing.get("tomorrow_plan") or "" if existing else ""
        default_notes = existing.get("notes") or "" if existing else ""

        with st.form("daily_checkin_form"):
            st.subheader("🗓️ Daily Check-in")
            if existing:
                st.caption("A check-in already exists for this date. Submitting will update it.")

            planned_hrs = st.number_input(
                "Planned Study Hours", min_value=0.0, max_value=16.0, value=float(default_planned), step=0.5
            )
            goal_completed = st.checkbox("Did you complete today's study goal?", value=default_goal_done)
            rating = st.selectbox(
                "Today's Productivity Rating (1–5)",
                options=[1, 2, 3, 4, 5],
                index=[1, 2, 3, 4, 5].index(default_rating),
                format_func=lambda x: PRODUCTIVITY_LABELS[x],
            )
            notes = st.text_area(
                "What did you learn today? / Additional Notes",
                value=default_notes,
                height=75,
            )
            tomorrow_plan = st.text_input(
                "What will you study tomorrow?",
                value=default_tomorrow,
                placeholder="e.g., Trees traversal & DBMS normalization",
            )

            if st.form_submit_button("Save Daily Check-in", type="primary", use_container_width=True):
                try:
                    save_checkin(
                        checkin_date=checkin_date,
                        goal_completed=goal_completed,
                        planned_study_hours=float(planned_hrs),
                        tomorrow_plan=tomorrow_plan,
                        productivity_rating=int(rating),
                        notes=notes,
                    )
                    st.session_state["study_msg"] = f"Daily check-in saved for {_format_display_date(checkin_date.isoformat())}!"
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

    with col_recent:
        st.subheader("📓 Recent Check-ins")
        checkins = list_daily_checkins(limit=10)
        if not checkins:
            st.info("No daily check-ins recorded yet.")
            return

        for chk in checkins:
            goal_badge = "Goal Met" if chk["goal_completed"] else "Goal Pending"
            badge_cls = "badge-completed" if chk["goal_completed"] else "badge-in-progress"
            planned_hrs = round((chk.get("planned_study_minutes") or 0) / 60.0, 1)
            st.markdown(
                f"""
                <div class="subject-card">
                    <div class="subject-card-header">
                        <div class="subject-card-title">{_format_display_date(chk['checkin_date'])}</div>
                        <span class="badge {badge_cls}">{goal_badge}</span>
                    </div>
                    <p class="subject-meta">
                        Planned: {planned_hrs:.1f} hrs • Rating: {chk.get('productivity_rating') or '—'}/5<br/>
                        Tomorrow: {chk.get('tomorrow_plan') or '—'}
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _render_history_tab(subjects: list) -> None:
    """Render filterable Study History with Edit and Delete controls."""
    st.subheader("📜 Complete Study History")

    f1, f2, f3, f4 = st.columns(4)
    with f1:
        date_filter = st.selectbox("Time Period", options=list(DATE_FILTER_OPTIONS), key="hist_period")
    with f2:
        subj_choices = {"All Subjects": None}
        for s in subjects:
            subj_choices[s["subject_name"]] = int(s["id"])
        sel_subj_name = st.selectbox("Filter by Subject", options=list(subj_choices.keys()), key="hist_subj")
        filter_subj_id = subj_choices[sel_subj_name]
    with f3:
        topic_choices = {"All Topics": None}
        if filter_subj_id is not None:
            for t in list_topics(filter_subj_id):
                topic_choices[t["topic_name"]] = int(t["id"])
        sel_topic_name = st.selectbox("Filter by Topic", options=list(topic_choices.keys()), key="hist_topic")
        filter_topic_id = topic_choices[sel_topic_name]
    with f4:
        filter_status = st.selectbox(
            "Filter by Status", options=["All"] + list(VALID_SESSION_STATUSES), key="hist_status"
        )

    custom_start, custom_end = None, None
    if date_filter == "Custom Date Range":
        cc1, cc2 = st.columns(2)
        with cc1:
            custom_start = st.date_input("From Date", value=date.today(), key="hist_from")
        with cc2:
            custom_end = st.date_input("To Date", value=date.today(), key="hist_to")

    try:
        start_iso, end_iso = get_date_range_for_filter(
            date_filter, custom_start=custom_start, custom_end=custom_end
        )
    except ValueError as exc:
        st.error(str(exc))
        return

    sessions = fetch_sessions(
        start_date=start_iso,
        end_date=end_iso,
        subject_id=filter_subj_id,
        topic_id=filter_topic_id,
        status=filter_status,
    )

    if not sessions:
        st.info("No study sessions match the selected filters.")
        return

    st.caption(f"Showing {len(sessions)} study session(s)")

    for sess in sessions:
        sid = int(sess["id"])
        topic_label = sess.get("topic_name") or "General Subject Study"
        time_window = (
            format_time_range_12h(sess.get("start_time"), sess.get("end_time"))
            if sess.get("start_time") and sess.get("end_time")
            else "Manual Entry"
        )
        rating_str = f"{sess['productivity_rating']}/5" if sess.get("productivity_rating") else "Not Rated"

        st.markdown(
            f"""
            <div class="subject-card">
                <div class="subject-card-header">
                    <div class="subject-card-title">
                        {_format_display_date(sess['study_date'])} — {sess['subject_name']} ({topic_label})
                    </div>
                    <span class="badge badge-completed">{sess['status']}</span>
                </div>
                <p class="subject-meta">
                    Duration: <strong>{format_minutes_hm(sess['duration_minutes'])}</strong> ({time_window}) •
                    Rating: {rating_str}<br/>
                    Completed: {sess.get('completed_work') or '—'} • Next: {sess.get('next_topic') or '—'}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.expander(f"Edit / Delete Session #{sid}"):
            with st.form(f"edit_session_{sid}"):
                e_date = st.date_input(
                    "Study Date",
                    value=date.fromisoformat(sess["study_date"]),
                    key=f"es_d_{sid}",
                )
                ec1, ec2 = st.columns(2)
                has_times = bool(sess.get("start_time") and sess.get("end_time"))
                with ec1:
                    e_start = st.time_input(
                        "Start Time",
                        value=_parse_time_or_default(sess.get("start_time"), time(18, 0)),
                        key=f"es_st_{sid}",
                    )
                with ec2:
                    e_end = st.time_input(
                        "End Time",
                        value=_parse_time_or_default(sess.get("end_time"), time(19, 0)),
                        key=f"es_et_{sid}",
                    )
                e_use_times = st.checkbox(
                    "Recalculate duration from Start & End Time",
                    value=has_times,
                    key=f"es_ut_{sid}",
                )
                e_manual_mins = st.number_input(
                    "Or Manual Duration (minutes)",
                    min_value=1,
                    value=int(sess["duration_minutes"]),
                    step=5,
                    key=f"es_mm_{sid}",
                )
                e_goal = st.text_input("Study Goal", value=sess.get("study_goal") or "", key=f"es_g_{sid}")
                e_comp = st.text_area("Completed Work", value=sess.get("completed_work") or "", key=f"es_c_{sid}", height=60)
                e_next = st.text_input("Next Topic", value=sess.get("next_topic") or "", key=f"es_nx_{sid}")
                es1, es2 = st.columns(2)
                with es1:
                    e_status = st.selectbox(
                        "Status",
                        options=list(VALID_SESSION_STATUSES),
                        index=list(VALID_SESSION_STATUSES).index(sess["status"]),
                        key=f"es_s_{sid}",
                    )
                with es2:
                    cur_r = sess.get("productivity_rating")
                    r_opts = [None, 1, 2, 3, 4, 5]
                    e_rating = st.selectbox(
                        "Productivity Rating",
                        options=r_opts,
                        index=r_opts.index(cur_r) if cur_r in r_opts else 0,
                        format_func=lambda x: "Not Rated" if x is None else PRODUCTIVITY_LABELS[x],
                        key=f"es_r_{sid}",
                    )
                e_notes = st.text_area("Notes", value=sess.get("notes") or "", key=f"es_n_{sid}", height=55)

                if st.form_submit_button("Save Session Changes", type="primary"):
                    try:
                        if e_use_times:
                            new_dur = calculate_duration_from_times(e_start, e_end)
                            st_val, et_val = e_start, e_end
                        else:
                            new_dur = int(e_manual_mins)
                            st_val, et_val = None, None

                        update_study_session(
                            session_id=sid,
                            subject_id=int(sess["subject_id"]),
                            study_date=e_date,
                            duration_minutes=new_dur,
                            topic_id=sess.get("topic_id"),
                            start_time=st_val,
                            end_time=et_val,
                            study_goal=e_goal,
                            completed_work=e_comp,
                            next_topic=e_next,
                            productivity_rating=e_rating,
                            status=e_status,
                            notes=e_notes,
                        )
                        st.session_state["study_msg"] = f"Study session #{sid} updated!"
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))

            confirm_del = st.checkbox(f"Confirm deletion of session #{sid}", key=f"del_chk_ss_{sid}")
            if st.button("🗑️ Delete Session", key=f"del_btn_ss_{sid}", disabled=not confirm_del):
                delete_study_session(sid)
                st.session_state["study_msg"] = f"Study session #{sid} deleted."
                st.rerun()


def _render_analysis_and_journey_tab(subjects: list) -> None:
    """Render Subject-wise Analysis, Topic-wise Analysis, and Learning Journey."""
    if not subjects:
        st.info("Add subjects and log study sessions to see time analysis and learning journeys.")
        return

    st.subheader("📚 Subject-wise Study Time Analysis")
    subj_summary = get_subject_study_summary()
    if any(s["total_minutes"] > 0 for s in subj_summary):
        df_subj = pd.DataFrame(subj_summary)
        fig = px.bar(
            df_subj,
            x="subject_name",
            y="total_hours_decimal",
            labels={"subject_name": "Subject", "total_hours_decimal": "Total Study Hours"},
            title="Actual Study Hours by Subject",
            color_discrete_sequence=["#0d9488"],
        )
        st.plotly_chart(fig, use_container_width=True)

        display_df = df_subj[
            ["subject_name", "formatted_time", "session_count", "avg_session_minutes"]
        ].rename(
            columns={
                "subject_name": "Subject",
                "formatted_time": "Total Study Time",
                "session_count": "Sessions",
                "avg_session_minutes": "Avg Session (mins)",
            }
        )
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("No study sessions logged yet for subject-wise analysis.")

    st.markdown("---")
    st.subheader("📝 Topic-wise Study Time Analysis")
    topic_summary = get_topic_study_summary()
    if topic_summary:
        df_topic = pd.DataFrame(topic_summary)[
            [
                "subject_name",
                "topic_name",
                "start_date",
                "completion_date",
                "total_hours",
                "session_count",
                "status",
            ]
        ].rename(
            columns={
                "subject_name": "Subject",
                "topic_name": "Topic",
                "start_date": "Start Date",
                "completion_date": "Completion Date",
                "total_hours": "Total Hours",
                "session_count": "Sessions",
                "status": "Status",
            }
        )
        st.dataframe(df_topic, use_container_width=True, hide_index=True)
    else:
        st.info("No topics found yet.")

    st.markdown("---")
    st.subheader("🗺️ Subject Learning Journey")
    subj_opts = {s["subject_name"]: int(s["id"]) for s in subjects}
    sel_journey_subj = st.selectbox("Select Subject", options=list(subj_opts.keys()), key="journey_subj")
    journey = get_subject_detailed_learning_journey(subj_opts[sel_journey_subj])

    subj_info = journey["subject"]
    st.markdown(
        f"**{subj_info['subject_name']}** — Subject Started: {_format_display_date(subj_info.get('start_date'), 'Not Started')}"
    )

    if not journey["sessions"] and not journey["topics"]:
        st.info("No topics or study sessions recorded for this subject yet.")
        return

    if journey["sessions"]:
        st.markdown("**Chronological Study Log:**")
        for s in journey["sessions"]:
            t_name = s.get("topic_name") or "General Subject Study"
            work = f" — {s['completed_work']}" if s.get("completed_work") else ""
            st.markdown(
                f"""
                <div class="timeline-item active">
                    <strong>{_format_display_date(s['study_date'])}</strong>:
                    {t_name} ({format_minutes_hm(s['duration_minutes'])}, {s['status']}){work}
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("No study sessions recorded for this subject yet.")


def main() -> None:
    """Render the Daily Study Tracker & Study Journal page."""
    st.set_page_config(
        page_title=f"Daily Study Tracker | {APP_NAME}", page_icon="⏱️", layout="wide"
    )
    load_css(STYLES_PATH)
    db_ready = initialize_database()
    render_sidebar(db_ready)

    st.title("⏱️ Daily Study Tracker & Study Journal")
    st.caption("Log your daily study sessions, complete daily check-ins, and analyze actual study time.")

    if "study_msg" in st.session_state:
        st.success(st.session_state.pop("study_msg"))

    _render_today_overview()
    st.markdown("---")

    subjects = list_subjects()
    tab_add, tab_checkin, tab_history, tab_analysis = st.tabs(
        [
            "➕ Add Study Session",
            "🗓️ Daily Check-in",
            "📜 Study History",
            "📈 Analysis & Learning Journey",
        ]
    )

    with tab_add:
        _render_add_session_tab(subjects)

    with tab_checkin:
        _render_checkin_tab()

    with tab_history:
        _render_history_tab(subjects)

    with tab_analysis:
        _render_analysis_and_journey_tab(subjects)


if __name__ == "__main__":
    main()
