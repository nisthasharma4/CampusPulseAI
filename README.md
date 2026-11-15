# 🎓 CampusPulse AI

### Intelligent Student Academic Planner, Performance Analysis & Study Progress Tracking System

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://campus-pulse-ai-nistha.streamlit.app/)
[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/Streamlit-1.38%2B-FF4B4B.svg?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Database](https://img.shields.io/badge/Database-SQLite3-003B57.svg?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Tests](https://img.shields.io/badge/Tests-141%20Passed-brightgreen.svg?logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![Design System](https://img.shields.io/badge/UI%2FUX-Design%20System%20V4.1-6C5CE7.svg)](#-design-system--uiux)

---

## 🌐 Live Application & Links

Experience **CampusPulse AI** in real time:

* **🚀 Live Interactive Demo:** [https://campus-pulse-ai-nistha.streamlit.app/](https://campus-pulse-ai-nistha.streamlit.app/)
* **📂 GitHub Repository:** [https://github.com/nisthasharma4/CampusPulseAI](https://github.com/nisthasharma4/CampusPulseAI)

> **Quick Access:** Click the **Streamlit** badge above or open the live link to explore the deployed application directly in your browser without local installation.

---

## 📌 Project Overview & Problem Statement

College students frequently struggle with academic fragmentation: study schedules are unorganized, assignment deadlines slip past unnoticed, attendance drops below the critical 75% institutional threshold without early warning, and exam preparation lacks structured revision planning. Existing productivity tools are either generic to-do lists that lack academic context or enterprise software too cumbersome for daily student use.

**CampusPulse AI** bridges this gap as an all-in-one, privacy-first academic productivity workspace. Operating on a local relational SQLite database and built with Python and Streamlit, it brings together daily study tracking, automated 7-day conflict-free timetable generation, real-time attendance deficit calculation, coursework management, and an explainable rule-based AI academic advisory engine into a single unified workspace.

---

## ✨ Key Features & Functional Modules

CampusPulse AI consists of **11 core functional modules** accessible via a responsive multipage architecture:

### 1. 📊 Central Student Dashboard (`app.py`)
- **Executive Academic Metrics:** Real-time summary cards displaying Overall Attendance %, Total Study Hours, Pending Assignments, and Active Subjects.
- **Planned vs. Recorded Study Separation:** Clear visual distinction between scheduled target sessions and actual recorded study hours.
- **Urgent Action Center:** Imminent assignment countdowns (due in 24h, 48h, or this week) and upcoming college academic calendar milestones.
- **Syllabus Progress Tracker:** Subject-wise syllabus completion percentages with responsive progress bars.
- **AI Recommendation Spotlight:** Top prioritized actionable academic alerts displayed directly on the home page.

### 2. 👤 Student Profile & Avatar Studio (`pages/1_Profile.py`)
- **Academic Identity:** Manages student name, institution, department, current semester, target GPA, and weekly study goal hours.
- **Dynamic Avatar Studio:** Supports 6 pre-built modern SVG character avatars, dynamic vector-initial avatars based on student initials, and custom photo uploads with automatic square aspect-ratio cropping and resizing via Pillow.
- **Profile Persistence:** Settings immediately sync across the sidebar navigation and all dashboard views.

### 3. 📚 Subjects & Syllabus Management (`pages/2_Subjects_Topics.py`)
- **Curriculum Organization:** Add and configure academic subjects with custom course codes, credit units, and difficulty ratings (1 to 5).
- **Granular Syllabus Topics:** Break down courses into distinct modular topics and units with interactive completion toggles.
- **Progress Tracking:** Instant visibility into completed vs. remaining topics per course.

### 4. ⏱️ Daily Study Tracker & Journal (`pages/3_Daily_Study_Tracker.py`)
- **Session Logging:** Record focused study sessions by subject, specific topic, duration (in minutes/hours), and subjective energy levels.
- **Study Journaling:** Optional session notes and key takeaways for retention.
- **Historical Activity Feed:** Filterable timeline of past study sessions with edit and delete capabilities.

### 5. 📈 Academic Performance & Attendance Manager (`pages/4_Academic_Performance.py`)
- **Marks & Examination Tracker:** Log internal assessments, midterms, lab evaluations, and final semester grades.
- **Mandatory 75% Attendance Calculator:** Accurate subject-wise attendance tracking calculating exact classes attended vs. conducted.
- **Shortage Warning Engine:** Automatically computes the exact number of consecutive classes a student must attend to recover to 75%, or how many classes they can safely miss while remaining above the threshold.

### 6. 📝 Coursework & Assignment Reminders (`pages/5_Assignments_Reminders.py`)
- **Assignment Pipeline:** Track homework, laboratory records, term papers, and mini-project milestones.
- **Priority & Due Date Filtering:** Categorize tasks by urgency (High, Medium, Low) with automated countdown timers.
- **Status Management:** Mark assignments as Pending, In Progress, or Submitted.

### 7. 📅 College Academic Calendar (`pages/6_College_Calendar.py`)
- **Event Scheduling:** Centralized calendar for university examinations, practical dates, project submission deadlines, club activities, and holidays.
- **Time Representation:** Standardized 12-hour AM/PM presentation layer with canonical 24-hour database persistence.
- **Chronological Sorting:** Visual categorization of events occurring today, this week, and later in the semester.

### 8. 🤖 Explainable AI Recommendation Engine (`pages/7_AI_Recommendations.py`)
- **Deterministic Rule-Based Intelligence:** Evaluates academic data across attendance, upcoming exams, pending deadlines, and study consistency without non-deterministic "black box" behavior.
- **Transparent Reasoning:** Each recommendation includes the underlying trigger (e.g., *"Data Structures attendance is at 68.4%, below 75%"*), recommended action, and urgency ranking (Critical, High, Medium, Info).

### 9. 🗓️ Smart Timetable Generator (`pages/8_Smart_Timetable.py`)
- **Algorithmic 7-Day Scheduler:** Generates balanced study schedules distributing workload across available days based on subject difficulty weightings and student availability.
- **Conflict-Free Slot Allocation:** Prevents overlapping study sessions and balances intense subjects with lighter revision periods.
- **Timetable Preview & Persistence:** Review generated timetables before saving to the active database.

### 10. 🎥 Video Lecture & Learning Resource Library (`pages/9_Video_Lectures.py`)
- **Educational Query Generator:** Constructs targeted, high-yield educational search queries based on active syllabus topics.
- **Personalized Resource Bookmark:** Save verified YouTube video links, online documentation, textbook references, and course lecture notes tagged by subject.

### 11. 📉 Progress Analytics & Data Export (`pages/10_Progress_Analytics.py`)
- **Interactive Plotly Visualizations:** Study distribution donut charts, weekly study hour trends, subject-wise time allocations, and consistency streaks.
- **1-Click CSV Data Export:** Export complete historical data across 6 categories (Study Sessions, Subjects, Attendance Records, Marks, Assignments, Calendar Events) for external analysis or academic audits.

### 12. ℹ️ About Project & Architectural Specification (`pages/11_About_Project.py`)
- Detailed architectural blueprint, design philosophy, technical documentation, and step-by-step project demonstration walkthrough.

---

## 🎨 Design System & UI/UX

CampusPulse AI features **Design System V4.1 — Midnight Plum & Iris**:
- **Palette:** Deep Midnight Plum (`#272539`), Iris Indigo (`#5C559A`), Soft Lavender accents (`#EDE9FE`), and a clean, high-contrast canvas (`#F5F3F8`).
- **Typography & Accessibility:** Crisp hierarchy with full WCAG 2.2 AA contrast compliance across all text labels, form inputs, and sidebar elements.
- **Custom CSS:** Styled in [`assets/styles.css`](assets/styles.css) with responsive containers, customized Streamlit KPI metric tiles, and clean card layouts.
- **12-Hour Time Format:** Intuitive 12-hour AM/PM presentation (`format_time_12h`) across user interfaces while preserving canonical 24-hour SQL storage.

---

## 🛠️ Technology Stack

| Layer / Category | Technology | Description |
|---|---|---|
| **Programming Language** | **Python 3.10+** | Core backend logic, business rules, and algorithms |
| **Web Framework** | **Streamlit (>= 1.38.0)** | Reactive multipage web presentation framework |
| **Relational Database** | **SQLite3** | Local persistent storage with 11 relational tables |
| **Data Processing** | **Pandas (>= 2.2.0)** | Data manipulation, aggregation, and tabular transformations |
| **Numerical Computing** | **NumPy (>= 1.26.0)** | Mathematical calculations and array operations |
| **Data Visualization** | **Plotly (>= 5.22.0)** | Interactive, publication-quality academic analytics charts |
| **Image Processing** | **Pillow (PIL)** | Avatar image resizing, thumbnailing, and aspect-ratio cropping |
| **Automated Testing** | **Pytest (>= 8.0.0)** | Comprehensive unit and integration test suite (141 tests) |
| **Frontend Styling** | **CSS3 / HTML5** | Custom theme variables, responsive card components, and layout styling |

---

## 🏗️ System Architecture

CampusPulse AI follows a clean **4-Tier Architecture** that enforces strict separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                       │
│  Streamlit Multipage UI (app.py + 11 pages in pages/)       │
│  Custom CSS Design System V4.1 (assets/styles.css)          │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                      Service Layer                          │
│  academic_service  •  analytics_service  •  study_service   │
│  assignment_service •  calendar_service   •  subject_service │
│  profile_service   •  video_service      •  avatar utilities│
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                    Intelligence Layer                       │
│  recommendation_service (Explainable Rule Engine)           │
│  timetable_service (Weighted 7-Day Algorithmic Scheduler)   │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                   Database & Storage Layer                  │
│  SQLite3 Engine (database/db.py & database/schema.py)       │
│  11 Relational Tables with Foreign Keys & Cascading Deletes │
└─────────────────────────────────────────────────────────────┘
```

### Relational Database Schema (11 Tables)
1. `student_profile` — Single-row identity, target GPA, study goals, avatar configuration.
2. `subjects` — Academic courses, difficulty ratings, credits, color tags.
3. `topics` — Granular subject syllabus topics and completion flags.
4. `study_sessions` — Timestamped study logs, duration, energy rating, session notes.
5. `attendance_records` — Daily/weekly class attendance counters.
6. `marks` — Exam titles, component types, maximum marks, scored marks.
7. `assignments` — Coursework tasks, priority, due dates, submission status.
8. `calendar_events` — College academic events, categories, start/end dates and times.
9. `recommendations` — Rule-engine generated academic suggestions and status.
10. `timetable_entries` — Active 7-day scheduled study blocks.
11. `video_resources` — Bookmarked educational videos, channel titles, URLs, notes.

---

## 📁 Repository Structure

```text
CampusPulseAI/
│
├── app.py                         # Application entrypoint & Student Dashboard
├── requirements.txt               # Pinned project dependencies
├── README.md                      # Comprehensive project documentation
├── .gitignore                     # Git exclusion rules (venv, db, local caches)
│
├── assets/
│   └── styles.css                 # Design System V4.1 CSS styling & theme rules
│
├── data/
│   └── avatars/                   # Uploaded student profile avatars (git-ignored)
│       └── .gitkeep
│
├── database/
│   ├── db.py                      # SQLite connection management & transaction helpers
│   ├── schema.py                  # DDL definitions for 11 relational tables
│   └── queries.py                 # Parameterized SQL query repository
│
├── docs/
│   └── PROJECT_DEMO_GUIDE.md      # Comprehensive demonstration & presentation guide
│
├── pages/
│   ├── 1_Profile.py               # Student Profile & Avatar Studio
│   ├── 2_Subjects_Topics.py       # Course & Syllabus Topic Management
│   ├── 3_Daily_Study_Tracker.py   # Daily Study Session Logging & History
│   ├── 4_Academic_Performance.py  # Marks & 75% Attendance Shortage Calculator
│   ├── 5_Assignments_Reminders.py # Coursework Tracker & Deadline Reminders
│   ├── 6_College_Calendar.py      # College Academic Events & Exam Scheduler
│   ├── 7_AI_Recommendations.py    # Explainable Rule-Based Recommendation Engine
│   ├── 8_Smart_Timetable.py       # Algorithmic 7-Day Timetable Generator
│   ├── 9_Video_Lectures.py        # Video Lecture Query Builder & Resource Library
│   ├── 10_Progress_Analytics.py   # Plotly Visualizations & 6 CSV Data Exports
│   └── 11_About_Project.py        # System Architecture & Live Demo Guide
│
├── services/
│   ├── __init__.py
│   ├── academic_service.py        # Attendance & marks business logic
│   ├── analytics_service.py       # Data aggregation & analytics computations
│   ├── assignment_service.py      # Assignment CRUD & urgency prioritization
│   ├── calendar_service.py        # Calendar event processing & time formatting
│   ├── profile_service.py         # Student profile & avatar preference logic
│   ├── recommendation_service.py  # Rule-based academic recommendation engine
│   ├── study_service.py           # Study session validation & streak calculator
│   ├── subject_service.py         # Subject & syllabus topic operations
│   ├── timetable_service.py       # Conflict-free study timetable algorithm
│   └── video_service.py           # Educational query & bookmark management
│
├── utils/
│   ├── __init__.py
│   ├── avatars.py                 # SVG avatar presets, initials generator & Pillow resizing
│   ├── config.py                  # Global application constants & paths
│   ├── formatters.py              # 12-hour AM/PM time formatters & date helpers
│   ├── ui.py                      # Shared UI components, cards, navigation & alerts
│   └── validators.py              # Form input validation utilities
│
└── tests/
    ├── test_database.py           # Schema, connection, and query tests
    ├── test_profile_and_subjects.py # Profile and subject management tests
    ├── test_study_tracker.py      # Study session logging and streak tests
    ├── test_academic_performance.py # Attendance calculation and marks tests
    ├── test_assignments_calendar.py # Assignment urgency and calendar tests
    ├── test_recommendations.py    # Rule-based AI engine verification tests
    ├── test_timetable.py          # 7-day scheduler and conflict avoidance tests
    ├── test_video_resources.py    # Resource bookmarking and query builder tests
    ├── test_analytics.py          # Data aggregation and export tests
    ├── test_avatar_system.py      # SVG, vector initials, and image upload tests
    ├── test_formatters.py         # 12-hour time and date formatting tests
    ├── test_final_integration.py  # End-to-end integration workflows
    └── test_subject_card_rendering.py # HTML card rendering & escaping tests
```

---

## ⚡ Quickstart & Local Installation

Follow these steps to run CampusPulse AI on your local machine:

### Prerequisites
- **Python 3.10+** installed on your system ([Download Python](https://www.python.org/downloads/))
- **Git** installed ([Download Git](https://git-scm.com/))

### 1. Clone the Repository
```bash
git clone https://github.com/nisthasharma4/CampusPulseAI.git
cd CampusPulseAI
```

### 2. Create a Virtual Environment
- **Windows (Command Prompt / PowerShell):**
  ```powershell
  python -m venv .venv
  .venv\Scripts\activate
  ```
- **macOS / Linux:**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Run the Application
```bash
streamlit run app.py
```

The application will automatically initialize the local SQLite database (`campuspulse.db`) and open in your default browser at:
```text
http://localhost:8501
```

---

## ☁️ Deployment on Streamlit Community Cloud

CampusPulse AI is configured for seamless zero-configuration cloud deployment on **Streamlit Community Cloud**:

1. **Repository:** Ensure your fork or repository is pushed to GitHub.
2. **App Entrypoint:** Set `Main file path` to `app.py`.
3. **Environment:** Streamlit Cloud automatically detects `requirements.txt` and provisions the Python 3.10+ environment with all necessary dependencies (`streamlit`, `pandas`, `numpy`, `plotly`, `pillow`, `pytest`).
4. **Data Persistence:** The local SQLite database is created automatically upon first run.

Access the live production instance anytime at:  
👉 **[https://campus-pulse-ai-nistha.streamlit.app/](https://campus-pulse-ai-nistha.streamlit.app/)**

---

## 🧪 Testing & Quality Assurance

CampusPulse AI includes an extensive automated test suite built with **pytest**, covering database integrity, business logic, algorithmic scheduling, attendance formulas, UI formatting, and end-to-end integration:

```bash
python -m pytest -p no:cacheprovider -v
```

### Verified Test Results
```text
============================= test session starts =============================
platform win32 -- Python 3.12.x, pytest-8.3.x, pluggy-1.5.x
rootdir: C:\Users\abhis\OneDrive\Desktop\CampusPulseAI
collected 141 items

tests/test_database.py .........................                         [ 17%]
tests/test_profile_and_subjects.py ............                          [ 26%]
tests/test_study_tracker.py .........                                    [ 32%]
tests/test_academic_performance.py ............                          [ 41%]
tests/test_assignments_calendar.py ............                          [ 49%]
tests/test_recommendations.py .........                                  [ 56%]
tests/test_timetable.py ....................                             [ 70%]
tests/test_video_resources.py .........                                  [ 76%]
tests/test_analytics.py ..............                                   [ 86%]
tests/test_avatar_system.py ........                                     [ 92%]
tests/test_formatters.py ......                                          [ 96%]
tests/test_final_integration.py ...                                      [ 98%]
tests/test_subject_card_rendering.py ..                                  [100%]

============================= 141 passed in ~24s ==============================
```
- **Total Test Cases:** `141 passed`
- **Test Coverage:** All 10 services, database CRUD, attendance shortage formula, priority normalization, 12-hour AM/PM time conversions, SVG avatar rendering, and HTML rendering safety.

---

## 🧠 Explainable Rule-Based AI Engine

Unlike opaque deep-learning models or unpredictable large language model prompts, CampusPulse AI employs a **deterministic, rule-based expert recommendation engine**. This ensures:

1. **100% Explainable Guidance:** Every suggestion cites exact mathematical grounds (e.g., *Attendance in Operating Systems is 71.4%, requiring 3 consecutive attended lectures to clear 75%*).
2. **Zero External API Costs & Latency:** Operates entirely locally with instantaneous execution.
3. **Privacy by Design:** Academic records and personal schedules never leave your local environment.
4. **Guaranteed Actionability:** Prioritizes recommendations into 4 clear urgency tiers (*Critical*, *High*, *Medium*, *Info*) to prevent student cognitive overload.

---

## 🔮 Future Enhancements & Roadmap

- [ ] **Cross-Device Cloud Synchronization:** Encrypted multi-device sync with cloud database options (PostgreSQL / Supabase).
- [ ] **Native OS Desktop Notifications:** System-level push alerts for imminent assignment deadlines and study session reminders.
- [ ] **Two-Way Google Calendar Integration:** Bi-directional sync for academic events and generated timetable slots.
- [ ] **PDF Academic Performance Reports:** Single-click export of semester progress reports and attendance certificates.
- [ ] **Mobile Responsive Layout Optimization:** Progressive Web App (PWA) wrapper for smartphone screens.

---

## 🤝 Contributing & License

### Contributing
Contributions, feedback, and feature requests are welcome!
1. Fork the repository (`https://github.com/nisthasharma4/CampusPulseAI`).
2. Create your feature branch (`git checkout -b feature/AmazingFeature`).
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4. Ensure all tests pass (`python -m pytest -p no:cacheprovider -v`).
5. Push to the branch (`git push origin feature/AmazingFeature`).
6. Open a Pull Request.

### License
This project was developed as a B.Tech Academic Mini-Project. Currently, no formal open-source license is specified. For permissions, educational usage, or collaboration inquiries, please contact the repository maintainer.

---

## 👤 Author & Acknowledgments

- **Nistha Sharma** — [GitHub Profile (@nisthasharma4)](https://github.com/nisthasharma4)
- **Project Repository:** [CampusPulseAI on GitHub](https://github.com/nisthasharma4/CampusPulseAI)
- **Live Deployment:** [CampusPulse AI on Streamlit Cloud](https://campus-pulse-ai-nistha.streamlit.app/)

---

<div align="center">
  <sub>CampusPulse AI — Plan Smarter. Study Better. Track Your Growth.</sub>
</div>
