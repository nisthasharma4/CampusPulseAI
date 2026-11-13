"""Central configuration settings for CampusPulse AI."""

from pathlib import Path

# Project root directory (parent of utils/)
BASE_DIR = Path(__file__).resolve().parent.parent

# Application metadata
APP_NAME = "CampusPulse AI"
APP_SUBTITLE = "Intelligent Student Academic Planner, Performance Analysis & Study Progress Tracking System"
APP_ICON = "🎓"
APP_TAGLINE = "Plan Smarter. Study Better. Track Your Growth."
APP_DESCRIPTION = (
    "Your personal academic companion to organize subjects, plan study schedules, "
    "manage assignments and monitor your learning progress."
)
DEV_STATUS = "Complete (v1.0)"

# Database configuration
DB_NAME = "campuspulse.db"
DB_PATH = BASE_DIR / DB_NAME

# Asset paths
STYLES_PATH = BASE_DIR / "assets" / "styles.css"

# Default academic & study settings
ATTENDANCE_TARGET = 75
ATTENDANCE_WARNING_BUFFER = 5.0  # Percentage buffer above target for 'Close to Target' warning
MARKS_WEAK_THRESHOLD = 60.0      # Weighted marks % below which a subject needs attention
DEFAULT_STUDY_SESSION_MINUTES = 60
DEFAULT_BREAK_MINUTES = 10

# Rule-based recommendation thresholds & priority scores
WEEKLY_STUDY_WARNING_RATIO = 0.70  # Warn if weekly study hours are below 70% of target
TOPIC_OVERDUE_WARNING = True       # Flag incomplete topics past their target completion date
PRODUCTIVITY_MIN_RECORDS = 4       # Minimum check-ins/rated sessions required for trend analysis

RECOMMENDATION_PRIORITY_SCORES = {
    "overdue_assignment": 100,
    "assignment_due_today": 95,
    "attendance_below_target": 90,
    "low_academic_marks": 85,
    "weak_subject_combined": 88,
    "topic_past_target": 75,
    "assignment_due_soon": 70,
    "weekly_study_below_target": 65,
    "attendance_close_to_target": 60,
    "topic_revision_needed": 50,
    "assignment_due_week": 35,
    "general_study_improvement": 30,
    "positive_progress": 20,
}

# Smart Timetable Generator settings (Step 8)
TIMETABLE_HORIZON_DAYS = 7
EXAM_PRIORITY_DAYS = 14
ASSIGNMENT_PRIORITY_DAYS = 7
DEFAULT_TIMED_EVENT_BLOCK_MINUTES = 120  # Assumed block duration for timed calendar events

SUBJECT_PRIORITY_WEIGHTS = {
    "marks_below_40": 40,
    "marks_40_to_50": 30,
    "marks_50_to_60": 20,
    "marks_60_to_75": 10,
    "attendance_below_target": 25,
    "attendance_close_to_target": 10,
    "topic_overdue": 20,
    "topic_in_progress": 10,
    "assignment_overdue": 30,
    "assignment_due_1_day": 25,
    "assignment_due_3_days": 15,
    "assignment_due_7_days": 5,
    "exam_within_3_days": 30,
    "exam_within_7_days": 20,
    "exam_within_14_days": 10,
    "low_recent_study": 5,
}

# Video Lecture Suggestions & Resource Library settings (Step 9)
VIDEO_LANGUAGES = ("Hindi", "English", "Both")
VIDEO_LECTURE_TYPES = (
    "Complete Course",
    "Topic Explanation",
    "Conceptual Understanding",
    "Quick Revision",
    "Problem Solving",
    "Practical Demonstration",
)
VIDEO_ACADEMIC_LEVELS = (
    "BTech Beginner",
    "College Level",
    "Advanced Understanding",
)
ALLOWED_YOUTUBE_DOMAINS = (
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
)

# Progress Analytics date filter presets (Step 10)
ANALYTICS_DATE_FILTERS = (
    "Today",
    "Last 7 Days",
    "Last 30 Days",
    "This Week",
    "Previous Week",
    "This Month",
    "Previous Month",
    "Last 3 Months",
    "Custom Date Range",
    "All Time",
)
