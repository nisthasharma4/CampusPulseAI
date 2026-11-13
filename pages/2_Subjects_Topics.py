"""Subject Management, Topic Tracker & Learning Journey page for CampusPulse AI."""

from datetime import date
from pathlib import Path
import sys
from typing import Optional
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database.db import initialize_database
from database.queries import VALID_SUBJECT_STATUSES, VALID_TOPIC_STATUSES
from services.subject_service import (
    change_topic_status,
    create_subject,
    create_topic,
    delete_subject,
    delete_topic,
    get_next_sequence_number,
    get_subject_learning_journey,
    get_subject_progress,
    list_subjects,
    list_topics,
    update_subject,
    update_topic_details,
)
from utils.config import APP_NAME, STYLES_PATH
from utils.ui import load_css, render_sidebar


def _parse_date_or_none(value: Optional[str]) -> Optional[date]:
    """Convert YYYY-MM-DD string to date or return None."""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _status_badge_html(status: str) -> str:
    """Return a styled HTML status badge."""
    css_map = {
        "Completed": "badge-completed",
        "In Progress": "badge-in-progress",
        "Not Started": "badge-not-started",
    }
    cls = css_map.get(status, "badge-not-started")
    return f'<span class="badge {cls}">{status}</span>'


def _format_display_date(value: Optional[str], fallback: str = "Not set") -> str:
    """Format YYYY-MM-DD into a readable date like '12 November 2026'."""
    parsed = _parse_date_or_none(value)
    if parsed is None:
        return fallback
    return parsed.strftime("%d %B %Y")


def _render_subjects_tab(subjects: list) -> None:
    """Render Subject Overview Cards, Add Subject, Edit Subject, and Delete Subject."""
    col_add, col_list = st.columns([1, 1.4], gap="large")

    with col_add:
        with st.form("add_subject_form", clear_on_submit=True):
            st.subheader("➕ Add New Subject")
            subj_name = st.text_input("Subject Name *", placeholder="e.g., Data Structures and Algorithms")
            c1, c2 = st.columns(2)
            with c1:
                subj_code = st.text_input("Subject Code (Optional)", placeholder="e.g., CS301")
            with c2:
                semester = st.number_input("Semester", min_value=1, max_value=12, value=3, step=1)

            d1, d2 = st.columns(2)
            with d1:
                start_date = st.date_input("Starting Date (Optional)", value=None)
            with d2:
                target_date = st.date_input("Target Completion Date (Optional)", value=None)

            status = st.selectbox("Subject Status", options=list(VALID_SUBJECT_STATUSES))
            notes = st.text_area("Subject Notes (Optional)", height=70)

            if st.form_submit_button("Add Subject", type="primary", use_container_width=True):
                try:
                    create_subject(
                        subject_name=subj_name,
                        subject_code=subj_code,
                        semester=int(semester),
                        start_date=start_date,
                        target_completion_date=target_date,
                        status=status,
                        notes=notes,
                    )
                    st.session_state["subject_msg"] = f"Subject '{subj_name.strip()}' added!"
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

    with col_list:
        st.subheader("📚 Your Subjects")
        if not subjects:
            st.info("No subjects added yet. Use the form on the left to add your first subject.")
            return

        for subj in subjects:
            sid = int(subj["id"])
            progress = get_subject_progress(sid)
            code_text = f"({subj['subject_code']})" if subj.get("subject_code") else ""
            sem_text = f"Sem {subj['semester']}" if subj.get("semester") else "Semester N/A"

            st.markdown(
                f"""
                <div class="subject-card">
                    <div class="subject-card-header">
                        <div class="subject-card-title">{subj['subject_name']} {code_text}</div>
                        {_status_badge_html(subj['status'])}
                    </div>
                    <p class="subject-meta">
                        {sem_text} • Started: {_format_display_date(subj.get('start_date'))} •
                        Target: {_format_display_date(subj.get('target_completion_date'))} •
                        Topics: {progress['completed_topics']} of {progress['total_topics']} completed ({progress['completion_percentage']:.1f}%)
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.progress(progress["completion_percentage"] / 100.0)

            with st.expander(f"Manage '{subj['subject_name']}'"):
                with st.form(f"edit_subject_{sid}"):
                    e_name = st.text_input("Subject Name *", value=subj["subject_name"], key=f"en_{sid}")
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        e_code = st.text_input("Subject Code", value=subj.get("subject_code") or "", key=f"ec_{sid}")
                    with ec2:
                        e_sem = st.number_input(
                            "Semester",
                            min_value=1,
                            max_value=12,
                            value=int(subj.get("semester") or 1),
                            step=1,
                            key=f"esem_{sid}",
                        )
                    ed1, ed2, ed3 = st.columns(3)
                    with ed1:
                        e_start = st.date_input(
                            "Start Date",
                            value=_parse_date_or_none(subj.get("start_date")),
                            key=f"esd_{sid}",
                        )
                    with ed2:
                        e_target = st.date_input(
                            "Target Date",
                            value=_parse_date_or_none(subj.get("target_completion_date")),
                            key=f"etd_{sid}",
                        )
                    with ed3:
                        e_comp = st.date_input(
                            "Completion Date",
                            value=_parse_date_or_none(subj.get("completion_date")),
                            key=f"ecd_{sid}",
                        )
                    e_status = st.selectbox(
                        "Status",
                        options=list(VALID_SUBJECT_STATUSES),
                        index=list(VALID_SUBJECT_STATUSES).index(subj["status"]),
                        key=f"est_{sid}",
                    )
                    e_notes = st.text_area("Notes", value=subj.get("notes") or "", key=f"eno_{sid}", height=65)

                    if st.form_submit_button("Save Changes", type="primary"):
                        try:
                            update_subject(
                                subject_id=sid,
                                subject_name=e_name,
                                subject_code=e_code,
                                semester=int(e_sem),
                                start_date=e_start,
                                target_completion_date=e_target,
                                completion_date=e_comp,
                                status=e_status,
                                notes=e_notes,
                            )
                            st.session_state["subject_msg"] = f"Subject '{e_name.strip()}' updated!"
                            st.rerun()
                        except ValueError as exc:
                            st.error(str(exc))

                st.warning(
                    "Deleting this subject will also remove its dependent topics, attendance, marks, assignments, and study records."
                )
                confirm_del = st.checkbox(
                    f"Confirm deletion of '{subj['subject_name']}'",
                    key=f"del_chk_subj_{sid}",
                )
                if st.button("🗑️ Delete Subject", key=f"del_btn_subj_{sid}", disabled=not confirm_del):
                    delete_subject(sid)
                    st.session_state["subject_msg"] = f"Subject '{subj['subject_name']}' deleted."
                    st.rerun()


def _render_topics_tab(subjects: list) -> None:
    """Render Topic & Syllabus Progress Tracker for a selected subject."""
    if not subjects:
        st.info("Add a subject in the 'Subjects Manager' tab first to manage its topics.")
        return

    subject_options = {
        f"{s['subject_name']}" + (f" ({s['subject_code']})" if s.get("subject_code") else ""): int(s["id"])
        for s in subjects
    }
    selected_label = st.selectbox("Select Subject", options=list(subject_options.keys()), key="topics_subj_select")
    subject_id = subject_options[selected_label]

    progress = get_subject_progress(subject_id)
    st.markdown(f"### {selected_label} — Syllabus Progress")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Topics", progress["total_topics"])
    m2.metric("Completed", progress["completed_topics"])
    m3.metric("In Progress", progress["in_progress_topics"])
    m4.metric("Pending", progress["pending_topics"])
    m5.metric("Overall Completion", f"{progress['completion_percentage']:.1f}%")
    st.progress(progress["completion_percentage"] / 100.0)

    st.markdown("---")
    col_form, col_topics = st.columns([1, 1.5], gap="large")

    with col_form:
        suggested_seq = get_next_sequence_number(subject_id)
        with st.form("add_topic_form", clear_on_submit=True):
            st.subheader("➕ Add Topic")
            topic_name = st.text_input("Topic Name *", placeholder="e.g., Binary Trees")
            tc1, tc2 = st.columns(2)
            with tc1:
                seq_num = st.number_input("Sequence #", min_value=1, value=suggested_seq, step=1)
            with tc2:
                est_hours = st.number_input("Estimated Hours", min_value=0.0, value=2.0, step=0.5)

            td1, td2 = st.columns(2)
            with td1:
                t_start = st.date_input("Start Date (Optional)", value=None)
            with td2:
                t_target = st.date_input("Planned Completion (Optional)", value=None)

            t_status = st.selectbox("Topic Status", options=list(VALID_TOPIC_STATUSES))
            t_notes = st.text_area("Notes (Optional)", height=65)

            if st.form_submit_button("Add Topic", type="primary", use_container_width=True):
                try:
                    create_topic(
                        subject_id=subject_id,
                        topic_name=topic_name,
                        sequence_number=int(seq_num),
                        start_date=t_start,
                        target_date=t_target,
                        estimated_hours=float(est_hours),
                        status=t_status,
                        notes=t_notes,
                    )
                    st.session_state["subject_msg"] = f"Topic '{topic_name.strip()}' added!"
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

    with col_topics:
        st.subheader("📋 Syllabus Topics")
        topics = list_topics(subject_id)
        if not topics:
            st.info("No topics added for this subject yet.")
            return

        for topic in topics:
            tid = int(topic["id"])
            seq_label = f"#{topic['sequence_number']}" if topic.get("sequence_number") else ""
            st.markdown(
                f"""
                <div class="subject-card">
                    <div class="subject-card-header">
                        <div class="subject-card-title">{seq_label} {topic['topic_name']}</div>
                        {_status_badge_html(topic['status'])}
                    </div>
                    <p class="subject-meta">
                        Est. Hours: {topic.get('estimated_hours') or 0:.1f} hrs •
                        Started: {_format_display_date(topic.get('start_date'), 'Not Started')} •
                        Completed: {_format_display_date(topic.get('completion_date'), 'Not Completed')}
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            b1, b2, _ = st.columns([1, 1, 2])
            with b1:
                if topic["status"] == "Not Started":
                    if st.button("▶️ Start Topic", key=f"start_t_{tid}"):
                        change_topic_status(tid, "In Progress")
                        st.session_state["subject_msg"] = f"Started '{topic['topic_name']}'."
                        st.rerun()
            with b2:
                if topic["status"] != "Completed":
                    if st.button("✅ Mark Completed", key=f"comp_t_{tid}"):
                        change_topic_status(tid, "Completed")
                        st.session_state["subject_msg"] = f"Completed '{topic['topic_name']}'!"
                        st.rerun()

            with st.expander(f"Edit / Delete '{topic['topic_name']}'"):
                with st.form(f"edit_topic_{tid}"):
                    et_name = st.text_input("Topic Name *", value=topic["topic_name"], key=f"etn_{tid}")
                    ec1, ec2, ec3 = st.columns(3)
                    with ec1:
                        et_seq = st.number_input(
                            "Sequence #",
                            min_value=1,
                            value=int(topic.get("sequence_number") or 1),
                            step=1,
                            key=f"ets_{tid}",
                        )
                    with ec2:
                        et_est = st.number_input(
                            "Estimated Hours",
                            min_value=0.0,
                            value=float(topic.get("estimated_hours") or 0.0),
                            step=0.5,
                            key=f"ete_{tid}",
                        )
                    with ec3:
                        et_status = st.selectbox(
                            "Status",
                            options=list(VALID_TOPIC_STATUSES),
                            index=list(VALID_TOPIC_STATUSES).index(topic["status"]),
                            key=f"etst_{tid}",
                        )

                    ed1, ed2, ed3 = st.columns(3)
                    with ed1:
                        et_start = st.date_input(
                            "Start Date",
                            value=_parse_date_or_none(topic.get("start_date")),
                            key=f"etsd_{tid}",
                        )
                    with ed2:
                        et_target = st.date_input(
                            "Planned Completion",
                            value=_parse_date_or_none(topic.get("target_date")),
                            key=f"ettd_{tid}",
                        )
                    with ed3:
                        et_comp = st.date_input(
                            "Completion Date",
                            value=_parse_date_or_none(topic.get("completion_date")),
                            key=f"etcd_{tid}",
                        )

                    et_notes = st.text_area("Notes", value=topic.get("notes") or "", key=f"etno_{tid}", height=60)

                    if st.form_submit_button("Save Topic Changes", type="primary"):
                        try:
                            update_topic_details(
                                topic_id=tid,
                                topic_name=et_name,
                                sequence_number=int(et_seq),
                                start_date=et_start,
                                target_date=et_target,
                                completion_date=et_comp,
                                estimated_hours=float(et_est),
                                status=et_status,
                                notes=et_notes,
                            )
                            st.session_state["subject_msg"] = f"Topic '{et_name.strip()}' updated!"
                            st.rerun()
                        except ValueError as exc:
                            st.error(str(exc))

                confirm_t_del = st.checkbox(
                    f"Confirm deletion of '{topic['topic_name']}'",
                    key=f"del_chk_t_{tid}",
                )
                if st.button("🗑️ Delete Topic", key=f"del_btn_t_{tid}", disabled=not confirm_t_del):
                    delete_topic(tid)
                    st.session_state["subject_msg"] = f"Topic '{topic['topic_name']}' deleted (study history preserved)."
                    st.rerun()


def _render_timeline_tab(subjects: list) -> None:
    """Render the chronological Learning Journey Timeline for a selected subject."""
    if not subjects:
        st.info("Add a subject and topics to view your learning journey timeline.")
        return

    subject_options = {
        f"{s['subject_name']}" + (f" ({s['subject_code']})" if s.get("subject_code") else ""): int(s["id"])
        for s in subjects
    }
    selected_label = st.selectbox("Select Subject for Timeline", options=list(subject_options.keys()), key="timeline_subj_select")
    subject_id = subject_options[selected_label]

    journey = get_subject_learning_journey(subject_id)
    subj = journey["subject"]
    topics = journey["topics"]

    st.markdown(f"### 🗺️ {subj['subject_name']} Learning Journey")
    st.markdown(
        f"**Subject Started:** {_format_display_date(subj.get('start_date'), 'Not Started')} &nbsp;|&nbsp; "
        f"**Status:** {subj['status']}"
    )
    st.markdown("")

    if not topics:
        st.info("No topics added under this subject yet.")
        return

    status_class_map = {
        "Completed": "done",
        "In Progress": "active",
        "Not Started": "pending",
    }

    for topic in topics:
        cls = status_class_map.get(topic["status"], "pending")
        seq = f"#{topic['sequence_number']} " if topic.get("sequence_number") else ""
        started = _format_display_date(topic.get("start_date"), "Not Started")
        completed = _format_display_date(topic.get("completion_date"), "Not Completed")
        actual_hrs = topic.get("actual_study_hours", 0.0)

        st.markdown(
            f"""
            <div class="timeline-item {cls}">
                <div class="subject-card-header">
                    <strong>{seq}{topic['topic_name']}</strong>
                    {_status_badge_html(topic['status'])}
                </div>
                <p class="subject-meta" style="margin-bottom:0;">
                    Started: {started} &nbsp;•&nbsp;
                    Completion Date: {completed} &nbsp;•&nbsp;
                    Actual Study Hours: {actual_hrs:.1f} hrs
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def main() -> None:
    """Render the Subjects & Topics Management page."""
    st.set_page_config(page_title=f"Subjects & Topics | {APP_NAME}", page_icon="📚", layout="wide")
    load_css(STYLES_PATH)
    db_ready = initialize_database()
    render_sidebar(db_ready)

    st.title("📚 Subjects & Topics Management")
    st.caption("Organize your college subjects, track syllabus topics, and monitor your learning journey.")

    if "subject_msg" in st.session_state:
        st.success(st.session_state.pop("subject_msg"))

    subjects = list_subjects()

    tab_subjects, tab_topics, tab_timeline = st.tabs(
        ["📚 Subjects Manager", "📝 Topics & Syllabus", "🗺️ Learning Journey"]
    )

    with tab_subjects:
        _render_subjects_tab(subjects)

    with tab_topics:
        _render_topics_tab(subjects)

    with tab_timeline:
        _render_timeline_tab(subjects)


if __name__ == "__main__":
    main()
