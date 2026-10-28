"""Fill the database with fictional demo data for screenshots and demos.

Usage:
    python manage.py seed_demo --reset

Wipes the school tables (NOT Django users or sessions) and creates fictional
students, parents, teachers, courses, attendance, grades, quizzes and
announcements. Demo password for every account: demo1234
"""

import random
from datetime import timedelta

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from School.models import (
    AnnouncementReadStatus,
    Announcements,
    Assignments,
    AttendanceGate,
    AttendanceList,
    CourseAnnouncementReadStatus,
    CourseContents,
    Courses,
    FinalGrade,
    HomeWorkGrades,
    HomeworkDelivered,
    MidtermGrades,
    Options,
    ParentInformation,
    Questions,
    QuizGrades,
    QuizTakeStatus,
    Quizzes,
    StudentAnswers,
    StudentCourses,
    StudentInformation,
    StudentTeacherCommunications,
    SubmittedAssignmentFlag,
    TeacherCourses,
    TeacherInformation,
    TeacherSchedule,
)

DEMO_PASSWORD = "demo1234"
SESSIONS = 8  # weekly attendance sessions per course
AVATAR = "default-avatar.png"  # file inside Project/static/Images

# id, name, level, image file inside Project/static/Images
COURSES = [
    (1, "Math 1", "1", "Math.jpg"),
    (2, "Physics", "1", "Physics.jpg"),
    (3, "Introduction to Computer Science", "1", "course_intro_cs.jpg"),
    (4, "Discrete Mathematics", "1", "course_discrete_math.jpg"),
    (5, "Object-Oriented Programming", "2", "course_oop.jpg"),
    (6, "Data Structures and Algorithms", "2", "course_data_structures.jpg"),
    (7, "Computer Architecture", "2", "course_computer_architecture.jpg"),
    (8, "Operating Systems", "3", "course_operating_systems.jpg"),
    (9, "Database Management Systems", "3", "course_databases.jpg"),
    (10, "Computer Networks", "3", "course_computer_networks.jpg"),
    (11, "Software Engineering", "4", "course_software_engineering.jpg"),
    (12, "Information Security", "4", "course_information_security.jpg"),
    (13, "Artificial Intelligence & ML", "4", "course_ai_ml.jpg"),
    (14, "Graduation Project", "4", "course_graduation_project.jpg"),
]

# id, name, age, gender, Course_Handle, course ids
# IMPORTANT: the teacher dashboard lists every course whose NAME contains the
# Course_Handle text, so each handle must match exactly that teacher's courses:
#   "Math" -> Math 1 + Discrete Mathematics      "Data" -> Data Structures + Database
#   "Computer" -> Intro to Computer Science + Computer Architecture + Computer Networks
TEACHERS = [
    (101, "Laila Hassan", 44, "Female", "Math", [1, 4]),
    (102, "Omar Nabil", 51, "Male", "Physics", [2]),
    (103, "Khaled Fawzy", 47, "Male", "Computer", [3, 7, 10]),
    (104, "Sara Mansour", 38, "Female", "Programming", [5]),
    (105, "Mona Adel", 41, "Female", "Data", [6, 9]),
    (106, "Tarek Samir", 53, "Male", "Operating", [8]),
    (107, "Hana Youssef", 39, "Female", "Software", [11]),
    (108, "Amr Salah", 46, "Male", "Security", [12]),
    (109, "Rania Kamel", 42, "Female", "Artificial", [13]),
    (110, "Hossam Ezzat", 55, "Male", "Graduation", [14]),
]

# id, name, age, gender, level, profile, parent name (None = no parent account)
STUDENTS = [
    (1001, "Youssef Adel", 19, "Male", 1, "strong", "Adel Mahmoud"),
    (1002, "Mariam Samir", 18, "Female", 1, "average", "Samir Hassan"),
    (1003, "Omar Hesham", 19, "Male", 1, "at_risk", "Hesham Fouad"),
    (1004, "Nour Khaled", 18, "Female", 1, "strong", None),
    (1005, "Ahmed Tarek", 20, "Male", 2, "average", "Tarek Ibrahim"),
    (1006, "Salma Mostafa", 19, "Female", 2, "strong", "Mostafa Kamal"),
    (1007, "Karim Walid", 20, "Male", 2, "at_risk", "Walid Fathy"),
    (1008, "Hana Ibrahim", 19, "Female", 2, "average", None),
    (1009, "Ziad Ashraf", 21, "Male", 3, "average", None),
    (1010, "Laila Mahmoud", 21, "Female", 3, "strong", "Mahmoud Aziz"),
    (1011, "Adam Fathy", 22, "Male", 4, "at_risk", None),
    (1012, "Dina Sherif", 22, "Female", 4, "strong", "Sherif Nabil"),
]

# attendance rate, quiz rate range, homework rate range, midterm range (of 20)
PROFILES = {
    "strong": dict(
        cgpa=(3.5, 3.9), att=0.97, quiz=(0.85, 0.98), hw=(0.85, 1.0), mid=(16, 19.5)
    ),
    "average": dict(
        cgpa=(2.6, 3.2), att=0.85, quiz=(0.60, 0.80), hw=(0.60, 0.85), mid=(10.5, 14.5)
    ),
    "at_risk": dict(
        cgpa=(1.4, 2.0), att=0.55, quiz=(0.25, 0.45), hw=(0.20, 0.45), mid=(3, 8)
    ),
}

# course id -> two questions: (text, correct answer, three wrong answers)
QUIZ = {1: [('What is the derivative of x^2?', '2x', ['x', 'x^2', '2']),
     ('What is the integral of 1 dx from 0 to 1?', '1', ['0', '2', '1/2'])],
 2: [('Which unit measures force?', 'Newton', ['Joule', 'Watt', 'Pascal']),
     ('Approximate gravity on Earth?',
      '9.8 m/s2',
      ['1.6 m/s2', '3.7 m/s2', '24.8 m/s2'])],
 3: [('Which part of a computer executes instructions?',
      'CPU',
      ['Monitor', 'Keyboard', 'Power supply']),
     ('How many bits are in one byte?', '8', ['4', '16', '32'])],
 4: [('How many subsets does a set of 3 elements have?', '8', ['3', '6', '9']),
     ('Which connective is true only when both statements are true?',
      'AND',
      ['OR', 'XOR', 'NOT'])],
 5: [('Which OOP concept hides internal details of an object?',
      'Encapsulation',
      ['Recursion', 'Compilation', 'Iteration']),
     ('A class that inherits from another class is called a:',
      'Subclass',
      ['Interface', 'Module', 'Constant'])],
 6: [('Which data structure is LIFO?', 'Stack', ['Queue', 'Array', 'Tree']),
     ('Time complexity of binary search?', 'O(log n)', ['O(n)', 'O(n^2)', 'O(1)'])],
 7: [('Which memory is the fastest?', 'Registers', ['Hard disk', 'RAM', 'SSD']),
     ('The ALU performs:',
      'Arithmetic and logic operations',
      ['Data storage', 'Screen output', 'Network routing'])],
 8: [('Which OS component decides which process runs next?',
      'Scheduler',
      ['Compiler', 'Linker', 'Editor']),
     ('A deadlock happens when processes:',
      'Wait for each other forever',
      ['Run too fast', 'Use too little memory', 'Finish early'])],
 9: [('Which SQL command reads data from a table?',
      'SELECT',
      ['INSERT', 'DELETE', 'DROP']),
     ('A primary key must be:', 'Unique', ['Empty', 'Repeated', 'Text only'])],
 10: [('Which protocol is used to load web pages?', 'HTTP', ['SMTP', 'FTP', 'SSH']),
      ('An IPv4 address has how many bits?', '32', ['16', '64', '128'])],
 11: [('Which model delivers software in short repeated cycles?',
       'Agile',
       ['Waterfall only', 'Big bang', 'Spiral of silence']),
      ('What is the purpose of unit testing?',
       'Test small parts of the code',
       ['Design the database', 'Write documentation', 'Deploy to users'])],
 12: [('What does a firewall do?',
       'Filters network traffic',
       ['Speeds up the CPU', 'Compresses files', 'Stores passwords in plain text']),
      ('Which is a strong password practice?',
       'Long and unique password',
       ['Reuse one password', 'Use your name', 'Share it with friends'])],
 13: [('Which technique helps reduce overfitting?',
       'Regularization',
       ['Removing the test set',
        'Adding noise to labels',
        'Training without validation']),
      ('Which algorithm is used for classification?',
       'Logistic regression',
       ['K-means', 'PCA', 'Apriori'])],
 14: [('A project proposal should first state the:',
       'Problem and objectives',
       ['Final grades', 'Font size', 'Team photos']),
      ('Which document records what the system must do?',
       'Requirements specification',
       ['Invoice', 'Poster', 'Menu'])]}

ANNOUNCEMENTS = [
    (
        "Midterm Exam Schedule Published",
        "The midterm timetable for all levels is now available. Please review "
        "it and contact your instructor with any questions.",
        2,
    ),
    (
        "Annual Science Fair",
        "Students are invited to submit project proposals by the end of the "
        "month. Teams of up to four are welcome.",
        6,
    ),
    (
        "New Academic Risk Dashboard",
        "Course pages now show an AI-assisted risk indicator with personal "
        "advice to help every student stay on track.",
        11,
    ),
    (
        "Parent-Teacher Meeting",
        "Parents are invited to meet instructors next Thursday to discuss "
        "student progress.",
        17,
    ),
]

WIPE = [
    AnnouncementReadStatus,
    Announcements,
    Assignments,
    AttendanceGate,
    AttendanceList,
    CourseAnnouncementReadStatus,
    CourseContents,
    FinalGrade,
    HomeWorkGrades,
    HomeworkDelivered,
    MidtermGrades,
    Options,
    Questions,
    Quizzes,
    QuizGrades,
    QuizTakeStatus,
    StudentAnswers,
    StudentTeacherCommunications,
    SubmittedAssignmentFlag,
    TeacherSchedule,
    TeacherCourses,
    StudentCourses,
    ParentInformation,
    StudentInformation,
    TeacherInformation,
    Courses,
]


def courses_for(level):
    """Courses of the student's level, filled up from the level below."""
    same = [c for c in COURSES if int(c[2]) == level]
    lower = [c for c in COURSES if int(c[2]) == level - 1]
    return (same + lower)[:4]


class Command(BaseCommand):
    help = "Fill the school tables with fictional demo data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Required: wipes the school tables first.",
        )

    def handle(self, *args, **options):
        if not options["reset"]:
            raise CommandError(
                "This command wipes the school tables. " "Run it again with --reset."
            )
        with transaction.atomic():  # any error rolls everything back
            self.seed()
        self.stdout.write(self.style.SUCCESS("Demo data created."))
        self.stdout.write(
            f"Password for every demo account: {DEMO_PASSWORD}\n"
            "Students 1001-1012 | Teachers 101-110 | "
            "Parents: see the list printed above"
        )

    def seed(self):
        rng = random.Random(42)  # same data on every run
        now = timezone.now()
        password = make_password(DEMO_PASSWORD)

        for model in WIPE:
            model.objects.all().delete()

        # ---- courses, teachers ----
        course_obj = {}
        for cid, name, level, image in COURSES:
            course_obj[cid] = Courses.objects.create(
                course_id=cid, course_name=name, course_level=level, image_url=image
            )
            AttendanceGate.objects.create(
                course=course_obj[cid], is_open=False, opened_at=now
            )

        teacher_obj, course_teacher = {}, {}
        for i, (tid, name, age, gender, handle, cids) in enumerate(TEACHERS):
            teacher_obj[tid] = TeacherInformation.objects.create(
                Teacher_Id=tid,
                Teacher_Name=name,
                Teacher_Age=str(age),
                Teacher_Gender=gender,
                Teacher_NationalID=f"8{tid:013d}",
                Course_Handle=handle,
                Teacher_Image=AVATAR,
                Passwordd=password,
            )
            days = [
                ("Sunday", "Tuesday"),
                ("Monday", "Wednesday"),
                ("Tuesday", "Thursday"),
            ][i % 3]
            slots = [("09:00", "10:30"), ("11:00", "12:30"),
                     ("13:00", "14:30"), ("15:00", "16:30")]
            for ci, cid in enumerate(cids):
                start, end = slots[(i + ci) % 4]
                for day in days:
                    TeacherSchedule.objects.create(
                        teacher_id=tid,
                        day=day,
                        start_time=start,
                        end_time=end,
                        course_name=COURSES[cid - 1][1],
                        room=f"A-{101 + i}",
                    )
            for cid in cids:
                TeacherCourses.objects.create(teacher_id=tid, course_id=cid)
                course_teacher[cid] = tid

        # ---- quizzes and assignments (one quiz, three assignments each) ----
        quiz_obj, question_obj = {}, {}
        for cid, name, level, image in COURSES:
            quiz = Quizzes.objects.create(
                QuizName=f"{name} - Quiz 1",
                Teacher=teacher_obj[course_teacher[cid]],
                course=course_obj[cid],
                QuizNumber=1,
            )
            quiz_obj[cid], question_obj[cid] = quiz, []
            for text, correct, wrong in QUIZ[cid]:
                question = Questions.objects.create(
                    Quiz=quiz, QuestionText=text, QuestionType="mcq", Marks=5
                )
                question_obj[cid].append(question)
                choices = [(correct, True)] + [(w, False) for w in wrong]
                rng.shuffle(choices)
                for option_text, is_correct in choices:
                    Options.objects.create(
                        Question=question, OptionText=option_text, IsCorrect=is_correct
                    )
            for number, days_ago in ((1, 21), (2, 10), (3, -7)):
                Assignments.objects.create(
                    DescriptionContent=(
                        f"{name}: assignment {number}. "
                        "Solve the exercises and submit."
                    ),
                    DeadlineDate=now - timedelta(days=days_ago),
                    AssignementNumber=number,
                    course=course_obj[cid],
                    Teacher_Id=course_teacher[cid],
                    TotalMark=10,
                    Flag=1,
                )

        # ---- students, parents, and everything they did ----
        parent_id = 2001
        credentials = []
        for sid, name, age, gender, level, profile, parent in STUDENTS:
            p = PROFILES[profile]
            student = StudentInformation.objects.create(
                Student_ID=sid,
                Student_Name=name,
                Student_Age=str(age),
                Student_Level=str(level),
                Student_Gender=gender,
                Student_Image=AVATAR,
                Student_Nationality="Egyptian",
                Student_NationalID=f"9{sid:013d}",
                Passwordd=password,
                student_cgpa=round(rng.uniform(*p["cgpa"]), 2),
                entry_year=2027 - level,
            )
            if parent:
                ParentInformation.objects.create(
                    Parent_Name=parent,
                    Parent_ID=parent_id,
                    Parent_NationalID=f"7{parent_id:013d}",
                    Parent_Image=AVATAR,
                    Student_ID=student,
                    Passwordd=password,
                )
                credentials.append((parent_id, parent, f"parent of {name}"))
                parent_id += 1

            for cid, cname, clevel, image in courses_for(level):
                tid = course_teacher[cid]
                StudentCourses.objects.create(
                    Student_ID=sid,
                    course_name=cname,
                    course_id=cid,
                    semester="Fall 2026",
                )
                for week in range(SESSIONS):
                    day = (now - timedelta(days=7 * (SESSIONS - week))).date()
                    status = "Present" if rng.random() < p["att"] else "Absent"
                    row = AttendanceList.objects.create(
                        Student_ID=str(sid),
                        Course_ID=cid,
                        Teacher_ID=tid,
                        Status=status,
                    )
                    # Date is auto_now_add, so set the real date afterwards
                    AttendanceList.objects.filter(pk=row.pk).update(Date=day)
                for question in question_obj[cid]:
                    marks = round(rng.uniform(*p["quiz"]) * 5 * 2) / 2
                    QuizGrades.objects.create(
                        StudentID=sid,
                        CourseID=cid,
                        QuizNumber=1,
                        QuestionID=question.QuestionID,
                        MarksObtained=marks,
                        TotalMarks=5.0,
                    )
                QuizTakeStatus.objects.create(
                    Student_ID=sid,
                    Quiz=quiz_obj[cid],
                    IsTaken=1,
                    TakenDate=now - timedelta(days=rng.randint(3, 20)),
                    course_id=cid,
                )
                for number in (1, 2):
                    HomeWorkGrades.objects.create(
                        Student_ID=sid,
                        course_id=cid,
                        AssignmentNumber=number,
                        MarksObtained=round(rng.uniform(*p["hw"]) * 10, 1),
                        TotalMarks=10.0,
                    )
                MidtermGrades.objects.create(
                    Student_ID=sid,
                    Course_ID=cid,
                    Teacher_ID=tid,
                    MarksObtained=round(rng.uniform(*p["mid"]), 1),
                    TotalMarks=20.0,
                )

        # ---- announcements ----
        for title, text, days_ago in ANNOUNCEMENTS:
            row = Announcements.objects.create(publisher_name=title, description=text)
            Announcements.objects.filter(pk=row.pk).update(
                date_posted=now - timedelta(days=days_ago)
            )

        self.stdout.write("Demo accounts (password: %s)" % DEMO_PASSWORD)
        self.stdout.write("Parents:")
        for pid, pname, note in credentials:
            self.stdout.write(f"  {pid}  {pname}  ({note})")
