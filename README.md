# 🎓 CampusPulse AI

### Intelligent Student Academic Planner & Productivity Platform

**CampusPulse AI** is an academic productivity platform designed to help college students manage their studies, organize academic activities, track performance and improve learning consistency through a centralized dashboard.

It combines study tracking, smart timetable generation, academic management and rule-based AI recommendations in one application.

## ✨ Features

- **📊 Interactive Dashboard** — Academic overview, study statistics, deadlines and progress summaries.
- **👤 Student Profile** — Personalized profile, study preferences and avatar customization.
- **📚 Subject & Topic Management** — Organize subjects, track syllabus completion and monitor learning progress.
- **⏱️ Daily Study Tracker** — Record study sessions, maintain study history and analyze productivity.
- **📈 Academic Performance** — Manage attendance, internal marks and identify subjects needing attention.
- **📝 Assignments & Reminders** — Manage assignments, deadlines and submission status.
- **📅 College Calendar** — Organize examinations, events, workshops and important academic dates.
- **🤖 AI Recommendations** — Rule-based personalized suggestions based on academic performance, attendance and study activity.
- **🗓️ Smart Timetable** — Generate and manage personalized study schedules using availability, priorities and deadlines.
- **🎥 Video Lecture Library** — Find educational lectures and organize saved learning resources.
- **📉 Progress Analytics** — Visualize study hours, subject progress, productivity and academic performance.

## 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| Python | Application logic |
| Streamlit | Web application framework |
| SQLite | Local database |
| Pandas | Data processing |
| Plotly | Interactive visualizations |
| HTML & CSS | Interface design |
| Pytest | Automated testing |
| Pillow | Profile image processing |

## 🏗️ Architecture

CampusPulse AI follows a modular architecture:

- **Presentation Layer:** Streamlit multipage interface.
- **Service Layer:** Python services for academic management, recommendations and scheduling.
- **Intelligence Layer:** Rule-based recommendation engine and priority-based timetable generator.
- **Database Layer:** SQLite database for persistent local storage.

## 📁 Project Structure

```text
CampusPulseAI/
│
├── app.py
├── assets/
│   └── styles.css
│
├── database/
│   ├── db.py
│   ├── queries.py
│   └── schema.py
│
├── pages/
│   ├── 1_Profile.py
│   ├── 2_Subjects_Topics.py
│   ├── 3_Daily_Study_Tracker.py
│   ├── 4_Academic_Performance.py
│   ├── 5_Assignments_Reminders.py
│   ├── 6_College_Calendar.py
│   ├── 7_AI_Recommendations.py
│   ├── 8_Smart_Timetable.py
│   ├── 9_Video_Lectures.py
│   ├── 10_Progress_Analytics.py
│   └── 11_About_Project.py
│
├── services/
├── utils/
├── data/
├── docs/
├── tests/
│
├── requirements.txt
├── README.md
└── .gitignore
```

## ⚙️ Installation & Setup

**Prerequisites:** Python 3.10+ and Git.

**1. Clone the repository**

```bash
git clone https://github.com/nistasharma4/CampusPulseAI.git
```

**2. Navigate to the project**

```bash
cd CampusPulseAI
```

**3. Create a virtual environment**

```bash
python -m venv .venv
```

**4. Activate the environment (Windows)**

```bash
.venv\Scripts\activate
```

**5. Install dependencies**

```bash
pip install -r requirements.txt
```

**6. Run the application**

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

## 🧪 Testing

Run the automated test suite:

```bash
python -m pytest -p no:cacheprovider -v
```

The project includes tests for database operations, academic management, study tracking, timetable generation, recommendations, analytics, avatar handling and other core functionality.

## 🧠 AI Approach

CampusPulse AI uses a **rule-based intelligent recommendation system**, not a trained Machine Learning model.

It evaluates available academic records, study consistency, attendance, assignments and syllabus progress to generate personalized recommendations.

Its timetable generator uses predefined priority and scheduling rules to organize study sessions according to student availability.

## 🔮 Future Scope

- Cloud synchronization and multi-device access.
- Smart notifications and deadline alerts.
- Google Calendar integration.
- Advanced academic performance prediction.
- Mobile application support.
- Enhanced personalized learning recommendations.

## 🎯 Project Objective

To provide students with a unified academic workspace that simplifies study planning, improves time management and makes academic progress easier to monitor.

---

### CampusPulse AI
**Plan Smarter. Study Better. Track Your Growth.**
