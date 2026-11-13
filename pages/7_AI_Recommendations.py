"""Rule-Based AI Recommendations & Personalized Student Insights page."""

from pathlib import Path
import sys
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database.db import initialize_database
from services.recommendation_service import (
    CATEGORY_LABELS,
    PRIORITY_LABELS,
    calculate_overall_progress_status,
    get_prioritized_recommendations,
)
from utils.config import APP_NAME, STYLES_PATH
from utils.ui import load_css, render_sidebar

PAGE_LINK_LABELS = {
    "pages/2_Subjects_Topics.py": ("Open Subjects & Topics", "📚"),
    "pages/3_Daily_Study_Tracker.py": ("Open Daily Study Tracker", "⏱️"),
    "pages/4_Academic_Performance.py": ("Open Academic Performance", "🎓"),
    "pages/5_Assignments_Reminders.py": ("Open Assignments & Reminders", "📌"),
}

PRIORITY_COLORS = {
    "High Priority": ("#F9E8E6", "#963B32"),
    "Medium Priority": ("#F8EFE3", "#875514"),
    "Low Priority": ("#E4EDF3", "#355C78"),
    "Positive Progress": ("#E6EFE8", "#315B42"),
}


def _render_overall_status(status_info: dict) -> None:
    """Render the Overall Student Progress Status card."""
    status = status_info["status"]
    reasons_html = "".join(f"<li style='margin-bottom: 4px;'>{r}</li>" for r in status_info["reasons"])

    border_color = "#93897B"
    if status == "Excellent Progress":
        border_color = "#315B42"
    elif status == "Good Progress":
        border_color = "#36594A"
    elif status == "Needs Attention":
        border_color = "#963B32"

    st.markdown(
        f"""
        <div class="info-card" style="border-left: 5px solid {border_color}; background-color: #FFFEFA;">
            <h3 style="color: #36594A; margin-bottom: 0.5rem;">🧠 Overall Student Progress Status: <span style="color: {border_color};">{status}</span></h3>
            <ul style="margin: 0.4rem 0 0.6rem 1.2rem; color: #292C28; font-size: 0.92rem; line-height: 1.5;">
                {reasons_html}
            </ul>
            <p style="font-size: 0.85rem; color: #5C5A50; margin-bottom: 0;">
                {status_info['disclaimer']}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_recommendation_card(rec: dict) -> None:
    """Render a single color-coded recommendation card with navigation link."""
    bg_color, text_color = PRIORITY_COLORS.get(
        rec["priority"], ("#f1f5f9", "#64748b")
    )

    st.markdown(
        f"""
        <div class="subject-card" style="border-left: 5px solid {text_color};">
            <div class="subject-card-header">
                <div class="subject-card-title">{rec['title']}</div>
                <span class="badge" style="background-color: {bg_color}; color: {text_color};">
                    {rec['priority']} • {rec['category']}
                </span>
            </div>
            <p class="subject-meta">
                <strong>Explanation:</strong> {rec['description']}<br/>
                <strong>Reason:</strong> {rec['reason']}<br/>
                <strong>Suggested Action:</strong> {rec['suggested_action']}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    target_page = rec.get("target_page")
    if target_page in PAGE_LINK_LABELS:
        label, icon = PAGE_LINK_LABELS[target_page]
        st.page_link(target_page, label=label, icon=icon)


def main() -> None:
    """Render the Rule-Based AI Recommendations page."""
    st.set_page_config(
        page_title=f"AI Recommendations | {APP_NAME}", page_icon="🧠", layout="wide"
    )
    load_css(STYLES_PATH)
    db_ready = initialize_database()
    render_sidebar(db_ready)

    st.title("🧠 Rule-Based AI Recommendations & Insights")
    st.caption(
        "Transparent, explainable Python rules analyzing your real SQLite academic, attendance, assignment, and study records."
    )

    status_info = calculate_overall_progress_status()
    _render_overall_status(status_info)
    st.markdown("---")

    all_recs = get_prioritized_recommendations()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("High Priority", sum(1 for r in all_recs if r["priority"] == "High Priority"))
    c2.metric("Medium Priority", sum(1 for r in all_recs if r["priority"] == "Medium Priority"))
    c3.metric("Low Priority", sum(1 for r in all_recs if r["priority"] == "Low Priority"))
    c4.metric("Positive Progress", sum(1 for r in all_recs if r["priority"] == "Positive Progress"))

    if not all_recs:
        st.info(
            "Not enough academic data yet. Start by setting up **My Profile**, adding **Subjects & Topics**, and logging your study sessions, attendance, or marks."
        )
        return

    fc1, fc2, fc3 = st.columns([1, 1, 1])
    with fc1:
        prio_filter = st.selectbox(
            "Filter by Priority",
            options=["All Recommendations"] + list(PRIORITY_LABELS),
        )
    with fc2:
        cat_filter = st.selectbox(
            "Filter by Category",
            options=["All Categories"] + list(CATEGORY_LABELS),
        )
    with fc3:
        show_all = st.checkbox("Show all recommendations", value=False)

    filtered = all_recs
    if prio_filter != "All Recommendations":
        filtered = [r for r in filtered if r["priority"] == prio_filter]
    if cat_filter != "All Categories":
        filtered = [r for r in filtered if r["category"] == cat_filter]

    if not filtered:
        st.info("No recommendations match the selected filters.")
        return

    display_list = filtered if show_all else filtered[:8]
    st.caption(f"Showing {len(display_list)} of {len(filtered)} recommendation(s)")

    for rec in display_list:
        _render_recommendation_card(rec)


if __name__ == "__main__":
    main()
