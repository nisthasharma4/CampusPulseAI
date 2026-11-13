# CampusPulse AI

**Intelligent Student Academic Planner, Performance Analysis & Study Progress Tracking System**

> *"Plan Smarter. Study Better. Track Your Growth."*

> **Project Status:** Complete (v1.0) — All 11 Development Steps Implemented, Fully Integrated, Elevated to **Design System V4** (Midnight Plum `#272539` & Iris `#5C559A`, Warm Canvas `#F5F3F8`, Ivory Surface `#FFFFFF`, Apricot `#E9B67D`, Terracotta `#C87863`, Muted Sage `#6B8B7F`, Student Avatar System, 60fps Micro-Interactions, WCAG 2.2 AA Contrast Compliant), and Verified with **109 Passing Automated Tests**.

---

## 1. Project Abstract

**CampusPulse AI** is a comprehensive, student-centric academic planner, study progress tracker, and performance analysis system designed specifically for college students. Developed as a BTech second-year mini project using Python, Streamlit, and SQLite, CampusPulse AI provides a unified, 100% local platform to eliminate fragmented academic tools. It integrates student profiling, syllabus topic management, daily study session tracking, aggregate attendance monitoring with class shortage calculations, internal marks tracking, assignment deadline reminders, a college academic calendar, a transparent rule-based AI recommendation engine, a deterministic weekly study timetable generator, encoded YouTube lecture discovery, and multi-period progress analytics with CSV data exports.

---

## 2. Problem Statement

College students frequently manage their academic responsibilities across disconnected notebooks, spreadsheets, mobile alarms, and video platforms. Consequently:
- Critical assignment deadlines and exam dates are easily overlooked.
- Students fall below mandatory attendance requirements without timely warnings.
- Weaker subjects and lagging syllabus topics are neglected until midterms.
- Daily study habits, actual study hours, and learning milestones remain untracked.

CampusPulse AI addresses this challenge by providing a centralized desktop web application that delivers end-to-end academic visibility and actionable study guidance.

---

## 3. Project Objectives

1. Maintain full student profiles and academic availability preferences.
2. Track subjects, syllabus topics, learning milestones, and completion dates.
3. Record daily study sessions, productivity ratings, and study journals.
4. Calculate weighted aggregate attendance and class shortage counts against target thresholds.
5. Record internal assessment marks and automatically identify weak subjects.
6. Manage assignments, deadline reminders, and college academic calendar events.
7. Provide transparent, explainable rule-based AI recommendations for academic improvement.
8. Deterministically generate conflict-free 7-day study timetables prioritizing weak subjects and exams.
9. Construct encoded YouTube lecture search URLs and organize a personal study resource library.
10. Generate multi-period progress analytics with interactive Plotly visualizations and CSV exports.

---

## 4. Main Application Modules

CampusPulse AI features 12 integrated pages built with Streamlit's native multipage architecture:

1. **Main Dashboard (`app.py`):** Central control center with 8 live KPI summary cards, today's schedule, today's study summary, upcoming assignments, calendar events, top AI recommendations, weekly study progress bar chart, syllabus progress table, and one-click quick action buttons.
2. **Student Profile (`pages/1_Profile.py`):** Configures student details, semester, branch, weekly study targets, daily study hours, attendance target, preferred study days, and session/break durations.
3. **Subjects & Topics (`pages/2_Subjects_Topics.py`):** Manages subjects, syllabus topics, sequence numbers, estimated hours, start/target/completion dates, and visual learning journeys.
4. **Daily Study Tracker (`pages/3_Daily_Study_Tracker.py`):** Logs study sessions (auto/manual duration, productivity rating 1–5, study goals, notes), daily goal check-ins, and reverse-chronological study logs.
5. **Academic Performance (`pages/4_Academic_Performance.py`):** Tracks aggregate classes held/attended, shortage formulas to reach target, internal assessment marks, and weak subject identification.
6. **Assignments & Reminders (`pages/5_Assignments_Reminders.py`):** Tracks assignment status (`Pending`, `In Progress`, `Completed`), priority levels, deadline countdowns, overdue badges, and completed timestamps.
7. **College Calendar (`pages/6_College_Calendar.py`):** Local academic calendar for examinations, practicals, submissions, holidays, workshops, and hackathons.
8. **AI Recommendations (`pages/7_AI_Recommendations.py`):** Transparent, explainable rule-based intelligence evaluating attendance shortages, overdue assignments, weak subjects, study consistency, and topic delays.
9. **Smart Timetable (`pages/8_Smart_Timetable.py`):** Deterministic 7-day study scheduler allocating study slots based on availability, break spacing, holiday/exam avoidance, and multi-factor subject priority scores.
10. **Video Lectures (`pages/9_Video_Lectures.py`):** Constructs URL-encoded YouTube search links by subject/topic/language/type, with personal library curation and HTTPS link validation.
11. **Progress Analytics (`pages/10_Progress_Analytics.py`):** Multi-period analytics (`Today`, `Last 7 Days`, `This Month`, `Custom`, `All Time`), daily/weekly/monthly charts, completion durations, streaks, and UTF-8 CSV exports.
12. **About Project (`pages/11_About_Project.py`):** Full technical documentation, system architecture, rule-based AI explanation, limitations, and future roadmap.
- **Smart Video Lecture Suggestions:** URL-encoded YouTube search links and a personal saved video resource manager.
- **Rule-Based AI Recommendation Engine:** Transparent, explainable Python rules for study and performance guidance (no ML training or paid APIs).
- **Progress Analytics & Export:** Interactive Plotly charts and CSV export for study history and summaries.

---

## 5. Technology Stack

- **Frontend:** Python Streamlit, Custom CSS, Plotly
- **Application Logic:** Python, Pandas, NumPy, `datetime`, `urllib.parse`
- **Database:** SQLite (`campuspulse.db` via Python's built-in `sqlite3`)
- **Testing:** Pytest

---

## 6. Initial Folder Structure

```text
CampusPulse_AI/
├── app.py                  # Main Streamlit entry point
├── pages/                  # Future multi-page Streamlit modules
├── database/
│   ├── __init__.py
│   ├── db.py               # SQLite connection & initialization
│   └── schema.py           # Database schema definitions (expanded in Step 2)
├── services/
│   └── __init__.py         # Business logic services (upcoming steps)
├── utils/
│   ├── __init__.py
│   ├── config.py           # Central app & database configuration
│   └── validators.py       # Reusable input validation helpers
├── assets/
│   └── styles.css          # Custom SaaS dashboard styling
├── data/                   # Static/reference data files
├── tests/                  # Automated unit & integration tests
├── requirements.txt        # Python dependencies
├── README.md               # Project documentation
└── .gitignore              # Git ignore rules
```

---

## 7. Installation & Setup (Windows PowerShell)

### Step 1: Create a Virtual Environment
Run the following command in the project root directory:
```powershell
python -m venv .venv
```

### Step 2: Activate the Virtual Environment
```powershell
.venv\Scripts\activate
```

### Step 3: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Start the Application
```powershell
streamlit run app.py
```

---

## 8. Database Architecture (Step 2)

CampusPulse AI uses a local **SQLite** database stored at the project root:

- **Database File:** `campuspulse.db` (configured via `utils/config.py`)
- **Schema Version:** Tracked via SQLite `PRAGMA user_version` (currently `v1`)
- **Initialization:** Calling `database.db.initialize_database()` runs `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS` safely without dropping tables or deleting existing records. Foreign key enforcement (`PRAGMA foreign_keys = ON`) is enabled on every connection.

### The 11 Database Tables
1. **`student_profile`**: Single-user student details, study availability (`available_days` as comma-separated days), session/break lengths, and attendance target.
2. **`subjects`**: College subjects with codes, semester, start/target/completion dates, and status (`Not Started`, `In Progress`, `Completed`).
3. **`topics`**: Syllabus topics linked to a subject (`ON DELETE CASCADE`), sequence order, estimated hours, dates, and status. Actual study hours are computed from `study_sessions`.
4. **`attendance`**: One aggregate attendance record per subject (`subject_id UNIQUE`), storing `classes_held` and `classes_attended`.
5. **`marks`**: Subject-wise assessment records (`marks_obtained`, `maximum_marks`, `assessment_type`, `assessment_date`).
6. **`assignments`**: Subject-linked assignments with deadlines, reminders, priority (`Low`, `Medium`, `High`), and status (`Pending`, `In Progress`, `Completed`).
7. **`calendar_events`**: Local college academic events (exams, practicals, holidays, workshops, seminars, hackathons).
8. **`study_sessions`**: Daily study logs linked to a subject and optionally a topic (`ON DELETE SET NULL` so study history is preserved even if a topic is edited or removed).
9. **`daily_checkins`**: Daily reflection check-ins (`checkin_date UNIQUE`, `goal_completed`, `planned_study_minutes`, `productivity_rating`, `tomorrow_plan`).
10. **`timetable`**: Generated and manually edited study timetable slots (`source` in `Generated` / `Manual`, `status` in `Planned` / `Completed` / `Skipped`).
11. **`video_resources`**: Saved educational video links associated with a subject and optional topic.

### Key Data Integrity & Validation Rules
- Study duration must be strictly positive (`duration_minutes > 0`).
- Productivity ratings must be between `1` and `5`.
- Marks cannot be negative, `maximum_marks` must be `> 0`, and `marks_obtained <= maximum_marks`.
- Attendance counts cannot be negative, and `classes_attended <= classes_held`.
- Optional `topic_id` references on `study_sessions`, `timetable`, and `video_resources` are validated to belong to the selected `subject_id`.

### Running Database Tests
Tests run against isolated temporary SQLite files via `pytest` (never touching `campuspulse.db`):
```powershell
.venv\Scripts\activate
pytest tests/test_database.py -v
```

---

## 9. Student Profile, Subject & Topic Management (Step 3)

### Student Profile (`pages/1_Profile.py`)
- Single-user local profile storing personal details, academic info (college, branch, semester, attendance target), and study preferences (weekly target, daily available hours, preferred start/end time, available days, session & break durations).
- Reuses the single `student_profile` row on edits, preserving `created_at` and updating `updated_at`.

### Subject & Topic Management (`pages/2_Subjects_Topics.py`)
- **Subjects Manager:** Add, edit, and delete subjects (with explicit confirmation and cascade warning). Prevents duplicate subjects with the same name and semester.
- **Topics & Syllabus Tracker:** Add ordered topics under each subject, reorder via sequence numbers, and update statuses (`Not Started`, `In Progress`, `Completed`) with quick action buttons or full editing.
- **Automatic Date Tracking:**
  - Changing a topic from `Not Started` to `In Progress` records today's date as `start_date` if none exists.
  - Marking a topic `Completed` records today's date as `completion_date` while preserving the original `start_date`.
  - Editing a topic without changing status preserves existing historical dates.
  - Reopening a completed topic preserves its historical completion date until completed again.
- **Subject Completion Calculation:**
  - `Completion Percentage = (Completed Topics / Total Topics) × 100` (safely `0.0%` when zero topics exist).
- **Learning Journey Timeline:** Displays the subject start date and chronological topic milestones (start date, completion date, status, and actual study hours from `study_sessions`).

### How to Use the New Pages
1. Start the app: `streamlit run app.py`
2. Open **1 Profile** from the left sidebar to set up or update your student profile.
3. Open **2 Subjects Topics** from the left sidebar to add subjects, manage syllabus topics, and view your learning journey timeline.

---

## 10. Daily Study Tracker & Learning History (Step 4)

The **Daily Study Tracker** (`pages/3_Daily_Study_Tracker.py` + `services/study_service.py`) manages daily learning logs and time analytics:

- **Today's Study Overview:** Displays today's studied hours, session count, completed sessions, average productivity rating, daily study target (from `student_profile`), remaining time, and target completion percentage.
- **Study Session Recording:** Log sessions by subject and optional topic (or general subject study) with two duration calculation methods:
  - **Start & End Time:** Automatically computes same-day duration in minutes.
  - **Manual Duration:** Direct entry of hours and minutes.
  - Recording the first session on a `Not Started` topic automatically moves it to `In Progress` and sets `start_date` if missing, without ever auto-completing topics or altering `Completed` topic dates.
- **Daily Check-in:** One check-in per date (`checkin_date UNIQUE`) tracking planned study hours, goal completion, productivity rating (`1–5`), notes, and tomorrow's plan. Re-submitting for the same date updates the existing record without duplicating.
- **Complete Study History:** Reverse-chronological log with filters for time period (`Today`, `Last 7 Days`, `Last 30 Days`, `This Month`, `Previous Month`, `Custom Date Range`), subject, topic, and status, plus session editing and confirmed deletion.
- **Subject-wise & Topic-wise Study Time:** Actual study hours are always calculated dynamically by summing `study_sessions.duration_minutes` (never stored as an independently editable field), visualized with a Plotly bar chart.
- **Learning Journey:** Chronological timeline of actual dated study sessions per subject.

---

## 11. Academic Performance, Attendance & Marks (Step 5)

The **Academic Performance** module (`pages/4_Academic_Performance.py` + `services/academic_service.py`) provides transparent tracking and analysis:

- **Attendance Formula:** `Attendance % = (Classes Attended / Classes Conducted) × 100` (safely handled when 0 classes are conducted).
- **Weighted Overall Attendance:** `(Sum of All Attended Classes / Sum of All Conducted Classes) × 100` across subjects.
- **Required Additional Classes Calculator:** For subjects below target `T` (decimal), calculates `n = ceil((T × H - A) / (1 - T))` consecutive classes needed, including safe handling for `0` classes and `100%` target edge cases.
- **Marks & Weighted Assessment Average:** Individual assessment percentage is `(Marks Obtained / Maximum Marks) × 100`; subject-wise weighted average is `(Sum of Marks Obtained / Sum of Maximum Marks) × 100`.
- **Weak Subject Identification:** Evaluates subjects against the configurable marks threshold (`MARKS_WEAK_THRESHOLD = 60%` in `utils/config.py`) and the student's `attendance_target`, flagging low marks, low attendance, or both with clear explanations, while marking subjects without marks as `Insufficient Data`.
- **How to Use:** Open **4 Academic Performance** in the left sidebar to update subject attendance, record/edit/delete assessment marks, review weak subjects, and explore interactive Plotly analytics charts.

---

## 12. Assignment Manager, Deadline Reminders & College Calendar (Step 6)

### Assignment Manager & Deadline Reminders (`pages/5_Assignments_Reminders.py`)
- **Assignment Management:** Create, filter (`All`, `Pending`, `In Progress`, `Completed`, `Overdue`, `Due Today`, `Due Within 3 Days`), edit, complete, and delete assignments linked to subjects.
- **Status & Completion Dates:** Marking an assignment `Completed` records `completed_at` while preserving `assigned_date` and `created_at`; reopening clears `completed_at`.
- **In-App Reminder Logic:** Classifies incomplete assignments into `Overdue`, `Due Today`, `Due Soon` (within 3 days), or `Upcoming`, and triggers reminders when `reminder_at` arrives. Completed assignments never trigger reminders.
- **Local Reminder Limitation:** Because CampusPulse AI runs locally in Streamlit, reminders are evaluated when the application is opened or refreshed—not when the app or computer is closed.

### College Academic Calendar (`pages/6_College_Calendar.py`)
- **Supported Event Types:** `Internal Examination`, `External Examination`, `Practical Examination`, `Assignment Submission`, `Project Submission`, `Holiday`, `Workshop`, `Seminar`, `Hackathon`, and `Other`.
- **Views & Filters:** Upcoming events list, Monthly View (month/year selector), custom date-range filter, event type filter, and full Add/Edit/Delete management.
- **Combined Upcoming Schedule:** Merges pending assignment deadlines (`assignments`) and upcoming college events (`calendar_events`) chronologically at the service layer without duplicating records across tables.

---

## 13. Rule-Based AI Recommendation Engine (Step 7)

CampusPulse AI uses a **transparent, explainable rule-based intelligent recommendation system** (`services/recommendation_service.py` + `pages/7_AI_Recommendations.py`). **It is not a trained Machine Learning model** and does not require historical ML datasets, Random Forest, neural networks, or paid external AI APIs.

### How Recommendations Work
- **Academic Marks Rules:** Compares subject-wise weighted marks against `MARKS_WEAK_THRESHOLD` (`60%` in `utils/config.py`) and compares dated assessments when `>= 2` records exist. Subjects without marks report `Insufficient assessment information`.
- **Attendance Rules:** Reuses `academic_service.py` to flag subjects below the student's `attendance_target` (`High Priority`), within `ATTENDANCE_WARNING_BUFFER` (`Medium Priority`), or comfortably above (`Positive Progress`).
- **Assignment Prioritization:** Prioritizes incomplete assignments (`Overdue` = 100, `Due Today` = 95, `Due in 1–2 days` = 70, `Due in 3–7 days` = 35) and suppresses `Completed` assignments.
- **Study Consistency & Weak Subjects:** Sums `study_sessions.duration_minutes` for the current Monday–Sunday week against `weekly_study_target`, and combines low marks + low attendance + limited weekly study hours into focused subject recommendations.
- **Topic Delay Detection:** Flags incomplete topics past `target_date`, in-progress topics exceeding `estimated_hours`, and subjects with 100% topic completion.
- **Overall Progress Status:** Evaluates real SQLite data into `Excellent Progress`, `Good Progress`, `Needs Attention`, or `Insufficient Data` with clear reasons (informational only, not an official university grade).

### Limitations of a Rule-Based System
- Recommendations depend strictly on the records entered by the student and configured static thresholds rather than adaptive statistical learning.

---

## 14. Step 8 — Smart Timetable Generator & Study Scheduler

Step 8 introduces `services/timetable_service.py` and `pages/8_Smart_Timetable.py`, providing deterministic, rule-based weekly study scheduling without machine learning or external AI APIs.

- **Availability Synchronization:** Reads and updates preferred study days, start/end times, daily available minutes, weekly target hours, session duration, and break duration directly in `student_profile`.
- **Deterministic Priority Scoring:** Scores every subject using weak-subject flags, marks percentage, attendance below target, incomplete syllabus topics, pending/overdue assignments within 7 days, upcoming calendar exams within 14 days, and optional manual exam-subject selection.
- **Conflict-Free Weekly Scheduling:** Allocates 7-day study sessions while respecting break durations, daily/weekly capacity caps, full-day holidays/events, timed calendar events, and existing `Manual` or `Completed` timetable entries.
- **Preview, Save & Manual Management:** Lets students inspect priority scores and reasons before saving, safely replace uncompleted `Generated` entries while preserving `Manual` and `Completed` sessions, add/edit/delete manual sessions, and update session statuses (`Planned`, `Completed`, `Skipped`).

---

## 15. Step 9 — Video Lecture Suggestions & Personal Learning Resource Library

Step 9 introduces `services/video_service.py` and `pages/9_Video_Lectures.py`, helping students discover relevant YouTube lectures and organize a personal subject-wise and topic-wise learning library without external APIs or scraping.

- **Subject & Topic Selection:** Dynamically loads subjects and subject-scoped topics from SQLite, while also supporting general subject-level searches when no topic is selected.
- **Lecture Preferences & Query Builder:** Combines subject, optional topic, Lecture Language (`Hindi`, `English`, `Both`), Lecture Type (`Complete Course`, `Topic Explanation`, `Conceptual Understanding`, `Quick Revision`, `Problem Solving`, `Practical Demonstration`), and Academic Level (`BTech Beginner`, `College Level`, `Advanced Understanding`) into natural, deduplicated search queries.
- **URL-Encoded YouTube Search Links:** Uses `urllib.parse.quote_plus` to generate valid `https://www.youtube.com/results?search_query=...` links and quick search variations (`Complete Explanation`, `Topic-Wise Lecture`, `Practice Problems`, `Revision Lecture`) opened via clickable links.
- **Personal Learning Resource Library:** Validates HTTPS YouTube domains (`youtube.com`, `www.youtube.com`, `m.youtube.com`, `youtu.be`), prevents duplicate subject/topic/URL entries, and supports saving, searching, filtering, editing, and deleting resources with subject-wise and topic-wise organization.
- **Limitations:** Search links open YouTube search results directly in the browser; CampusPulse AI does not call the YouTube API, scrape video metadata, or automatically pre-verify individual videos — students select and save their preferred lectures.

---

## 16. Step 10 — Student Progress Analytics, Performance Reports & Data Export

Step 10 introduces `services/analytics_service.py` and `pages/10_Progress_Analytics.py`, implementing a comprehensive progress analytics engine, interactive Plotly dashboards, custom date-range reports, and UTF-8 CSV exports using actual SQLite data.

- **Multi-Period Date Filters:** Supports `Today`, `Last 7 Days`, `Last 30 Days`, `This Week`, `Previous Week`, `This Month`, `Previous Month`, `Last 3 Months`, `Custom Date Range`, and `All Time`, maintaining strict date boundaries and distinguishing date-filtered metrics from overall academic snapshots.
- **Study Time Trends:** Plots daily study hours with missing-day zeros filled, weekly Monday–Sunday groupings, monthly study aggregations, and session completion breakdowns.
- **Subject & Topic Analytics:** Calculates subject-wise study time distribution, topic-wise study time bar charts, topic calendar completion days versus actual logged study hours, and preserves historical study sessions whose topic was deleted (`topic_id = NULL`).
- **Consistency & Productivity:** Computes longest and current consecutive study-recording streaks, daily goal completion percentages, and tracks check-in ratings and session ratings separately without artificial averaging.
- **Academic Marks & Attendance Snapshot:** Calculates weighted subject-wise marks percentages, assessment type breakdowns, and presents the aggregate attendance snapshot with clear documentation that date-by-date tracking requires dated attendance logs.
- **Assignments & Timetable Completion:** Analyzes period-specific assignment status and completion rates, tracks timetable scheduled vs. completed sessions, and keeps planned timetable hours strictly distinct from actual logged study time.
- **Custom Progress Report & CSV Export:** Generates printable progress summary cards and enables one-click CSV downloads for Study History, Subject Summary, Topic Summary, Assessment History, Assignment Summary, and Timetable History.

---

## 17. Project Development Roadmap

1. **Step 1 (Completed):** Project foundation, virtual environment setup, configuration, validation helpers, SQLite connection foundation, and initial welcome UI.
2. **Step 2 (Completed):** Complete 11-table SQLite schema, foreign keys, indexes, parameterized CRUD helpers, and automated database test suite.
3. **Step 3 (Completed):** Student Profile (`pages/1_Profile.py`), Subject & Topic Management (`pages/2_Subjects_Topics.py`), automatic date tracking, and learning journey timeline.
4. **Step 4 (Completed):** Daily Study Tracker (`pages/3_Daily_Study_Tracker.py`), Study Journal, Daily Check-ins, and Time Analysis.
5. **Step 5 (Completed):** Academic Performance (`pages/4_Academic_Performance.py`), Attendance Tracker, Marks Manager, and Weak Subject Identification.
6. **Step 6 (Completed):** Assignment Manager & Reminders (`pages/5_Assignments_Reminders.py`) and College Academic Calendar (`pages/6_College_Calendar.py`).
7. **Step 7 (Completed):** Rule-Based AI Recommendation Engine (`pages/7_AI_Recommendations.py`).
8. **Step 8 (Completed):** Smart Timetable Generator & Personalized Study Scheduler (`pages/8_Smart_Timetable.py`).
9. **Step 9 (Completed):** Video Lecture Suggestions & Personal Learning Resource Library (`pages/9_Video_Lectures.py`).
10. **Step 10 (Completed):** Complete Student Progress Analytics, Performance Reports and Data Export (`pages/10_Progress_Analytics.py`).
11. **Step 11 (Completed):** Final Application Integration, Main Dashboard Enhancement, About Project Documentation, Full Test Suite Verification (95 Tests), and Project Completion.

---

## 17. Design System V3: Warm Cream · Forest Green · Editorial Academic Workspace

CampusPulse AI features **Design System V3: Warm Editorial Academic Productivity Workspace**, inspired by modern university productivity environments, clean editorial layouts, and warm stationery interfaces. It delivers a distraction-free, accessible, human-designed aesthetic adhering strictly to **WCAG 2.2 AA** accessibility standards:

### Core Design Tokens & Palette
- **Main App Background (Warm Cream):** `#F6F2E9` — Calm, natural, warm surface that reduces eye fatigue compared to harsh white or artificial dark modes.
- **Card & Container Surface (Ivory White):** `#FFFEFA` — Crisp, warm white containers with `#93897B` subtle borders and light elevations.
- **Sidebar Background (Soft Beige):** `#ECE5D8` — Dedicated navigation column with `#D8D0C5` border separator.
- **Primary Brand (Forest Green):** `#36594A` — Grounded, professional academic brand tone (Deep Forest hover `#29483A`).
- **Secondary Accent (Earthy Terracotta):** `#9D563A` — Warm, restrained editorial accent for complementary data series and highlights.
- **Primary Body Text (Warm Charcoal):** `#292C28` — High-contrast deep charcoal text providing crisp legibility (passes AAA standards).
- **Secondary / Supporting Text (Warm Grey):** `#5C5A50` — Subdued slate tone (passes AA standard $\ge 4.5:1$).
- **Interface Borders (Warm Stone):** `#93897B` — Delineates inputs and cards without harsh digital contrast.
- **Selected Navigation (Soft Sage):** `#DCE5D9` — Highlights active workspace link with `#29483A` deep forest text.
- **Semantic Status Badges:**
  - **Success:** `#315B42` text on `#E6EFE8` background (`#C4D8CA` border)
  - **Warning:** `#875514` text on `#F8EFE3` background (`#E8D4BE` border)
  - **Danger / Overdue:** `#963B32` text on `#F9E8E6` background (`#ECC8C5` border)
  - **Information:** `#355C78` text on `#E4EDF3` background (`#C3D5E2` border)

### WCAG 2.2 AA Contrast Compliance Verification
| UI Element Pair | Foreground | Background | Measured Ratio | WCAG 2.2 AA Standard | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Main Text on Warm Cream | `#292C28` | `#F6F2E9` | **12.66:1** | $\ge 4.5:1$ (AA) | **Passes AAA** |
| Main Text on Ivory White | `#292C28` | `#FFFEFA` | **14.01:1** | $\ge 4.5:1$ (AA) | **Passes AAA** |
| Main Text on Soft Beige | `#292C28` | `#ECE5D8` | **11.29:1** | $\ge 4.5:1$ (AA) | **Passes AAA** |
| Secondary Text on Ivory White | `#5C5A50` | `#FFFEFA` | **6.86:1** | $\ge 4.5:1$ (AA) | **Passes AA** |
| Secondary Text on Warm Cream | `#5C5A50` | `#F6F2E9` | **6.20:1** | $\ge 4.5:1$ (AA) | **Passes AA** |
| Primary Forest Green on White text | `#36594A` | `#FFFFFF` | **7.82:1** | $\ge 4.5:1$ (AA) | **Passes AAA** |
| Deep Forest on Soft Sage (Active Link) | `#29483A` | `#DCE5D9` | **7.81:1** | $\ge 4.5:1$ (AA) | **Passes AAA** |
| Warm Stone Border on Ivory White | `#93897B` | `#FFFEFA` | **3.41:1** | $\ge 3.0:1$ (Non-text) | **Passes Non-Text** |
| Success Status on White | `#315B42` | `#FFFFFF` | **7.76:1** | $\ge 4.5:1$ (AA) | **Passes AAA** |
| Warning Status on White | `#875514` | `#FFFFFF` | **6.29:1** | $\ge 4.5:1$ (AA) | **Passes AA** |
| Danger Status on White | `#963B32` | `#FFFFFF` | **7.07:1** | $\ge 4.5:1$ (AA) | **Passes AAA** |
| Information Status on White | `#355C78` | `#FFFFFF` | **7.11:1** | $\ge 4.5:1$ (AA) | **Passes AAA** |
| Earthy Terracotta on Ivory White | `#9D563A` | `#FFFEFA` | **5.44:1** | $\ge 4.5:1$ (AA) | **Passes AA** |

### Critical Bug Fix & Navigation Architecture
1. **Duplicate Widget ID Resolution:** Fixed `StreamlitDuplicateElementId` in `app.py` caused by redundant duplicate button declarations in `_render_quick_actions()`. All quick action buttons now feature stable, unique keys (`dashboard_quick_log_study`, `dashboard_quick_subjects`, `dashboard_quick_attendance`, `dashboard_quick_assignments`, `dashboard_quick_timetable`, `dashboard_quick_video_lectures`, `dashboard_quick_analytics`).
2. **Top-Level Sidebar Branding:** CampusPulse AI branding (`CampusPulse AI` and `Your Academic Workspace`) is positioned at the very **top** of the sidebar, followed by a divider, the navigation links, and a system status card at the bottom.
3. **Explicit Navigation Labels:** Hides default automatic navigation via `client.showSidebarNavigation = false` and uses explicit `st.page_link` definitions, replacing the filename `app` with **Dashboard** (📊).
4. **Button Hierarchy:** Primary actions receive filled Forest Green styling (`#36594A`), secondary actions use Ivory surfaces with Warm Stone borders, and destructive actions use Earthy Red / Terracotta with confirmation modals.
5. **Responsive Quick Actions:** Split across 2 balanced rows (4 and 3 columns) preventing horizontal overflow or clipped labels on mobile and tablet viewport widths.

### Performance & Interactivity Optimizations
1. **Schema Check Memoization:** Implemented in-process database path validation tracking (`_INITIALIZED_PATHS`) in `database/db.py`. On subsequent page loads and interactive widget changes, repeated execution of 11 `CREATE TABLE` and 13 `CREATE INDEX` statements is bypassed, reducing connection initialization from **9.59 ms** down to **0.69 ms** (**93% latency reduction**).
2. **Form Grouping:** Interactive form submissions across Profile, Subjects, Study Tracker, Attendance, Marks, Assignments, Calendar, and Timetable are grouped inside `st.form`, ensuring zero wasted UI reruns during typing and field selection.
3. **Streamlit Theming Parity:** Explicit `.streamlit/config.toml` light base theme configuration prevents browser/OS dark mode inheritance from causing mismatched, inverted widget states.

---

## 18. Design System V4: Midnight Plum & Iris Architecture

CampusPulse AI features **Design System V4**, a distinctive academic productivity workspace designed with premium visual hierarchy, high-contrast readability, 60fps micro-interactions, and a native student avatar system.

### Color Palette & WCAG 2.2 AA Contrast Compliance

| Token | Hex Code | UI Application | Target Background | Contrast Ratio | WCAG Compliance |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Canvas Background** | `#F5F3F8` | Page background / Warm Canvas | — | — | Base Canvas |
| **Card Surface** | `#FFFFFF` | Metric cards, forms, panels | `#F5F3F8` | — | Base Surface |
| **Main Text** | `#282536` | Primary headers, body text, form inputs | `#FFFFFF` | **14.91:1** | **Passes AAA** (>= 7:1) |
| **Muted Text** | `#666273` | Subtitles, timestamps, metadata | `#FFFFFF` | **5.90:1** | **Passes AA** (>= 4.5:1) |
| **Brand Primary (Iris)** | `#5C559A` | Primary buttons, active tabs, accents | `#FFFFFF` | **6.52:1** | **Passes AA** (>= 4.5:1) |
| **Primary Hover** | `#48427D` | Button hover state | `#FFFFFF` | **8.93:1** | **Passes AAA** (>= 7:1) |
| **Sidebar Background** | `#272539` | Midnight Plum sidebar background | — | — | Deep Base |
| **Sidebar Text** | `#EAE7F2` | Navigation link labels | `#272539` | **12.21:1** | **Passes AAA** (>= 7:1) |
| **Active Nav Indicator** | `#E9B67D` | Apricot active indicator stripe | `#272539` | **8.12:1** | **Passes AAA** (>= 7:1) |
| **Status: Success** | `#38684F` | Completed badge text | `#EAF4EE` | **6.44:1** | **Passes AA** (>= 4.5:1) |
| **Status: Warning** | `#925B1F` | In Progress / Due Today badge text | `#FEF5E9` | **5.62:1** | **Passes AA** (>= 4.5:1) |
| **Status: Danger** | `#9A4147` | Overdue / Attendance shortage badge | `#FCEEEF` | **6.52:1** | **Passes AA** (>= 4.5:1) |
| **Status: Info** | `#4D6593` | Tips / Event type badge text | `#EDF3FC` | **5.84:1** | **Passes AA** (>= 4.5:1) |

### Student Avatar System (`utils/avatars.py`)

The application includes an end-to-end Student Avatar System supporting three tiers of visual representation:
1. **Dynamic Initials SVG Generator:** Algorithmic generation of crisp, circular vector SVGs rendered with student initials against a gradient backdrop.
2. **6 Themed Vector SVG Presets:**
   - *Classic Scholar:* Graduate cap & spectacles (`classic_student`)
   - *Academic Explorer:* Compass star & telescope (`academic_explorer`)
   - *Tech Innovator:* Code brackets & digital circuit (`tech_student`)
   - *Creative Mind:* Lightbulb spark & artist palette (`creative_learner`)
   - *Focused Scholar:* Open book & radiant beacon (`focused_scholar`)
   - *Minimalist Icon:* Modern geometric student silhouette (`minimal_portrait`)
3. **Pillow (PIL) Photo Processing & Storage:**
   - Direct file upload (`PNG`, `JPG`, `JPEG`, `WEBP`) with `<= 2.0 MB` validation.
   - High-quality center-square cropping and thumbnail resizing to exact `512×512` pixels via `Image.Resampling.LANCZOS`.
   - Local on-disk persistence in `data/avatars/` with UUID-based filenames and Base64 data URI browser embedding.
   - Automatic cleanup of superseded photo files on avatar replacement or reset.
4. **Additive SQLite Schema Migration:**
   - Safe additive migration adding `avatar_preset TEXT` and `avatar_path TEXT` to `student_profile` without dropping tables or altering existing student records.

---

## 19. Technology Stack

- **Programming Language:** Python 3.10+ (tested on Python 3.13)
- **Web Application Framework:** Streamlit (Native Multipage Architecture)
- **Embedded Relational Database:** SQLite 3 (with foreign key constraints and indexed queries)
- **Image Processing:** Pillow (PIL) 13.0+
- **Data Manipulation & Analysis:** Pandas
- **Interactive Visualizations:** Plotly Express & Plotly Graph Objects
- **Testing Framework:** Pytest (109 passing tests with isolated `tmp_path` test databases)
- **Styling:** Custom CSS Design System V4 (`assets/styles.css`) with Midnight Plum `#272539` & Iris `#5C559A`
- **Machine Learning / Paid External APIs:** **None** (Clean, deterministic, rule-based mathematical models)

---

## 20. Installation & Running Instructions

### Prerequisites
- Python 3.10 or higher installed.
- Windows PowerShell or Bash terminal.

### Setup Steps (Windows PowerShell)

```powershell
# 1. Create a Python virtual environment (if not already created)
python -m venv .venv

# 2. Activate the virtual environment
.venv\Scripts\activate

# 3. Install project dependencies
pip install -r requirements.txt

# 4. Run the automated test suite
python -m pytest -p no:cacheprovider -v

# 5. Launch CampusPulse AI
streamlit run app.py
```

The application will launch locally at `http://localhost:8501`.

---

## 20. Project Limitations & Ethical Design

- **Local Storage:** All student data is stored locally in `campuspulse.db`. Cloud synchronization and multi-device replication are not implemented.
- **Rule-Based System:** Recommendations and timetable generation rely on deterministic academic rules rather than predictive statistical learning.
- **Attendance Model:** Attendance is stored as aggregate counts per subject; daily roll-call records would require dated session attendance tables.
- **YouTube Integration:** Generates safe, URL-encoded search links without requiring YouTube API keys, quota management, or web scraping.

---

## 21. Demonstration Guide

For a structured evaluation walkthrough, refer to [docs/PROJECT_DEMO_GUIDE.md](file:///c:/Users/abhis/OneDrive/Desktop/CampusPulseAI/docs/PROJECT_DEMO_GUIDE.md).
