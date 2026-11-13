"""Subject-Wise Video Lecture Suggestions and Personal Learning Resource Library page."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database.db import initialize_database
from services.subject_service import list_subjects, list_topics
from services.video_service import (
    delete_video_resource,
    generate_search_variations,
    generate_youtube_search_query,
    generate_youtube_search_url,
    get_all_video_resources,
    get_resources_by_topic,
    get_subject_video_summary,
    save_video_resource,
    search_video_resources,
    update_video_resource,
)
from utils.config import (
    APP_NAME,
    STYLES_PATH,
    VIDEO_ACADEMIC_LEVELS,
    VIDEO_LANGUAGES,
    VIDEO_LECTURE_TYPES,
)
from utils.ui import load_css, render_sidebar

st.set_page_config(
    page_title=f"Video Lectures & Library | {APP_NAME}",
    page_icon="🎥",
    layout="wide",
)


def _format_saved_date(created_at: Optional[str]) -> str:
    """Format ISO timestamp into a clean date string."""
    if not created_at:
        return "Recently"
    return str(created_at)[:10]


def _render_find_lectures(subjects: List[Dict[str, Any]]) -> None:
    """Render Find Video Lectures search builder and YouTube search buttons."""
    st.subheader("Find Video Lectures on YouTube")
    st.caption(
        "CampusPulse AI builds tailored YouTube search links for your subjects and topics. "
        "Open YouTube to browse results and save the lectures you find most helpful."
    )

    subject_map = {s["id"]: s["subject_name"] for s in subjects}
    col1, col2 = st.columns(2)
    with col1:
        selected_subject_id = st.selectbox(
            "Select Subject",
            options=[s["id"] for s in subjects],
            format_func=lambda sid: subject_map.get(sid, f"Subject {sid}"),
            key="search_subject_id",
        )
    topics = list_topics(subject_id=selected_subject_id)
    topic_map = {t["id"]: t["topic_name"] for t in topics}
    with col2:
        selected_topic_id = st.selectbox(
            "Select Topic (Optional)",
            options=[None] + [t["id"] for t in topics],
            format_func=lambda tid: (
                "General Subject Search (All Topics)"
                if tid is None
                else topic_map.get(tid, f"Topic {tid}")
            ),
            key="search_topic_id",
        )
        if not topics:
            st.caption("No topics added for this subject yet — general subject search is ready.")

    st.markdown("#### Search Preferences")
    p1, p2, p3 = st.columns(3)
    with p1:
        language = st.selectbox(
            "Lecture Language",
            options=["Any"] + list(VIDEO_LANGUAGES),
            index=1,
            key="search_language",
        )
    with p2:
        lecture_type = st.selectbox(
            "Lecture Type",
            options=["Any"] + list(VIDEO_LECTURE_TYPES),
            index=1,
            key="search_lecture_type",
        )
    with p3:
        academic_level = st.selectbox(
            "Academic Level",
            options=["Any"] + list(VIDEO_ACADEMIC_LEVELS),
            index=1,
            key="search_academic_level",
        )

    subject_name = subject_map[selected_subject_id]
    topic_name = topic_map.get(selected_topic_id) if selected_topic_id is not None else None
    lang_val = None if language == "Any" else language
    type_val = None if lecture_type == "Any" else lecture_type
    level_val = None if academic_level == "Any" else academic_level

    query = generate_youtube_search_query(
        subject_name=subject_name,
        topic_name=topic_name,
        lecture_type=type_val,
        academic_level=level_val,
        language=lang_val,
    )
    search_url = generate_youtube_search_url(query)

    with st.container(border=True):
        st.markdown("**Generated YouTube Search Query**")
        st.code(query, language=None)
        st.link_button("Open YouTube Search", search_url, type="primary")
        st.caption(
            "Note: Clicking opens YouTube search results in a new tab. "
            "Individual videos are not automatically pre-verified or scraped."
        )

    st.markdown("#### Quick Search Variations")
    variations = generate_search_variations(
        subject_name=subject_name,
        topic_name=topic_name,
        academic_level=level_val,
        language=lang_val,
    )
    var_cols = st.columns(len(variations))
    for idx, var in enumerate(variations):
        with var_cols[idx]:
            with st.container(border=True):
                st.markdown(f"**{var['label']}**")
                st.caption(var["query"])
                st.link_button("Search YouTube", var["url"], use_container_width=True)


def _render_save_resource_form(subjects: List[Dict[str, Any]]) -> None:
    """Render form to manually save a YouTube lecture resource."""
    st.subheader("Save Learning Resource")
    st.caption("Save helpful YouTube lectures so you can revisit them by subject and topic.")

    subject_map = {s["id"]: s["subject_name"] for s in subjects}
    save_subject_id = st.selectbox(
        "Subject",
        options=[s["id"] for s in subjects],
        format_func=lambda sid: subject_map.get(sid, f"Subject {sid}"),
        key="save_resource_subject",
    )
    topics = list_topics(subject_id=save_subject_id)
    topic_map = {t["id"]: t["topic_name"] for t in topics}

    with st.form("save_video_resource_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            save_topic_id = st.selectbox(
                "Topic (Optional)",
                options=[None] + [t["id"] for t in topics],
                format_func=lambda tid: (
                    "General Subject Resource"
                    if tid is None
                    else topic_map.get(tid, f"Topic {tid}")
                ),
            )
            title = st.text_input(
                "Video Title *",
                placeholder="e.g., Binary Trees Complete Explanation in Hindi",
            )
            channel_name = st.text_input(
                "Channel Name (Optional)",
                placeholder="e.g., CodeHelp / Gate Smashers",
            )
        with c2:
            video_url = st.text_input(
                "YouTube URL *",
                placeholder="https://www.youtube.com/watch?v=...",
            )
            notes = st.text_area(
                "Notes (Optional)",
                placeholder="Key timestamps, formulas covered, or why this lecture helped...",
                height=118,
            )

        if st.form_submit_button("Save Video Resource", type="primary"):
            try:
                save_video_resource(
                    subject_id=save_subject_id,
                    topic_id=save_topic_id,
                    title=title,
                    channel_name=channel_name,
                    video_url=video_url,
                    notes=notes,
                )
                st.success("Video resource saved to your library.")
                st.rerun()
            except Exception as exc:
                st.error(f"Could not save video resource: {exc}")


def _render_resource_card(
    item: Dict[str, Any],
    subjects: List[Dict[str, Any]],
    key_prefix: str,
) -> None:
    """Render a single saved video resource card with Open, Edit, and Delete controls."""
    subject_map = {s["id"]: s["subject_name"] for s in subjects}
    topic_label = item.get("topic_name") or "General Subject"
    channel_label = item.get("channel_name") or "Not specified"
    saved_date = _format_saved_date(item.get("created_at"))

    with st.container(border=True):
        top_l, top_r = st.columns([4, 1])
        with top_l:
            st.markdown(f"### {item['title']}")
            st.caption(
                f"Subject: **{item['subject_name']}** | Topic: **{topic_label}** | "
                f"Channel: **{channel_label}** | Saved: **{saved_date}**"
            )
            if item.get("notes"):
                st.write(item["notes"])
        with top_r:
            st.link_button("Open Video", item["video_url"], type="primary", use_container_width=True)

        edit_col, del_col = st.columns([2, 1])
        with edit_col:
            with st.expander("Edit Resource"):
                edit_subj_id = st.selectbox(
                    "Subject",
                    options=[s["id"] for s in subjects],
                    index=[s["id"] for s in subjects].index(item["subject_id"])
                    if item["subject_id"] in subject_map
                    else 0,
                    format_func=lambda sid: subject_map.get(sid, f"Subject {sid}"),
                    key=f"{key_prefix}_edit_subj_{item['id']}",
                )
                edit_topics = list_topics(subject_id=edit_subj_id)
                edit_topic_opts = [None] + [t["id"] for t in edit_topics]
                edit_topic_map = {t["id"]: t["topic_name"] for t in edit_topics}
                default_topic_idx = (
                    edit_topic_opts.index(item["topic_id"])
                    if item.get("topic_id") in edit_topic_opts
                    else 0
                )

                with st.form(f"{key_prefix}_edit_form_{item['id']}"):
                    new_topic_id = st.selectbox(
                        "Topic (Optional)",
                        options=edit_topic_opts,
                        index=default_topic_idx,
                        format_func=lambda tid: (
                            "General Subject"
                            if tid is None
                            else edit_topic_map.get(tid, f"Topic {tid}")
                        ),
                    )
                    new_title = st.text_input("Video Title *", value=item["title"])
                    new_channel = st.text_input(
                        "Channel Name", value=item.get("channel_name") or ""
                    )
                    new_url = st.text_input("YouTube URL *", value=item["video_url"])
                    new_notes = st.text_area("Notes", value=item.get("notes") or "")

                    if st.form_submit_button("Save Changes"):
                        try:
                            update_video_resource(
                                resource_id=item["id"],
                                subject_id=edit_subj_id,
                                topic_id=new_topic_id,
                                title=new_title,
                                channel_name=new_channel,
                                video_url=new_url,
                                notes=new_notes,
                            )
                            st.success("Video resource updated.")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Could not update resource: {exc}")

        with del_col:
            with st.expander("Delete Resource"):
                confirm = st.checkbox(
                    "Confirm delete",
                    key=f"{key_prefix}_confirm_del_{item['id']}",
                )
                if st.button(
                    "Delete",
                    key=f"{key_prefix}_del_btn_{item['id']}",
                    disabled=not confirm,
                ):
                    try:
                        delete_video_resource(item["id"])
                        st.success("Resource deleted.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Could not delete resource: {exc}")


def _render_library(subjects: List[Dict[str, Any]]) -> None:
    """Render My Learning Resource Library with filters, search, and cards."""
    st.subheader("My Learning Resource Library")

    subject_map = {s["id"]: s["subject_name"] for s in subjects}
    f1, f2, f3 = st.columns(3)
    with f1:
        filter_subject_id = st.selectbox(
            "Filter by Subject",
            options=[None] + [s["id"] for s in subjects],
            format_func=lambda sid: (
                "All Subjects" if sid is None else subject_map.get(sid, f"Subject {sid}")
            ),
            key="lib_filter_subject",
        )
    with f2:
        topic_choices = (
            list_topics(subject_id=filter_subject_id)
            if filter_subject_id is not None
            else []
        )
        topic_map = {t["id"]: t["topic_name"] for t in topic_choices}
        filter_topic_id = st.selectbox(
            "Filter by Topic",
            options=[None] + [t["id"] for t in topic_choices],
            format_func=lambda tid: (
                "All Topics" if tid is None else topic_map.get(tid, f"Topic {tid}")
            ),
            disabled=filter_subject_id is None,
            key="lib_filter_topic",
        )
    with f3:
        search_term = st.text_input(
            "Search by Video Title / Channel",
            placeholder="Type keyword...",
            key="lib_search_term",
        )

    resources = search_video_resources(
        search_term=search_term,
        subject_id=filter_subject_id,
        topic_id=filter_topic_id,
    )

    if not resources:
        with st.container(border=True):
            st.info(
                "No saved video lectures match your current view. "
                "Use **Find Video Lectures** to search YouTube and **Save Learning Resource** to build your library."
            )
        return

    st.caption(f"Showing **{len(resources)}** saved video resource(s).")
    for item in resources:
        _render_resource_card(item, subjects=subjects, key_prefix="lib")


def _render_subject_and_topic_collections(subjects: List[Dict[str, Any]]) -> None:
    """Render Subject-wise Video Collection and Topic-wise Resource Navigation."""
    st.subheader("Subject-Wise & Topic-Wise Collection")

    view_subj_tab, view_topic_tab = st.tabs(
        ["Subject-Wise Collection", "Topic-Wise Navigation"]
    )

    with view_subj_tab:
        summary = get_subject_video_summary()
        subject_map = {s["subject_id"]: s for s in summary}
        selected_sid = st.selectbox(
            "Select Subject to Inspect",
            options=[None] + [s["subject_id"] for s in summary],
            format_func=lambda sid: (
                "All Subjects"
                if sid is None
                else f"{subject_map[sid]['subject_name']} ({subject_map[sid]['total_videos']})"
            ),
            key="coll_subject_select",
        )

        items_to_show = (
            summary
            if selected_sid is None
            else [s for s in summary if s["subject_id"] == selected_sid]
        )

        any_videos = any(s["total_videos"] > 0 for s in items_to_show)
        if not any_videos:
            st.info("No saved videos in this subject collection yet.")
        else:
            for subj_block in items_to_show:
                if subj_block["total_videos"] == 0 and selected_sid is None:
                    continue
                with st.container(border=True):
                    st.markdown(
                        f"### {subj_block['subject_name'].upper()} "
                        f"({subj_block['total_videos']} saved)"
                    )
                    if not subj_block["topics"]:
                        st.caption("No saved videos for this subject yet.")
                    else:
                        for topic_label, videos in subj_block["topics"].items():
                            st.markdown(f"**{topic_label}:**")
                            for vid in videos:
                                c_a, c_b = st.columns([4, 1])
                                ch = f" — {vid['channel_name']}" if vid.get("channel_name") else ""
                                c_a.markdown(f"- {vid['title']}{ch}")
                                c_b.link_button("Open", vid["video_url"], use_container_width=True)

    with view_topic_tab:
        subject_map_raw = {s["id"]: s["subject_name"] for s in subjects}
        nav_subj_id = st.selectbox(
            "Subject",
            options=[s["id"] for s in subjects],
            format_func=lambda sid: subject_map_raw.get(sid, f"Subject {sid}"),
            key="topic_nav_subj",
        )
        nav_topics = list_topics(subject_id=nav_subj_id)
        if not nav_topics:
            st.info(
                "This subject has no syllabus topics yet. Add topics in Subjects & Topics "
                "or save a general subject video in the Save Learning Resource tab."
            )
            return

        nav_topic_map = {t["id"]: t["topic_name"] for t in nav_topics}
        nav_topic_id = st.selectbox(
            "Topic",
            options=[t["id"] for t in nav_topics],
            format_func=lambda tid: nav_topic_map.get(tid, f"Topic {tid}"),
            key="topic_nav_topic",
        )

        topic_videos = get_resources_by_topic(nav_topic_id)
        if not topic_videos:
            st.info(
                "No saved videos for this topic yet. Search YouTube and save your preferred lecture."
            )
            quick_query = generate_youtube_search_query(
                subject_name=subject_map_raw[nav_subj_id],
                topic_name=nav_topic_map[nav_topic_id],
                lecture_type="Topic Explanation",
            )
            st.link_button(
                f"Search YouTube for '{nav_topic_map[nav_topic_id]}'",
                generate_youtube_search_url(quick_query),
                type="primary",
            )
        else:
            for item in topic_videos:
                _render_resource_card(item, subjects=subjects, key_prefix="topicnav")


def main() -> None:
    """Render the Video Lectures & Personal Learning Resource Library page."""
    load_css(STYLES_PATH)
    db_ready = initialize_database()
    render_sidebar(db_ready=db_ready)

    st.title("Video Lecture Suggestions & Learning Resource Library")
    st.caption(
        "Generate tailored YouTube lecture searches for your syllabus and build "
        "a curated subject-wise and topic-wise personal video library."
    )

    subjects = list_subjects()
    if not subjects:
        st.warning("Please add your subjects first in Subjects & Topics.")
        return

    all_saved = get_all_video_resources()
    m1, m2, m3 = st.columns(3)
    m1.metric("Saved Video Resources", len(all_saved))
    m2.metric(
        "Subjects Covered",
        len({r["subject_id"] for r in all_saved}),
    )
    m3.metric(
        "Topics Covered",
        len({r["topic_id"] for r in all_saved if r.get("topic_id") is not None}),
    )

    tab_find, tab_save, tab_lib, tab_coll = st.tabs(
        [
            "Find Video Lectures",
            "Save Learning Resource",
            "My Learning Resource Library",
            "Subject & Topic Collection",
        ]
    )
    with tab_find:
        _render_find_lectures(subjects)
    with tab_save:
        _render_save_resource_form(subjects)
    with tab_lib:
        _render_library(subjects)
    with tab_coll:
        _render_subject_and_topic_collections(subjects)


if __name__ == "__main__":
    main()
