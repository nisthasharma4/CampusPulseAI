"""Business logic for Video Lecture Search Generation and Personal Resource Library."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import quote_plus, urlparse

from database.db import execute_query, fetch_all, fetch_one
from database.queries import save_video_resource as _db_save_video_resource
from services.subject_service import get_subject, get_topic, list_subjects
from utils.config import ALLOWED_YOUTUBE_DOMAINS
from utils.validators import validate_non_empty_text

YOUTUBE_SEARCH_BASE_URL = "https://www.youtube.com/results?search_query="


def _now_iso() -> str:
    """Return current local timestamp as ISO-8601 string."""
    return datetime.now().isoformat(timespec="seconds")


def _clean_optional_text(value: Optional[str]) -> Optional[str]:
    """Strip optional text and convert blank strings to None."""
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned if cleaned else None


def generate_youtube_search_query(
    subject_name: str,
    topic_name: Optional[str] = None,
    lecture_type: Optional[str] = None,
    academic_level: Optional[str] = None,
    language: Optional[str] = None,
) -> str:
    """Build a natural YouTube search query from subject, topic, and preferences."""
    ok, msg = validate_non_empty_text(subject_name, "Subject Name")
    if not ok:
        raise ValueError(msg)

    raw_parts: List[str] = [str(subject_name).strip()]
    for part in (topic_name, lecture_type, academic_level):
        cleaned = _clean_optional_text(part)
        if cleaned:
            raw_parts.append(cleaned)

    lang_clean = _clean_optional_text(language)
    if lang_clean and lang_clean.lower() != "both":
        raw_parts.append(lang_clean)

    # Deduplicate tokens case-insensitively while preserving natural word order.
    seen_tokens = set()
    final_tokens: List[str] = []
    for part in raw_parts:
        for token in part.split():
            lowered = token.lower()
            if lowered not in seen_tokens:
                seen_tokens.add(lowered)
                final_tokens.append(token)

    return " ".join(final_tokens)


def get_video_search_query(
    subject_name: str,
    topic_name: Optional[str] = None,
    lecture_type: Optional[str] = None,
    academic_level: Optional[str] = None,
    language: Optional[str] = None,
) -> str:
    """Alias for generate_youtube_search_query()."""
    return generate_youtube_search_query(
        subject_name=subject_name,
        topic_name=topic_name,
        lecture_type=lecture_type,
        academic_level=academic_level,
        language=language,
    )


def generate_youtube_search_url(query: str) -> str:
    """Return a URL-encoded YouTube search URL for the given query."""
    ok, msg = validate_non_empty_text(query, "Search Query")
    if not ok:
        raise ValueError(msg)
    return f"{YOUTUBE_SEARCH_BASE_URL}{quote_plus(str(query).strip())}"


def generate_search_variations(
    subject_name: str,
    topic_name: Optional[str] = None,
    academic_level: Optional[str] = None,
    language: Optional[str] = None,
) -> List[Dict[str, str]]:
    """Generate common study-oriented YouTube search variations for a subject/topic."""
    variations = [
        ("Complete Explanation", "Complete Course"),
        ("Topic-Wise Lecture", "Topic Explanation"),
        ("Practice Problems", "Problem Solving"),
        ("Revision Lecture", "Quick Revision"),
    ]
    results: List[Dict[str, str]] = []
    for label, ltype in variations:
        query = generate_youtube_search_query(
            subject_name=subject_name,
            topic_name=topic_name,
            lecture_type=ltype,
            academic_level=academic_level,
            language=language,
        )
        results.append(
            {
                "label": label,
                "lecture_type": ltype,
                "query": query,
                "url": generate_youtube_search_url(query),
            }
        )
    return results


def validate_video_url(video_url: str) -> Tuple[bool, str]:
    """Validate that a video URL is a well-formed HTTPS YouTube link."""
    ok, msg = validate_non_empty_text(video_url, "YouTube URL")
    if not ok:
        return False, msg

    cleaned = str(video_url).strip()
    if any(ch.isspace() for ch in cleaned):
        return False, "YouTube URL cannot contain spaces."

    parsed = urlparse(cleaned)
    if parsed.scheme.lower() != "https":
        return False, "Only HTTPS YouTube links are accepted."

    host = parsed.netloc.lower().split(":")[0]
    if host not in ALLOWED_YOUTUBE_DOMAINS:
        return (
            False,
            "URL must be from a supported YouTube domain "
            "(youtube.com, www.youtube.com, m.youtube.com, or youtu.be).",
        )

    if not parsed.path.strip("/") and not parsed.query:
        return False, "Please provide a complete YouTube video or playlist URL."

    return True, ""


def _validate_resource_inputs(
    subject_id: int,
    title: str,
    video_url: str,
    topic_id: Optional[int] = None,
    exclude_resource_id: Optional[int] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> Tuple[str, str]:
    """Validate title, subject/topic relationship, URL format, and duplicate URLs."""
    ok, msg = validate_non_empty_text(title, "Video Title")
    if not ok:
        raise ValueError(msg)

    if get_subject(subject_id, db_path=db_path) is None:
        raise ValueError(f"Subject ID {subject_id} does not exist.")

    if topic_id is not None:
        topic = get_topic(topic_id, db_path=db_path)
        if topic is None or int(topic["subject_id"]) != int(subject_id):
            raise ValueError("Selected topic does not belong to the selected subject.")

    url_ok, url_msg = validate_video_url(video_url)
    if not url_ok:
        raise ValueError(url_msg)

    clean_title = str(title).strip()
    clean_url = str(video_url).strip()

    existing_rows = fetch_all(
        """
        SELECT id, topic_id, video_url
        FROM video_resources
        WHERE subject_id = ?;
        """,
        (subject_id,),
        db_path=db_path,
    )
    for row in existing_rows:
        if exclude_resource_id is not None and int(row["id"]) == int(exclude_resource_id):
            continue
        if (
            row["topic_id"] == topic_id
            and (row["video_url"] or "").strip().lower() == clean_url.lower()
        ):
            raise ValueError(
                "This YouTube URL is already saved for the selected subject and topic."
            )

    return clean_title, clean_url


def save_video_resource(
    subject_id: int,
    title: str,
    video_url: str,
    topic_id: Optional[int] = None,
    channel_name: Optional[str] = None,
    notes: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Validate and save a video resource into the video_resources table."""
    clean_title, clean_url = _validate_resource_inputs(
        subject_id=subject_id,
        title=title,
        video_url=video_url,
        topic_id=topic_id,
        db_path=db_path,
    )
    return _db_save_video_resource(
        subject_id=subject_id,
        title=clean_title,
        video_url=clean_url,
        topic_id=topic_id,
        channel_name=_clean_optional_text(channel_name),
        notes=_clean_optional_text(notes),
        db_path=db_path,
    )


def get_all_video_resources(
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Return all saved video resources joined with subject and topic metadata."""
    rows = fetch_all(
        """
        SELECT
            vr.*,
            s.subject_name,
            s.subject_code,
            t.topic_name
        FROM video_resources vr
        JOIN subjects s ON vr.subject_id = s.id
        LEFT JOIN topics t ON vr.topic_id = t.id
        ORDER BY vr.created_at DESC, vr.id DESC;
        """,
        db_path=db_path,
    )
    return [dict(row) for row in rows]


def get_resources_by_subject(
    subject_id: int,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Return saved video resources for a specific subject."""
    rows = fetch_all(
        """
        SELECT
            vr.*,
            s.subject_name,
            s.subject_code,
            t.topic_name
        FROM video_resources vr
        JOIN subjects s ON vr.subject_id = s.id
        LEFT JOIN topics t ON vr.topic_id = t.id
        WHERE vr.subject_id = ?
        ORDER BY vr.created_at DESC, vr.id DESC;
        """,
        (subject_id,),
        db_path=db_path,
    )
    return [dict(row) for row in rows]


def get_resources_by_topic(
    topic_id: int,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Return saved video resources associated with a specific topic."""
    rows = fetch_all(
        """
        SELECT
            vr.*,
            s.subject_name,
            s.subject_code,
            t.topic_name
        FROM video_resources vr
        JOIN subjects s ON vr.subject_id = s.id
        LEFT JOIN topics t ON vr.topic_id = t.id
        WHERE vr.topic_id = ?
        ORDER BY vr.created_at DESC, vr.id DESC;
        """,
        (topic_id,),
        db_path=db_path,
    )
    return [dict(row) for row in rows]


def search_video_resources(
    search_term: Optional[str] = None,
    subject_id: Optional[int] = None,
    topic_id: Optional[int] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Filter saved video resources by subject, topic, and title/channel/notes keyword."""
    query = """
        SELECT
            vr.*,
            s.subject_name,
            s.subject_code,
            t.topic_name
        FROM video_resources vr
        JOIN subjects s ON vr.subject_id = s.id
        LEFT JOIN topics t ON vr.topic_id = t.id
        WHERE 1 = 1
    """
    params: List[Any] = []

    if subject_id is not None:
        query += " AND vr.subject_id = ?"
        params.append(subject_id)

    if topic_id is not None:
        query += " AND vr.topic_id = ?"
        params.append(topic_id)

    cleaned_term = _clean_optional_text(search_term)
    if cleaned_term:
        like = f"%{cleaned_term}%"
        query += " AND (vr.title LIKE ? OR COALESCE(vr.channel_name, '') LIKE ? OR COALESCE(vr.notes, '') LIKE ?)"
        params.extend([like, like, like])

    query += " ORDER BY vr.created_at DESC, vr.id DESC;"
    rows = fetch_all(query, tuple(params), db_path=db_path)
    return [dict(row) for row in rows]


def update_video_resource(
    resource_id: int,
    subject_id: int,
    title: str,
    video_url: str,
    topic_id: Optional[int] = None,
    channel_name: Optional[str] = None,
    notes: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Update an existing saved video resource after validating inputs."""
    existing = fetch_one(
        "SELECT id FROM video_resources WHERE id = ?;",
        (resource_id,),
        db_path=db_path,
    )
    if existing is None:
        raise ValueError(f"Video resource ID {resource_id} does not exist.")

    clean_title, clean_url = _validate_resource_inputs(
        subject_id=subject_id,
        title=title,
        video_url=video_url,
        topic_id=topic_id,
        exclude_resource_id=resource_id,
        db_path=db_path,
    )

    execute_query(
        """
        UPDATE video_resources
        SET subject_id = ?,
            topic_id = ?,
            title = ?,
            channel_name = ?,
            video_url = ?,
            notes = ?
        WHERE id = ?;
        """,
        (
            subject_id,
            topic_id,
            clean_title,
            _clean_optional_text(channel_name),
            clean_url,
            _clean_optional_text(notes),
            resource_id,
        ),
        db_path=db_path,
    )
    return int(resource_id)


def delete_video_resource(
    resource_id: int,
    db_path: Optional[Union[str, Path]] = None,
) -> None:
    """Delete a saved video resource by ID."""
    existing = fetch_one(
        "SELECT id FROM video_resources WHERE id = ?;",
        (resource_id,),
        db_path=db_path,
    )
    if existing is None:
        raise ValueError(f"Video resource ID {resource_id} does not exist.")

    execute_query(
        "DELETE FROM video_resources WHERE id = ?;",
        (resource_id,),
        db_path=db_path,
    )


def get_subject_video_summary(
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Return subject-wise and topic-wise grouped video resource summaries."""
    subjects = list_subjects(db_path=db_path)
    all_resources = get_all_video_resources(db_path=db_path)

    by_subject: Dict[int, List[Dict[str, Any]]] = {}
    for item in all_resources:
        by_subject.setdefault(int(item["subject_id"]), []).append(item)

    summary: List[Dict[str, Any]] = []
    for subj in subjects:
        sid = int(subj["id"])
        items = by_subject.get(sid, [])
        topics_grouped: Dict[str, List[Dict[str, Any]]] = {}
        for res in items:
            topic_label = res.get("topic_name") or "General Subject Resources"
            topics_grouped.setdefault(topic_label, []).append(res)

        summary.append(
            {
                "subject_id": sid,
                "subject_name": subj["subject_name"],
                "subject_code": subj.get("subject_code"),
                "total_videos": len(items),
                "topics": topics_grouped,
            }
        )

    return summary
