"""Student Profile Management page for CampusPulse AI (Design System V4)."""

from __future__ import annotations

from datetime import time
import html
from pathlib import Path
import sys
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database.db import initialize_database
from services.profile_service import (
    DAYS_OF_WEEK,
    get_profile,
    remove_avatar,
    save_profile,
    set_avatar_preset,
    set_avatar_upload,
)
from utils.avatars import (
    PRESET_AVATARS,
    generate_initials_svg,
    get_avatar_html,
    svg_to_data_uri,
)
from utils.config import (
    APP_NAME,
    ATTENDANCE_TARGET,
    DEFAULT_BREAK_MINUTES,
    DEFAULT_STUDY_SESSION_MINUTES,
    STYLES_PATH,
)
from utils.formatters import format_time_12h, format_time_range_12h
from utils.ui import load_css, render_page_header, render_section_header, render_sidebar


def _render_profile_hero(profile: dict) -> None:
    """Render the top personalized profile hero with avatar and key metadata."""
    avatar_html = get_avatar_html(profile, size=84, border=True)
    name = html.escape(profile.get("name") or "Student")
    college = html.escape(profile.get("college_name") or "CampusPulse AI Academy")
    branch = html.escape(profile.get("branch") or "General Studies")
    semester = profile.get("semester") or 1

    # Avatar mode description
    if profile.get("avatar_path"):
        avatar_type_badge = '<span class="cp-badge cp-badge-success">📷 Custom Photo</span>'
    elif profile.get("avatar_preset"):
        preset_name = PRESET_AVATARS.get(profile["avatar_preset"], {}).get("title", profile["avatar_preset"])
        avatar_type_badge = f'<span class="cp-badge cp-badge-info">🎨 {html.escape(preset_name)}</span>'
    else:
        avatar_type_badge = '<span class="cp-badge cp-badge-neutral">🔤 Initials Avatar</span>'

    st.markdown(
        f"""
        <div class="cp-welcome-card" style="margin-bottom: 1.25rem;">
            <div style="display: flex; align-items: center; gap: 1.5rem; flex-wrap: wrap;">
                <div>{avatar_html}</div>
                <div style="flex: 1; min-width: 240px;">
                    <div style="margin-bottom: 6px;">{avatar_type_badge}</div>
                    <h1 style="margin: 0 0 4px 0; font-size: 1.85rem; color: var(--cp-midnight);">{name}</h1>
                    <div style="font-size: 0.95rem; color: var(--cp-muted); margin-bottom: 6px;">
                        <strong>{branch}</strong> • Semester {semester} • {college}
                    </div>
                    <div style="display: flex; gap: 0.65rem; flex-wrap: wrap;">
                        <span class="cp-badge cp-badge-info">Target: {profile.get('weekly_study_target', 0)} hrs/week</span>
                        <span class="cp-badge cp-badge-warning">Attendance Target: {profile.get('attendance_target', ATTENDANCE_TARGET):.0f}%</span>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_avatar_customizer(profile: dict) -> None:
    """Interactive Avatar Studio: presets, photo upload, and initials preview."""
    with st.expander("✨ Avatar Studio — Customize Your Profile Avatar", expanded=False):
        tab_presets, tab_upload, tab_initials = st.tabs(["🎨 Vector Presets", "📷 Upload Photo", "🔤 Vector Initials"])

        with tab_presets:
            st.markdown(
                "<p style='font-size: 0.9rem; color: var(--cp-muted); margin-bottom: 1rem;'>"
                "Choose from 6 professionally crafted vector presets designed in the Midnight Plum & Iris palette."
                "</p>",
                unsafe_allow_html=True,
            )

            current_preset = profile.get("avatar_preset")
            cols = st.columns(3, gap="medium")

            for idx, (key, data) in enumerate(PRESET_AVATARS.items()):
                col = cols[idx % 3]
                with col:
                    is_active = (current_preset == key and not profile.get("avatar_path"))
                    active_class = "active" if is_active else ""
                    active_badge = "<span class='cp-badge cp-badge-success' style='margin-top:6px;'>Selected</span>" if is_active else ""

                    # Render preview SVG
                    preview_html = get_avatar_html(profile.get("name"), preset=key, size=64)

                    st.markdown(
                        f"""
                        <div class="preset-avatar-card {active_class}">
                            <div>{preview_html}</div>
                            <div style="font-weight: 700; color: var(--cp-midnight); font-size: 0.95rem; margin-top: 8px;">{data['title']}</div>
                            <div style="font-size: 0.78rem; color: var(--cp-muted); margin: 2px 0 6px 0;">{data['description']}</div>
                            {active_badge}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    if st.button(f"Use {data['title']}", key=f"btn_preset_{key}", use_container_width=True):
                        try:
                            set_avatar_preset(key)
                            st.session_state["avatar_flash_msg"] = f"Avatar set to '{data['title']}'."
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))

        with tab_upload:
            st.markdown(
                "<p style='font-size: 0.9rem; color: var(--cp-muted); margin-bottom: 0.85rem;'>"
                "Upload a square student photo (PNG, JPG, or WEBP, max 2.0 MB). It is automatically centered, thumbnail cropped, and stored locally in <code>data/avatars/</code>."
                "</p>",
                unsafe_allow_html=True,
            )

            col_up1, col_up2 = st.columns([2, 1], gap="medium")
            with col_up1:
                uploaded_photo = st.file_uploader(
                    "Select Photo File",
                    type=["png", "jpg", "jpeg", "webp"],
                    help="Max file size 2MB. Square center-crop applied automatically.",
                )
                if uploaded_photo is not None:
                    if st.button("Save Uploaded Photo", type="primary", use_container_width=True):
                        ok, msg = set_avatar_upload(uploaded_photo)
                        if ok:
                            st.session_state["avatar_flash_msg"] = msg
                            st.rerun()
                        else:
                            st.error(msg)

            with col_up2:
                st.markdown("**Current Custom Photo**")
                if profile.get("avatar_path"):
                    st.markdown(get_avatar_html(profile, size=96), unsafe_allow_html=True)
                    if st.button("Remove Custom Photo", key="btn_rm_photo", type="secondary"):
                        remove_avatar()
                        st.session_state["avatar_flash_msg"] = "Custom photo removed."
                        st.rerun()
                else:
                    st.caption("No custom photo uploaded yet.")

        with tab_initials:
            st.markdown(
                "<p style='font-size: 0.9rem; color: var(--cp-muted); margin-bottom: 0.85rem;'>"
                "Revert to a sleek, vector initials avatar generated algorithmically from your student name."
                "</p>",
                unsafe_allow_html=True,
            )
            col_in1, col_in2 = st.columns([1, 2], gap="medium")
            with col_in1:
                init_svg = generate_initials_svg(profile.get("name"), size=80)
                uri = svg_to_data_uri(init_svg)
                st.markdown(
                    f'<img src="{uri}" style="width:80px;height:80px;border-radius:50%;border:2px solid var(--cp-apricot);box-shadow:0 4px 12px rgba(39,37,57,0.15);" />',
                    unsafe_allow_html=True,
                )
            with col_in2:
                st.markdown(f"**Generated Initials for:** {html.escape(profile.get('name') or 'Student')}")
                if st.button("Reset to Default Initials", type="secondary"):
                    remove_avatar()
                    st.session_state["avatar_flash_msg"] = "Avatar reset to default initials."
                    st.rerun()


def _render_profile_cards(profile: dict) -> None:
    """Display saved student profile across three structured cards."""
    col1, col2, col3 = st.columns(3, gap="medium")

    with col1:
        st.markdown(
            f"""
            <div class="cp-card">
                <div style="font-size: 1.05rem; font-weight: 700; color: var(--cp-midnight); margin-bottom: 0.65rem;">
                    👤 Personal Profile
                </div>
                <p><strong>Student Name:</strong> {html.escape(profile.get("name") or "—")}</p>
                <p><strong>College Name:</strong> {html.escape(profile.get("college_name") or "Not specified")}</p>
                <p><strong>Last Updated:</strong> {html.escape(str(profile.get("updated_at") or "—")[:16])}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
            <div class="cp-card">
                <div style="font-size: 1.05rem; font-weight: 700; color: var(--cp-midnight); margin-bottom: 0.65rem;">
                    🎓 Academic Standing
                </div>
                <p><strong>Branch / Department:</strong> {html.escape(profile.get("branch") or "Not specified")}</p>
                <p><strong>Current Semester:</strong> Semester {profile.get("semester") or "—"}</p>
                <p><strong>Attendance Target:</strong> {profile.get("attendance_target", ATTENDANCE_TARGET):.0f}%</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        days_display = ", ".join(profile.get("available_days_list") or []) or "None selected"
        study_window_display = format_time_range_12h(
            profile.get("preferred_start_time"),
            profile.get("preferred_end_time"),
            separator=" to ",
        )
        st.markdown(
            f"""
            <div class="cp-card">
                <div style="font-size: 1.05rem; font-weight: 700; color: var(--cp-midnight); margin-bottom: 0.65rem;">
                    ⏱️ Study Preferences
                </div>
                <p><strong>Weekly Target:</strong> {profile.get("weekly_study_target") or 0} hrs</p>
                <p><strong>Daily Available:</strong> {profile.get("daily_available_hours", 0):.1f} hrs</p>
                <p><strong>Study Window:</strong> {html.escape(study_window_display)}</p>
                <p><strong>Session / Break:</strong> {profile.get("session_duration_minutes") or DEFAULT_STUDY_SESSION_MINUTES} min / {profile.get("break_duration_minutes") or DEFAULT_BREAK_MINUTES} min</p>
                <p><strong>Available Days:</strong> {html.escape(days_display)}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_profile_form(existing: dict | None) -> None:
    """Render the create/edit profile form."""
    is_edit = existing is not None
    form_title = "Edit Student Profile" if is_edit else "Create Your Student Profile"

    default_name = existing.get("name", "") if is_edit else ""
    default_college = existing.get("college_name") or "" if is_edit else ""
    default_branch = existing.get("branch") or "" if is_edit else ""
    default_semester = int(existing.get("semester") or 3) if is_edit else 3
    default_weekly = int(existing.get("weekly_study_target") or 14) if is_edit else 14
    default_daily_hrs = float(existing.get("daily_available_hours") or 2.0) if is_edit else 2.0
    default_start = existing.get("preferred_start_time_obj", time(18, 0)) if is_edit else time(18, 0)
    default_end = existing.get("preferred_end_time_obj", time(21, 0)) if is_edit else time(21, 0)
    default_days = (
        existing.get("available_days_list") or DAYS_OF_WEEK[:5]
        if is_edit
        else DAYS_OF_WEEK[:5]
    )
    default_session = (
        int(existing.get("session_duration_minutes") or DEFAULT_STUDY_SESSION_MINUTES)
        if is_edit
        else DEFAULT_STUDY_SESSION_MINUTES
    )
    default_break = (
        int(existing.get("break_duration_minutes") or DEFAULT_BREAK_MINUTES)
        if is_edit
        else DEFAULT_BREAK_MINUTES
    )
    default_attendance = (
        float(existing.get("attendance_target") or ATTENDANCE_TARGET)
        if is_edit
        else float(ATTENDANCE_TARGET)
    )

    with st.form("student_profile_form"):
        st.subheader(form_title)

        col_a, col_b = st.columns(2, gap="medium")
        with col_a:
            name = st.text_input("Student Name *", value=default_name, placeholder="e.g., Aarav Sharma")
            college_name = st.text_input(
                "College Name (Optional)",
                value=default_college,
                placeholder="e.g., Institute of Technology",
            )
        with col_b:
            branch = st.text_input(
                "Branch / Department",
                value=default_branch,
                placeholder="e.g., Computer Science & Engineering",
            )
            semester = st.number_input(
                "Current Semester *", min_value=1, max_value=12, value=default_semester, step=1
            )

        st.markdown("---")
        st.markdown("**Study Preferences**")

        col_c, col_d, col_e = st.columns(3, gap="medium")
        with col_c:
            weekly_study_target = st.number_input(
                "Weekly Study Target (hours)", min_value=0, max_value=100, value=default_weekly, step=1
            )
            daily_available_hours = st.number_input(
                "Daily Available Study Hours", min_value=0.0, max_value=16.0, value=default_daily_hrs, step=0.5
            )
        with col_d:
            preferred_start_time = st.time_input("Preferred Study Start Time", value=default_start)
            preferred_end_time = st.time_input("Preferred Study End Time", value=default_end)
        with col_e:
            session_duration = st.number_input(
                "Preferred Study Session Duration (min)",
                min_value=15,
                max_value=240,
                value=default_session,
                step=5,
            )
            break_duration = st.number_input(
                "Break Duration (min)", min_value=0, max_value=60, value=default_break, step=5
            )

        col_f, col_g = st.columns([2, 1], gap="medium")
        with col_f:
            available_days = st.multiselect(
                "Available Study Days",
                options=DAYS_OF_WEEK,
                default=default_days,
            )
        with col_g:
            attendance_target = st.number_input(
                "Attendance Target (%)",
                min_value=0.0,
                max_value=100.0,
                value=default_attendance,
                step=1.0,
            )

        submit_label = "Update Profile" if is_edit else "Save Profile"
        submitted = st.form_submit_button(submit_label, type="primary", use_container_width=True)

        if submitted:
            try:
                save_profile(
                    name=name,
                    college_name=college_name,
                    branch=branch,
                    semester=int(semester),
                    weekly_study_target=int(weekly_study_target),
                    daily_available_hours=float(daily_available_hours),
                    preferred_start_time=preferred_start_time,
                    preferred_end_time=preferred_end_time,
                    available_days=available_days,
                    session_duration_minutes=int(session_duration),
                    break_duration_minutes=int(break_duration),
                    attendance_target=float(attendance_target),
                )
                st.session_state["profile_saved_msg"] = (
                    "Student profile updated successfully!"
                    if is_edit
                    else "Student profile created successfully!"
                )
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))


def main() -> None:
    """Render the Student Profile Management page."""
    st.set_page_config(page_title=f"My Profile | {APP_NAME}", page_icon="👤", layout="wide")
    load_css(STYLES_PATH)
    db_ready = initialize_database()
    render_sidebar(db_ready)

    render_page_header(
        "My Student Profile",
        "Manage your academic identity, personal avatar, and study schedule parameters.",
        badge_text="Profile Management",
    )

    if "profile_saved_msg" in st.session_state:
        st.success(st.session_state.pop("profile_saved_msg"))
    if "avatar_flash_msg" in st.session_state:
        st.success(st.session_state.pop("avatar_flash_msg"))

    profile = get_profile()

    if profile is None:
        st.info(
            "No student profile found yet. Complete the form below to set up your profile."
        )
        _render_profile_form(None)
    else:
        _render_profile_hero(profile)
        _render_avatar_customizer(profile)
        _render_profile_cards(profile)
        st.markdown("")
        with st.expander("✏️ Edit Profile Details", expanded=False):
            _render_profile_form(profile)


if __name__ == "__main__":
    main()
