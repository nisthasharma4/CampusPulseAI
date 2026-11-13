"""About Project page for CampusPulse AI."""

from __future__ import annotations

from pathlib import Path
import sys

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database.db import initialize_database
from utils.config import (
    APP_DESCRIPTION,
    APP_ICON,
    APP_NAME,
    APP_SUBTITLE,
    APP_TAGLINE,
    DEV_STATUS,
    STYLES_PATH,
)
from utils.ui import load_css, render_sidebar

st.set_page_config(
    page_title=f"About Project | {APP_NAME}",
    page_icon="ℹ️",
    layout="wide",
)


def main() -> None:
    """Render the comprehensive About Project documentation page."""
    load_css(STYLES_PATH)
    db_ready = initialize_database()
    render_sidebar(db_ready=db_ready)

    st.title("About CampusPulse AI")
    st.caption("Comprehensive Project Documentation & Technical Overview — BTech Second-Year Mini Project")

    # Hero Banner
    with st.container(border=True):
        st.markdown(
            f"""
            # {APP_ICON} {APP_NAME}
            ### {APP_SUBTITLE}
            *"{APP_TAGLINE}"*
            
            {APP_DESCRIPTION}
            """
        )
        st.caption(f"Status: **{DEV_STATUS}** | Database: **SQLite (campuspulse.db)** | Framework: **Python & Streamlit**")

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("### 🎯 Problem Statement")
            st.write(
                "College students frequently juggle diverse academic commitments using fragmented, disconnected tools. "
                "Class notes, syllabus PDFs, attendance spreadsheets, physical planners, video playlists, and calendar apps "
                "are maintained across separate systems with no centralized visibility."
            )
            st.write(
                "As a result, students often miss critical assignment deadlines, fall below strict university attendance thresholds, "
                "neglect weaker subjects until exam season, and fail to sustain a consistent daily study routine."
            )

    with col2:
        with st.container(border=True):
            st.markdown("### 💡 Proposed Solution")
            st.write(
                "**CampusPulse AI** provides a unified, 100% local, student-focused academic productivity platform. "
                "It combines syllabus topic tracking, daily study journal logging, aggregate attendance monitoring, "
                "internal assessment marks tracking, deadline reminders, rule-based AI recommendations, a deterministic "
                "smart timetable generator, YouTube study lecture discovery, and multi-period progress analytics."
            )

    st.markdown("### 🧩 Core System Modules")
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(
            """
            **1. Student Profile**  
            Maintains semester, branch, weekly study targets, preferred days, and session/break timing.

            **2. Subjects & Topics**  
            Tracks full syllabus hierarchy, start/target dates, topic completion status, and learning timelines.

            **3. Daily Study Tracker**  
            Logs actual study sessions, productivity ratings, study journal notes, and daily goal check-ins.
            """
        )
    with m2:
        st.markdown(
            """
            **4. Academic Performance**  
            Tracks aggregate attendance counts, class shortage calculations, and weighted assessment marks.

            **5. Assignments & Reminders**  
            Manages assignment deadlines, priority queues, overdue alerts, and completion timestamps.

            **6. College Calendar**  
            Schedules academic events, exams, practicals, holidays, and campus submission dates.
            """
        )
    with m3:
        st.markdown(
            """
            **7. AI Recommendation Engine**  
            Deterministic rule-based insights prioritizing low attendance, overdue tasks, and weak subjects.

            **8. Smart Timetable**  
            Automated conflict-free 7-day study scheduler respecting availability, break times, and calendar events.

            **9. Video Lectures Library**  
            Builds encoded YouTube search URLs by subject/topic/language and curates a personal learning library.
            """
        )
    with m4:
        st.markdown(
            """
            **10. Progress Analytics**  
            Multi-period interactive Plotly analytics, completion duration comparisons, streaks, and UTF-8 CSV exports.

            **11. Main Dashboard**  
            Central control center with live KPIs, today's schedule, priority recommendations, and quick actions.

            **12. About Project**  
            Full architectural specification and demonstration guide for college evaluation.
            """
        )

    st.markdown("---")

    col_arch, col_tech = st.columns([1.2, 1])
    with col_arch:
        with st.container(border=True):
            st.markdown("### 🏗️ System Architecture")
            st.markdown(
                """
                CampusPulse AI is built using a clean 4-tier layered architecture:

                1. **Presentation Layer (Streamlit UI):**  
                   Clean, responsive SaaS dashboard with tabs, KPI cards, custom CSS themes, and Plotly visualizations.
                2. **Application Logic Layer (Python Services):**  
                   Streamlit-independent service modules (`services/`) encapsulating validation, aggregations, and business logic.
                3. **Intelligence Layer (Rule-Based AI Engine):**  
                   Deterministic scoring algorithms for academic priorities and greedy conflict-free scheduling without opaque heuristics.
                4. **Persistence Layer (SQLite Database):**  
                   11 relational tables (`campuspulse.db`) with foreign key constraints, cascade triggers, and performance indexes.
                """
            )

    with col_tech:
        with st.container(border=True):
            st.markdown("### ⚙️ Technology Stack")
            st.markdown(
                """
                - **Language:** Python 3.10+
                - **Web Framework:** Streamlit (Multipage architecture)
                - **Design System:** Design System V4 (Midnight Plum `#272539` & Iris `#5C559A`, Warm Canvas `#F5F3F8`, WCAG 2.2 AA compliant)
                - **Avatar System:** Built-in vector SVG generator, 6 themed SVG presets, and Pillow (PIL) photo thumbnailing
                - **Database:** SQLite3 (Local embedded relational DB)
                - **Data Processing:** Pandas
                - **Visualization:** Plotly Express & Plotly Graph Objects
                - **Testing:** Pytest (with isolated `tmp_path` test fixtures)
                - **Machine Learning / External AI:** **None** (Clean deterministic rule-based algorithms; zero paid API costs, zero privacy leakage)
                """
            )

    st.markdown("---")

    col_ai, col_limit = st.columns(2)
    with col_ai:
        with st.container(border=True):
            st.markdown("### 🧠 Transparent Rule-Based Intelligence")
            st.write(
                "CampusPulse AI intentionally avoids opaque Machine Learning 'black-box' models. "
                "Instead, it implements deterministic, auditable mathematical scoring algorithms:"
            )
            st.markdown(
                """
                - **Weighted Multi-Factor Scoring:** Combines assessment marks percentage, attendance shortage buffers, overdue assignments, pending topics, and upcoming exam dates.
                - **Deterministic Timetable Allocation:** Generates exact, repeatable 7-day study slots based on verified student availability, break spacing, and calendar event avoidance.
                - **Explainable Insights:** Every recommendation explicitly explains the underlying academic reason (e.g. *Attendance at 68% is below your 75% target*).
                """
            )

    with col_limit:
        with st.container(border=True):
            st.markdown("### ⚠️ Current System Limitations")
            st.markdown(
                """
                - **Local SQLite Storage:** Single-user embedded database; multi-device synchronization is not implemented.
                - **In-App Reminders:** Deadline and calendar alerts trigger within the application session rather than OS-level background daemons.
                - **Attendance Snapshot:** Stores aggregate counts (`classes_held`, `classes_attended`); day-by-day attendance trends require dated roll-call records.
                - **YouTube Search Links:** Generates URL-encoded searches; individual video discovery is student-curated without web scraping or API keys.
                """
            )

    st.markdown("---")
    with st.container(border=True):
        st.markdown("### 🚀 Future Roadmap")
        st.markdown(
            """
            - Cross-platform mobile application using Flutter or React Native.
            - Automated cloud synchronization and backup via Supabase or Firebase.
            - Integration with university Learning Management Systems (Moodle, Canvas, Google Classroom).
            - Native desktop push notifications for upcoming deadlines and study sessions.
            - OCR syllabus parser for automatic topic ingestion from university curriculum PDFs.
            """
        )


if __name__ == "__main__":
    main()
