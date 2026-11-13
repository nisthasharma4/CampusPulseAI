"""College Academic Calendar & Combined Upcoming Schedule page."""

from datetime import date, datetime, time
from pathlib import Path
import sys
from typing import Optional
import pandas as pd
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database.db import initialize_database
from database.queries import VALID_EVENT_TYPES
from services.calendar_service import (
    create_calendar_event,
    delete_calendar_event,
    fetch_all_events,
    fetch_events_by_date_range,
    fetch_events_by_month,
    fetch_upcoming_events,
    get_combined_upcoming_schedule,
    update_calendar_event,
)
from utils.config import APP_NAME, STYLES_PATH
from utils.formatters import format_time_12h
from utils.ui import load_css, render_sidebar

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


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
    """Format YYYY-MM-DD into '12 November 2026'."""
    if not value:
        return fallback
    try:
        return date.fromisoformat(value).strftime("%d %B %Y")
    except ValueError:
        return str(value)


def _render_upcoming_and_combined_tab() -> None:
    """Render Upcoming College Events and Combined Schedule (Events + Assignments)."""
    col_left, col_right = st.columns(2, gap="large")

    with col_left:
        st.subheader("📅 Upcoming College Events")
        ev_type = st.selectbox(
            "Filter by Event Type",
            options=["All"] + list(VALID_EVENT_TYPES),
            key="cal_up_type",
        )
        upcoming = fetch_upcoming_events(event_type=ev_type)
        if not upcoming:
            st.info("No upcoming college events found.")
        else:
            for ev in upcoming:
                date_span = _format_display_date(ev["start_date"])
                if ev.get("end_date") and ev["end_date"] != ev["start_date"]:
                    date_span += f" to {_format_display_date(ev['end_date'])}"
                time_str = f" at {format_time_12h(ev['start_time'])}" if ev.get("start_time") else ""
                st.markdown(
                    f"""
                    <div class="subject-card">
                        <div class="subject-card-header">
                            <div class="subject-card-title">{ev['title']}</div>
                            <span class="badge badge-completed">{ev['event_type']}</span>
                        </div>
                        <p class="subject-meta">
                            Date: <strong>{date_span}</strong>{time_str}<br/>
                            {ev.get('description') or ''}
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    with col_right:
        st.subheader("🗓️ Combined Upcoming Schedule")
        st.caption("Pending assignment deadlines and college events in chronological order.")
        combined = get_combined_upcoming_schedule()
        if not combined:
            st.info("No upcoming assignments or college events scheduled.")
        else:
            df = pd.DataFrame(combined)[["date", "time", "source_type", "title", "category", "details"]].rename(
                columns={
                    "date": "Date",
                    "time": "Time",
                    "source_type": "Type",
                    "title": "Title",
                    "category": "Category / Subject",
                    "details": "Details",
                }
            )
            df["Time"] = df["Time"].apply(lambda t: format_time_12h(t) if t else "—")
            st.dataframe(df, use_container_width=True, hide_index=True)


def _render_monthly_and_filter_tab() -> None:
    """Render Monthly View and Date Range Filter."""
    st.subheader("📆 Monthly & Date-Range Calendar View")

    today = date.today()
    mc1, mc2, mc3 = st.columns(3)
    with mc1:
        sel_month_name = st.selectbox("Month", options=MONTH_NAMES, index=today.month - 1)
        sel_month = MONTH_NAMES.index(sel_month_name) + 1
    with mc2:
        sel_year = st.number_input("Year", min_value=2020, max_value=2035, value=today.year, step=1)
    with mc3:
        sel_type = st.selectbox("Event Type", options=["All"] + list(VALID_EVENT_TYPES), key="cal_m_type")

    monthly_events = fetch_events_by_month(int(sel_year), int(sel_month), event_type=sel_type)
    if not monthly_events:
        st.info(f"No events scheduled in {sel_month_name} {sel_year}.")
    else:
        for ev in monthly_events:
            time_part = f" • {format_time_12h(ev['start_time'])}" if ev.get('start_time') else ''
            st.markdown(
                f"""
                <div class="timeline-item active">
                    <strong>{_format_display_date(ev['start_date'])}</strong> —
                    {ev['title']} (<em>{ev['event_type']}</em>)
                    {time_part}
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.subheader("🔍 Filter Events by Date Range")
    dc1, dc2, dc3 = st.columns(3)
    with dc1:
        range_start = st.date_input("From Date", value=today, key="cal_r_start")
    with dc2:
        range_end = st.date_input("To Date", value=today, key="cal_r_end")
    with dc3:
        range_type = st.selectbox("Type", options=["All"] + list(VALID_EVENT_TYPES), key="cal_r_type")

    try:
        range_events = fetch_events_by_date_range(range_start, range_end, event_type=range_type)
        if not range_events:
            st.info("No events found in this date range.")
        else:
            st.dataframe(
                pd.DataFrame(range_events)[["start_date", "end_date", "start_time", "event_type", "title", "description"]],
                use_container_width=True,
                hide_index=True,
            )
    except ValueError as exc:
        st.error(str(exc))


def _render_add_and_manage_tab() -> None:
    """Render Add Event form and Edit/Delete controls."""
    col_add, col_manage = st.columns([1, 1.3], gap="large")

    with col_add:
        with st.form("add_event_form", clear_on_submit=True):
            st.subheader("➕ Add College Event")
            title = st.text_input("Event Title *", placeholder="e.g., Mid-Semester Examination")
            event_type = st.selectbox("Event Type *", options=list(VALID_EVENT_TYPES))
            d1, d2 = st.columns(2)
            with d1:
                start_date = st.date_input("Start Date *", value=date.today())
            with d2:
                end_date = st.date_input("End Date", value=date.today())

            use_time = st.checkbox("Specify Start Time", value=False)
            start_time = st.time_input("Start Time", value=time(9, 30))

            use_rem = st.checkbox("Set Reminder Date & Time", value=False)
            r1, r2 = st.columns(2)
            with r1:
                rem_date = st.date_input("Reminder Date", value=date.today())
            with r2:
                rem_time = st.time_input("Reminder Time", value=time(8, 0))

            desc = st.text_area("Description (Optional)", height=70)

            if st.form_submit_button("💾 Save Event", type="primary", use_container_width=True):
                try:
                    t_val = start_time if use_time else None
                    rem_val = datetime.combine(rem_date, rem_time) if use_rem else None
                    create_calendar_event(
                        title=title,
                        event_type=event_type,
                        start_date=start_date,
                        end_date=end_date,
                        start_time=t_val,
                        description=desc,
                        reminder_at=rem_val,
                    )
                    st.session_state["cal_msg"] = f"Event '{title.strip()}' added!"
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

    with col_manage:
        st.subheader("🗂️ All Saved Events")
        events = fetch_all_events()
        if not events:
            st.info("No college events saved yet.")
            return

        for ev in events:
            eid = int(ev["id"])
            with st.expander(f"{_format_display_date(ev['start_date'])} — {ev['title']} ({ev['event_type']})"):
                with st.form(f"edit_ev_{eid}"):
                    et_title = st.text_input("Title *", value=ev["title"], key=f"evt_{eid}")
                    et_type = st.selectbox(
                        "Event Type",
                        options=list(VALID_EVENT_TYPES),
                        index=list(VALID_EVENT_TYPES).index(ev["event_type"]),
                        key=f"evty_{eid}",
                    )
                    ed1, ed2 = st.columns(2)
                    with ed1:
                        et_sd = st.date_input("Start Date", value=_parse_date(ev["start_date"], date.today()), key=f"evsd_{eid}")
                    with ed2:
                        et_ed = st.date_input(
                            "End Date",
                            value=_parse_date(ev.get("end_date") or ev["start_date"], date.today()),
                            key=f"eved_{eid}",
                        )
                    et_use_t = st.checkbox("Include Start Time", value=bool(ev.get("start_time")), key=f"evut_{eid}")
                    et_st = st.time_input("Start Time", value=_parse_time(ev.get("start_time"), time(9, 30)), key=f"evst_{eid}")
                    et_desc = st.text_area("Description", value=ev.get("description") or "", key=f"evds_{eid}", height=60)

                    if st.form_submit_button("Save Changes", type="primary"):
                        try:
                            update_calendar_event(
                                event_id=eid,
                                title=et_title,
                                event_type=et_type,
                                start_date=et_sd,
                                end_date=et_ed,
                                start_time=et_st if et_use_t else None,
                                description=et_desc,
                                reminder_at=ev.get("reminder_at"),
                            )
                            st.session_state["cal_msg"] = f"Event '{et_title.strip()}' updated!"
                            st.rerun()
                        except ValueError as exc:
                            st.error(str(exc))

                confirm_del = st.checkbox(f"Confirm deletion of '{ev['title']}'", key=f"evdc_{eid}")
                if st.button("🗑️ Delete Event", key=f"evdb_{eid}", disabled=not confirm_del):
                    delete_calendar_event(eid)
                    st.session_state["cal_msg"] = f"Event '{ev['title']}' deleted."
                    st.rerun()


def main() -> None:
    """Render the College Academic Calendar page."""
    st.set_page_config(
        page_title=f"College Calendar | {APP_NAME}", page_icon="📅", layout="wide"
    )
    load_css(STYLES_PATH)
    db_ready = initialize_database()
    render_sidebar(db_ready)

    st.title("📅 College Academic Calendar")
    st.caption("Manage examinations, practicals, holidays, workshops, and view your combined schedule.")

    if "cal_msg" in st.session_state:
        st.success(st.session_state.pop("cal_msg"))

    tab_up, tab_month, tab_manage = st.tabs(
        [
            "🗓️ Upcoming & Combined Schedule",
            "📆 Monthly & Date Filter",
            "➕ Add / Manage Events",
        ]
    )

    with tab_up:
        _render_upcoming_and_combined_tab()

    with tab_month:
        _render_monthly_and_filter_tab()

    with tab_manage:
        _render_add_and_manage_tab()


if __name__ == "__main__":
    main()
