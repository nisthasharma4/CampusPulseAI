# CampusPulse AI — Project Demonstration & Evaluation Guide

This guide provides a structured walkthrough for college viva, evaluation, and project demonstration.

---

## 1. Quick Launch Instructions

Open PowerShell in the project directory:

```powershell
# 1. Activate the virtual environment
.venv\Scripts\activate

# 2. Run the automated test suite
python -m pytest -p no:cacheprovider -v

# 3. Launch CampusPulse AI
streamlit run app.py
```

The application opens automatically in your default browser at `http://localhost:8501`.

---

## 2. Recommended Demonstration Flow (Step-by-Step)

### Step 1: Main Dashboard Overview (`app.py`)
- Show the **Welcome Banner**, **8 Academic Summary Cards**, and **Quick Action buttons**.
- Point out the clean empty states if starting with a fresh database or existing live statistics.
- Highlight that planned timetable hours are strictly kept separate from actual logged study time.

### Step 2: Student Profile Setup (`pages/1_Profile.py`)
- Enter student details: Name, Branch, Semester, College.
- Set **Weekly Study Target** (e.g. 14 hours), **Daily Study Target**, and **Attendance Threshold** (e.g. 75%).
- Configure study availability (preferred days, start/end times, session/break duration).
- Click **Save Profile** and verify success.

### Step 3: Subject & Syllabus Topic Management (`pages/2_Subjects_Topics.py`)
- Add 2 subjects (e.g., *Data Structures and Algorithms* and *Database Management Systems*).
- For *Data Structures*, add syllabus topics (e.g., *Arrays*, *Linked Lists*, *Binary Trees*, *Graphs*).
- Set estimated study hours and target completion dates.
- Mark *Arrays* as **Completed** and observe the live syllabus completion percentage update.

### Step 4: Daily Study Tracking & Study Journal (`pages/3_Daily_Study_Tracker.py`)
- Log a 60-minute study session for *Data Structures* -> *Linked Lists*.
- Enter study goal, completed work, and a 4-star productivity rating.
- Save a **Daily Check-in** with tomorrow's study plan.
- Check the learning journey timeline to see the study history recorded in reverse-chronological order.

### Step 5: Academic Performance — Attendance & Marks (`pages/4_Academic_Performance.py`)
- Record attendance for *Data Structures* (e.g., 20 held, 13 attended -> 65% attendance).
- Note the automatic calculation showing how many consecutive classes must be attended to reach 75%.
- Record assessment marks (e.g., Midsem: 16/30 -> 53.3%).
- Observe the **Weak Subject Identification** alert flagging the subject due to low marks and attendance.

### Step 6: Assignments & Reminders (`pages/5_Assignments_Reminders.py`)
- Add an assignment: *Binary Tree Implementation Lab*, priority **High**, due in 2 days.
- Observe the live countdown badge and reminder status.

### Step 7: College Academic Calendar (`pages/6_College_Calendar.py`)
- Add an examination event: *Mid-Semester Examinations*, starting next Monday.
- Notice how it is categorized as an examination event without duplicate assignment entries.

### Step 8: Rule-Based AI Recommendations (`pages/7_AI_Recommendations.py`)
- Open the page to reveal prioritized, transparent recommendations:
  1. *Attendance Shortage Alert* for Data Structures with exact required classes.
  2. *Upcoming Assignment Deadline* alert.
  3. *Weak Subject Focus* recommendation combining marks and attendance.
- Emphasize to the evaluators: **This is a transparent, explainable rule-based intelligence engine**, not a black-box ML model.

### Step 9: Smart Timetable Generator (`pages/8_Smart_Timetable.py`)
- Click **Generate Timetable Preview**.
- Inspect the generated 7-day schedule:
  - Higher weight and more study slots are allocated to *Data Structures* (weak subject + low attendance + upcoming assignment).
  - Break times are properly spaced between sessions.
  - Full-day holidays and timed calendar events are avoided.
- Click **Save Timetable** and view the weekly schedule.

### Step 10: Video Lecture Suggestions & Resource Library (`pages/9_Video_Lectures.py`)
- Select *Data Structures* and topic *Binary Trees*.
- Select preferences: Language = **Hindi**, Type = **Complete Course**, Level = **BTech Beginner**.
- Show the generated URL: `https://www.youtube.com/results?search_query=Data+Structures+Binary+Trees+Complete+Course+BTech+Beginner+Hindi`.
- Click **Open YouTube Search** (opens in a new browser tab).
- Paste a sample YouTube lecture URL into **Save Learning Resource** and verify it appears in **My Learning Resource Library**.

### Step 11: Progress Analytics & CSV Export (`pages/10_Progress_Analytics.py`)
- Demonstrate the **Date Range Filter** (Today, Last 7 Days, Last 30 Days, This Month, Custom).
- Showcase the interactive Plotly visualizations:
  - Daily Study Hours line chart (with missing days filled with 0 hours).
  - Subject study time distribution pie/donut chart.
  - Topic study hours bar chart.
  - Topic calendar completion duration vs actual study hours table.
  - Consecutive study-recording streaks.
- Go to **Custom Report & Export** and download the 6 UTF-8 CSV reports.

### Step 12: About Project Documentation (`pages/11_About_Project.py`)
- Display the problem statement, 4-tier system architecture, transparent rule-based algorithm description, and future roadmap.

---

## 3. Key Viva / Presentation Talking Points

1. **Why SQLite?**
   - Embedded, zero-configuration, cross-platform relational database with zero server management overhead.
   - Enforces referential integrity with foreign key constraints (`ON DELETE CASCADE` and `ON DELETE SET NULL`).
2. **Why Rule-Based AI instead of Machine Learning?**
   - Student academic planning requires **100% deterministic, explainable, and trustworthy outputs**.
   - A student needs to know *why* a subject is prioritized (e.g. *Attendance at 65% is below 75% target*), which ML classifiers cannot explain reliably.
   - Operates locally with zero GPU requirements, zero dataset training latency, and zero cloud API subscription costs.
3. **Data Integrity & Separation of Concerns:**
   - Planned timetable time is never counted as actual study time unless explicitly logged in `study_sessions`.
   - Historical sessions are preserved even if a syllabus topic is deleted.
   - Attendance calculations use weighted aggregate formulas, preventing misleading simple averages.
