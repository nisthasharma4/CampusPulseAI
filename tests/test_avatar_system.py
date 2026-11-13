"""Automated tests for Student Avatar System (Design System V4)."""

from io import BytesIO
from pathlib import Path
import sqlite3
from PIL import Image
import pytest

from database.db import fetch_one, initialize_database
from database.schema import create_tables
from services.profile_service import (
    get_profile,
    remove_avatar,
    save_profile,
    set_avatar_preset,
    set_avatar_upload,
)
from utils.avatars import (
    ALLOWED_EXTENSIONS,
    MAX_AVATAR_BYTES,
    PRESET_AVATARS,
    TARGET_AVATAR_SIZE,
    delete_custom_avatar_file,
    extract_initials,
    generate_initials_svg,
    get_avatar_html,
    render_preset_svg,
    validate_and_save_avatar_upload,
)


class DummyUpload:
    """Mock Streamlit uploaded file object."""

    def __init__(self, name: str, data: bytes):
        self.name = name
        self._data = data

    def getvalue(self) -> bytes:
        return self._data

    def read(self) -> bytes:
        return self._data


def _create_test_image_bytes(width: int, height: int, fmt: str = "PNG") -> bytes:
    """Create in-memory image bytes using PIL."""
    img = Image.new("RGB", (width, height), color=(92, 85, 154))
    buf = BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


@pytest.fixture()
def temp_db(tmp_path):
    """Provide a clean initialized temporary SQLite database."""
    db_file = tmp_path / "test_avatar.db"
    assert initialize_database(db_file) is True
    return db_file


# ---------------------------------------------------------------------------
# Unit tests: Initials & SVG Generators
# ---------------------------------------------------------------------------


def test_extract_initials():
    assert extract_initials("Aarav Sharma") == "AS"
    assert extract_initials("arav") == "AR"
    assert extract_initials("A") == "A"
    assert extract_initials("First Middle Last") == "FL"
    assert extract_initials("") == "CP"
    assert extract_initials(None) == "CP"
    assert extract_initials("   ") == "CP"


def test_generate_initials_svg():
    svg = generate_initials_svg("Aarav Sharma", size=64)
    assert "<svg" in svg
    assert "</svg>" in svg
    assert "AS" in svg
    assert 'width="64"' in svg
    assert 'height="64"' in svg


def test_all_preset_avatars_defined_and_valid():
    expected_presets = {
        "classic_student",
        "academic_explorer",
        "creative_learner",
        "tech_student",
        "focused_scholar",
        "minimal_portrait",
    }
    assert expected_presets.issubset(set(PRESET_AVATARS.keys()))

    for key, data in PRESET_AVATARS.items():
        assert "title" in data
        assert "description" in data
        assert "svg" in data
        rendered = render_preset_svg(key, size=72)
        assert "<svg" in rendered
        assert "</svg>" in rendered
        assert 'width="72"' in rendered


# ---------------------------------------------------------------------------
# Unit tests: HTML Rendering Hierarchy
# ---------------------------------------------------------------------------


def test_get_avatar_html_fallback_initials():
    html = get_avatar_html({"name": "Priya Patel"}, size=64)
    assert "<img" in html
    assert 'data:image/svg+xml;base64,' in html
    assert 'class="st-cp-avatar' in html


def test_get_avatar_html_preset():
    html = get_avatar_html(
        {"name": "Rohan Verma", "avatar_preset": "tech_student"},
        size=64,
    )
    assert "<img" in html
    assert 'data:image/svg+xml;base64,' in html


def test_get_avatar_html_custom_photo(tmp_path):
    # Create fake image on disk
    photo_file = tmp_path / "my_pic.png"
    photo_file.write_bytes(_create_test_image_bytes(200, 200, "PNG"))

    html = get_avatar_html(
        {"name": "Ananya Roy", "avatar_path": str(photo_file)},
        size=64,
    )
    assert "<img" in html
    assert 'data:image/png;base64,' in html


# ---------------------------------------------------------------------------
# Unit tests: Upload Validation & Thumbnail Processing
# ---------------------------------------------------------------------------


def test_validate_and_save_avatar_upload_valid(tmp_path):
    storage_dir = tmp_path / "avatars"
    raw_bytes = _create_test_image_bytes(800, 600, "PNG")
    upload = DummyUpload("profile.png", raw_bytes)

    ok, msg, path_str = validate_and_save_avatar_upload(upload, storage_dir=storage_dir)
    assert ok is True
    assert path_str is not None
    saved_path = Path(path_str)
    assert saved_path.is_file()

    # Verify thumbnail size is exact 512x512
    with Image.open(saved_path) as im:
        assert im.size == TARGET_AVATAR_SIZE


def test_validate_and_save_avatar_upload_oversized(tmp_path):
    storage_dir = tmp_path / "avatars"
    oversized_bytes = b"0" * (MAX_AVATAR_BYTES + 1024)
    upload = DummyUpload("big.png", oversized_bytes)

    ok, msg, path_str = validate_and_save_avatar_upload(upload, storage_dir=storage_dir)
    assert ok is False
    assert "exceeds" in msg.lower()
    assert path_str is None


def test_validate_and_save_avatar_upload_invalid_extension(tmp_path):
    storage_dir = tmp_path / "avatars"
    upload = DummyUpload("document.pdf", b"fake pdf content")

    ok, msg, path_str = validate_and_save_avatar_upload(upload, storage_dir=storage_dir)
    assert ok is False
    assert "unsupported" in msg.lower()
    assert path_str is None


# ---------------------------------------------------------------------------
# Integration tests: Service & Database Persistence
# ---------------------------------------------------------------------------


def test_profile_avatar_preset_lifecycle(temp_db):
    # 1. Create initial profile
    save_profile(name="Kavya Iyer", semester=3, db_path=temp_db)
    p = get_profile(db_path=temp_db)
    assert p["name"] == "Kavya Iyer"
    assert p["avatar_preset"] is None
    assert p["avatar_path"] is None

    # 2. Select preset
    set_avatar_preset("creative_learner", db_path=temp_db)
    p = get_profile(db_path=temp_db)
    assert p["avatar_preset"] == "creative_learner"
    assert p["avatar_path"] is None

    # 3. Update profile data without avatar params -> avatar preset must be preserved
    save_profile(name="Kavya I.", semester=4, db_path=temp_db)
    p = get_profile(db_path=temp_db)
    assert p["name"] == "Kavya I."
    assert p["avatar_preset"] == "creative_learner"

    # 4. Remove avatar
    remove_avatar(db_path=temp_db)
    p = get_profile(db_path=temp_db)
    assert p["avatar_preset"] is None
    assert p["avatar_path"] is None


def test_profile_photo_upload_and_cleanup(temp_db, tmp_path, monkeypatch):
    # Point storage dir to tmp_path
    monkeypatch.setattr("utils.avatars.AVATARS_DIR", tmp_path / "avatars")

    save_profile(name="Dev Patel", semester=2, db_path=temp_db)

    # Upload photo 1
    upload1 = DummyUpload("pic1.png", _create_test_image_bytes(300, 300, "PNG"))
    ok, msg = set_avatar_upload(upload1, db_path=temp_db)
    assert ok is True
    p1 = get_profile(db_path=temp_db)
    path1 = Path(p1["avatar_path"])
    assert path1.is_file()

    # Upload photo 2 -> photo 1 must be cleaned up from disk
    upload2 = DummyUpload("pic2.jpg", _create_test_image_bytes(400, 400, "JPEG"))
    ok, msg = set_avatar_upload(upload2, db_path=temp_db)
    assert ok is True
    p2 = get_profile(db_path=temp_db)
    path2 = Path(p2["avatar_path"])
    assert path2.is_file()
    assert not path1.is_file()  # Cleaned up!

    # Switch to preset -> photo 2 must be cleaned up from disk
    set_avatar_preset("academic_explorer", db_path=temp_db)
    p3 = get_profile(db_path=temp_db)
    assert p3["avatar_preset"] == "academic_explorer"
    assert p3["avatar_path"] is None
    assert not path2.is_file()  # Cleaned up!


def test_additive_schema_migration_preserves_legacy_data(tmp_path):
    """Verify that an older database without avatar columns is cleanly migrated without losing records."""
    legacy_db = tmp_path / "legacy.db"
    conn = sqlite3.connect(legacy_db)

    # Create legacy table without avatar_preset and avatar_path
    conn.execute(
        """
        CREATE TABLE student_profile (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            branch TEXT,
            semester INTEGER,
            college_name TEXT,
            weekly_study_target INTEGER,
            preferred_start_time TEXT,
            preferred_end_time TEXT,
            available_days TEXT,
            daily_available_minutes INTEGER,
            session_duration_minutes INTEGER,
            break_duration_minutes INTEGER,
            attendance_target REAL DEFAULT 75,
            created_at TEXT,
            updated_at TEXT
        );
        """
    )
    conn.execute(
        "INSERT INTO student_profile (name, branch, semester) VALUES ('Legacy Student', 'ECE', 2);"
    )
    conn.commit()
    conn.close()

    # Run initialize_database (calls create_tables with migration)
    assert initialize_database(legacy_db) is True

    # Check that columns now exist and data is preserved
    row = fetch_one("SELECT * FROM student_profile WHERE id = 1;", db_path=legacy_db)
    assert row["name"] == "Legacy Student"
    assert row["branch"] == "ECE"
    assert "avatar_preset" in row.keys()
    assert "avatar_path" in row.keys()
    assert row["avatar_preset"] is None
