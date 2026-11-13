"""Assignment Manager and In-App Deadline Reminder page for CampusPulse AI."""

from datetime import date, datetime, time
from pathlib import Path
import sys
from typing import Optional
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database.db import initialize_database
from database.queries import VALID_ASSIGNMENT_STATUSES, VALID_PRIORITIES
from services.assignment_service import (
    ASSIGNMENT_FILTER_OPTIONS,
    create_assignment,
    delete_assignment,
    fetch_active_reminders,
    fetch_assignments,
    get_assignment_overview,
    mark_assignment_completed,
    update_assignment,
)
from services.subject_service import list_subjects
from utils.config import APP_NAME, STYLES_PATH
from utils.formatters import format_time_12h
from utils.ui import load_css, render_sidebar


def _parse_date(value: Optional[str], fallback: date) -> date:
    """Parse YYYY-MM-DD or return fallback."""
    if not value:
        return fallback
    try:
        return date.fromisoformat(value)
    except ValueError:
        return fallback


def _parse_time(value: Optional[str], fallback: time) -> time:
    """Parse HH:MM or return fallback."""
    if not value:
        return fallback
    try:
        parts = value.split(":")
        return time(int(parts[0]), int(parts[1]))
    except (ValueError, IndexError):
        return fallback


def _format_display_date(value: Optional[str], fallback: str = "—") -> str:
    """Format YYYY-MM-DD as '12 November 2026'."""
    if not value:
        return fallback
    try:
        return date.fromisoformat(value).strftime("%d %B %Y")
    except ValueError:
        return str(value)


def _render_overview_and_reminders() -> None:
    """Render Assignment Overview KPIs and active in-app reminders."""
    overview = get_assignment_overview()
    st.subheader("📌 Assignment Overview")

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total", overview["total"])
    c2.metric("Pending", overview["pending"])
    c3.metric("In Progress", overview["in_progress"])
    c4.metric("Completed", overview["completed"])
    c5.metric("Overdue", overview["overdue"])
    c6.metric("Due Today", overview["due_today"])

    st.caption(
        "Note: Reminders are checked locally whenever you open or refresh CampusPulse AI."
    )

    if "dismissed_reminders" not in st.session_state:
        st.session_state["dismissed_reminders"] = set()

    reminders = fetch_active_reminders()
    if reminders:
        for rem in reminders:
            aid = int(rem["id"])
            state = rem["reminder_state"]
            is_overdue = state["category"] == "Overdue"
            if aid in st.session_state["dismissed_reminders"] and not is_overdue:
                continue

            rem_time_info = (
                f" | Reminder: {rem['reminder_at']}" if rem.get("reminder_at") else ""
            )
            msg = (
                f"**{rem['title']}** ({rem['subject_name']}) — "
                f"Deadline: {_format_display_date(rem['deadline_date'])} "
                f"{rem.get('deadline_time') or ''}{rem_time_info} — {state['message']}"
            )
            col_msg, col_btn = st.columns([5, 1])
            with col_msg:
                if state["severity"] == "error":
                    st.error(msg)
                else:
                    st.warning(msg)
            with col_btn:
                if not is_overdue:
                    if st.button("Dismiss", key=f"dismiss_rem_{aid}"):
                        st.session_state["dismissed_reminders"].add(aid)
                        st.rerun()


def _render_add_assignment_tab(subjects: list) -> None:
    """Render the Add New Assignment form."""
    if not subjects:
        st.warning("No subjects found. Add subjects in **Subjects & Topics** first.")
        return

    subject_map = {s["subject_name"]: int(s["id"]) for s in subjects}

    with st.form("add_assignment_form", clear_on_submit=True):
        st.subheader("➕ Add New Assignment")
        title = st.text_input("Assignment Title *", placeholder="e.g., DBMS ER Diagram Report")
        c1, c2, c3 = st.columns(3)
        with c1:
            sel_subj = st.selectbox("Select Subject *", options=list(subject_map.keys()))
        with c2:
            priority = st.selectbox("Priority", options=list(VALID_PRIORITIES), index=1)
        with c3:
            status = st.selectbox("Status", options=list(VALID_ASSIGNMENT_STATUSES))

        d1, d2, d3 = st.columns(3)
        with d1:
            assigned_date = st.date_input("Assigned Date", value=date.today())
        with d2:
            deadline_date = st.date_input("Submission Deadline Date *", value=date.today())
        with d3:
            deadline_time = st.time_input("Submission Time", value=time(23, 59))

        use_reminder = st.checkbox("Set an in-app reminder date and time", value=False)
        rc1, rc2 = st.columns(2)
        with rc1:
            rem_date = st.date_input("Reminder Date", value=date.today())
        with rc2:
            rem_time = st.time_input("Reminder Time", value=time(18, 0))

        description = st.text_area("Description (Optional)", height=70)

        if st.form_submit_button("💾 Save Assignment", type="primary", use_container_width=True):
            try:
                rem_dt = (
                    datetime.combine(rem_date, rem_time) if use_reminder else None
                )
                create_assignment(
                    subject_id=subject_map[sel_subj],
                    title=title,
                    deadline_date=deadline_date,
                    description=description,
                    assigned_date=assigned_date,
                    deadline_time=deadline_time,
                    reminder_at=rem_dt,
                    priority=priority,
                    status=status,
                )
                st.session_state["assign_msg"] = f"Assignment '{title.strip()}' saved!"
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))


def _render_assignment_card_list(items: list, subjects: list, key_prefix: str) -> None:
    """Render a list of assignment cards with quick complete, edit, and delete."""
    if not items:
        st.info("No assignments match the selected view.")
        return

    subject_map = {s["subject_name"]: int(s["id"]) for s in subjects}

    for item in items:
        aid = int(item["id"])
        state = item["reminder_state"]
        days_rem = item["days_remaining"]
        if item["status"] == "Completed":
            rem_text = f"Completed on {_format_display_date((item.get('completed_at') or '')[:10])}"
            badge_cls = "badge-completed"
        elif days_rem < 0:
            rem_text = f"Overdue by {abs(days_rem)} day(s)"
            badge_cls = "badge-in-progress"
        elif days_rem == 0:
            rem_text = "Due Today"
            badge_cls = "badge-in-progress"
        else:
            rem_text = f"{days_rem} day(s) remaining"
            badge_cls = "badge-not-started"

        time_formatted = f" at {format_time_12h(item['deadline_time'])}" if item.get('deadline_time') else ""
        st.markdown(
            f"""
            <div class="subject-card">
                <div class="subject-card-header">
                    <div class="subject-card-title">{item['title']} — {item['subject_name']}</div>
                    <span class="badge {badge_cls}">{item['status']} • {item['priority']}</span>
                </div>
                <p class="subject-meta">
                    Deadline: <strong>{_format_display_date(item['deadline_date'])}</strong>{time_formatted} •
                    Assigned: {_format_display_date(item.get('assigned_date'))} •
                    {rem_text}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if item["status"] != "Completed":
            if st.button("✅ Mark Completed", key=f"{key_prefix}_done_{aid}"):
                mark_assignment_completed(aid)
                st.session_state["assign_msg"] = f"Marked '{item['title']}' as Completed!"
                st.rerun()

        with st.expander(f"Edit / Delete '{item['title']}'", expanded=False):
            with st.form(f"{key_prefix}_edit_{aid}"):
                e_title = st.text_input("Title *", value=item["title"], key=f"{key_prefix}_t_{aid}")
                ec1, ec2, ec3 = st.columns(3)
                subj_names = list(subject_map.keys())
                cur_subj_idx = subj_names.index(item["subject_name"]) if item["subject_name"] in subj_names else 0
                with ec1:
                    e_subj = st.selectbox("Subject", options=subj_names, index=cur_subj_idx, key=f"{key_prefix}_s_{aid}")
                with ec2:
                    e_prio = st.selectbox(
                        "Priority",
                        options=list(VALID_PRIORITIES),
                        index=list(VALID_PRIORITIES).index(item["priority"]),
                        key=f"{key_prefix}_p_{aid}",
                    )
                with ec3:
                    e_stat = st.selectbox(
                        "Status",
                        options=list(VALID_ASSIGNMENT_STATUSES),
                        index=list(VALID_ASSIGNMENT_STATUSES).index(item["status"]),
                        key=f"{key_prefix}_st_{aid}",
                    )

                ed1, ed2, ed3 = st.columns(3)
                with ed1:
                    e_assigned = st.date_input(
                        "Assigned Date",
                        value=_parse_date(item.get("assigned_date"), date.today()),
                        key=f"{key_prefix}_ad_{aid}",
                    )
                with ed2:
                    e_deadline = st.date_input(
                        "Deadline Date",
                        value=_parse_date(item["deadline_date"], date.today()),
                        key=f"{key_prefix}_dd_{aid}",
                    )
                with ed3:
                    e_dtime = st.time_input(
                        "Submission Time",
                        value=_parse_time(item.get("deadline_time"), time(23, 59)),
                        key=f"{key_prefix}_dt_{aid}",
                    )

                has_rem = bool(item.get("reminder_at"))
                e_use_rem = st.checkbox("Enable Reminder", value=has_rem, key=f"{key_prefix}_ur_{aid}")
                er1, er2 = st.columns(2)
                rem_default_dt = (
                    datetime.fromisoformat(item["reminder_at"])
                    if has_rem
                    else datetime.combine(date.today(), time(18, 0))
                )
                with er1:
                    e_rem_d = st.date_input("Reminder Date", value=rem_default_dt.date(), key=f"{key_prefix}_rd_{aid}")
                with er2:
                    e_rem_t = st.time_input("Reminder Time", value=rem_default_dt.time(), key=f"{key_prefix}_rt_{aid}")

                e_desc = st.text_area("Description", value=item.get("description") or "", key=f"{key_prefix}_ds_{aid}", height=60)

                if st.form_submit_button("Save Changes", type="primary"):
                    try:
                        rem_val = datetime.combine(e_rem_d, e_rem_t) if e_use_rem else None
                        update_assignment(
                            assignment_id=aid,
                            subject_id=subject_map[e_subj],
                            title=e_title,
                            deadline_date=e_deadline,
                            description=e_desc,
                            assigned_date=e_assigned,
                            deadline_time=e_dtime,
                            reminder_at=rem_val,
                            priority=e_prio,
                            status=e_stat,
                        )
                        st.session_state["assign_msg"] = f"Assignment '{e_title.strip()}' updated!"
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))

            confirm_del = st.checkbox(
                f"Confirm deletion of '{item['title']}'",
                key=f"{key_prefix}_dc_{aid}",
            )
            if st.button("🗑️ Delete Assignment", key=f"{key_prefix}_db_{aid}", disabled=not confirm_del):
                delete_assignment(aid)
                st.session_state["assign_msg"] = f"Assignment '{item['title']}' deleted."
                st.rerun()


def main() -> None:
    """Render the Assignment Manager & Deadline Reminders page."""
    st.set_page_config(
        page_title=f"Assignments & Reminders | {APP_NAME}", page_icon="📌", layout="wide"
    )
    load_css(STYLES_PATH)
    db_ready = initialize_database()
    render_sidebar(db_ready)

    st.title("📌 Assignment Manager & Deadline Reminders")
    st.caption("Track assignment deadlines, priorities, completion status, and in-app reminders.")

    if "assign_msg" in st.session_state:
        st.success(st.session_state.pop("assign_msg"))

    _render_overview_and_reminders()
    st.markdown("---")

    subjects = list_subjects()
    tab_manage, tab_add, tab_reminders, tab_completed = st.tabs(
        [
            "📋 Manage Assignments",
            "➕ Add New Assignment",
            "🔔 Deadline Reminders",
            "✅ Completed Assignments",
        ]
    )

    with tab_manage:
        fc1, fc2 = st.columns(2)
        with fc1:
            filter_mode = st.selectbox("Filter Assignments", options=list(ASSIGNMENT_FILTER_OPTIONS))
        with fc2:
            subj_opts = {"All Subjects": None}
            for s in subjects:
                subj_opts[s["subject_name"]] = int(s["id"])
            sel_subj_filter = st.selectbox("Filter by Subject", options=list(subj_opts.keys()))

        items = fetch_assignments(
            subject_id=subj_opts[sel_subj_filter], filter_mode=filter_mode
        )
        _render_assignment_card_list(items, subjects, "manage")

    with tab_add:
        _render_add_assignment_tab(subjects)

    with tab_reminders:
        st.subheader("🔔 Active Deadline Reminders")
        active = fetch_active_reminders()
        if not active:
            st.success("No urgent or overdue assignment reminders right now!")
        else:
            _render_assignment_card_list(active, subjects, "rem")

    with tab_completed:
        st.subheader("✅ Completed Assignments")
        completed_items = fetch_assignments(filter_mode="Completed")
        _render_assignment_card_list(completed_items, subjects, "comp")


if __name__ == "__main__":
    main()
