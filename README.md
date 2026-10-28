# Smart School System

A web-based school management system built with **Django**, with an **AI early-warning model** that flags students at risk of failing, and **face recognition** for student login and class attendance.

> Graduation project, rebuilt and extended by Faisal Ahmed.

## Features

| Role | What they can do |
|------|------------------|
| **Admin** | Manage students, teachers, parents, courses and enrolments; see the "Students at risk" overview |
| **Teacher** | Weekly schedule, course materials, assignments and grading, quizzes, announcements, face-based attendance sessions, final grades |
| **Student** | Dashboard, timetable, courses, homework upload, quizzes, grades with attendance %, face login, AI risk report |
| **Parent** | Read-only view of their child's progress, attendance and risk level |

## AI components

### 1. Student risk model (XGBoost)
- Features: normalised term work, cumulative GPA, passed credit hours, level.
- Label: the student failed / was absent in a course.
- Evaluated with a **split by student** (no student appears in both train and test), so the numbers are not inflated:

| Metric | Value |
|--------|-------|
| Accuracy | 0.876 |
| Recall (at-risk class) | 0.825 |
| ROC-AUC | 0.951 |

- Re-run it yourself: `python evaluate_risk_model.py` (writes `model_evaluation.txt`).
- Risk levels: `> 60 %` critical, `> 30 %` caution.
- A small manual calibration rule lowers the score for students with strong term work.
- The model was trained on anonymised records that are **not** published in this repository.

### 2. Face recognition (OpenCV LBPH)
- Haar-cascade face detection, then LBPH matching (distance threshold configurable: `FACE_THRESHOLD` in `settings.py`, default 75, lower = stricter).
- Enrolment stores up to 30 face crops per student; login and attendance compare against that student only (1:1).
- Attendance always uses the **logged-in** student, never an id sent by the browser.
- Limitation: LBPH is a classic method; a printed photo can fool it. For production use a liveness check.

## Security
- Role-based access control middleware (default deny, owners only see their own data).
- Hashed passwords (old plain-text passwords upgrade automatically at first login).
- CSRF protection on all forms and APIs; login lock after 5 wrong passwords (5 minutes).

## Tech stack
Python, Django 5.2, SQLite, XGBoost, scikit-learn, OpenCV (contrib), HTML/CSS/JS.

## Run it
```bash
python -m venv venv
venv\Scripts\activate            # Windows
pip install -r requirements.txt
cd web
python manage.py migrate
python manage.py seed_demo --reset   # demo data, password: demo1234
python manage.py runserver
python manage.py test                # automated tests
```

Demo logins (password `demo1234`): students 1001-1012, teachers 101-110, parents 2001-2008, see `seed_demo.py`.

## Screenshots

| Home | Admin dashboard |
|------|-----------------|
| ![Home](docs/screenshots/home.jpg) | ![Admin dashboard](docs/screenshots/admin-dashboard.jpg) |

**AI risk indicator** (same course, two students: a strong one and one with poor attendance and scores)

| Low risk | High risk |
|----------|-----------|
| ![Low risk](docs/screenshots/risk-low.jpg) | ![High risk](docs/screenshots/risk-high.jpg) |

| Teacher dashboard | Parent dashboard |
|-------------------|------------------|
| ![Teacher](docs/screenshots/teacher-dashboard.jpg) | ![Parent](docs/screenshots/parent-dashboard.jpg) |

| Student courses | Weekly timetable |
|-----------------|------------------|
| ![Courses](docs/screenshots/student-courses.jpg) | ![Timetable](docs/screenshots/weekly-timetable.jpg) |

| Academic transcript | Course catalog (admin) |
|---------------------|------------------------|
| ![Transcript](docs/screenshots/academic-transcript.jpg) | ![Catalog](docs/screenshots/course-catalog.jpg) |

All data shown is fictional demo data created by `python manage.py seed_demo --reset`.

## Known limitations
- Course announcements module is being rewritten.
- Much of the data access still uses raw SQL; migrating to the Django ORM is planned.
- The face recognizer has no liveness detection.

## Credits
Original team project; extended, secured and documented by Faisal Ahmed.
