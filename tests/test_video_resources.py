"""Automated tests for Step 9 — Video Lecture Suggestions & Resource Library."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database.db import initialize_database
from database.queries import insert_subject, insert_topic
from services.video_service import (
    delete_video_resource,
    generate_search_variations,
    generate_youtube_search_query,
    generate_youtube_search_url,
    get_all_video_resources,
    get_resources_by_subject,
    get_resources_by_topic,
    get_subject_video_summary,
    get_video_search_query,
    save_video_resource,
    search_video_resources,
    update_video_resource,
    validate_video_url,
)


@pytest.fixture()
def temp_db(tmp_path: Path) -> Path:
    """Create an isolated temporary SQLite database with full schema."""
    db_file = tmp_path / "test_video_resources.db"
    initialize_database(db_path=db_file)
    return db_file


def test_subject_only_search_query_generation() -> None:
    query = generate_youtube_search_query("DBMS")
    assert query == "DBMS"
    assert get_video_search_query("DBMS") == "DBMS"


def test_subject_and_topic_search_query_generation() -> None:
    query = generate_youtube_search_query(
        subject_name="Data Structures and Algorithms",
        topic_name="Binary Trees",
    )
    assert query == "Data Structures and Algorithms Binary Trees"


def test_hindi_and_english_and_both_query_generation() -> None:
    hindi_q = generate_youtube_search_query(
        subject_name="DBMS",
        topic_name="Normalization",
        lecture_type="Complete Course",
        academic_level="BTech Beginner",
        language="Hindi",
    )
    assert hindi_q == "DBMS Normalization Complete Course BTech Beginner Hindi"

    english_q = generate_youtube_search_query(
        subject_name="Java",
        topic_name="OOP Concepts",
        lecture_type="Topic Explanation",
        language="English",
    )
    assert english_q == "Java OOP Concepts Topic Explanation English"

    both_q = generate_youtube_search_query(
        subject_name="Operating Systems",
        topic_name="Deadlocks",
        language="Both",
    )
    assert "Both" not in both_q
    assert both_q == "Operating Systems Deadlocks"


def test_complete_course_and_practice_problem_variations_and_dedup() -> None:
    practice_q = generate_youtube_search_query(
        subject_name="Engineering Mathematics",
        topic_name="Integration",
        lecture_type="Problem Solving",
    )
    assert practice_q == "Engineering Mathematics Integration Problem Solving"

    # Duplicate words across fields should not repeat
    dedup_q = generate_youtube_search_query(
        subject_name="BTech Data Structures",
        topic_name="Data Structures Trees",
        academic_level="BTech Beginner",
    )
    assert dedup_q == "BTech Data Structures Trees Beginner"

    variations = generate_search_variations(
        subject_name="DSA",
        topic_name="Graphs",
        academic_level="College Level",
        language="Hindi",
    )
    assert len(variations) == 4
    labels = {v["label"] for v in variations}
    assert {"Complete Explanation", "Topic-Wise Lecture", "Practice Problems", "Revision Lecture"} == labels
    assert all(v["url"].startswith("https://www.youtube.com/results?search_query=") for v in variations)


def test_youtube_url_encoding() -> None:
    url = generate_youtube_search_url("DBMS Normalization & SQL Joins")
    assert url == "https://www.youtube.com/results?search_query=DBMS+Normalization+%26+SQL+Joins"
    with pytest.raises(ValueError):
        generate_youtube_search_url("   ")


def test_validate_video_url_accepts_youtube_and_youtu_be() -> None:
    for valid_url in (
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com/watch?v=abc123",
        "https://m.youtube.com/watch?v=xyz789",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/playlist?list=PL12345",
    ):
        ok, msg = validate_video_url(valid_url)
        assert ok is True, f"Expected valid for {valid_url}, got: {msg}"


def test_validate_video_url_rejects_non_https_and_unrelated_domains() -> None:
    for bad_url in (
        "",
        "http://www.youtube.com/watch?v=abc123",
        "http://youtu.be/abc123",
        "www.youtube.com/watch?v=abc123",
        "https://vimeo.com/123456",
        "https://example.com/youtube.com/watch?v=123",
        "https://www.youtube.com",
        "https://www.youtube.com/watch?v=abc 123",
    ):
        ok, _ = validate_video_url(bad_url)
        assert ok is False, f"Expected invalid for {bad_url}"


def test_resource_crud_and_filtering(temp_db: Path) -> None:
    s1 = insert_subject("Data Structures", subject_code="CS201", db_path=temp_db)
    s2 = insert_subject("DBMS", subject_code="CS202", db_path=temp_db)
    t1 = insert_topic(s1, "Binary Trees", db_path=temp_db)
    t2 = insert_topic(s1, "Graphs", db_path=temp_db)

    r1 = save_video_resource(
        subject_id=s1,
        topic_id=t1,
        title="Binary Trees Full Lecture",
        channel_name="CodeHelp",
        video_url="https://www.youtube.com/watch?v=bt123",
        notes="Great dry run",
        db_path=temp_db,
    )
    r2 = save_video_resource(
        subject_id=s1,
        topic_id=t2,
        title="Graph Traversal BFS DFS",
        channel_name="Striver",
        video_url="https://youtu.be/gr456",
        db_path=temp_db,
    )
    r3 = save_video_resource(
        subject_id=s2,
        topic_id=None,
        title="DBMS Complete Course",
        video_url="https://m.youtube.com/watch?v=dbms789",
        db_path=temp_db,
    )

    all_res = get_all_video_resources(db_path=temp_db)
    assert len(all_res) == 3

    subj1_res = get_resources_by_subject(s1, db_path=temp_db)
    assert {r["id"] for r in subj1_res} == {r1, r2}

    topic1_res = get_resources_by_topic(t1, db_path=temp_db)
    assert [r["id"] for r in topic1_res] == [r1]

    searched = search_video_resources(search_term="Striver", subject_id=s1, db_path=temp_db)
    assert [r["id"] for r in searched] == [r2]

    summary = get_subject_video_summary(db_path=temp_db)
    assert len(summary) == 2
    s1_block = next(item for item in summary if item["subject_id"] == s1)
    assert s1_block["total_videos"] == 2
    assert "Binary Trees" in s1_block["topics"]

    # Edit resource
    update_video_resource(
        resource_id=r1,
        subject_id=s1,
        topic_id=t1,
        title="Binary Trees Updated",
        channel_name="CodeHelp - Babbar",
        video_url="https://www.youtube.com/watch?v=bt123",
        notes="Updated notes",
        db_path=temp_db,
    )
    updated = get_resources_by_topic(t1, db_path=temp_db)[0]
    assert updated["title"] == "Binary Trees Updated"
    assert updated["channel_name"] == "CodeHelp - Babbar"

    # Delete resource
    delete_video_resource(r3, db_path=temp_db)
    assert len(get_all_video_resources(db_path=temp_db)) == 2


def test_invalid_topic_subject_and_duplicate_rejection(temp_db: Path) -> None:
    s1 = insert_subject("OS", subject_code="CS301", db_path=temp_db)
    s2 = insert_subject("CN", subject_code="CS302", db_path=temp_db)
    t_other = insert_topic(s2, "TCP/IP", db_path=temp_db)

    with pytest.raises(ValueError):
        save_video_resource(
            subject_id=s1,
            topic_id=t_other,
            title="Wrong Topic Mapping",
            video_url="https://www.youtube.com/watch?v=abc123",
            db_path=temp_db,
        )

    save_video_resource(
        subject_id=s1,
        topic_id=None,
        title="OS One Shot",
        video_url="https://www.youtube.com/watch?v=os111",
        db_path=temp_db,
    )
    with pytest.raises(ValueError):
        save_video_resource(
            subject_id=s1,
            topic_id=None,
            title="OS One Shot Duplicate",
            video_url="https://www.youtube.com/watch?v=os111",
            db_path=temp_db,
        )
