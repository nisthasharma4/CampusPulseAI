"""Database schema definitions and migrations for CampusPulse AI."""

import sqlite3

SCHEMA_VERSION = 2

REQUIRED_TABLES = (
    "student_profile",
    "subjects",
    "topics",
    "attendance",
    "marks",
    "assignments",
    "calendar_events",
    "study_sessions",
    "daily_checkins",
    "timetable",
    "video_resources",
)


def get_schema_version(connection: sqlite3.Connection) -> int:
    """Return the current SQLite schema version stored in PRAGMA user_version."""
    row = connection.execute("PRAGMA user_version;").fetchone()
    return int(row[0]) if row else 0


def create_tables(connection: sqlite3.Connection) -> None:
    """Create all 11 CampusPulse AI tables and indexes if they do not exist.

    Safe to execute multiple times without dropping tables or deleting records.
    """
    connection.execute("PRAGMA foreign_keys = ON;")

    # 1. student_profile
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS student_profile (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL CHECK(length(trim(name)) > 0),
            branch TEXT,
            semester INTEGER CHECK(semester IS NULL OR semester > 0),
            college_name TEXT,
            weekly_study_target INTEGER CHECK(weekly_study_target IS NULL OR weekly_study_target >= 0),
            preferred_start_time TEXT,
            preferred_end_time TEXT,
            available_days TEXT,
            daily_available_minutes INTEGER CHECK(daily_available_minutes IS NULL OR daily_available_minutes >= 0),
            session_duration_minutes INTEGER CHECK(session_duration_minutes IS NULL OR session_duration_minutes > 0),
            break_duration_minutes INTEGER CHECK(break_duration_minutes IS NULL OR break_duration_minutes >= 0),
            attendance_target REAL DEFAULT 75 CHECK(attendance_target IS NULL OR (attendance_target >= 0 AND attendance_target <= 100)),
            avatar_preset TEXT,
            avatar_path TEXT,
            created_at TEXT,
            updated_at TEXT
        );
        """
    )

    # 2. subjects
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_name TEXT NOT NULL CHECK(length(trim(subject_name)) > 0),
            subject_code TEXT,
            semester INTEGER CHECK(semester IS NULL OR semester > 0),
            start_date TEXT,
            target_completion_date TEXT,
            completion_date TEXT,
            status TEXT NOT NULL DEFAULT 'Not Started'
                CHECK(status IN ('Not Started', 'In Progress', 'Completed')),
            notes TEXT,
            created_at TEXT,
            updated_at TEXT
        );
        """
    )

    # 3. topics
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            topic_name TEXT NOT NULL CHECK(length(trim(topic_name)) > 0),
            sequence_number INTEGER CHECK(sequence_number IS NULL OR sequence_number >= 0),
            start_date TEXT,
            target_date TEXT,
            completion_date TEXT,
            estimated_hours REAL CHECK(estimated_hours IS NULL OR estimated_hours >= 0),
            status TEXT NOT NULL DEFAULT 'Not Started'
                CHECK(status IN ('Not Started', 'In Progress', 'Completed')),
            notes TEXT,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
        );
        """
    )

    # 4. attendance
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL UNIQUE,
            classes_held INTEGER NOT NULL DEFAULT 0 CHECK(classes_held >= 0),
            classes_attended INTEGER NOT NULL DEFAULT 0
                CHECK(classes_attended >= 0 AND classes_attended <= classes_held),
            updated_at TEXT,
            FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
        );
        """
    )

    # 5. marks
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS marks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            assessment_type TEXT NOT NULL CHECK(length(trim(assessment_type)) > 0),
            marks_obtained REAL NOT NULL CHECK(marks_obtained >= 0),
            maximum_marks REAL NOT NULL CHECK(maximum_marks > 0),
            assessment_date TEXT,
            notes TEXT,
            created_at TEXT,
            CHECK(marks_obtained <= maximum_marks),
            FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
        );
        """
    )

    # 6. assignments
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            title TEXT NOT NULL CHECK(length(trim(title)) > 0),
            description TEXT,
            assigned_date TEXT,
            deadline_date TEXT NOT NULL CHECK(length(trim(deadline_date)) > 0),
            deadline_time TEXT,
            reminder_at TEXT,
            priority TEXT NOT NULL DEFAULT 'Medium'
                CHECK(priority IN ('Low', 'Medium', 'High')),
            status TEXT NOT NULL DEFAULT 'Pending'
                CHECK(status IN ('Pending', 'In Progress', 'Completed')),
            completed_at TEXT,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
        );
        """
    )

    # 7. calendar_events
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS calendar_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL CHECK(length(trim(title)) > 0),
            event_type TEXT NOT NULL CHECK(
                event_type IN (
                    'Internal Examination',
                    'External Examination',
                    'Practical Examination',
                    'Assignment Submission',
                    'Project Submission',
                    'Holiday',
                    'Workshop',
                    'Seminar',
                    'Hackathon',
                    'Other'
                )
            ),
            start_date TEXT NOT NULL CHECK(length(trim(start_date)) > 0),
            end_date TEXT,
            start_time TEXT,
            description TEXT,
            reminder_at TEXT,
            created_at TEXT,
            updated_at TEXT
        );
        """
    )

    # 8. study_sessions
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS study_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            topic_id INTEGER,
            study_date TEXT NOT NULL CHECK(length(trim(study_date)) > 0),
            start_time TEXT,
            end_time TEXT,
            duration_minutes INTEGER NOT NULL CHECK(duration_minutes > 0),
            study_goal TEXT,
            completed_work TEXT,
            next_topic TEXT,
            productivity_rating INTEGER
                CHECK(productivity_rating IS NULL OR (productivity_rating >= 1 AND productivity_rating <= 5)),
            status TEXT NOT NULL DEFAULT 'Completed'
                CHECK(status IN ('Completed', 'Partially Completed', 'Not Completed')),
            notes TEXT,
            created_at TEXT,
            FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
            FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE SET NULL
        );
        """
    )

    # 9. daily_checkins
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            checkin_date TEXT NOT NULL UNIQUE CHECK(length(trim(checkin_date)) > 0),
            goal_completed INTEGER NOT NULL DEFAULT 0 CHECK(goal_completed IN (0, 1)),
            planned_study_minutes INTEGER
                CHECK(planned_study_minutes IS NULL OR planned_study_minutes >= 0),
            tomorrow_plan TEXT,
            productivity_rating INTEGER
                CHECK(productivity_rating IS NULL OR (productivity_rating >= 1 AND productivity_rating <= 5)),
            notes TEXT,
            created_at TEXT,
            updated_at TEXT
        );
        """
    )

    # 10. timetable
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS timetable (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            topic_id INTEGER,
            study_date TEXT NOT NULL CHECK(length(trim(study_date)) > 0),
            start_time TEXT NOT NULL CHECK(length(trim(start_time)) > 0),
            end_time TEXT NOT NULL CHECK(length(trim(end_time)) > 0),
            session_title TEXT,
            priority TEXT NOT NULL DEFAULT 'Medium'
                CHECK(priority IN ('Low', 'Medium', 'High')),
            status TEXT NOT NULL DEFAULT 'Planned'
                CHECK(status IN ('Planned', 'Completed', 'Skipped')),
            source TEXT NOT NULL DEFAULT 'Generated'
                CHECK(source IN ('Generated', 'Manual')),
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
            FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE SET NULL
        );
        """
    )

    # 11. video_resources
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS video_resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            topic_id INTEGER,
            title TEXT NOT NULL CHECK(length(trim(title)) > 0),
            channel_name TEXT,
            video_url TEXT NOT NULL CHECK(length(trim(video_url)) > 0),
            notes TEXT,
            created_at TEXT,
            FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
            FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE SET NULL
        );
        """
    )

    # Helpful indexes for common queries
    indexes = (
        "CREATE INDEX IF NOT EXISTS idx_topics_subject_id ON topics(subject_id);",
        "CREATE INDEX IF NOT EXISTS idx_marks_subject_id ON marks(subject_id);",
        "CREATE INDEX IF NOT EXISTS idx_assignments_subject_id ON assignments(subject_id);",
        "CREATE INDEX IF NOT EXISTS idx_assignments_deadline_date ON assignments(deadline_date);",
        "CREATE INDEX IF NOT EXISTS idx_calendar_events_dates ON calendar_events(start_date, end_date);",
        "CREATE INDEX IF NOT EXISTS idx_study_sessions_subject_id ON study_sessions(subject_id);",
        "CREATE INDEX IF NOT EXISTS idx_study_sessions_topic_id ON study_sessions(topic_id);",
        "CREATE INDEX IF NOT EXISTS idx_study_sessions_study_date ON study_sessions(study_date);",
        "CREATE INDEX IF NOT EXISTS idx_timetable_subject_id ON timetable(subject_id);",
        "CREATE INDEX IF NOT EXISTS idx_timetable_topic_id ON timetable(topic_id);",
        "CREATE INDEX IF NOT EXISTS idx_timetable_study_date ON timetable(study_date);",
        "CREATE INDEX IF NOT EXISTS idx_video_resources_subject_id ON video_resources(subject_id);",
        "CREATE INDEX IF NOT EXISTS idx_video_resources_topic_id ON video_resources(topic_id);",
    )
    for index_sql in indexes:
        connection.execute(index_sql)

    # Safe additive schema migration for student_profile (avatar columns)
    try:
        profile_cols = {
            row[1]
            for row in connection.execute("PRAGMA table_info(student_profile);").fetchall()
        }
        if profile_cols:
            if "avatar_preset" not in profile_cols:
                connection.execute("ALTER TABLE student_profile ADD COLUMN avatar_preset TEXT;")
            if "avatar_path" not in profile_cols:
                connection.execute("ALTER TABLE student_profile ADD COLUMN avatar_path TEXT;")
    except Exception:
        pass

    # Record schema version for future additive migrations
    if get_schema_version(connection) < SCHEMA_VERSION:
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION};")

    connection.commit()


def initialize_schema(conn: sqlite3.Connection) -> None:
    """Backward-compatible wrapper around create_tables()."""
    create_tables(conn)
