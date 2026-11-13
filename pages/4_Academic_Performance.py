"""Academic Performance, Attendance Tracker, Marks Manager & Weak Subjects page."""

from datetime import date
from pathlib import Path
import sys
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database.db import initialize_database
from services.academic_service import (
    ASSESSMENT_TYPES,
    analyze_weak_subjects,
    calculate_overall_weighted_attendance,
    create_marks_record,
    delete_marks_record,
    fetch_marks_records,
    get_academic_overview,
    get_attendance_by_subject,
    get_attendance_chart_data,
    get_attendance_summary_all_subjects,
    get_attendance_target,
    get_combined_performance_data,
    get_marks_chart_data,
    get_subject_marks_summary,
    update_marks_record,
    upsert_attendance,
)
from services.profile_service import get_profile
from services.subject_service import list_subjects
from utils.config import APP_NAME, MARKS_WEAK_THRESHOLD, STYLES_PATH
from utils.ui import load_css, render_sidebar


def _render_academic_overview(subjects: list) -> None:
    """Render top-level academic KPI cards."""
    overview = get_academic_overview()
    st.subheader("📊 Academic Overview")

    if get_profile() is None:
        st.info(
            "Tip: Set up your **My Profile** page to customize your attendance target percentage."
        )

    if not subjects:
        st.warning(
            "No subjects found yet. Visit **Subjects & Topics** in the sidebar to add your subjects first."
        )

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Subjects", overview["total_subjects"])
    c2.metric(
        "Overall Attendance",
        f"{overview['overall_attendance']:.1f}%"
        if overview["overall_attendance"] is not None
        else "No Data",
    )
    c3.metric(
        "Average Marks",
        f"{overview['overall_marks_average']:.1f}%"
        if overview["overall_marks_average"] is not None
        else "No Data",
    )
    c4.metric("Needing Attention", overview["subjects_needing_attention"])
    c5.metric("Assessments Recorded", overview["total_assessments"])


def _render_attendance_tab(subjects: list) -> None:
    """Render Attendance Tracker, Weighted Overall Attendance, Warnings & Chart."""
    if not subjects:
        st.info("Add subjects first to track attendance.")
        return

    target = get_attendance_target()
    overall = calculate_overall_weighted_attendance()

    st.markdown(f"**Configured Attendance Target:** `{target:.0f}%`")
    oc1, oc2, oc3, oc4 = st.columns(4)
    oc1.metric(
        "Weighted Overall Attendance",
        f"{overall['overall_percentage']:.1f}%"
        if overall["overall_percentage"] is not None
        else "No Data",
    )
    oc2.metric("Total Classes Conducted", overall["total_classes_held"])
    oc3.metric("Total Classes Attended", overall["total_classes_attended"])
    oc4.metric("Total Classes Missed", overall["total_classes_missed"])

    st.markdown("---")
    col_form, col_table = st.columns([1, 1.5], gap="large")

    with col_form:
        subject_map = {s["subject_name"]: int(s["id"]) for s in subjects}
        sel_subj = st.selectbox(
            "Select Subject", options=list(subject_map.keys()), key="att_subj_sel"
        )
        sid = subject_map[sel_subj]
        existing_att = get_attendance_by_subject(sid)
        def_held = int(existing_att["classes_held"]) if existing_att else 0
        def_att = int(existing_att["classes_attended"]) if existing_att else 0

        with st.form("attendance_form"):
            st.subheader("📝 Update Attendance")
            held = st.number_input("Total Classes Conducted", min_value=0, value=def_held, step=1)
            attended = st.number_input("Classes Attended", min_value=0, value=def_att, step=1)

            if st.form_submit_button("💾 Save Attendance", type="primary", use_container_width=True):
                try:
                    upsert_attendance(sid, int(held), int(attended))
                    st.session_state["acad_msg"] = f"Attendance updated for {sel_subj}!"
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

    with col_table:
        st.subheader("📋 Subject-wise Attendance")
        summary = get_attendance_summary_all_subjects(target_percent=target)

        for item in summary:
            pct = item["attendance_percentage"]
            pct_str = f"{pct:.1f}%" if pct is not None else "No attendance recorded yet"
            status = item["status"]
            if status == "Needs Improvement":
                st.error(
                    f"**{item['subject_name']}** — {pct_str} "
                    f"({item['classes_attended']}/{item['classes_held']}) | "
                    f"{item['required_info']['message']}"
                )
            elif status == "Close to Target":
                st.warning(
                    f"**{item['subject_name']}** — {pct_str} (Close to {target:.0f}% target)"
                )

        table_rows = [
            {
                "Subject": r["subject_name"],
                "Total Classes": r["classes_held"],
                "Attended": r["classes_attended"],
                "Missed": r["missed_classes"],
                "Attendance %": f"{r['attendance_percentage']:.1f}%"
                if r["attendance_percentage"] is not None
                else "No attendance recorded yet.",
                "Status": r["status"],
                "Action / Target": r["required_info"]["message"],
            }
            for r in summary
        ]
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

    chart_data = get_attendance_chart_data()
    if chart_data:
        df_att = pd.DataFrame(chart_data)
        fig = px.bar(
            df_att,
            x="subject_name",
            y="attendance_percentage",
            color="status",
            labels={"subject_name": "Subject", "attendance_percentage": "Attendance (%)"},
            title="Subject-wise Attendance Comparison",
            color_discrete_map={
                "Good": "#315B42",
                "Close to Target": "#875514",
                "Needs Improvement": "#963B32",
            },
        )
        fig.add_hline(y=target, line_dash="dash", line_color="#292C28", annotation_text=f"Target {target:.0f}%")
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="system-ui, sans-serif", color="#292C28"),
            xaxis=dict(showgrid=False, linecolor="#93897B"),
            yaxis=dict(gridcolor="#D8D0C5", linecolor="#93897B"),
        )
        st.plotly_chart(fig, use_container_width=True)


def _render_marks_tab(subjects: list) -> None:
    """Render Internal Marks entry, weighted subject summary, and record management."""
    if not subjects:
        st.info("Add subjects first to record marks.")
        return

    col_form, col_summary = st.columns([1, 1.4], gap="large")
    subject_map = {s["subject_name"]: int(s["id"]) for s in subjects}

    with col_form:
        with st.form("add_marks_form", clear_on_submit=True):
            st.subheader("➕ Record Assessment Marks")
            sel_subj = st.selectbox("Select Subject *", options=list(subject_map.keys()))
            assess_type = st.selectbox("Assessment Type *", options=list(ASSESSMENT_TYPES))
            mc1, mc2 = st.columns(2)
            with mc1:
                marks_obt = st.number_input("Marks Obtained *", min_value=0.0, value=0.0, step=0.5)
            with mc2:
                max_marks = st.number_input("Maximum Marks *", min_value=0.5, value=25.0, step=0.5)
            assess_date = st.date_input("Assessment Date", value=date.today())
            notes = st.text_area("Notes (Optional)", height=60)

            if st.form_submit_button("💾 Save Marks", type="primary", use_container_width=True):
                try:
                    create_marks_record(
                        subject_id=subject_map[sel_subj],
                        assessment_type=assess_type,
                        marks_obtained=float(marks_obt),
                        maximum_marks=float(max_marks),
                        assessment_date=assess_date,
                        notes=notes,
                    )
                    st.session_state["acad_msg"] = f"Saved {assess_type} marks for {sel_subj}!"
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

    with col_summary:
        st.subheader("📊 Subject-wise Weighted Marks")
        marks_summary = get_subject_marks_summary()
        rows = [
            {
                "Subject": m["subject_name"],
                "Assessments": m["total_assessments"],
                "Obtained": m["total_obtained"],
                "Maximum": m["total_maximum"],
                "Weighted Average": f"{m['weighted_percentage']:.1f}%"
                if m["weighted_percentage"] is not None
                else "No assessment records available.",
            }
            for m in marks_summary
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("🗂️ Assessment Records History")
    fc1, fc2 = st.columns(2)
    with fc1:
        f_subj_opts = {"All Subjects": None, **subject_map}
        f_subj_name = st.selectbox("Filter by Subject", options=list(f_subj_opts.keys()), key="mk_f_subj")
    with fc2:
        f_type = st.selectbox("Filter by Assessment Type", options=["All"] + list(ASSESSMENT_TYPES), key="mk_f_type")

    records = fetch_marks_records(
        subject_id=f_subj_opts[f_subj_name], assessment_type=f_type
    )
    if not records:
        st.info("No assessment records match the selected filters.")
        return

    for rec in records:
        mid = int(rec["id"])
        st.markdown(
            f"""
            <div class="subject-card">
                <div class="subject-card-header">
                    <div class="subject-card-title">{rec['subject_name']} — {rec['assessment_type']}</div>
                    <span class="badge badge-completed">{rec['percentage']:.1f}%</span>
                </div>
                <p class="subject-meta">
                    Marks: <strong>{rec['marks_obtained']} / {rec['maximum_marks']}</strong> •
                    Date: {rec.get('assessment_date') or 'Not set'} •
                    Notes: {rec.get('notes') or '—'}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.expander(f"Edit / Delete Record #{mid}"):
            with st.form(f"edit_mark_{mid}"):
                ec1, ec2, ec3 = st.columns(3)
                with ec1:
                    e_type = st.selectbox(
                        "Assessment Type",
                        options=list(ASSESSMENT_TYPES),
                        index=list(ASSESSMENT_TYPES).index(rec["assessment_type"])
                        if rec["assessment_type"] in ASSESSMENT_TYPES
                        else 0,
                        key=f"emt_{mid}",
                    )
                with ec2:
                    e_obt = st.number_input(
                        "Marks Obtained", min_value=0.0, value=float(rec["marks_obtained"]), step=0.5, key=f"emo_{mid}"
                    )
                with ec3:
                    e_max = st.number_input(
                        "Maximum Marks", min_value=0.5, value=float(rec["maximum_marks"]), step=0.5, key=f"emm_{mid}"
                    )
                e_date_val = (
                    date.fromisoformat(rec["assessment_date"])
                    if rec.get("assessment_date")
                    else date.today()
                )
                e_date = st.date_input("Assessment Date", value=e_date_val, key=f"emd_{mid}")
                e_notes = st.text_input("Notes", value=rec.get("notes") or "", key=f"emn_{mid}")

                if st.form_submit_button("Save Changes", type="primary"):
                    try:
                        update_marks_record(
                            mark_id=mid,
                            subject_id=int(rec["subject_id"]),
                            assessment_type=e_type,
                            marks_obtained=float(e_obt),
                            maximum_marks=float(e_max),
                            assessment_date=e_date,
                            notes=e_notes,
                        )
                        st.session_state["acad_msg"] = f"Marks record #{mid} updated!"
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))

            confirm_del = st.checkbox(f"Confirm deletion of record #{mid}", key=f"del_chk_mk_{mid}")
            if st.button("🗑️ Delete Record", key=f"del_btn_mk_{mid}", disabled=not confirm_del):
                delete_marks_record(mid)
                st.session_state["acad_msg"] = f"Marks record #{mid} deleted."
                st.rerun()


def _render_weak_subjects_tab(subjects: list) -> None:
    """Render Weak Subject Identification with configurable marks threshold."""
    if not subjects:
        st.info("Add subjects and record marks/attendance to analyze weak subjects.")
        return

    st.subheader("🎯 Weak Subject Identification")
    threshold = st.slider(
        "Marks Performance Threshold (%)",
        min_value=30.0,
        max_value=90.0,
        value=float(MARKS_WEAK_THRESHOLD),
        step=5.0,
    )
    att_target = get_attendance_target()
    st.caption(f"Evaluating against Marks Threshold: {threshold:.0f}% | Attendance Target: {att_target:.0f}%")

    analysis = analyze_weak_subjects(marks_threshold=threshold, attendance_target=att_target)
    for item in analysis:
        status = item["performance_status"]
        marks_str = f"{item['average_marks']:.1f}%" if item["average_marks"] is not None else "No Marks"
        att_str = f"{item['attendance_percentage']:.1f}%" if item["attendance_percentage"] is not None else "No Attendance"

        badge_cls = "badge-completed"
        if status == "Needs Attention":
            badge_cls = "badge-in-progress"
        elif status == "Insufficient Data":
            badge_cls = "badge-not-started"

        st.markdown(
            f"""
            <div class="subject-card">
                <div class="subject-card-header">
                    <div class="subject-card-title">{item['subject_name']}</div>
                    <span class="badge {badge_cls}">{status}</span>
                </div>
                <p class="subject-meta">
                    Average Marks: <strong>{marks_str}</strong> •
                    Attendance: <strong>{att_str}</strong><br/>
                    Reason: {item['reason']}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_analytics_tab(subjects: list) -> None:
    """Render the 4 interactive Plotly Performance Analytics charts."""
    if not subjects:
        st.info("Add subjects and academic records to view analytics.")
        return

    st.subheader("📈 Academic Performance Analytics")

    att_data = get_attendance_chart_data()
    marks_data = get_marks_chart_data()
    combined_data = get_combined_performance_data()
    all_marks = fetch_marks_records()

    col1, col2 = st.columns(2, gap="medium")
    with col1:
        if att_data:
            fig_att = px.bar(
                pd.DataFrame(att_data),
                x="subject_name",
                y="attendance_percentage",
                title="1. Subject-wise Attendance Comparison",
                labels={"subject_name": "Subject", "attendance_percentage": "Attendance (%)"},
                color_discrete_sequence=["#36594A"],
            )
            fig_att.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="system-ui, sans-serif", color="#292C28"),
                xaxis=dict(showgrid=False, linecolor="#93897B"),
                yaxis=dict(gridcolor="#D8D0C5", linecolor="#93897B"),
            )
            st.plotly_chart(fig_att, use_container_width=True)
        else:
            st.info("No attendance records available for Attendance Comparison chart.")

    with col2:
        if marks_data:
            fig_mk = px.bar(
                pd.DataFrame(marks_data),
                x="subject_name",
                y="weighted_percentage",
                title="2. Subject-wise Internal Marks (Weighted %)",
                labels={"subject_name": "Subject", "weighted_percentage": "Weighted Marks (%)"},
                color_discrete_sequence=["#9D563A"],
            )
            fig_mk.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="system-ui, sans-serif", color="#292C28"),
                xaxis=dict(showgrid=False, linecolor="#93897B"),
                yaxis=dict(gridcolor="#D8D0C5", linecolor="#93897B"),
            )
            st.plotly_chart(fig_mk, use_container_width=True)
        else:
            st.info("No marks records available for Internal Marks chart.")

    col3, col4 = st.columns(2, gap="medium")
    with col3:
        if combined_data:
            fig_comb = px.scatter(
                pd.DataFrame(combined_data),
                x="attendance_percentage",
                y="average_marks",
                text="subject_name",
                title="3. Attendance vs Academic Performance",
                labels={
                    "attendance_percentage": "Attendance (%)",
                    "average_marks": "Weighted Marks (%)",
                },
                color_discrete_sequence=["#36594A"],
            )
            fig_comb.update_traces(textposition="top center", marker=dict(size=12))
            fig_comb.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="system-ui, sans-serif", color="#292C28"),
                xaxis=dict(showgrid=False, linecolor="#93897B"),
                yaxis=dict(gridcolor="#D8D0C5", linecolor="#93897B"),
            )
            st.plotly_chart(fig_comb, use_container_width=True)
        else:
            st.info("Record both attendance and marks for at least one subject to view Attendance vs Marks.")

    with col4:
        if all_marks:
            fig_assess = px.bar(
                pd.DataFrame(all_marks),
                x="subject_name",
                y="percentage",
                color="assessment_type",
                barmode="group",
                title="4. Assessment Performance by Subject",
                labels={"subject_name": "Subject", "percentage": "Score (%)"},
                color_discrete_sequence=["#36594A", "#9D563A", "#355C78", "#875514"],
            )
            fig_assess.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="system-ui, sans-serif", color="#292C28"),
                xaxis=dict(showgrid=False, linecolor="#93897B"),
                yaxis=dict(gridcolor="#D8D0C5", linecolor="#93897B"),
            )
            st.plotly_chart(fig_assess, use_container_width=True)
        else:
            st.info("No individual assessment records available yet.")


def main() -> None:
    """Render the Academic Performance Management page."""
    st.set_page_config(
        page_title=f"Academic Performance | {APP_NAME}", page_icon="🎓", layout="wide"
    )
    load_css(STYLES_PATH)
    db_ready = initialize_database()
    render_sidebar(db_ready)

    st.title("🎓 Academic Performance, Attendance & Marks")
    st.caption("Monitor subject-wise attendance, internal marks, weak subjects, and performance trends.")

    if "acad_msg" in st.session_state:
        st.success(st.session_state.pop("acad_msg"))

    subjects = list_subjects()
    _render_academic_overview(subjects)
    st.markdown("---")

    tab_att, tab_marks, tab_weak, tab_analytics = st.tabs(
        [
            "📅 Attendance Tracker",
            "📝 Marks & Assessments",
            "🎯 Weak Subjects",
            "📈 Performance Analytics",
        ]
    )

    with tab_att:
        _render_attendance_tab(subjects)

    with tab_marks:
        _render_marks_tab(subjects)

    with tab_weak:
        _render_weak_subjects_tab(subjects)

    with tab_analytics:
        _render_analytics_tab(subjects)


if __name__ == "__main__":
    main()
