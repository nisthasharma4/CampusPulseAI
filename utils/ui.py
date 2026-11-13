"""Shared UI helpers for CSS loading, sidebar rendering, and Design System V4 components."""

from __future__ import annotations

from datetime import datetime
import html
from pathlib import Path
from typing import Any, Dict, Optional, Union
import streamlit as st

from utils.avatars import get_avatar_html
from utils.config import APP_ICON, APP_NAME, APP_TAGLINE, DEV_STATUS

# Explicit page definitions for custom sidebar navigation
NAV_PAGES = [
    ("app.py", "Dashboard", "📊"),
    ("pages/1_Profile.py", "My Profile", "👤"),
    ("pages/2_Subjects_Topics.py", "Subjects & Topics", "📚"),
    ("pages/3_Daily_Study_Tracker.py", "Daily Study Tracker", "⏱️"),
    ("pages/4_Academic_Performance.py", "Academic Performance", "🎓"),
    ("pages/5_Assignments_Reminders.py", "Assignments & Reminders", "📌"),
    ("pages/6_College_Calendar.py", "College Calendar", "📅"),
    ("pages/7_AI_Recommendations.py", "AI Recommendations", "🧠"),
    ("pages/8_Smart_Timetable.py", "Smart Timetable", "🗓️"),
    ("pages/9_Video_Lectures.py", "Video Lectures", "🎥"),
    ("pages/10_Progress_Analytics.py", "Progress Analytics", "📈"),
    ("pages/11_About_Project.py", "About Project", "ℹ️"),
]


def load_css(css_path: Path) -> None:
    """Load custom CSS from the assets directory into the Streamlit app."""
    if css_path.exists():
        with open(css_path, "r", encoding="utf-8") as css_file:
            st.markdown(f"<style>{css_file.read()}</style>", unsafe_allow_html=True)


def get_greeting_for_hour(hour: int | None = None) -> str:
    """Return an appropriate dynamic greeting based on time of day."""
    if hour is None:
        hour = datetime.now().hour
    if 5 <= hour < 12:
        return "Good morning"
    elif 12 <= hour < 17:
        return "Good afternoon"
    elif 17 <= hour < 22:
        return "Good evening"
    return "Burning the midnight oil"


def render_sidebar(db_ready: bool, stage_label: str = DEV_STATUS) -> None:
    """Render the top-branded Midnight Plum application sidebar with student info & custom navigation."""
    with st.sidebar:
        # 1. CampusPulse AI branding at the TOP
        st.markdown(
            f"""
            <div class="cp-sidebar-brand">
                <div class="cp-sidebar-brand-name">
                    {APP_ICON} CampusPulse <span class="accent">AI</span>
                </div>
                <div class="cp-sidebar-tagline">Academic Workspace</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 2. Student Mini Profile Card (if student profile exists)
        try:
            from services.profile_service import get_profile
            profile = get_profile()
            if profile and profile.get("name"):
                name = profile["name"]
                branch = profile.get("branch") or "Engineering"
                sem = profile.get("semester")
                sem_text = f"Sem {sem}" if sem else ""
                meta = f"{branch} • {sem_text}" if sem_text else branch
                avatar_html = get_avatar_html(profile, size=40, border=True)
                st.markdown(
                    f"""
                    <div class="cp-sidebar-user">
                        <div>{avatar_html}</div>
                        <div class="cp-sidebar-user-info">
                            <div class="cp-sidebar-user-name" title="{html.escape(name)}">{html.escape(name)}</div>
                            <div class="cp-sidebar-user-meta" title="{html.escape(meta)}">{html.escape(meta)}</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    """
                    <div class="cp-sidebar-user">
                        <div style="font-size: 1.4rem;">👤</div>
                        <div class="cp-sidebar-user-info">
                            <div class="cp-sidebar-user-name">Welcome Student</div>
                            <div class="cp-sidebar-user-meta">Set up profile in My Profile</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        except Exception:
            pass

        st.markdown('<hr class="cp-sidebar-divider" />', unsafe_allow_html=True)

        # 3. Application Navigation Links with explicit Dashboard title
        for page_path, page_title, page_icon in NAV_PAGES:
            st.page_link(page_path, label=page_title, icon=page_icon)

        # 4. System Status card near the bottom
        db_status_text = "Connected" if db_ready else "Offline"
        status_color = "#38684F" if db_ready else "#9A4147"
        st.markdown(
            f"""
            <div class="cp-sidebar-status">
                <div style="font-weight: 650; color: #FAF9F6; margin-bottom: 4px; display: flex; align-items: center; justify-content: space-between;">
                    <span>System Status</span>
                    <span style="font-size: 0.72rem; color: #E9B67D;">v1.0 (DS4)</span>
                </div>
                <div><span style="color: #AFAABF;">Database:</span> <span style="color: {status_color}; font-weight: 650;">{db_status_text}</span></div>
                <div><span style="color: #AFAABF;">Storage:</span> <span style="color: #FAF9F6;">campuspulse.db</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_page_header(title: str, subtitle: str, badge_text: str | None = None) -> None:
    """Render a consistent Design System V4 page header with optional badge."""
    badge_html = (
        f'<span class="cp-badge cp-badge-info" style="margin-bottom: 6px;">{html.escape(badge_text)}</span><br/>'
        if badge_text
        else ""
    )
    st.markdown(
        f"""
        <div class="cp-page-header">
            {badge_html}
            <h1>{html.escape(title)}</h1>
            <p>{html.escape(subtitle)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_header(title: str, subtitle: str | None = None) -> None:
    """Render a section header with optional small subtitle."""
    sub_html = (
        f'<p style="font-size: 0.86rem; color: var(--cp-muted); margin: 0 0 10px 0;">{html.escape(subtitle)}</p>'
        if subtitle
        else ""
    )
    st.markdown(
        f"""
        <div style="margin-top: 1.4rem; margin-bottom: 0.6rem;">
            <div class="cp-section-header" style="margin: 0 0 3px 0;">{html.escape(title)}</div>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_status_badge(text: str, status: str = "neutral") -> str:
    """Return HTML for a status badge using Design System V4 semantic palette."""
    valid_statuses = {"success", "warning", "danger", "info", "neutral"}
    safe_status = status.lower() if status.lower() in valid_statuses else "neutral"
    return f'<span class="cp-badge cp-badge-{safe_status}">{html.escape(text)}</span>'


def render_empty_state(title: str, message: str, icon: str = "📋") -> None:
    """Render a modern empty state callout."""
    st.markdown(
        f"""
        <div class="onboarding-card">
            <div style="font-size: 2.2rem; margin-bottom: 0.6rem;">{icon}</div>
            <div style="font-size: 1.05rem; font-weight: 650; color: var(--cp-midnight); margin-bottom: 0.35rem;">{html.escape(title)}</div>
            <div style="font-size: 0.88rem; color: var(--cp-muted); max-width: 480px; margin: 0 auto; line-height: 1.5;">{html.escape(message)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_info_panel(title: str, text: str, panel_type: str = "info") -> None:
    """Render a high-contrast alert/info card."""
    configs = {
        "info": {"bg": "#EDF3FC", "border": "#C5D8F5", "color": "#4D6593", "icon": "ℹ️"},
        "success": {"bg": "#EAF4EE", "border": "#BEE3CD", "color": "#38684F", "icon": "✅"},
        "warning": {"bg": "#FEF5E9", "border": "#F6D7B2", "color": "#925B1F", "icon": "⚠️"},
        "danger": {"bg": "#FCEEEF", "border": "#F5C2C6", "color": "#9A4147", "icon": "🚨"},
    }
    cfg = configs.get(panel_type.lower(), configs["info"])
    st.markdown(
        f"""
        <div style="background-color: {cfg['bg']}; border: 1px solid {cfg['border']}; border-radius: 8px; padding: 0.9rem 1.1rem; margin: 0.85rem 0;">
            <div style="display: flex; align-items: flex-start; gap: 0.65rem;">
                <span style="font-size: 1.2rem; line-height: 1.3;">{cfg['icon']}</span>
                <div>
                    <div style="font-weight: 650; color: {cfg['color']}; font-size: 0.94rem; margin-bottom: 2px;">{html.escape(title)}</div>
                    <div style="font-size: 0.88rem; color: #282536; line-height: 1.45;">{html.escape(text)}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_enhanced_metric_card(
    label: str,
    value: str,
    delta: Optional[str] = None,
    accent_color: str = "#5C559A",
    icon: str = "📊",
    help_text: Optional[str] = None,
) -> None:
    """Render a custom designed KPI card with visible border, micro-elevation and accent stripe (DS V4.1)."""
    delta_html = ""
    if delta:
        delta_color = "#38684F" if delta.startswith("+") or "completed" in delta.lower() or "met" in delta.lower() else "#925B1F"
        delta_html = f'<div style="font-size: 0.78rem; font-weight: 600; color: {delta_color}; margin-top: 4px;">{html.escape(delta)}</div>'

    help_attr = f'title="{html.escape(help_text)}"' if help_text else ""
    st.markdown(
        f"""
        <div class="cp-kpi-card" style="border-top: 3.5px solid {accent_color}; border: 1.5px solid #D0CBDC; margin-bottom: 0;" {help_attr}>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <span style="font-size: 0.78rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: var(--cp-muted);">{html.escape(label)}</span>
                <span style="font-size: 1.15rem;">{icon}</span>
            </div>
            <div style="font-size: 1.85rem; font-weight: 750; color: var(--cp-midnight); line-height: 1.1;">{html.escape(value)}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def build_subject_card_html(
    subject: Dict[str, Any],
    progress: Optional[Dict[str, Any]] = None,
    study_hours: float = 0.0,
) -> str:
    """Build accessible, high-contrast HTML for a single subject syllabus card (DS V4.1).

    Handles:
    - Multiple topics, all completed, partially completed, or 0 completed.
    - Zero topics added ('No topics added' state with 'Add Topics' badge).
    - Missing or present subject code.
    - Zero or positive logged study hours.
    """
    prog = progress or {}
    raw_name = subject.get("subject_name") or "Subject"
    subject_name = html.escape(str(raw_name))

    raw_code = subject.get("subject_code")
    if raw_code and str(raw_code).strip():
        code_badge = f'<span class="cp-badge cp-badge-neutral" style="font-size: 0.72rem;">{html.escape(str(raw_code).strip())}</span>'
    else:
        code_badge = '<span class="cp-badge cp-badge-neutral" style="font-size: 0.72rem; opacity: 0.6;">No Code</span>'

    total_topics = max(0, int(prog.get("total_topics") or 0))
    completed_topics = max(0, int(prog.get("completed_topics") or 0))
    hours_val = max(0.0, float(study_hours or 0.0))

    if total_topics == 0:
        card_class = "cp-subject-card-v41 empty-topics"
        accent_color = "#E9B67D"
        progress_label = "No topics added"
        pct_display = "0%"
        pct_bar_width = 0.0
        status_badge = '<span class="cp-badge cp-badge-warning" style="font-size: 0.7rem; padding: 1px 6px;">Add Topics</span>'
    else:
        card_class = "cp-subject-card-v41"
        accent_color = "var(--cp-primary)"
        calc_pct = round((completed_topics / total_topics) * 100.0, 1)
        progress_label = f"{completed_topics}/{total_topics} Topics"
        pct_display = f"{calc_pct:.0f}%"
        pct_bar_width = min(100.0, max(0.0, calc_pct))
        if completed_topics >= total_topics:
            status_badge = '<span class="cp-badge cp-badge-success" style="font-size: 0.7rem; padding: 1px 6px;">Completed</span>'
        elif completed_topics > 0:
            status_badge = '<span class="cp-badge cp-badge-warning" style="font-size: 0.7rem; padding: 1px 6px;">In Progress</span>'
        else:
            status_badge = '<span class="cp-badge cp-badge-info" style="font-size: 0.7rem; padding: 1px 6px;">Active</span>'

    # Pure, unindented single-block HTML with no leading whitespace on any line
    return (
        f'<div class="{card_class}" style="border-top: 3.5px solid {accent_color}; min-height: 148px;">'
        f'<div>'
        f'<div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 0.5rem; margin-bottom: 6px;">'
        f'<div style="font-weight: 750; color: var(--cp-midnight); font-size: 1.02rem; line-height: 1.25;">{subject_name}</div>'
        f'{code_badge}'
        f'</div>'
        f'<div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.82rem; color: var(--cp-muted);">'
        f'<span>{progress_label}</span>'
        f'<strong style="color: var(--cp-midnight);">{pct_display}</strong>'
        f'</div>'
        f'<div class="cp-progress-bar-container">'
        f'<div class="cp-progress-bar-fill" style="width: {pct_bar_width}%;"></div>'
        f'</div>'
        f'</div>'
        f'<div style="font-size: 0.78rem; color: var(--cp-muted); margin-top: 6px; display: flex; justify-content: space-between; align-items: center;">'
        f'<span>⏱️ Logged: <strong>{hours_val:.1f} hrs</strong></span>'
        f'{status_badge}'
        f'</div>'
        f'</div>'
    )


def render_subject_card(
    subject: Dict[str, Any],
    progress: Optional[Dict[str, Any]] = None,
    study_hours: float = 0.0,
) -> None:
    """Render a single Subject Progress Card into Streamlit safely without markdown code block escaping."""
    card_html = build_subject_card_html(subject, progress, study_hours)
    if hasattr(st, "html"):
        st.html(card_html)
    else:
        st.markdown(card_html, unsafe_allow_html=True)

