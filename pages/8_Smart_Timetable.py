"""Smart Timetable Generator and Personalized Study Scheduler page."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database.db import initialize_database
from database.queries import VALID_PRIORITIES, VALID_TIMETABLE_STATUSES
from services.profile_service import DAYS_OF_WEEK, get_profile, save_profile
from services.subject_service import list_subjects, list_topics
from services.timetable_service import (
    add_manual_session,
    delete_timetable_session,
    generate_weekly_timetable,
    get_saved_timetable,
    get_student_availability,
    get_timetable_summary,
    has_generated_timetable_in_range,
    normalize_subject_priorities,
    save_generated_timetable,
    update_session_status,
    update_timetable_session,
)
from utils.config import APP_NAME, STYLES_PATH
from utils.formatters import format_time_12h, format_time_range_12h
from utils.ui import load_css, render_sidebar

st.set_page_config(
    page_title=f"Smart Timetable | {APP_NAME}",
    page_icon="🗓️",
    layout="wide",
)


def _parse_time_or_default(time_str: Optional[str], fallback: time) -> time:
    """Parse HH:MM string into a datetime.time object."""
    if not time_str:
        return fallback
    try:
        return datetime.strptime(str(time_str).strip(), "%H:%M").time()
    except ValueError:
        return fallback


def _render_overview(week_start: date, week_end: date) -> None:
    """Display weekly timetable summary metrics."""
    summary = get_timetable_summary(week_start.isoformat(), week_end.isoformat())
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Planned Sessions", summary["total_planned"])
    c2.metric("Completed Sessions", summary["completed"])
    c3.metric("Skipped Sessions", summary["skipped"])
    c4.metric("Scheduled Hours", f"{summary['scheduled_hours']:.1f} hrs")


def _render_availability_settings() -> None:
    """Display and update student study availability synced with student_profile."""
    availability = get_student_availability()
    profile = get_profile()

    with st.expander("Study Availability Settings (Synced with Student Profile)", expanded=not availability["has_profile"]):
        if not availability["has_profile"]:
            st.info(
                "No student profile saved yet. Default study availability is active "
                "until you save your preferences here or on the Profile page."
            )

        with st.form("availability_settings_form"):
            col1, col2 = st.columns(2)
            with col1:
                selected_days = st.multiselect(
                    "Available Study Days",
                    options=DAYS_OF_WEEK,
                    default=[d for d in availability["available_days"] if d in DAYS_OF_WEEK]
                    or DAYS_OF_WEEK,
                )
                pref_start = st.time_input(
                    "Preferred Start Time",
                    value=_parse_time_or_default(availability["preferred_start_time"], time(18, 0)),
                )
                pref_end = st.time_input(
                    "Preferred End Time",
                    value=_parse_time_or_default(availability["preferred_end_time"], time(22, 0)),
                )

            with col2:
                daily_minutes = st.number_input(
                    "Daily Available Study Minutes",
                    min_value=30,
                    max_value=720,
                    value=int(availability["daily_available_minutes"]),
                    step=15,
                )
                weekly_hours = st.number_input(
                    "Weekly Study Target (Hours)",
                    min_value=1.0,
                    max_value=84.0,
                    value=round(availability["weekly_study_target_minutes"] / 60.0, 1),
                    step=0.5,
                )
                session_minutes = st.number_input(
                    "Session Duration (Minutes)",
                    min_value=15,
                    max_value=180,
                    value=int(availability["session_duration_minutes"]),
                    step=15,
                )
                break_minutes = st.number_input(
                    "Break Duration (Minutes)",
                    min_value=0,
                    max_value=60,
                    value=int(availability["break_duration_minutes"]),
                    step=5,
                )

            submitted = st.form_submit_button("Save Availability Settings", type="primary")
            if submitted:
                if not selected_days:
                    st.error("Please select at least one available study day.")
                elif pref_end <= pref_start:
                    st.error("Preferred end time must be after preferred start time.")
                else:
                    try:
                        base_profile = dict(profile) if profile else {}
                        save_profile(
                            name=base_profile.get("name") or "Student",
                            branch=base_profile.get("branch"),
                            semester=int(base_profile.get("semester") or 3),
                            college_name=base_profile.get("college_name"),
                            weekly_study_target=int(round(float(weekly_hours))),
                            daily_available_hours=round(daily_minutes / 60.0, 2),
                            preferred_start_time=pref_start,
                            preferred_end_time=pref_end,
                            available_days=selected_days,
                            session_duration_minutes=int(session_minutes),
                            break_duration_minutes=int(break_minutes),
                            attendance_target=float(
                                base_profile.get("attendance_target") or 75.0
                            ),
                        )
                        st.success("Study availability saved and synchronized with Student Profile.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Could not save availability: {exc}")


def _render_generator_and_preview(subjects: List[Dict[str, Any]]) -> None:
    """Render timetable generation controls and preview/save panel."""
    st.subheader("Generate Smart Weekly Timetable")

    if not subjects:
        st.warning("Add at least one subject on the Subjects & Topics page before generating a timetable.")
        return

    subject_map = {s["id"]: s["subject_name"] for s in subjects}

    col1, col2 = st.columns([1, 2])
    with col1:
        start_date = st.date_input(
            "Timetable Start Date (7-day plan)",
            value=date.today(),
            key="gen_start_date",
        )
    with col2:
        exam_subject_ids = st.multiselect(
            "Optional Priority Exam Subjects",
            options=list(subject_map.keys()),
            format_func=lambda sid: subject_map.get(sid, f"Subject {sid}"),
            help="Boost priority for subjects with upcoming exams or manual focus needs.",
            key="gen_exam_subjects",
        )

    if st.button("Generate Timetable Preview", type="primary"):
        try:
            plan = generate_weekly_timetable(
                current_date=date.today(),
                start_date=start_date,
                exam_subject_ids=exam_subject_ids or None,
            )
            st.session_state["timetable_preview"] = plan
        except Exception as exc:
            st.error(f"Failed to generate timetable: {exc}")

    preview = st.session_state.get("timetable_preview")
    if not preview:
        return

    st.markdown("---")
    st.subheader(f"Timetable Preview ({preview['start_date']} to {preview['end_date']})")

    if preview.get("exam_recommendation"):
        st.info(preview["exam_recommendation"])

    if preview.get("capacity_warning"):
        st.warning(preview["capacity_warning"])

    total_gen_mins = int(preview.get("total_generated_minutes") or 0)
    weekly_target_mins = int(preview.get("weekly_target_minutes") or 0)
    unscheduled_mins = max(0, weekly_target_mins - total_gen_mins)
    sessions = preview.get("sessions") or []

    # A. Preview Summary KPIs
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Generated Study Time", f"{total_gen_mins / 60.0:.1f} hrs")
    m2.metric("Weekly Target", f"{weekly_target_mins / 60.0:.1f} hrs")
    m3.metric("Generated Sessions", len(sessions))
    m4.metric("Unscheduled Target", f"{unscheduled_mins / 60.0:.1f} hrs")

    # B. Subject Priority Scores & Reasons Section
    # Normalize priority data defensively regardless of whether it was stored as list, dict, or string items
    raw_prio = preview.get("subject_allocations")
    if not raw_prio:
        raw_prio = preview.get("subject_priorities")

    canonical_priorities = normalize_subject_priorities(
        priority_data=raw_prio,
        subjects=subjects,
        sessions=sessions,
    )

    with st.expander("Subject Priority Scores & Reasons", expanded=True):
        if canonical_priorities:
            alloc_rows = []
            for item in canonical_priorities:
                alloc_rows.append(
                    {
                        "Subject": item["subject_name"],
                        "Priority": item["priority"],
                        "Score": round(float(item["score"]), 2),
                        "Sessions": int(item["sessions"]),
                        "Hours": round(float(item["hours"]), 2),
                        "Reasons": "; ".join(item.get("reasons") or ["Regular balanced revision"]),
                    }
                )
            st.dataframe(pd.DataFrame(alloc_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No sufficient information to calculate subject priorities yet.")

    # C. Weekly Schedule Preview
    if not sessions:
        st.info("No study sessions could be scheduled in the selected window.")
        return

    preview_rows = []
    for s in sessions:
        s_date_str = s["study_date"]
        try:
            day_str = s.get("day_name") or datetime.strptime(s_date_str, "%Y-%m-%d").strftime("%A")
        except Exception:
            day_str = "—"

        dur_mins = s.get("duration_minutes") or 60
        preview_rows.append(
            {
                "Date": s_date_str,
                "Day": day_str,
                "Time": format_time_range_12h(s.get("start_time"), s.get("end_time")),
                "Duration": f"{dur_mins} min",
                "Subject": s.get("subject_name") or subject_map.get(s["subject_id"], ""),
                "Topic": s.get("topic_name") or "General Review",
                "Session Title": s.get("session_title") or "Study Session",
                "Priority": s.get("priority") or "Medium",
            }
        )

    st.markdown("**Scheduled Sessions Preview**")
    st.dataframe(pd.DataFrame(preview_rows), use_container_width=True, hide_index=True)

    has_existing = has_generated_timetable_in_range(preview["start_date"], preview["end_date"])
    replace_confirmed = True
    if has_existing:
        st.warning(
            "Generated timetable entries already exist in this date range. "
            "Replacing them will remove old uncompleted Generated sessions while preserving Manual and Completed entries."
        )
        replace_confirmed = st.checkbox(
            "Confirm replacing existing Generated timetable entries",
            key="confirm_replace_generated",
        )

    col_save, col_clear = st.columns([1, 1])
    with col_save:
        if st.button(
            "Save Timetable",
            disabled=has_existing and not replace_confirmed,
            key="btn_save_timetable_preview",
            type="primary",
        ):
            try:
                saved_count = save_generated_timetable(
                    sessions=sessions,
                    start_date=preview["start_date"],
                    end_date=preview["end_date"],
                    replace_existing=has_existing,
                )
                st.session_state.pop("timetable_preview", None)
                st.success(f"Saved {saved_count} timetable session(s).")
                st.rerun()
            except Exception as exc:
                st.error(f"Could not save timetable: {exc}")
    with col_clear:
        if st.button("Discard Preview", key="btn_discard_timetable_preview"):
            st.session_state.pop("timetable_preview", None)
            st.rerun()


def _render_saved_timetable(week_start: date, week_end: date, subjects: List[Dict[str, Any]]) -> None:
    """Display saved weekly timetable with filters and status actions."""
    st.subheader(f"Saved Weekly Timetable ({week_start.isoformat()} to {week_end.isoformat()})")

    f1, f2 = st.columns(2)
    with f1:
        subject_options = [None] + [s["id"] for s in subjects]
        subject_map = {s["id"]: s["subject_name"] for s in subjects}
        selected_subject = st.selectbox(
            "Filter by Subject",
            options=subject_options,
            format_func=lambda sid: "All Subjects" if sid is None else subject_map.get(sid, f"Subject {sid}"),
            key="saved_filter_subject",
        )
    with f2:
        selected_status = st.selectbox(
            "Filter by Status",
            options=["All"] + list(VALID_TIMETABLE_STATUSES),
            key="saved_filter_status",
        )

    entries = get_saved_timetable(
        start_date=week_start.isoformat(),
        end_date=week_end.isoformat(),
        subject_id=selected_subject,
        status=None if selected_status == "All" else selected_status,
    )

    if not entries:
        st.info("No saved timetable sessions found for this week and filter selection.")
        return

    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for entry in entries:
        grouped.setdefault(entry["study_date"], []).append(entry)

    for day_str in sorted(grouped.keys()):
        day_label = datetime.strptime(day_str, "%Y-%m-%d").strftime("%A, %b %d, %Y")
        with st.container(border=True):
            st.markdown(f"**{day_label}**")
            for item in grouped[day_str]:
                cols = st.columns([3, 1.5, 1.5, 2])
                with cols[0]:
                    topic_part = f" — {item['topic_name']}" if item.get("topic_name") else ""
                    time_range_fmt = format_time_range_12h(item.get("start_time"), item.get("end_time"))
                    st.markdown(
                        f"**{time_range_fmt}** | "
                        f"{item.get('subject_name', 'Subject')}{topic_part}  \n"
                        f"*{item.get('session_title') or 'Study Session'}*"
                    )
                with cols[1]:
                    st.caption(f"Priority: **{item['priority']}**  \nSource: `{item['source']}`")
                with cols[2]:
                    st.caption(f"Status: **{item['status']}**")
                with cols[3]:
                    b1, b2 = st.columns(2)
                    if item["status"] != "Completed":
                        if b1.button("Complete", key=f"complete_{item['id']}"):
                            update_session_status(item["id"], "Completed")
                            st.rerun()
                    else:
                        if b1.button("Reopen", key=f"reopen_{item['id']}"):
                            update_session_status(item["id"], "Planned")
                            st.rerun()

                    if item["status"] != "Skipped":
                        if b2.button("Skip", key=f"skip_{item['id']}"):
                            update_session_status(item["id"], "Skipped")
                            st.rerun()


def _render_manual_management(week_start: date, week_end: date, subjects: List[Dict[str, Any]]) -> None:
    """Render tabs for adding, editing, or deleting manual/saved timetable sessions."""
    st.subheader("Manage Timetable Sessions")
    if not subjects:
        st.info("Create a subject first before adding timetable sessions.")
        return

    subject_map = {s["id"]: s["subject_name"] for s in subjects}
    tab_add, tab_edit = st.tabs(["Add Manual Session", "Edit / Delete Session"])

    with tab_add:
        add_subject_id = st.selectbox(
            "Subject",
            options=[s["id"] for s in subjects],
            format_func=lambda sid: subject_map.get(sid, f"Subject {sid}"),
            key="manual_add_subject",
        )
        topics = list_topics(subject_id=add_subject_id)
        topic_options = [None] + [t["id"] for t in topics]
        topic_map = {t["id"]: t["topic_name"] for t in topics}

        with st.form("add_manual_session_form"):
            c1, c2 = st.columns(2)
            with c1:
                add_topic_id = st.selectbox(
                    "Topic (Optional)",
                    options=topic_options,
                    format_func=lambda tid: "None / General" if tid is None else topic_map.get(tid, f"Topic {tid}"),
                )
                add_date = st.date_input("Study Date", value=date.today())
                add_priority = st.selectbox("Priority", options=list(VALID_PRIORITIES), index=1)
            with c2:
                add_start = st.time_input("Start Time", value=time(18, 0))
                add_end = st.time_input("End Time", value=time(19, 0))
                add_title = st.text_input("Session Title", placeholder="e.g., Numerical Practice")

            enforce_avail = st.checkbox(
                "Enforce preferred availability hours",
                value=True,
                help="Uncheck to schedule outside your normal study window.",
            )
            if st.form_submit_button("Add Manual Session", type="primary"):
                try:
                    add_manual_session(
                        subject_id=add_subject_id,
                        study_date=add_date.isoformat(),
                        start_time=add_start.strftime("%H:%M"),
                        end_time=add_end.strftime("%H:%M"),
                        topic_id=add_topic_id,
                        session_title=add_title or None,
                        priority=add_priority,
                        enforce_availability=enforce_avail,
                    )
                    st.success("Manual study session added.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not add manual session: {exc}")

    with tab_edit:
        saved_entries = get_saved_timetable(
            start_date=week_start.isoformat(),
            end_date=week_end.isoformat(),
        )
        if not saved_entries:
            st.info("No sessions in the selected week to edit or delete.")
            return

        entry_map = {e["id"]: e for e in saved_entries}
        selected_id = st.selectbox(
            "Select Session",
            options=list(entry_map.keys()),
            format_func=lambda eid: (
                f"{entry_map[eid]['study_date']} {format_time_range_12h(entry_map[eid]['start_time'], entry_map[eid]['end_time'])} "
                f"| {entry_map[eid].get('subject_name', '')} ({entry_map[eid]['status']})"
            ),
            key="edit_session_select",
        )
        current = entry_map[selected_id]
        edit_subject_id = st.selectbox(
            "Subject",
            options=[s["id"] for s in subjects],
            index=[s["id"] for s in subjects].index(current["subject_id"])
            if current["subject_id"] in subject_map
            else 0,
            format_func=lambda sid: subject_map.get(sid, f"Subject {sid}"),
            key="edit_session_subject",
        )
        edit_topics = list_topics(subject_id=edit_subject_id)
        edit_topic_options = [None] + [t["id"] for t in edit_topics]
        edit_topic_map = {t["id"]: t["topic_name"] for t in edit_topics}
        default_topic_idx = (
            edit_topic_options.index(current["topic_id"])
            if current.get("topic_id") in edit_topic_options
            else 0
        )

        with st.form("edit_session_form"):
            ec1, ec2 = st.columns(2)
            with ec1:
                new_topic_id = st.selectbox(
                    "Topic (Optional)",
                    options=edit_topic_options,
                    index=default_topic_idx,
                    format_func=lambda tid: "None / General" if tid is None else edit_topic_map.get(tid, f"Topic {tid}"),
                )
                new_date = st.date_input(
                    "Study Date",
                    value=datetime.strptime(current["study_date"], "%Y-%m-%d").date(),
                )
                new_priority = st.selectbox(
                    "Priority",
                    options=list(VALID_PRIORITIES),
                    index=list(VALID_PRIORITIES).index(current["priority"])
                    if current["priority"] in VALID_PRIORITIES
                    else 1,
                )
            with ec2:
                new_start = st.time_input(
                    "Start Time",
                    value=_parse_time_or_default(current["start_time"], time(18, 0)),
                )
                new_end = st.time_input(
                    "End Time",
                    value=_parse_time_or_default(current["end_time"], time(19, 0)),
                )
                new_title = st.text_input(
                    "Session Title",
                    value=current.get("session_title") or "",
                )

            col_upd, col_del = st.columns(2)
            update_clicked = col_upd.form_submit_button("Update Session", type="primary")
            delete_clicked = col_del.form_submit_button("Delete Session")

            if update_clicked:
                try:
                    update_timetable_session(
                        session_id=selected_id,
                        subject_id=edit_subject_id,
                        study_date=new_date.isoformat(),
                        start_time=new_start.strftime("%H:%M"),
                        end_time=new_end.strftime("%H:%M"),
                        topic_id=new_topic_id,
                        session_title=new_title or None,
                        priority=new_priority,
                    )
                    st.success("Timetable session updated.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not update session: {exc}")

            if delete_clicked:
                try:
                    delete_timetable_session(selected_id)
                    st.success("Timetable session deleted.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not delete session: {exc}")


def main() -> None:
    """Render the Smart Timetable Generator page."""
    load_css(STYLES_PATH)
    db_ready = initialize_database()
    render_sidebar(db_ready=db_ready)

    st.title("Smart Timetable Generator & Study Scheduler")
    st.caption(
        "Deterministic rule-based weekly scheduler prioritizing weak subjects, "
        "low attendance, incomplete topics, assignments, and upcoming exams."
    )

    week_col1, week_col2 = st.columns([1, 3])
    with week_col1:
        week_start = st.date_input(
            "View Week Starting",
            value=date.today(),
            key="timetable_week_start",
        )
    week_end = week_start + timedelta(days=6)
    with week_col2:
        st.info(f"Showing timetable window: **{week_start.isoformat()}** to **{week_end.isoformat()}**")

    subjects = list_subjects()
    _render_overview(week_start, week_end)
    st.markdown("")
    _render_availability_settings()

    tab_gen, tab_saved, tab_manage = st.tabs(
        ["Generate & Preview", "Saved Weekly Timetable", "Add / Edit Sessions"]
    )
    with tab_gen:
        _render_generator_and_preview(subjects)
    with tab_saved:
        _render_saved_timetable(week_start, week_end, subjects)
    with tab_manage:
        _render_manual_management(week_start, week_end, subjects)


if __name__ == "__main__":
    main()
