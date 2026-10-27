import base64
import mimetypes
import os
from django.conf import settings
from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Max
from datetime import datetime, timezone
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.db import connection, transaction
import json
from .models import StudentInformation
from .models import TeacherInformation as TeacherModel
from .models import ParentInformation as ParentModel
from .models import ParentInformation
from .models import Courses
from .models import Announcements
from .models import Quizzes as QuizModel
from .models import Questions as QuestionModel
from .models import Options as OptionModel
from .models import QuizTakeStatus
from .models import StudentAnswers
from School.models import Courses
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponse, Http404
from django.http import JsonResponse
from .models import StudentInformation as StudentInfoModel
from .models import TeacherInformation as TeacherInfoModel
from .models import ParentInformation as ParentInfoModel
from .models import Courses as CourseDataModel
import cv2
import os
import numpy as np
import base64
from django.shortcuts import redirect
from django.contrib import messages
from django.core.files.base import ContentFile
from .analytics_utils import get_student_risk_report
from django.contrib.auth.hashers import make_password


def index(request):
    with connection.cursor() as cursor:
        # Added COALESCE to ensure a date always shows up
        cursor.execute("""
            SELECT id, publisher_name, description, 
                   strftime('%d-%m-%Y', COALESCE(date_posted, 'now')) 
            FROM Announcements 
            ORDER BY id DESC 
            LIMIT 3
        """)
        records = cursor.fetchall()

    announcements = []
    for r in records:
        announcements.append(
            {
                "id": r[0],
                "publisher": r[1],  # Matches {{ announcement.publisher }} in HTML
                "content": r[2],  # Matches {{ announcement.content }} in HTML
                "date": r[3],  # Matches {{ announcement.date }} in HTML
            }
        )

    return render(request, "pages/Main.html", {"announcements": announcements})


def index2(request, Student_Id):
    Student_data = []

    with connection.cursor() as cursor:
        # 1. FETCH STUDENT PROFILE
        # Removed 'Class' to stop the crash; check your actual column name (e.g., Student_Class?)
        cursor.execute(
            """
            SELECT Student_Name, Student_Image, Student_Level, Student_ID
            FROM StudentInformation
            WHERE Student_ID = %s 
        """,
            [Student_Id],
        )
        StudentRecord = cursor.fetchall()

        if not StudentRecord:
            return HttpResponse("Student profile not found.")

        for Record in StudentRecord:
            img_base64 = ""
            if Record[1] and isinstance(Record[1], bytes):
                img_base64 = base64.b64encode(Record[1]).decode("utf-8")

            Student_data.append(
                {
                    "StudentName": Record[0],
                    "StudentImage": img_base64,
                    "Student_Level": Record[2],
                    "StudentID": Record[3],
                    # 'Class': Record[?]  <-- Add this back only once you confirm the column name
                }
            )

        # 2. FETCH ENROLLED COURSES
        # Fixed: Using 'Courses' as confirmed previously
        cursor.execute(
            """
            SELECT Courses.course_id, Courses.course_name, Courses.course_level
            FROM Courses 
            INNER JOIN StudentCourses ON Courses.course_id = StudentCourses.course_id
            WHERE StudentCourses.Student_ID = %s 
        """,
            [Student_Id],
        )
        records = cursor.fetchall()

    context = {"Record": records, "StudentRecord": Student_data}

    return render(request, "pages/Attendance_History.html", context)


def index3(request, Teacher_Id, Course_Id, CourseName):
    context = {
        "Teacher_Id": Teacher_Id,
        "Course_Id": Course_Id,
        "CourseName": CourseName,
    }
    return render(request, "pages/temp.html", context)


def add_course_Page(request):
    # Get the next ID automatically
    max_id = Courses.objects.aggregate(Max("course_id"))["course_id__max"]
    next_id = (max_id or 0) + 1
    return render(request, "pages/add_course.html", {"LastRecord": next_id})


def AddannouncementsPage(request):
    return render(request, "pages/add_announcement.html")


def AddTeacherCoursPage(request):
    return render(request, "pages/AddTeacherCourse.html")


def SaveFinalGrade(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            print("Received data:", data)

            student_id = data.get("StudentID")
            studentGrades = data.get("Grades")
            assignment = data.get("Assignment")
            quiz = data.get("Quiz")
            midterm = data.get("MidTerm")
            finalExam = data.get("Final")
            participation = data.get("Participation")
            attendance = data.get("Attendance")
            CourseID = data.get("CourseID")
            Credit = ""
            StudentStatus = ""

            # Assign credit and status based on grades
            if studentGrades >= 90:
                Credit = "A"
                StudentStatus = "Passed"
            elif studentGrades >= 80:
                Credit = "B"
                StudentStatus = "Passed"
            elif studentGrades >= 70:
                Credit = "C"
                StudentStatus = "Passed"
            elif studentGrades >= 60:
                Credit = "D"
                StudentStatus = "Passed"
            else:
                Credit = "F"
                StudentStatus = "Failed"

            print("Student ID:", student_id, "Total mark:", studentGrades)

            # Use a single cursor for all database operations
            with connection.cursor() as cursor:
                # Check if the student grade already exists
                cursor.execute(
                    """
                    SELECT Student_ID
                    FROM FinalGrade
                    WHERE Student_ID = %s 
                """,
                    [student_id],
                )
                StudentGrade = cursor.fetchone()

                if StudentGrade:
                    # Update the existing record
                    cursor.execute(
                        """
                        UPDATE FinalGrade   
                        SET TotalQuizMark = %s,
                            TotalAssignment = %s,
                            MidTerm = %s,
                            Final = %s,
                            ClassParticipation = %s,
                            ClassAttendance = %s,
                            Total = %s,
                            course_id = %s,
                            Credit = %s,
                            StudentStatus = %s
                        WHERE Student_ID = %s
                    """,
                        [
                            quiz,
                            assignment,
                            midterm,
                            finalExam,
                            participation,
                            attendance,
                            studentGrades,
                            CourseID,
                            Credit,
                            StudentStatus,
                            student_id,
                        ],
                    )
                else:
                    # Insert a new record
                    cursor.execute(
                        """
                        INSERT INTO FinalGrade 
                        (TotalQuizMark, TotalAssignment, MidTerm, Final, ClassParticipation, ClassAttendance, Total, Student_ID, course_id, Credit, StudentStatus)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                        [
                            quiz,
                            assignment,
                            midterm,
                            finalExam,
                            participation,
                            attendance,
                            studentGrades,
                            student_id,
                            CourseID,
                            Credit,
                            StudentStatus,
                        ],
                    )

            # Return a success response
            return JsonResponse(
                {"message": "Grades confirmed successfully!"}, status=200
            )

        except Exception as e:
            print("Error:", e)
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request method"}, status=405)


def GenerateGrades(request, CourseID):
    with connection.cursor() as cursor:
        cursor.execute("""
                SELECT Student_Name, Student_Image, Student_ID, Class
                FROM StudentInformation
                ORDER BY Class, Student_ID ASC;
                    """)
        StudentRecord = cursor.fetchall()

    Student_data = []
    if StudentRecord:
        for Record in StudentRecord:
            Student_Name = Record[0]
            Student_Image = Record[1]
            Student_ID = Record[2]
            Class = Record[3]
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                            SELECT 
                                SUM(MarksObtained) AS TotalMarksObtained
                            FROM 
                                HomeWorkGrades
                            WHERE 
                                Student_ID = %s

                            """,
                    [Student_ID],
                )
                AssignmentGrade = cursor.fetchall()

                cursor.execute(
                    """
                            SELECT 
                                SUM(MarksObtained) AS TotalMarksObtained
                            FROM 
                                QuizGrades
                            WHERE 
                                StudentID = %s
                            """,
                    [Student_ID],
                )
                QuizGrade = cursor.fetchall()

                cursor.execute(
                    """
                        SELECT 
                            SUM(AttendanceList.Mark) AS TotalMark
                        FROM 
                            AttendanceList 
                        WHERE
                            AttendanceList.course_id = 1201 AND AttendanceList.Student_ID = %s
                            """,
                    [Student_ID],
                )
                AttendanceGrade = cursor.fetchall()

            Student_data.append(
                {
                    "StudentName": Student_Name,
                    "StudentImage": base64.b64encode(Student_Image).decode("utf-8"),
                    "StudentID": Student_ID,
                    "Class": Class,
                    "TotalAssignmentGrade": AssignmentGrade[0][0],
                    "TotalQuizGrade": QuizGrade[0][0],
                    "TotalAttendanceGrade": AttendanceGrade[0][0],
                    "CourseID": CourseID,
                }
            )

    context = {
        "StudentRecord": Student_data,
    }
    return render(request, "pages/GenerateGrades.html", context)


def AddAnnouncementsCoursePage(request, Teacher_Id, Course_Id):
    context = {"TeacherID": Teacher_Id, "CourseID": Course_Id}

    return render(request, "pages/AddCourseAnnouncement.html", context)


def AddStudentCourse(request):
    return render(request, "pages/AddStudentCourse.html")


def StudentSchedulePage(request, Student_ID):
    with connection.cursor() as cursor:
        # 1. Fetch Student Info
        cursor.execute(
            """
            SELECT Student_Name, Student_Image, Student_ID
            FROM StudentInformation
            WHERE Student_ID = %s 
        """,
            [Student_ID],
        )
        student_row = cursor.fetchone()

        # 2. Fetch Courses AND their Schedule (Day/Time)
        # We use 'image_url' here as defined in your model
        cursor.execute(
            """
            SELECT c.course_id, c.course_name, c.course_level, c.image_url
            FROM StudentCourses sc
            INNER JOIN Courses c ON c.course_id = sc.course_id
            WHERE sc.Student_ID = %s 
        """,
            [Student_ID],
        )
        course_rows = cursor.fetchall()

        # 3. Fetch Unread Announcements Count
        cursor.execute(
            """
            SELECT COUNT(*) 
            FROM AnnouncementReadStatus
            WHERE Student_ID = %s AND IsRead = 0
        """,
            [Student_ID],
        )
        unread_count = cursor.fetchone()[0]

    # Process Course Data
    course_list = []
    for row in course_rows:
        img_data = row[3]
        # Handle base64 encoding if it's binary data
        try:
            if img_data and not img_data.startswith("http"):
                img_display = base64.b64encode(img_data).decode("utf-8")
            else:
                img_display = img_data
        except:
            img_display = img_data

        course_list.append(
            {
                "CourseID": row[0],
                "CourseName": row[1],
                "CourseLevel": row[2],
                "image_url": img_display,
            }
        )

    # Process Student Data
    student_data = []
    if student_row:
        try:
            s_img = (
                base64.b64encode(student_row[1]).decode("utf-8")
                if student_row[1]
                else ""
            )
        except:
            s_img = student_row[1]

        student_data.append(
            {
                "StudentName": student_row[0],
                "StudentImage": s_img,
                "StudentID": student_row[2],
            }
        )

    # ---- Build the weekly timetable from TeacherSchedule ----
    day_names = ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"]
    color_classes = ["math", "physics", "chemistry", "cs", "stats"]
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT ts.day, ts.start_time, ts.end_time, ts.course_name, ts.room
            FROM TeacherSchedule ts
            INNER JOIN Courses c ON c.course_name = ts.course_name
            INNER JOIN StudentCourses sc ON sc.course_id = c.course_id
            WHERE sc.Student_ID = %s
            """,
            [Student_ID],
        )
        sched_rows = cursor.fetchall()

    slots = sorted({(r[1], r[2]) for r in sched_rows})
    timetable = []
    for start, end in slots:
        cells = []
        for day in day_names:
            found = [
                {
                    "name": r[3],
                    "room": r[4],
                    "color": color_classes[sum(map(ord, r[3])) % len(color_classes)],
                }
                for r in sched_rows
                if r[0] == day and r[1] == start and r[2] == end
            ]
            cells.append(found)
        timetable.append({"label": f"{start} - {end}", "cells": cells})

    context = {
        "StudentRecord": student_data,
        "CourseRecord": course_list,
        "AnnouncementNum": unread_count,
        "Timetable": timetable,
    }

    return render(request, "pages/StudentSchedule.html", context)


def CoursePageStudent(request, Student_ID, course_id):
    # Safety function to handle both binary data and strings
    def safe_encode(data):
        if not data:
            return ""
        if isinstance(data, bytes):
            return base64.b64encode(data).decode("utf-8")
        # If it's already a string, just return it
        return data

    ai_report = get_student_risk_report(Student_ID, course_id)
    with connection.cursor() as cursor:
        # 1. Course Materials
        cursor.execute(
            """
            SELECT PublisherImage, PublisherName, DateOfPublish,
            DescriptionText, MaterialPath, MaterialIcon 
            FROM CourseContents
            WHERE course_id_id = %s
            ORDER BY MaterialID DESC
        """,
            [course_id],
        )
        materials = cursor.fetchall()

        # 2. Student Info
        cursor.execute(
            """
            SELECT Student_Name, Student_Image, Student_ID
            FROM StudentInformation
            WHERE Student_ID = %s
        """,
            [Student_ID],
        )
        StudentRecords = cursor.fetchall()

        # 3. Course Info
        cursor.execute(
            "SELECT course_id, course_name FROM Courses WHERE course_id = %s",
            [course_id],
        )
        CourseRecord = cursor.fetchall()

        # 4. Announcements
        cursor.execute(
            """
            SELECT COUNT(*) FROM AnnouncementReadStatus
            WHERE Student_ID = %s AND IsRead = 0
        """,
            [Student_ID],
        )
        AnnouncementNum = cursor.fetchone()[0]

        # 5. Quiz Status
        try:
            cursor.execute(
                """
                SELECT COUNT(*) FROM QuizTakeStatus
                WHERE Student_ID = %s AND IsTaken = 0 AND course_id = %s
            """,
                [Student_ID, course_id],
            )
            QuizNum = cursor.fetchone()[0]
        except:
            QuizNum = 0

    # --- Processing Data with Safety Checks ---
    Student_data = []
    for record in StudentRecords:
        Student_data.append(
            {
                "StudentName": record[0],
                "StudentImage": safe_encode(record[1]),
                "StudentId": record[2],
            }
        )

    material_data = []
    for mat in materials:
        # Process the material path (mat[4])
        # If it's binary data (the file itself), we encode it.
        # If it's a string path, we keep it as a string.
        m_path_raw = mat[4]
        m_path_processed = safe_encode(m_path_raw)

        # Detect type safely
        m_path_str = str(m_path_raw).lower()
        if ".pdf" in m_path_str:
            m_type = "pdf"
        elif any(v in m_path_str for v in [".mp4", ".mov", ".avi"]):
            m_type = "video"
        else:
            m_type = "file"

        material_data.append(
            {
                "publisher_image": safe_encode(mat[0]),
                "publisher_name": mat[1],
                "date_posted": mat[2],
                "description": mat[3],
                "file_path": m_path_processed,
                "material_icon": mat[5],
                "material_type": m_type,
                "is_binary": isinstance(m_path_raw, bytes),  # Useful for HTML logic
            }
        )

    context = {
        "materials": material_data,
        "StudentRecord": Student_data,
        "CourseRecord": CourseRecord,
        "AnnouncementNum": AnnouncementNum,
        "QuizNum": QuizNum,
        "StudentID": Student_ID,
        "CourseID": course_id,
        "ai_report": ai_report,
    }
    return render(request, "pages/CoursePageStudent.html", context)


import base64
from django.db import connection
from django.shortcuts import render


def FinalGrade(request, StudentID):
    Student_data = []
    FinalGrade_data = []

    with connection.cursor() as cursor:
        # 1. Fetch Student Info
        cursor.execute(
            """
            SELECT Student_Name, Student_Image, Student_ID
            FROM StudentInformation
            WHERE Student_ID = %s 
        """,
            [StudentID],
        )
        student_raw = cursor.fetchall()

        if student_raw:
            for rec in student_raw:
                img_base64 = ""
                if rec[1] and isinstance(rec[1], bytes):
                    img_base64 = base64.b64encode(rec[1]).decode("utf-8")

                Student_data.append(
                    {
                        "StudentName": rec[0],
                        "StudentImage": img_base64,
                        "StudentID": rec[2],
                    }
                )

        # 2. Get all courses this student is enrolled in
        cursor.execute(
            "SELECT course_id, course_name FROM StudentCourses WHERE Student_ID = %s",
            [StudentID],
        )
        enrolled_courses = cursor.fetchall()

        for course in enrolled_courses:
            c_id = course[0]
            c_name = course[1]

            # A. Calculate LIVE Attendance
            cursor.execute(
                "SELECT COUNT(*) FROM AttendanceList WHERE Student_ID = %s AND Course_ID = %s",
                [StudentID, c_id],
            )
            total_sessions = cursor.fetchone()[0] or 1  # Avoid division by zero

            cursor.execute(
                "SELECT COUNT(*) FROM AttendanceList WHERE Student_ID = %s AND Course_ID = %s AND Status = 'Present'",
                [StudentID, c_id],
            )
            present_count = cursor.fetchone()[0]

            attendance_pct = round((present_count / total_sessions) * 100, 1)

            # B. Get Quiz Total
            cursor.execute(
                "SELECT SUM(MarksObtained) FROM QuizGrades WHERE StudentID = %s AND CourseID = %s",
                [StudentID, c_id],
            )
            total_quiz = cursor.fetchone()[0] or 0

            # C. Get Homework Total
            cursor.execute(
                "SELECT SUM(MarksObtained) FROM HomeWorkGrades WHERE Student_ID = %s AND course_id = %s",
                [StudentID, c_id],
            )
            total_hw = cursor.fetchone()[0] or 0

            # D. Fetch Midterm/Final/Participation from Summary Table
            cursor.execute(
                """
                SELECT MidTerm, Final, ClassParticipation, Credit, StudentStatus, Total
                FROM School_finalgrade
                WHERE student_id = %s AND course_id = %s
            """,
                [StudentID, c_id],
            )
            summary = cursor.fetchone()

            if summary:
                FinalGrade_data.append(
                    {
                        "CourseName": c_name,
                        "TotalAssignment": total_hw,
                        "TotalQuizMark": total_quiz,
                        "MidTerm": summary[0],
                        "Final": summary[1],
                        "ClassParticipation": summary[2],
                        "ClassAttendance": f"{attendance_pct}%",
                        "AttendancePct": attendance_pct,
                        "Credit": summary[3],
                        "StudentStatus": summary[4],
                        "Total": summary[5],
                    }
                )
            else:
                # No summary record yet: use the real midterm mark if it exists
                cursor.execute(
                    "SELECT MarksObtained FROM MidtermGrades WHERE Student_ID = %s AND Course_ID = %s",
                    [StudentID, c_id],
                )
                mid_row = cursor.fetchone()
                FinalGrade_data.append(
                    {
                        "CourseName": c_name,
                        "TotalAssignment": total_hw,
                        "TotalQuizMark": total_quiz,
                        "MidTerm": mid_row[0] if mid_row else None,
                        "Final": None,
                        "ClassParticipation": 0,
                        "ClassAttendance": f"{attendance_pct}%",
                        "AttendancePct": attendance_pct,
                        "Credit": 0,
                        "StudentStatus": "Active",
                        "Total": 0,
                    }
                )

    context = {"StudentRecord": Student_data, "FinalGrades": FinalGrade_data}
    return render(request, "pages/FinalGrades.html", context)


def TeacherSchedule(request, teacher_id):
    with connection.cursor() as cursor:
        # 1. Fetch Teacher Info
        # Ensure 'TeacherInformation' matches your models.py Meta db_table
        cursor.execute(
            "SELECT Teacher_Name, Teacher_Image FROM TeacherInformation WHERE Teacher_Id = %s",
            [teacher_id],
        )
        teacher_row = cursor.fetchone()

        teacher_data = {}
        if teacher_row:
            raw_img = teacher_row[1]
            img_b64 = (
                base64.b64encode(raw_img).decode("utf-8")
                if raw_img and isinstance(raw_img, bytes)
                else ""
            )

            teacher_data = {
                "TeacherName": teacher_row[0],
                "TeacherImage": raw_img or "",
            }

        # 2. Fetch Schedule Info
        # This matches the 'db_table' we set in models.py
        cursor.execute(
            """
            SELECT day, start_time, end_time, course_name, room 
            FROM TeacherSchedule 
            WHERE teacher_id = %s
        """,
            [teacher_id],
        )
        schedule_rows = cursor.fetchall()

        schedules_list = []
        for r in schedule_rows:
            schedules_list.append(
                {"day": r[0], "start": r[1], "end": r[2], "course": r[3], "room": r[4]}
            )

        context = {
            "TeacherRecord": [teacher_data] if teacher_data else [],
            "Schedules": schedules_list,
        }
    return render(request, "pages/TeacherSchedule.html", context)


def AddTeacherPage(request):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT Teacher_Id FROM TeacherInformation ORDER BY Teacher_Id DESC LIMIT 1"
        )
        last_record = cursor.fetchone()
        last_Teacher_Id = last_record[0] if last_record else 0

    new_Teacher_Id = last_Teacher_Id + 1

    context = {"LastRecord": new_Teacher_Id}

    return render(request, "pages/AddTeacher.html", context)


def AddCoursePage(request):
    return render(request, "pages/add_course.html")


def AddStudentForm(request):
    return render(request, "pages/AddStudent.html")


def AddParentForm(request):
    return render(request, "pages/AddParent.html")


def student_info_view(request, Student_ID):
    with connection.cursor() as cursor:
        # 1. Update column names to match your database exactly
        # 2. Update table name to StudentInformation if the first one fails
        cursor.execute(
            """
            SELECT Student_Name, Student_Image, Student_ID, 
                   Student_Nationality, Student_Level, Student_NationalID, Student_Age
            FROM StudentInformation
            WHERE Student_ID = %s
        """,
            [Student_ID],
        )

        StudentRecord = cursor.fetchall()

        Student_data = []
        if StudentRecord:
            for Record in StudentRecord:
                name = Record[0]
                raw_image = Record[1]
                s_id = Record[2]
                nationality = Record[3]
                level = Record[4]
                national_id = Record[5]
                age = Record[6]

                # Safe Image Encoding
                encoded_image = ""
                if raw_image:
                    try:
                        # If image is binary/BLOB
                        encoded_image = base64.b64encode(raw_image).decode("utf-8")
                    except:
                        # If image is just a string filename
                        encoded_image = raw_image

                Student_data.append(
                    {
                        "StudentName": name,
                        "StudentImage": encoded_image,
                        "StudentID": s_id,
                        "Nationality": nationality,
                        "StudentLevel": level,
                        "NationalID": national_id,
                        "Age": age,
                    }
                )

        context = {
            "StudentRecord": Student_data,
        }

    return render(request, "pages/StudentInformation.html", context)


def TeacherInformation(request, Teacher_ID):
    with connection.cursor() as cursor:
        # We only select columns that exist in your Model class
        cursor.execute(
            """
            SELECT Teacher_Name, Teacher_Id, Teacher_Age, 
                   Teacher_Gender, Teacher_NationalID, Teacher_Image
            FROM TeacherInformation
            WHERE Teacher_Id = %s
        """,
            [Teacher_ID],
        )

        row = cursor.fetchone()

        Teacher_data = []
        if row:
            # Handle image: check if it's base64 string or raw bytes
            raw_image = row[5]
            display_image = ""
            if raw_image:
                # If your DB stores it as raw bytes, encode it.
                # If it's already a string/path, use it directly.
                if isinstance(raw_image, bytes):
                    display_image = base64.b64encode(raw_image).decode("utf-8")
                else:
                    display_image = raw_image

            Teacher_data.append(
                {
                    "TeacherName": row[0],
                    "TeacherID": row[1],
                    "Age": row[2],
                    "Gender": row[3],
                    "NationalID": row[4],
                    "TeacherImage": display_image,
                }
            )

        context = {
            "TeacherRecord": Teacher_data,
        }

    return render(request, "pages/TeacherInformation.html", context)


def GenerateQuizPage(request, teacher_id, course_id):
    context = {"TecherID": teacher_id, "CourseID": course_id}
    return render(request, "pages/GenerateQuiz.html", context)


def GenerateReportPage(request):
    return render(request, "pages/GenerateReport2.html")


def UploadMaterialPage(request, Teacher_Id, course_id):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT Teacher_Name, Teacher_Id 
            FROM TeacherInformation 
            WHERE Teacher_Id = %s
        """,
            [Teacher_Id],
        )
        TeacherRecord = cursor.fetchone()

        cursor.execute(
            "SELECT course_id FROM Courses WHERE course_id = %s", [course_id]
        )
        CourseRecord = cursor.fetchone()

    if TeacherRecord and CourseRecord:
        context = {
            "teacher_name": TeacherRecord[0],
            "teacher_id": TeacherRecord[1],
            "course_id": CourseRecord[0],
        }
        return render(request, "pages/UploadMaterials.html", context)
    else:
        return HttpResponse(
            f"Lookup Failed. Teacher {Teacher_Id} not found in TeacherInformation."
        )


def UpdateMaterial(request, Teacher_Id, course_id, content_id):
    if request.method == "POST":
        print("In the UodateMaterialFunction")
        description = request.POST.get("description")
        media_type = request.POST.get("media-type")

        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE CourseContents
                SET DescriptionText = %s, MaterialType = %s
                WHERE MaterialID = %s
            """,
                [description, media_type, content_id],
            )

        return JsonResponse({"message": "Material updated successfully!"}, status=200)


def UpdateMaterialPage(request, Teacher_Id, course_id, content_id):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT Teacher_Name, Teacher_Id
            FROM TeacherInformation
            WHERE Teacher_Id = %s 
        """,
            [Teacher_Id],
        )

        TeacherRecord = cursor.fetchall()

        cursor.execute(
            """
                SELECT course_id
                FROM Courses
                WHERE course_id = %s
            """,
            [course_id],
        )

        CourseRecord = cursor.fetchall()

        cursor.execute(
            """
        SELECT CourseContents.MaterialID, CourseContents.DescriptionText,  CourseContents.MaterialType
        FROM CourseContents 
        INNER JOIN Courses ON Courses.course_id = CourseContents.course_id
        WHERE  CourseContents.MaterialID = %s
            """,
            [content_id],
        )
        CourseContent = cursor.fetchall()

    if TeacherRecord:
        context = {
            "Record1": TeacherRecord,
            "Record2": CourseRecord,
            "CourseContent": CourseContent,
        }

    return render(request, "pages/UpdateMaterial.html", context)


def add_teacher_page(request):
    last_teacher = TeacherModel.objects.order_by("Teacher_Id").last()
    new_id = (last_teacher.Teacher_Id + 1) if last_teacher else 1

    with connection.cursor() as cursor:
        cursor.execute("SELECT course_id, course_name FROM Courses")
        courses = [{"id": r[0], "name": r[1]} for r in cursor.fetchall()]

    context = {"LastRecord": new_id, "courses": courses}
    return render(request, "pages/AddTeacher.html", context)


def SaveTeacher(request):
    if request.method == "POST":
        t_id = request.POST.get("teacher_id")
        name = request.POST.get("teacher_name")
        n_id = request.POST.get("national_id")
        age = request.POST.get("teacher_age")
        gender = request.POST.get("teacher_gender")
        assigned_course = request.POST.get("teacher_course")
        image = request.FILES.get("teacher_image")

        # Logic: First 3 letters (Upper) + @ + National ID
        try:
            # We use .upper() to keep it consistent (KAR@112233)
            name_part = name.replace(" ", "")[:3].upper() if name else "TEA"
            generated_pw = f"{name_part}@{n_id}"
        except:
            generated_pw = f"TEA@{n_id}"

        try:
            # Note: Since your model has Teacher_Image as CharField,
            # we should save the name or handle binary differently.
            # For now, let's store the raw binary if you want to use base64 in login.

            new_teacher = TeacherModel(
                Teacher_Id=t_id,
                Teacher_Name=name,
                Teacher_NationalID=n_id,
                Teacher_Age=age,
                Teacher_Gender=gender,
                Course_Handle=assigned_course,
                Passwordd=make_password(generated_pw),
            )

            if image:
                # If you want to use base64.b64encode in the login view,
                # you must save the binary data.
                new_teacher.Teacher_Image = base64.b64encode(image.read()).decode(
                    "utf-8"
                )
            else:
                new_teacher.Teacher_Image = ""

            new_teacher.save()

            return JsonResponse(
                {
                    "success": True,
                    "message": f"Instructor saved! Password: {generated_pw}",
                }
            )
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)

    return redirect("AddTeacherPage")


def update_teacher_page(request, t_id):
    teacher = get_object_or_404(TeacherModel, Teacher_Id=t_id)

    # Fetch all courses for the dropdown
    with connection.cursor() as cursor:
        cursor.execute("SELECT course_name FROM Courses")
        all_courses = [row[0] for row in cursor.fetchall()]

    if request.method == "POST":
        teacher.Teacher_Name = request.POST.get("teacher_name")
        teacher.Teacher_Age = request.POST.get("teacher_age")
        teacher.Teacher_Gender = request.POST.get("teacher_gender")
        teacher.Course_Handle = request.POST.get("teacher_course")
        # ADD THIS LINE:
        teacher.Teacher_NationalID = request.POST.get("national_id")
        name_part = teacher.Teacher_Name.replace(" ", "")[:3].upper()
        teacher.Passwordd = make_password(f"{name_part}@{teacher.Teacher_NationalID}")
        if "teacher_image" in request.FILES:
            teacher.Teacher_Image = request.FILES["teacher_image"]

        teacher.save()
        return redirect("view_teachers")

    return render(
        request,
        "pages/UpdateTeacher.html",
        {"teacher": teacher, "all_courses": all_courses},
    )


def CourseContent(request):
    return render(request, "pages/CoursePage.html")


def Upload(request):
    return render(request, "pages/add_course.html")


def upload_assignment_Page(request, Teacher_Id, Course_Id):
    Teacher_data = []
    Course_data = []

    with connection.cursor() as cursor:
        # 1. Fetch Teacher Info (Default table name)
        cursor.execute(
            """
            SELECT Teacher_Name, Teacher_Image, Teacher_Id
            FROM TeacherInformation
            WHERE Teacher_Id = %s 
        """,
            [Teacher_Id],
        )
        TeacherRecord = cursor.fetchall()

        if TeacherRecord:
            for Record in TeacherRecord:
                # Handle Image: Teacher_Image is a CharField (URL/Path) in your model
                Teacher_data.append(
                    {
                        "TeacherName": Record[0],
                        "TeacherImage": Record[1],  # String path from CharField
                        "TeacherID": Record[2],
                    }
                )

        # 2. Fetch Courses for this Teacher (Uses 'Courses' table from your Meta class)
        cursor.execute(
            """
            SELECT c.course_id, c.course_name, c.course_level, c.image_url
            FROM TeacherCourses tc
            INNER JOIN Courses c ON c.course_id = tc.course_id
            WHERE tc.Teacher_Id = %s 
        """,
            [Teacher_Id],
        )

        CourseRecords = cursor.fetchall()
        for Record in CourseRecords:
            Course_data.append(
                {
                    "CourseID": Record[0],
                    "CourseName": Record[1],
                    "Courselevel": Record[2],
                    "image_url": Record[3],  # image_url from your model
                }
            )

    # Fallback check
    if not Teacher_data:
        return HttpResponse("Teacher not found in database.")

    context = {
        "TeacherID": Teacher_Id,
        "CourseID": Course_Id,
        "TeacherRecords": Teacher_data,
        "CourseRecord": Course_data,
    }

    return render(request, "pages/UploadAssignment.html", context)


def CoursePage(request, teacher_id, course_id):
    with connection.cursor() as cursor:
        # 1. Fetch Materials for this specific course
        cursor.execute(
            """
            SELECT PublisherImage, PublisherName, DateOfPublish,
                   DescriptionText, MaterialPath
            FROM CourseContents
            WHERE course_id = %s
            ORDER BY MaterialID
        """,
            [course_id],
        )

        course_contents = cursor.fetchall()

    # 2. Process File Types (mimetypes logic)
    formatted_contents = []
    for description in course_contents:
        pub_img, pub_name, date, desc, path = description

        # Determine the file type based on the extension (e.g., .mp4, .pdf)
        file_type, _ = mimetypes.guess_type(path) if path else (None, None)

        if file_type:
            if file_type.startswith("image"):
                content_type = "image"
            elif file_type.startswith("video"):
                content_type = "video"
            elif file_type.startswith("audio"):
                content_type = "audio"
            elif file_type == "application/pdf":
                content_type = "pdf"
            else:
                content_type = "file"  # General file icon
        else:
            content_type = "unknown"

        formatted_contents.append(
            {
                "publisher_image": pub_img,
                "publisher_name": pub_name,
                "date_of_publish": date,
                "description_text": desc,
                "material_path": path,
                "content_type": content_type,
            }
        )

    # 3. Render the page
    # Passing IDs back ensures your "Upload" and "Back" buttons work correctly
    return render(
        request,
        "pages/CoursePage.html",
        {
            "course_contents": formatted_contents,
            "teacher_id": teacher_id,
            "course_id": course_id,
        },
    )


def add_course(request):
    if request.method == "POST":
        course_name = request.POST.get("course_name")
        course_id = request.POST.get("course_id")
        course_level = request.POST.get("course_level")
        course_image = request.FILES.get("course_image")
        image_to_save = course_image.name if course_image else "default.jpg"

        with connection.cursor() as cursor:
            try:
                # Removed credit_hours from columns and values
                cursor.execute(
                    """
                    INSERT INTO Courses (course_id, course_name, course_level, image_url, link_url)
                    VALUES (%s, %s, %s, %s, %s)
                """,
                    [course_id, course_name, course_level, image_to_save, "#"],
                )

                return JsonResponse({"status": "success"})
            except Exception as e:
                return JsonResponse({"status": "error", "message": str(e)}, status=400)


def get_records(request, course_id):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT CourseContents.PublisherImage, CourseContents.PublisherName, CourseContents.DateOfPublish,
            CourseContents.DescriptionText, CourseContents.MaterialPath, CourseContents.MaterialIcon
            FROM CourseContents
            INNER JOIN Courses ON CourseContents.course_id = Courses.course_id
            WHERE Courses.course_id = %s
            ORDER BY CourseContents.MaterialID
        """,
            [course_id],
        )
        # ("SELECT PublisherImage, PublisherName, DateOfPublish, DescriptionText, MaterialPath, MaterialIcon  FROM CourseContents")
        course_contents = cursor.fetchall()

    if course_contents:
        records_data = []
        for record in course_contents:
            file_path = record[4]
            if file_path.endswith(".pdf"):
                content_type = "pdf"
            elif file_path.endswith(".mp4"):
                content_type = "video"
            else:
                content_type = "unknown"
            records_data.append(
                {
                    "avatar": record[0],
                    "publisher_name": record[1],
                    "date": record[2],
                    "description": record[3],
                    "Icon": record[5],
                    "file_path": file_path,
                    "content_type": content_type,
                }
            )

        return render(request, "pages/Try.html", {"records": records_data})
    else:
        return HttpResponse("Null record")


def get_course_contents(request, course_id):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT CourseContents.PublisherImage, CourseContents.PublisherName, CourseContents.DateOfPublish,
            CourseContents.DescriptionText, CourseContents.MaterialPath, CourseContents.MaterialIcon
            FROM CourseContents
            INNER JOIN Courses ON CourseContents.course_id = Courses.course_id
            WHERE Courses.course_id = %s
            ORDER BY CourseContents.MaterialID
        """,
            [course_id],
        )

        course_contents = cursor.fetchall()

    if course_contents:
        print(course_id)
        return render(request, "pages/Try.html", {"course_contents": course_contents})
    else:
        return HttpResponse("Null record")


def add_student(request):
    if request.method == "POST":
        # 1. Collect basic info
        student_name = request.POST.get("student_name")
        student_id = request.POST.get("student_id")
        student_age = request.POST.get("student_age")
        student_level = request.POST.get("student_level")
        student_gender = request.POST.get("student_gender")
        student_nationality = request.POST.get("student_nationality")
        national_id = request.POST.get("national_id")

        # 2. Collect New AI Features (Fixed the key to 'student_cgpa')
        raw_cgpa = request.POST.get("student_cgpa")
        raw_entry = request.POST.get("entry_year")

        # 3. Clean and Convert Data (Prevents 'None' or 'IntegrityError')
        try:
            cgpa = float(raw_cgpa) if raw_cgpa else 0.0
        except ValueError:
            cgpa = 0.0

        try:
            entry = int(raw_entry) if raw_entry else 2026
        except ValueError:
            entry = 2026

        # 4. Password Generation Logic
        name_prefix = student_name[:3] if student_name else "STU"
        generated_password = f"{name_prefix}@{national_id}"

        # 5. Handle Image Upload
        student_image = None
        if request.FILES.get("student_image"):
            img = request.FILES["student_image"]
            student_image = img.name

        if StudentInformation.objects.filter(Student_NationalID=national_id).exists():
            messages.error(
                request,
                f"Error: A student with National ID {national_id} is already registered.",
            )
            return redirect("add_student_page")
        # 6. Save to database
        try:
            StudentInformation.objects.create(
                Student_Name=student_name,
                Student_ID=student_id,
                Student_Age=student_age,
                Student_Level=student_level,
                Student_Gender=student_gender,
                Student_Nationality=student_nationality,
                Student_NationalID=national_id,
                Student_Image=student_image,
                Passwordd=make_password(generated_password),
                student_cgpa=cgpa,  # Verified float value
                entry_year=entry,  # Verified int value
            )
            messages.success(
                request, f"Student added! Password: {generated_password} | CGPA: {cgpa}"
            )
        except Exception as e:
            messages.error(request, f"Error saving student: {str(e)}")

        return redirect("add_student_page")

    return redirect("add_student_page")


from django.db import connection


def view_teachers(request):
    # This automatically gets the correct table name from your model
    teacher_table = TeacherModel._meta.db_table

    with connection.cursor() as cursor:
        cursor.execute(f"""
            SELECT 
                t.Teacher_Id, 
                t.Teacher_Name, 
                t.Teacher_Age, 
                t.Teacher_Gender, 
                t.Teacher_Image,
                c.course_id,
                c.course_name,
                t.Teacher_NationalID  -- Added this column to the SQL query
            FROM {teacher_table} t
            LEFT JOIN Courses c ON t.Course_Handle = c.course_name
        """)
        rows = cursor.fetchall()

    teachers_list = []
    for row in rows:
        teachers_list.append(
            {
                "Teacher_Id": row[0],
                "Teacher_Name": row[1],
                "Teacher_Age": row[2],
                "Teacher_Gender": row[3],
                "Teacher_Image": row[4],
                "Course_ID": row[5] if row[5] else "N/A",
                "Course_Name": row[6] if row[6] else "No Course Assigned",
                "Teacher_NationalID": row[7],  # Map the 8th column (index 7) here
            }
        )

    return render(request, "pages/ViewTeachers.html", {"teachers": teachers_list})


def delete_teacher(request, t_id):  # Now it accepts the ID from the URL
    teacher = get_object_or_404(TeacherModel, Teacher_Id=t_id)
    teacher.delete()
    return redirect("view_teachers")


def view_students(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                s.Student_ID, 
                s.Student_Name, 
                s.Student_Age, 
                s.Student_Level, 
                s.Student_Gender, 
                s.Student_Image,
                s.Student_NationalID,
                s.student_cgpa,              -- Index 7
                s.entry_year,                -- Index 8
                GROUP_CONCAT(c.course_name, ', ') -- Index 9
            FROM StudentInformation s 
            LEFT JOIN StudentCourses sc ON s.Student_ID = sc.Student_ID
            LEFT JOIN Courses c ON sc.course_id = c.course_id
            GROUP BY s.Student_ID
        """)
        rows = cursor.fetchall()

    students = []
    for row in rows:
        students.append(
            {
                "Student_ID": row[0],
                "Student_Name": row[1],
                "Student_Age": row[2],
                "Student_Level": row[3],
                "Student_Gender": row[4],
                "Student_Image": row[5],
                "Student_NationalID": row[6],
                "student_cgpa": row[7] if row[7] is not None else "0.00",  # New mapping
                "entry_year": row[8] if row[8] else "N/A",  # New mapping
                "courses": row[9] if row[9] else "No courses assigned",
            }
        )

    return render(request, "pages/ViewStudents.html", {"students": students})


def add_student_page(request):
    context = {
        "levels": range(1, 13),  # This creates [1, 2, ..., 12]
    }
    return render(request, "pages/AddStudent.html", context)


def delete_student(request, student_id):
    student = get_object_or_404(StudentInformation, Student_ID=student_id)
    student.delete()
    messages.success(request, f"Student {student.Student_Name} deleted successfully!")
    return redirect("view_students")


def update_student(request, student_id):
    student = get_object_or_404(StudentInformation, Student_ID=student_id)

    if request.method == "POST":
        # Update Student Details
        student.Student_Name = request.POST.get("student_name")
        student.Student_Age = request.POST.get("student_age")
        student.Student_Level = request.POST.get("student_level")
        student.Student_Gender = request.POST.get("student_gender")
        student.Student_NationalID = request.POST.get("student_nationalid")

        # --- NEW FIELDS ADDED HERE ---
        raw_cgpa = request.POST.get("student_cgpa")
        raw_entry = request.POST.get("entry_year")

        # Safe numeric conversion
        student.student_cgpa = float(raw_cgpa) if raw_cgpa else 0.0
        student.entry_year = int(raw_entry) if raw_entry else 2026
        # -----------------------------

        if request.FILES.get("student_image"):
            student.Student_Image = request.FILES.get("student_image")

        student.save()

        # Handle Course Removal
        remove_course_id = request.POST.get("remove_course_id")
        if remove_course_id:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM StudentCourses WHERE Student_ID = %s AND course_id = %s",
                    [student_id, remove_course_id],
                )

        # Handle Course Addition
        new_course_id = request.POST.get("new_course_id")
        if new_course_id:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM StudentCourses WHERE Student_ID = %s AND course_id = %s",
                    [student_id, new_course_id],
                )
                if not cursor.fetchone():
                    cursor.execute(
                        "INSERT INTO StudentCourses (Student_ID, course_id) VALUES (%s, %s)",
                        [student_id, new_course_id],
                    )

        messages.success(request, f"{student.Student_Name} updated successfully!")
        return redirect("view_students")

    # Fetch Current Courses for the form
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT c.course_id, c.course_name 
            FROM Courses c
            JOIN StudentCourses sc ON c.course_id = sc.course_id
            WHERE sc.Student_ID = %s
        """,
            [student_id],
        )
        current_courses = [{"id": r[0], "name": r[1]} for r in cursor.fetchall()]

        cursor.execute("SELECT course_id, course_name FROM Courses")
        all_courses = [{"id": r[0], "name": r[1]} for r in cursor.fetchall()]

    levels = range(1, 13)
    return render(
        request,
        "pages/UpdateStudent.html",
        {
            "student": student,
            "levels": levels,
            "current_courses": current_courses,
            "all_courses": all_courses,
        },
    )


def view_courses(request):
    courses = Courses.objects.all().order_by("course_id")
    return render(request, "pages/ViewCourses.html", {"courses": courses})


def delete_course(request, course_id):
    course = get_object_or_404(Courses, course_id=course_id)
    course_name = course.course_name  # Store name before deleting for the message
    course.delete()
    messages.success(request, f"Course '{course_name}' deleted successfully!")
    return redirect("view_courses")


def update_course(request, course_id):
    course = get_object_or_404(Courses, course_id=course_id)

    if request.method == "POST":
        course.course_name = request.POST.get("course_name")
        course.course_level = request.POST.get("course_level")
        # Only update the image if a new one was uploaded
        if request.FILES.get("course_image"):
            course.image_url = request.FILES.get("course_image").name

        course.save()
        messages.success(
            request, f"Course '{course.course_name}' updated successfully!"
        )
        return redirect("view_courses")

    return render(request, "pages/UpdateCourse.html", {"course": course})


def add_parent_page(request):
    # Safely get the max ID
    max_id = ParentModel.objects.aggregate(Max("Parent_ID"))["Parent_ID__max"]

    # If table is empty, start at 1, otherwise add 1
    next_id = (max_id or 0) + 1

    # We pass 'LastRecord' because your HTML template uses: value="{{ LastRecord }}"
    return render(request, "pages/AddParent.html", {"LastRecord": next_id})


def add_parent(request):
    if request.method == "POST":
        p_name = request.POST.get("parent_name")
        p_id = request.POST.get("parent_id")
        p_national_id = request.POST.get("parent_national_id")
        s_id = request.POST.get("student_id")
        p_image = request.FILES.get("parent_image")

        try:
            student_instance = get_object_or_404(StudentInformation, Student_ID=s_id)

            # --- PASSWORD LOGIC ---
            # Take first 3 letters of name, remove spaces, make lowercase
            name_part = p_name.replace(" ", "")[:3]
            generated_password = f"{name_part}@{p_national_id}"

            new_parent = ParentInformation(
                Parent_ID=p_id,
                Parent_Name=p_name,
                Parent_NationalID=p_national_id,
                Student_ID=student_instance,
                Parent_Image=p_image.name if p_image else "default.png",
                Passwordd=make_password(generated_password),
            )
            new_parent.save()
            return JsonResponse({"status": "success"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)


def view_parents(request):
    # Using ParentInformation to match your model class
    parents = (
        ParentModel.objects.all().select_related("Student_ID").order_by("Parent_ID")
    )
    return render(request, "pages/ViewParents.html", {"parents": parents})


def delete_parent(request, parent_id):
    parent = get_object_or_404(ParentModel, Parent_ID=parent_id)
    parent_name = parent.Parent_Name
    parent.delete()
    messages.success(request, f"Parent {parent_name} deleted successfully!")
    return redirect("view_parents")


def update_parent(request, parent_id):
    parent = get_object_or_404(ParentInformation, Parent_ID=parent_id)

    if request.method == "POST":
        s_id = request.POST.get("student_id")
        p_name = request.POST.get("parent_name")
        p_national_id = request.POST.get("parent_national_id")

        try:
            student_instance = get_object_or_404(StudentInformation, Student_ID=s_id)

            parent.Parent_Name = p_name
            parent.Parent_NationalID = p_national_id
            parent.Student_ID = student_instance

            # --- UPDATE PASSWORD LOGIC ---
            name_part = p_name.replace(" ", "")[:3]
            new_pw = f"{name_part}@{p_national_id}"
            new_pw = make_password(new_pw)

            if request.FILES.get("parent_image"):
                parent.Parent_Image = request.FILES.get("parent_image").name

            parent.save()
            messages.success(
                request,
                f"Parent {parent.Parent_Name} updated. New Password: {parent.Passwordd}",
            )
            return redirect("view_parents")

        except Exception as e:
            messages.error(request, f"Error updating parent: {e}")

    students = StudentInformation.objects.all()
    return render(
        request, "pages/UpdateParent.html", {"parent": parent, "students": students}
    )


def AddTeacher(request):
    if request.method == "POST":
        teacher_name = request.POST["teacher_name"]
        teacher_id = request.POST["teacher_id"]
        teacher_age = request.POST["teacher_age"]
        teacher_specialist = request.POST["teacher_specialist"]
        teacher_nationality = request.POST["teacher_nationality"]
        teacher_gender = request.POST["teacher_gender"]
        date_of_birth = request.POST["dateOfBirth"]

        current_date = datetime.now()
        enrollment_date = current_date.strftime("%b %d")

        teacher_image = request.FILES["teacher_image"]
        image_binary = None

        if isinstance(teacher_image, InMemoryUploadedFile):
            image_binary = teacher_image.read()

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO TeacherInformation (
                    Teacher_Name, 
                    Teacher_Id, 
                    Teacher_Age,
                    Teacher_specialist, 
                    Nationality, 
                    Teacher_Gender, 
                    Teacher_Image, 
                    DateOfBirth, 
                    EnrolmentDate, 
                    Passwordd
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
                [
                    teacher_name,
                    teacher_id,
                    teacher_age,
                    teacher_specialist,
                    teacher_nationality,
                    teacher_gender,
                    image_binary,
                    date_of_birth,
                    enrollment_date,
                    make_password("123"),
                ],
            )

        return JsonResponse({"message": "Teacher added successfully"})


def redirectAddStudent(request):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT Student_ID FROM StudentInformation ORDER BY Student_ID DESC LIMIT 1"
        )
        last_record = cursor.fetchone()
        last_student_id = last_record[0] if last_record else 0

    new_student_id = last_student_id + 1

    context = {"LastRecord": new_student_id}

    return render(request, "pages/AddStudent.html", context)


def UploadMaterial(request, Teacher_Id, course_id):
    if request.method == "POST":
        description = request.POST.get("description")
        media_type = request.POST.get("media-type")
        media_file = request.FILES.get("media-file")

        icon_mapping = {
            "pdf": "fas fa-file-pdf",
            "video": "fas fa-video",
            "image": "fas fa-image",
        }
        selected_icon = icon_mapping.get(media_type, "fas fa-file")
        current_date = datetime.now().strftime("%d %b")

        with connection.cursor() as cursor:
            # 1. AUTO-SYNC TEACHER: Mirror from TeacherInformation to TeacherInformation
            cursor.execute(
                """
                INSERT OR IGNORE INTO TeacherInformation (Teacher_Id, Teacher_Name, Teacher_Image)
                SELECT Teacher_Id, Teacher_Name, Teacher_Image 
                FROM TeacherInformation 
                WHERE Teacher_Id = %s
            """,
                [Teacher_Id],
            )

            # 2. AUTO-SYNC COURSE: Mirror from Courses to School_courses
            cursor.execute(
                """
                INSERT OR IGNORE INTO Courses (course_id, course_name, course_level, image_url, link_url)
                SELECT course_id, course_name, course_level, image_url, link_url 
                FROM Courses 
                WHERE course_id = %s
            """,
                [course_id],
            )

            # 3. VERIFY DATA EXISTS (After Sync Attempt)
            cursor.execute(
                "SELECT Teacher_Name, Teacher_Image FROM TeacherInformation WHERE Teacher_Id = %s",
                [Teacher_Id],
            )
            teacher_record = cursor.fetchone()

            if teacher_record:
                teacher_name, teacher_image = teacher_record
                material_data = media_file.read()

                # 4. FINAL INSERT (The Foreign Key should now always pass)
                cursor.execute(
                    """
                    INSERT INTO CourseContents(
                        PublisherImage, PublisherName, DateOfPublish, 
                        DescriptionText, MaterialPath, course_id_id, MaterialIcon
                    ) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                    [
                        teacher_image,
                        teacher_name,
                        current_date,
                        description,
                        material_data,
                        course_id,
                        selected_icon,
                    ],
                )

                return JsonResponse({"status": "success"})
            else:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": f"Teacher {Teacher_Id} not found in master records.",
                    },
                    status=404,
                )

    return JsonResponse({"status": "error", "message": "Invalid method"}, status=400)


def DeleteMaterial(request, material_id):
    if request.method == "POST":
        try:
            with connection.cursor() as cursor:
                # Optional: Check if the record exists first
                cursor.execute(
                    "SELECT MaterialID FROM CourseContents WHERE MaterialID = %s",
                    [material_id],
                )
                if cursor.fetchone():
                    cursor.execute(
                        "DELETE FROM CourseContents WHERE MaterialID = %s",
                        [material_id],
                    )
                    return JsonResponse(
                        {
                            "status": "success",
                            "message": "Material deleted successfully",
                        }
                    )
                else:
                    return JsonResponse(
                        {"status": "error", "message": "Material not found"}, status=404
                    )
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse(
        {"status": "error", "message": "Invalid request method"}, status=400
    )


def upload_material_view(request):
    return render(request, "pages/CoursePage2.html")

    if file_data.startswith(b"%PDF"):
        return "pdf"
    elif file_data.startswith(b"\xff\xd8"):
        return "image"
    elif file_data.startswith(b"\x89PNG"):
        return "image"
    elif file_data.startswith(b"\x00\x00\x00\x18ftypmp4"):
        return "video"
    elif file_data.startswith(b"OggS"):
        return "video"
    return "unknown"


def materials_view(request, Teacher_Id, course_id):
    # Safety function to prevent "bytes-like object" errors
    def safe_encode(data):
        if not data:
            return ""
        return (
            base64.b64encode(data).decode("utf-8") if isinstance(data, bytes) else data
        )

    with connection.cursor() as cursor:
        # 1. FETCH FROM CourseContents (Where your upload goes!)
        cursor.execute(
            """
            SELECT PublisherImage, PublisherName, DateOfPublish,
                   DescriptionText, MaterialPath, MaterialIcon, MaterialID
            FROM CourseContents
            WHERE course_id_id = %s
            ORDER BY MaterialID DESC
        """,
            [course_id],
        )
        materials = cursor.fetchall()

        # 2. Student/Teacher info from manual tables
        cursor.execute(
            """
            SELECT Teacher_Name, Teacher_Image, Teacher_Id
            FROM TeacherInformation
            WHERE Teacher_Id = %s
        """,
            [Teacher_Id],
        )
        TeacherRecords = cursor.fetchall()

        cursor.execute(
            "SELECT course_id, course_name FROM Courses WHERE course_id = %s",
            [course_id],
        )
        CourseRecord = cursor.fetchall()

    # Process Teacher Data
    Teacher_data = []
    for Record in TeacherRecords:
        Teacher_data.append(
            {
                "TeacherName": Record[0],
                "TeacherImage": safe_encode(Record[1]),
                "TeacherID": Record[2],
            }
        )

    # Process Material Data
    material_data = []
    for material in materials:
        material_data.append(
            {
                "publisher_image": safe_encode(material[0]),
                "publisher_name": material[1],
                "date_posted": material[2],
                "description": material[3],
                "file_path": safe_encode(material[4]),  # Binary file description
                "material_icon": material[5],  # The icon string
                "material_id": material[6],  # For deletion
            }
        )

    context = {
        "materials": material_data,
        "TeacherRecords": Teacher_data,
        "CourseRecord": CourseRecord,
        "teacher_id": Teacher_Id,  # Used for back-links
        "course_id": course_id,
    }

    return render(request, "pages/CoursePage2.html", context)


def ViewStudentsCourse(request, Course_ID):
    with connection.cursor() as cursor:
        # Note: I'm using "StudentInformation" which is the Django default.
        # If your database shell showed just "StudentInformation", change it back.
        cursor.execute(
            """
            SELECT 
                SI.Student_Image, 
                SI.Student_Name, 
                SI.Student_ID, 
                SI.Student_Level
            FROM StudentInformation SI
            INNER JOIN StudentCourses SC ON SI.Student_ID = SC.Student_ID
            WHERE SC.course_id = %s
        """,
            [Course_ID],
        )

        StudentRecords = cursor.fetchall()

        # This will print in your VS Code / CMD terminal
        print(f"--- DEBUG: Course {Course_ID} ---")
        print(f"Total Rows Found: {len(StudentRecords)}")

        for r in StudentRecords:
            print(f"Found Student: {r[1]} (ID: {r[2]})")

    Student_data = []
    for Record in StudentRecords:
        raw_img = Record[0]
        try:
            if isinstance(raw_img, bytes):
                encoded_img = base64.b64encode(raw_img).decode("utf-8")
            else:
                encoded_img = str(raw_img)
        except:
            encoded_img = ""

        Student_data.append(
            {
                "StudentImage": encoded_img,
                "StudentName": Record[1],
                "StudentID": Record[2],
                "StudentLevel": Record[3] if Record[3] else "Not Set",
            }
        )

    return render(
        request,
        "pages/StudentInformationCourse.html",
        {"StudentRecords": Student_data, "Course_ID": Course_ID},
    )


def StudentDashboard(request, Student_ID):
    with connection.cursor() as cursor:
        # 1. Fetch Student Basic Info
        cursor.execute(
            """
            SELECT Student_Name, Student_Image, Student_ID
            FROM StudentInformation
            WHERE Student_ID = %s 
        """,
            [Student_ID],
        )
        student_row = cursor.fetchone()  # Get single record

        # 2. Fetch Enrolled Courses
        cursor.execute(
            """
            SELECT Courses.course_id, Courses.course_name, Courses.course_level, Courses.image_url
            FROM StudentCourses 
            INNER JOIN Courses ON Courses.course_id = StudentCourses.course_id
            WHERE StudentCourses.Student_ID = %s 
        """,
            [Student_ID],
        )
        course_records = cursor.fetchall()

        # 3. Fetch Unread Announcement Count
        cursor.execute(
            """
            SELECT COUNT(*) 
            FROM AnnouncementReadStatus
            WHERE Student_ID = %s AND IsRead = 0;
        """,
            [Student_ID],
        )
        announcement_count = cursor.fetchone()[0]

    # Process Course Data
    course_data = []
    for row in course_records:
        course_data.append(
            {
                "CourseID": row[0],
                "CourseName": row[1],
                "CourseLevel": row[2],
                "image_url": row[3],  # Matches your model field name
            }
        )

    # Build Context - Direct keys match your HTML variables
    context = {
        "StudentName": student_row[0] if student_row else "Student",
        "StudentImage": student_row[1] if student_row else "",
        "StudentID": Student_ID,
        "CourseRecord": course_data,
        "AnnouncementNum": announcement_count,
    }

    return render(request, "pages/Student.html", context)


def attendance_history(request, Name, Student_Id):
    with connection.cursor() as cursor:
        # We JOIN AttendanceList with Courses to get the actual Course Name
        cursor.execute(
            """
            SELECT c.course_name, a.Date, a.Status
            FROM AttendanceList a
            JOIN Courses c ON a.Course_ID = c.course_id
            WHERE c.course_name = %s AND a.Student_ID = %s
            ORDER BY a.Date DESC
        """,
            [Name, Student_Id],
        )

        records = cursor.fetchall()

    attendance_data = [
        {"CourseName": r[0], "Attendance_Date": r[1], "AttendanceStatus": r[2]}
        for r in records
    ]

    return JsonResponse(attendance_data, safe=False)


from django.db import connection


def AssignStudentCourse(request):
    if request.method == "POST":
        course_id = request.POST.get("course_id")
        student_id = request.POST.get("student_id")

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*) FROM StudentCourses 
                WHERE Student_ID = %s AND course_id = %s
            """,
                [student_id, course_id],
            )
            exists = cursor.fetchone()[0]

            if exists > 0:
                print("Duplicate entry: Record already exists")
                messages.error(request, "Duplicate entry: Record already exists")
                return redirect("/AddStudentCourse3/?success=true")

            else:
                cursor.execute(
                    """
                    INSERT INTO StudentCourses (Student_ID, course_id)
                    VALUES (%s, %s)
                """,
                    [student_id, course_id],
                )

                if cursor.rowcount == 1:
                    print("Record inserted successfully")
                    messages.success(request, "Record inserted successfully")
                    return redirect("/AddStudentCourse3/?success=true")

                else:
                    print("Insertion failed")
                    messages.success(request, "Failed to insert the record")
                    return redirect("/AddStudentCourse3/?success=true")


def fetchcoursesLists(request):
    print("In the CourseList Function: ")
    with connection.cursor() as cursor:
        # Explicitly ask for columns in a specific order
        cursor.execute("SELECT course_id, course_name, course_level FROM Courses")
        rows = cursor.fetchall()

        # Now we KNOW:
        # row[0] is course_id
        # row[1] is course_name
        # row[2] is course_level
        courses = [{"id": row[0], "name": row[1], "level": row[2]} for row in rows]

    return JsonResponse(courses, safe=False)


def AssignStudentCourse2(request):
    # Check if it's a POST request (X-Requested-With check can be strict/unreliable)
    if request.method == "POST":
        course_id = request.POST.get("course_id")
        student_id = request.POST.get("student_id")

        if not course_id or not student_id:
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Please provide both Student ID and Course selection.",
                }
            )

        try:
            with connection.cursor() as cursor:
                # 1. Check for duplicates
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM StudentCourses 
                    WHERE Student_ID = %s AND course_id = %s
                """,
                    [student_id, course_id],
                )
                if cursor.fetchone()[0] > 0:
                    return JsonResponse(
                        {
                            "status": "error",
                            "message": "This student is already assigned to this course.",
                        }
                    )

                # 2. FETCH THE COURSE NAME (Crucial Step!)
                # Your model requires a course_name, so we must find it first
                cursor.execute(
                    "SELECT course_name FROM Courses WHERE course_id = %s", [course_id]
                )
                course_data = cursor.fetchone()
                course_name = course_data[0] if course_data else "Unknown Course"

                # 3. INSERT with all required fields
                cursor.execute(
                    """
                    INSERT INTO StudentCourses (Student_ID, course_id, course_name)
                    VALUES (%s, %s, %s)
                """,
                    [student_id, course_id, course_name],
                )

                return JsonResponse(
                    {"status": "success", "message": "Record inserted successfully"}
                )

        except Exception as e:
            # This will send the actual error (like a missing column) to your screen
            return JsonResponse(
                {"status": "error", "message": f"Database Error: {str(e)}"}
            )

    return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)


def AssignTeacherCourse(request):
    if (
        request.method == "POST"
        and request.headers.get("x-requested-with") == "XMLHttpRequest"
    ):
        print("In the function AssignTeacherCourse")
        course_id = request.POST.get("course_id")
        teacher_id = request.POST.get("teacher_id")

        if not course_id or not teacher_id:
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Both Course ID and Teacher ID are required.",
                }
            )

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*) FROM TeacherCourses 
                WHERE Teacher_Id = %s AND Course_Id = %s
            """,
                [teacher_id, course_id],
            )
            exists = cursor.fetchone()[0]

            if exists > 0:
                print("Duplicate entry: Record already exists")
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Duplicate entry: Record already exists",
                    }
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO TeacherCourses (Teacher_Id, Course_Id)
                    VALUES (%s, %s)
                """,
                    [teacher_id, course_id],
                )

                if cursor.rowcount == 1:
                    print("Record inserted successfully")
                    return JsonResponse(
                        {"status": "success", "message": "Record inserted successfully"}
                    )
                else:
                    print("Insertion failed")
                    return JsonResponse(
                        {"status": "error", "message": "Failed to insert the record"}
                    )

    return JsonResponse({"status": "error", "message": "Invalid request method."})


def AddStudentCourse3(request):
    return render(
        request,
        "pages/AddStudentCourse.html",
        {
            "messages": messages.get_messages(request),
        },
    )


def upload_media(request):
    if request.method == "POST" and request.FILES["file"]:
        uploaded_file = request.FILES["file"]

        uploads_dir = os.path.join(settings.MEDIA_ROOT, "uploads")

        if not os.path.exists(uploads_dir):
            os.makedirs(uploads_dir)

        file_name = uploaded_file.name
        file_path = os.path.join(uploads_dir, file_name)

        with open(file_path, "wb+") as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

        file_type = None
        if file_name.lower().endswith(("jpg", "jpeg", "png", "gif")):
            file_type = "image"
        elif file_name.lower().endswith(("mp4", "avi", "mov")):
            file_type = "video"
        elif file_name.lower().endswith("pdf"):
            file_type = "pdf"

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO MediaFiles (file_path, file_type, uploaded_at)
                VALUES (%s, %s, GETDATE())
            """,
                ["/media/uploads/" + file_name, file_type],
            )

        return redirect("media_list")

    return render(request, "upload_media.html")


def media_list(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, file_path, file_type FROM MediaFiles")
        media_records = cursor.fetchall()

    return render(request, "pages/media_list.html", {"media_records": media_records})


def Addannouncements(request):
    if (
        request.method == "POST"
        and request.headers.get("X-Requested-With") == "XMLHttpRequest"
    ):
        try:
            publisher_name = request.POST.get("publisher_name")
            description = request.POST.get("description")
            now = datetime.now()
            admin_image = b""  # Placeholder binary for image

            pdf_file = None
            video_file = None
            fs = FileSystemStorage()

            if "pdf_file" in request.FILES:
                pdf_file_upload = request.FILES["pdf_file"]
                pdf_filename = fs.save(pdf_file_upload.name, pdf_file_upload)
                with open(fs.path(pdf_filename), "rb") as pdf:
                    pdf_file = pdf.read()

            if "video_file" in request.FILES:
                video_file_upload = request.FILES["video_file"]
                video_filename = fs.save(video_file_upload.name, video_file_upload)
                with open(fs.path(video_filename), "rb") as video:
                    video_file = video.read()

            with connection.cursor() as cursor:
                # Insert including date_posted
                cursor.execute(
                    """
                    INSERT INTO Announcements (publisher_name, description, publisher_image, pdf_file, video_file, Admin_ID, date_posted)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                    [
                        publisher_name,
                        description,
                        admin_image,
                        pdf_file,
                        video_file,
                        1,
                        now,
                    ],
                )

                announcement_id = cursor.lastrowid

                # Create Read Status records
                cursor.execute("SELECT Teacher_Id FROM TeacherInformation")
                for t_id in [row[0] for row in cursor.fetchall()]:
                    cursor.execute(
                        "INSERT INTO AnnouncementReadStatus (Teacher_Id, AnnouncementId, IsRead) VALUES (%s, %s, 0)",
                        [t_id, announcement_id],
                    )

                cursor.execute("SELECT Student_ID FROM StudentInformation")
                for s_id in [row[0] for row in cursor.fetchall()]:
                    cursor.execute(
                        "INSERT INTO AnnouncementReadStatus (Student_ID, AnnouncementId, IsRead) VALUES (%s, %s, 0)",
                        [s_id, announcement_id],
                    )

            return JsonResponse(
                {"message": "Announcement added successfully!"}, status=200
            )
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method."}, status=400)


def serve_announcement_file(request, announcement_id, file_type):
    with connection.cursor() as cursor:
        if file_type == "pdf":
            cursor.execute(
                "SELECT pdf_file FROM Announcements WHERE id = %s", [announcement_id]
            )
            content_type = "application/pdf"
            filename = f"announcement_{announcement_id}.pdf"
        else:
            cursor.execute(
                "SELECT video_file FROM Announcements WHERE id = %s", [announcement_id]
            )
            content_type = "video/mp4"  # Or video/webm
            filename = f"video_{announcement_id}.mp4"

        record = cursor.fetchone()

    if record and record[0]:
        response = HttpResponse(record[0], content_type=content_type)
        # 'inline' opens in browser, 'attachment' forces download
        response["description-Disposition"] = f'inline; filename="{filename}"'
        return response

    raise Http404("File not found")


def AddAnnouncementsCourse(request, Teacher_Id, Course_Id):
    if (
        request.method == "POST"
        and request.headers.get("X-Requested-With") == "XMLHttpRequest"
    ):
        try:
            print("In the function")
            description = request.POST.get("description")

            TeacherID = Teacher_Id
            with connection.cursor() as cursor:
                cursor.execute(
                    """SELECT Teacher_Image, Teacher_Name FROM TeacherInformation WHERE Teacher_Id = %s
                """,
                    [TeacherID],
                )
                Record = cursor.fetchone()

            Teacher_image = Record[0] if Record and Record[0] is not None else None
            Teacher_Name = Record[1]

            pdf_file = None
            video_file = None

            if "pdf_file" in request.FILES:
                pdf_file_upload = request.FILES["pdf_file"]
                fs = FileSystemStorage()
                pdf_filename = fs.save(pdf_file_upload.name, pdf_file_upload)
                pdf_path = fs.path(pdf_filename)
                with open(pdf_path, "rb") as pdf:
                    pdf_file = pdf.read()

            if "video_file" in request.FILES:
                video_file_upload = request.FILES["video_file"]
                video_filename = fs.save(video_file_upload.name, video_file_upload)
                video_path = fs.path(video_filename)
                with open(video_path, "rb") as video:
                    video_file = video.read()

            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO CourseAnnouncement (publisher_name, description, publisher_image, pdf_file, video_file, Teacher_Id, course_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                    [
                        Teacher_Name,
                        description,
                        Teacher_image,
                        pdf_file,
                        video_file,
                        TeacherID,
                        Course_Id,
                    ],
                )
                cursor.execute(
                    " SELECT TOP 1 id  FROM CourseAnnouncement ORDER BY id DESC "
                )
                result = cursor.fetchone()
                announcement_id = result[0]

            with connection.cursor() as cursor:
                cursor.execute("SELECT Student_ID FROM StudentInformation")
                student_ids = [row[0] for row in cursor.fetchall()]

            for student_id in student_ids:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO CourseAnnouncementReadStatus (Student_ID, AnnouncementId, IsRead, ReadDate, course_id)
                        VALUES (%s, %s, 0, NULL, %s)
                    """,
                        [student_id, announcement_id, Course_Id],
                    )

            return JsonResponse(
                {"message": "Announcement added successfully!"}, status=200
            )

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method or type."}, status=400)


def course_list(request, Student_ID):
    with connection.cursor() as cursor:
        # Use Student_ID to filter the courses so students only see their own classes
        cursor.execute(
            """
            SELECT c.course_id, c.course_name, c.course_level, c.image_url 
            FROM Courses c
            INNER JOIN StudentCourses sc ON c.course_id = sc.course_id
            WHERE sc.Student_ID = %s
        """,
            [Student_ID],
        )
        courses = cursor.fetchall()

    if courses:
        # Pass StudentID back to the template so your "Back" button works
        return render(
            request,
            "pages/course_list.html",
            {"courses": courses, "StudentID": Student_ID},
        )
    else:
        return render(
            request,
            "pages/course_list.html",
            {
                "courses": [],
                "StudentID": Student_ID,
                "message": "You are not enrolled in any courses yet.",
            },
        )


def announcement_list(request, ID):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                id,  
                publisher_name, 
                description, 
                strftime('%d-%m-%Y', COALESCE(date_posted, 'now')) AS formatted_date,
                publisher_image,
                pdf_file,  
                video_file 
            FROM Announcements
            ORDER BY id DESC
        """)
        AnnouncementRecord = cursor.fetchall()

        # Mark as read for this specific student
        cursor.execute(
            """
            UPDATE AnnouncementReadStatus
            SET IsRead = 1, ReadDate = %s 
            WHERE Student_ID = %s AND IsRead = 0
        """,
            [datetime.now(), ID],
        )

    announcements = []
    for record in AnnouncementRecord:
        # Match keys to the variables in your HTML Template
        announcements.append(
            {
                "id": record[0],
                "publisher": record[1],  # Matches {{ announcement.publisher }}
                "content": record[2],  # Matches {{ announcement.content }}
                "publish_date": record[3],  # Matches {{ announcement.publish_date }}
                "publisher_image": (
                    base64.b64encode(record[4]).decode("utf-8") if record[4] else None
                ),
                "pdf_file": (
                    base64.b64encode(record[5]).decode("utf-8") if record[5] else None
                ),
                "video_file": (
                    base64.b64encode(record[6]).decode("utf-8") if record[6] else None
                ),
            }
        )

    context = {"announcements": announcements, "StudentID": ID}

    return render(request, "pages/announcement_list.html", context)


def delete_announcement(request, announcement_id):
    with connection.cursor() as cursor:
        # Delete read statuses first (Foreign Key constraint)
        cursor.execute(
            "DELETE FROM AnnouncementReadStatus WHERE AnnouncementId = %s",
            [announcement_id],
        )
        # Delete the announcement
        cursor.execute("DELETE FROM Announcements WHERE id = %s", [announcement_id])

    messages.success(request, "Announcement deleted successfully!")
    return redirect("announcements2")


# 2. Update Announcement
def update_announcement(request, announcement_id):
    # Fetch current data
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT id, publisher_name, description FROM Announcements WHERE id = %s",
            [announcement_id],
        )
        record = cursor.fetchone()

    if not record:
        return redirect("announcement_list2")

    announcement = {
        "id": record[0],
        "publisher_name": record[1],
        "description": record[2],
    }

    if request.method == "POST":
        publisher_name = request.POST.get("publisher_name")
        description = request.POST.get("description")
        pdf_file = request.FILES.get("pdf_file")
        video_file = request.FILES.get("video_file")

        with connection.cursor() as cursor:
            # Update text fields
            cursor.execute(
                """
                UPDATE Announcements 
                SET publisher_name = %s, description = %s 
                WHERE id = %s
            """,
                [publisher_name, description, announcement_id],
            )

            # Update PDF only if a new one is uploaded
            if pdf_file:
                cursor.execute(
                    "UPDATE Announcements SET pdf_file = %s WHERE id = %s",
                    [pdf_file.read(), announcement_id],
                )

            # Update Video only if a new one is uploaded
            if video_file:
                cursor.execute(
                    "UPDATE Announcements SET video_file = %s WHERE id = %s",
                    [video_file.read(), announcement_id],
                )

        messages.success(request, "Announcement updated successfully!")
        return redirect("announcement_list2")

    return render(
        request, "pages/UpdateAnnouncement.html", {"announcement": announcement}
    )


def announcement_list2(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, publisher_name, description, 
                   strftime('%d-%m-%Y', COALESCE(date_posted, 'now')) AS date_posted,
                   publisher_image, pdf_file, video_file
            FROM Announcements ORDER BY id DESC
        """)
        rows = cursor.fetchall()

    announcements = []
    for record in rows:
        # Match these keys to your HTML variables
        announcements.append(
            {
                "id": record[0],
                "publisher": record[1],  # Matches {{ announcement.publisher }}
                "content": record[2],  # Matches {{ announcement.content }}
                "publish_date": record[3],  # Matches {{ announcement.publish_date }}
                "publisher_image": (
                    base64.b64encode(record[4]).decode("utf-8") if record[4] else None
                ),
                "pdf_file": (
                    base64.b64encode(record[5]).decode("utf-8") if record[5] else None
                ),
                "video_file": (
                    base64.b64encode(record[6]).decode("utf-8") if record[6] else None
                ),
            }
        )

    return render(
        request, "pages/announcement_list.html", {"announcements": announcements}
    )


def CourseAnnouncement(request, StudentID, Course_Id):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT 
                id, 
                publisher_name, 
                description, 
                CONCAT(LEFT(DATENAME(MONTH, date_posted), 3), ' ', DAY(date_posted), ' ', YEAR(date_posted)) AS date_posted,
                publisher_image,
                pdf_file,  -- Fetch the PDF column here
                video_file -- Fetch the video column here
            FROM 
                CourseAnnouncement WHERE course_id = %s 
            ORDER BY 
                id DESC
        """,
            [Course_Id],
        )
        AnnouncementRecord = cursor.fetchall()

        cursor.execute(
            """
                update CourseAnnouncementReadStatus
                set IsRead = 1  where Student_ID = %s AND course_id = %s
            """,
            [StudentID, Course_Id],
        )

    announcements = []
    for record in AnnouncementRecord:
        image_data = None
        if record[4]:
            image_data = base64.b64encode(record[4]).decode("utf-8")

        pdf_data = None
        if record[5]:
            pdf_data = base64.b64encode(record[5]).decode("utf-8")

        video_data = None
        if record[6]:
            video_data = base64.b64encode(record[6]).decode("utf-8")

        announcements.append(
            {
                "id": record[0],
                "publisher_name": record[1],
                "description": record[2],
                "date_posted": record[3],
                "publisher_image": image_data,
                "pdf_file": pdf_data,
                "video_file": video_data,
            }
        )

    return render(
        request, "pages/CourseAnnouncement.html", {"announcements": announcements}
    )


def upload_assignment(request, Teacher_Id, Course_Id):
    if request.method == "POST":
        # 1. Extract data from the POST request
        file = request.FILES["fileInput"]
        description = request.POST["description"]
        deadline_date = request.POST["deadlineDate"]
        deadline_hour = request.POST["deadlineHour"]
        deadline_minute = request.POST["deadlineMinute"]
        TotalMark = request.POST["TotalMark"]

        # 2. Format the Date and Deadline string
        current_date = datetime.now()
        UploadDate = str(current_date.strftime("%b %d"))
        # Formatting deadline as 'YYYY-MM-DD HH:MM:SS'
        deadline = f"{deadline_date} {deadline_hour}:{deadline_minute}:00"

        with connection.cursor() as cursor:
            # 3. Fetch the Teacher's Profile Image
            cursor.execute(
                """
                SELECT Teacher_Image FROM TeacherInformation 
                WHERE Teacher_Id = %s
            """,
                [Teacher_Id],
            )
            Record = cursor.fetchone()  # fetchone is cleaner here than fetchall
            PublisherImage = Record[0] if Record and Record[0] else None

            # 4. Calculate the Assignment Number for this course
            cursor.execute(
                """
                SELECT COUNT(*) FROM Assignments 
                WHERE course_id = %s
            """,
                [Course_Id],
            )
            CountRecord = cursor.fetchone()
            Num = (CountRecord[0] + 1) if CountRecord else 1

            # 5. Insert the new assignment including the 'Flag' column
            # We add 'Flag' at the end to satisfy the NOT NULL constraint
            sql = """
                INSERT INTO Assignments (
                    FileContent, DescriptionContent, DeadlineDate, 
                    AssignementNumber, course_id, Teacher_Id, 
                    PublisherImage, CreatedAt, TotalMark, Flag
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            cursor.execute(
                sql,
                [
                    file.read(),  # The PDF binary data
                    description,  # Text description
                    deadline,  # Formatted date/time string
                    Num,  # Assignment #1, #2, etc.
                    Course_Id,  # Foreign Key to Course
                    Teacher_Id,  # Foreign Key to Teacher
                    PublisherImage,  # Teacher's profile pic
                    UploadDate,  # Date string (e.g., 'Dec 17')
                    TotalMark,  # The point value
                    1,  # Flag: 1 means Active/Visible
                ],
            )

        return JsonResponse(
            {"success": True, "message": "Assignment uploaded successfully!"}
        )

    return JsonResponse({"success": False, "message": "Invalid request method."})


def HomeWork(request, Course_ID, StudentID):

    assignment_list = []
    Student_data = []
    now = datetime.now()

    with connection.cursor() as cursor:
        # 1. FETCH STUDENT DATA SAFELY
        cursor.execute(
            """
            SELECT Student_Name, Student_Image, Student_ID
            FROM StudentInformation
            WHERE Student_ID = %s
        """,
            [StudentID],
        )
        StudentRecord = cursor.fetchall()
        if not StudentRecord:
            return HttpResponse(
                "Error: Student profile not found. Please ensure the Student ID is correct."
            )
        for Record in StudentRecord:
            # Check if image exists and is binary (bytes) before encoding
            img_base64 = ""
            if Record[1] and isinstance(Record[1], bytes):
                img_base64 = base64.b64encode(Record[1]).decode("utf-8")
            Student_data.append(
                {
                    "StudentName": Record[0],
                    "StudentImage": img_base64,
                    "StudentID": Record[2],
                    "CourseID": Course_ID,
                }
            )
        cursor.execute(
            """
            SELECT course_name
            FROM Courses
            WHERE course_id = %s
        """,
            [Course_ID],
        )
        CourseRecord = cursor.fetchone()
        CourseName = CourseRecord[0] if CourseRecord else "Unknown Course"
        cursor.execute(
            """
            SELECT
                FileContent, DescriptionContent, DeadlineDate,
                AssignementNumber, PublisherImage, CreatedAt,
                AssignmentId, Teacher_Id, Flag      
            FROM Assignments
            WHERE course_id = %s          
        """,
            [Course_ID],
        )
        assignments = cursor.fetchall()
        # 4. PROCESS EACH ASSIGNMENT
        for record in assignments:
            # Safety checks for binary fields (PDF and Teacher Image)
            pdf_data = None
            if record[0] and isinstance(record[0], bytes):
                pdf_data = base64.b64encode(record[0]).decode("utf-8")
            publisher_image = None
            if record[4] and isinstance(record[4], bytes):
                publisher_image = base64.b64encode(record[4]).decode("utf-8")
            # Fetch Teacher Name for this specific assignment
            cursor.execute(
                """
                SELECT Teacher_Name FROM TeacherInformation WHERE Teacher_Id = %s

            """,
                [record[7]],
            )

            TeacherRecord = cursor.fetchone()
            TeacherName = TeacherRecord[0] if TeacherRecord else "Unknown Teacher"
            # Check if this student has already submitted this specific assignment
            cursor.execute(
                """
                SELECT Flag FROM SubmittedAssignmentFlag
                WHERE Student_ID = %s AND AssignmentId = %s
            """,
                [StudentID, record[6]],
            )

            flag_result = cursor.fetchone()
            Flag = flag_result[0] if flag_result else 0

            deadline_date = record[2]
            deadline_passed = False
            if deadline_date:
                # Ensure it's a datetime object before comparison
                if isinstance(deadline_date, str):
                    try:
                        deadline_date = datetime.strptime(
                            deadline_date, "%Y-%m-%d %H:%M:%S"
                        )
                    except ValueError:
                        deadline_date = datetime.strptime(deadline_date, "%Y-%m-%d")
                deadline_passed = deadline_date < now

            assignment_list.append(
                {
                    "File_Content": pdf_data,
                    "Description": record[1],
                    "Deadline_Date": deadline_date,
                    "Assignement_Number": record[3],
                    "PublisherImage": publisher_image,
                    "DateOfPublish": record[5],
                    "Deadline_Passed": deadline_passed,
                    "AssignmentID": record[6],
                    "TeacherName": TeacherName,
                    "CourseID": Course_ID,
                    "StudentID": StudentID,
                    "CourseName": CourseName,
                    "Flag": Flag,
                }
            )

    context = {
        "assignments": assignment_list,
        "StudentRecord": Student_data,
    }
    return render(request, "pages/HomeWork.html", context)


@csrf_exempt
def HomeworkDelivered(request):
    if request.method == "POST":
        student_id = request.POST.get("student_id")
        course_id = request.POST.get("course_id")
        assignment_id = request.POST.get("assignment_id")
        file = request.FILES.get("file")
        BinaryFile = file.read()

        print("CourseID, StudentID: ", course_id, student_id)
        print("The assignment id = ", assignment_id)

        check_query = """
            SELECT COUNT(*) FROM HomeworkDelivered 
            WHERE course_id = %s AND Student_ID = %s AND AssignmentId = %s;
        """

        with connection.cursor() as cursor:
            cursor.execute(check_query, [course_id, student_id, assignment_id])
            result = cursor.fetchone()
            record_exists = result[0] > 0

        if record_exists:
            update_query = update_query = """
                UPDATE HomeworkDelivered
                SET FileContent = %s, DeliveredDate = CURRENT_TIMESTAMP
                WHERE course_id = %s AND Student_ID = %s AND AssignmentId = %s;
            """
            with connection.cursor() as cursor:
                cursor.execute(
                    update_query, [BinaryFile, course_id, student_id, assignment_id]
                )

            message = "File updated successfully!"
        else:
            insert_query = """
                INSERT INTO HomeworkDelivered (course_id, Student_ID, AssignmentId, DeliveredDate, FileContent, AssignmentNumber, TotalMark, Flag)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP, %s, %s, %s, 0);
            """
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM Assignments")
                result = cursor.fetchone()
                AssignmentNumber = result[0]
                cursor.execute(
                    "SELECT TotalMark FROM Assignments WHERE AssignmentId = %s ",
                    [assignment_id],
                )
                result = cursor.fetchone()
                TotalMark = result[0]
                cursor.execute(
                    insert_query,
                    [
                        course_id,
                        student_id,
                        assignment_id,
                        BinaryFile,
                        AssignmentNumber,
                        TotalMark,
                    ],
                )

                cursor.execute(
                    """
                INSERT INTO SubmittedAssignmentFlag (AssignmentId, Flag, course_id, Student_ID)
                Values(%s, 1, %s, %s)
            """,
                    [assignment_id, course_id, student_id],
                )

            message = "Homework submitted successfully!"

        return JsonResponse(
            {
                "message": message,
                "assignment_id": assignment_id,
                "student_id": student_id,
                "file_name": file.name,
            }
        )

    return JsonResponse({"error": "Invalid request method"}, status=405)


def Grade(request, Course_ID, StudentID):
    Student_data = []
    AssignmentGrades_data = []
    QuizGrades_data = []

    with connection.cursor() as cursor:
        # 1. Fetch Student Info
        cursor.execute(
            """
            SELECT Student_Name, Student_Image, Student_ID
            FROM StudentInformation
            WHERE Student_ID = %s 
        """,
            [StudentID],
        )
        student_raw = cursor.fetchall()

        if not student_raw:
            return HttpResponse("Student profile not found.")

        for Record in student_raw:
            img_base64 = ""
            if Record[1] and isinstance(Record[1], bytes):
                img_base64 = base64.b64encode(Record[1]).decode("utf-8")

            Student_data.append(
                {
                    "StudentName": Record[0],
                    "StudentImage": img_base64,
                    "StudentID": Record[2],
                }
            )

        # 2. Fetch Course Name
        cursor.execute(
            "SELECT course_name FROM Courses WHERE course_id = %s", [Course_ID]
        )
        course_res = cursor.fetchone()
        course_name = course_res[0] if course_res else "Unknown Course"

        # 3. Fetch Homework Grades
        cursor.execute(
            """
            SELECT AssignmentNumber, MarksObtained, TotalMarks FROM HomeWorkGrades
            WHERE Student_ID = %s AND course_id = %s
            ORDER BY AssignmentNumber ASC;
        """,
            [StudentID, Course_ID],
        )
        for row in cursor.fetchall():
            AssignmentGrades_data.append(
                {
                    "AssignmentNumber": row[0],
                    "MarksObtained": row[1],
                    "TotalMarks": row[2],
                }
            )

        # 4. Fetch Quiz Grades - UPDATED WITH JOIN
        cursor.execute(
            """
            SELECT qg.QuizNumber, SUM(qg.MarksObtained), SUM(qg.TotalMarks)
            FROM QuizGrades qg
            INNER JOIN Quizzes q ON qg.QuizNumber = q.QuizNumber AND qg.CourseID = q.course_id
            WHERE qg.StudentID = %s AND qg.CourseID = %s
            GROUP BY qg.QuizNumber
            ORDER BY qg.QuizNumber ASC;
        """,
            [StudentID, Course_ID],
        )
        for row in cursor.fetchall():
            QuizGrades_data.append(
                {"QuizNumber": row[0], "MarksObtained": row[1], "TotalMarks": row[2]}
            )

        # 5. Announcements
        cursor.execute(
            """
            SELECT COUNT(*) FROM CourseAnnouncementReadStatus
            WHERE Student_ID = %s AND IsRead = 0;
        """,
            [StudentID],
        )
        ann_res = cursor.fetchone()
        AnnouncementNum = ann_res[0] if ann_res else 0

    context = {
        "StudentRecord": Student_data,
        "CourseName": course_name,
        "CourseID": Course_ID,
        "AnnouncementNum": AnnouncementNum,
        "AssignmentGradeRecord": AssignmentGrades_data,
        "QuizGradeRecord": QuizGrades_data,
    }

    return render(request, "pages/Grade.html", context)


def CourseAttendanceHistory(request, Course_ID, StudentID):
    Attendance_data = []

    # 1. FETCH COURSE NAME USING DJANGO ORM (Much more reliable for finding the name)
    try:
        # This will use your 'Courses' table and 'course_id' primary key automatically
        course_obj = Courses.objects.get(course_id=Course_ID)
        course_name = course_obj.course_name
    except Courses.DoesNotExist:
        # If this hits, the ID in your URL does not exist in the 'Courses' table
        course_name = f"ID {Course_ID} Not Found"

    with connection.cursor() as cursor:
        # 2. Fetch Attendance Records using Raw SQL
        try:
            cursor.execute(
                """
                SELECT Student_ID_id, Attendance_Date, 
                       AttendanceTime, AttendanceStatus, LectureNumber 
                FROM AttendanceList 
                WHERE course_id_id = %s AND Student_ID_id = %s
                ORDER BY Attendance_Date DESC
            """,
                [Course_ID, StudentID],
            )

            AttendanceRecord = cursor.fetchall()

            for Record in AttendanceRecord:
                Attendance_data.append(
                    {
                        "Student_ID": Record[0],
                        "CourseName": course_name,
                        "Attendance_Date": Record[1],
                        "AttendanceTime": Record[2],
                        "AttendanceStatus": Record[3],  # Corrected Index
                        "LectureNumber": Record[4],  # Corrected Index
                    }
                )
        except Exception as e:
            print(f"DATABASE ERROR: {e}")

    context = {
        "AttendanceRecord": Attendance_data,
        "CourseName": course_name,
        "StudentID": StudentID,
        "CourseID": Course_ID,
    }

    return render(request, "pages/CourseAttendanceHistory.html", context)


def QuizInsertion(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            quiz_name = data.get("quiz_name")
            teacher_id = data.get("TeacherID")
            course_id = data.get("CourseID")
            questions_data = data.get("questions")

            with transaction.atomic():
                # 1. Fetch Objects
                teacher = TeacherModel.objects.get(Teacher_Id=teacher_id)
                course = Courses.objects.get(course_id=course_id)

                # 2. Create the Quiz
                quiz_count = QuizModel.objects.filter(course=course).count()
                new_quiz = QuizModel.objects.create(
                    QuizName=quiz_name,
                    Teacher=teacher,
                    course=course,
                    QuizNumber=quiz_count + 1,
                )

                # 3. Create Questions & Options
                for q_item in questions_data:
                    new_question = QuestionModel.objects.create(
                        Quiz=new_quiz,
                        QuestionText=q_item.get("text"),
                        QuestionType=q_item.get("type"),
                        Marks=q_item.get("mark"),
                    )

                    if q_item.get("type") == "mcq":
                        options = q_item.get("options", [])
                        try:
                            correct_idx = int(q_item.get("correct_option", -1))
                        except:
                            correct_idx = -1

                        for i, opt_text in enumerate(options):
                            OptionModel.objects.create(
                                Question=new_question,
                                OptionText=opt_text.strip(),
                                IsCorrect=(i == correct_idx),
                            )

                # 4. Enroll Students into the TakeStatus table
                all_students = StudentInformation.objects.all()
                for student in all_students:
                    # Using the exact class name from your Traceback
                    QuizTakeStatus.objects.create(
                        Student_ID=student.Student_ID,
                        Quiz=new_quiz,
                        IsTaken=0,
                        course_id=course_id,
                    )

            return JsonResponse({"message": "Quiz created successfully!"}, status=200)

        except Exception as e:
            # This will show you exactly which field is causing trouble if it fails again
            print(f"CRITICAL ERROR: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid method"}, status=400)


def take_quiz(request, StudentID, CourseID):
    Flag = 0
    quiz_name = "No Quiz Available"
    question_data = []

    status_record = (
        QuizTakeStatus.objects.filter(
            Student_ID=StudentID, course_id=CourseID, IsTaken=0
        )
        .select_related("Quiz")
        .first()
    )

    if status_record:
        quiz = status_record.Quiz
        quiz_name = quiz.QuizName
        questions = QuestionModel.objects.filter(Quiz=quiz)

        for q in questions:
            options = OptionModel.objects.filter(Question=q).values_list(
                "OptionID", "OptionText"
            )
            question_data.append(
                {
                    "id": q.QuestionID,
                    "text": q.QuestionText,
                    "type": q.QuestionType,
                    "marks": q.Marks or 0,
                    "options": list(options),
                }
            )
    else:
        # Check if already submitted
        if StudentAnswers.objects.filter(
            StudentID=StudentID, Quiz__course_id=CourseID
        ).exists():
            Flag = 1

    context = {
        "StudentID": StudentID,
        "quiz_name": quiz_name,
        "questions": question_data,
        "Flag": Flag,
        "CourseID": CourseID,
    }
    return render(request, "pages/StudentQuiz.html", context)


def submit_quiz(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            answers = data.get("answers", {})
            student_id = data.get("studentId")

            if not answers:
                return JsonResponse({"error": "No answers received."}, status=400)

            with transaction.atomic():
                # Identify Quiz from the first question
                first_q_id = list(answers.keys())[0]
                sample_q = QuestionModel.objects.get(QuestionID=first_q_id)
                current_quiz = sample_q.Quiz

                for q_id, student_ans in answers.items():
                    question = QuestionModel.objects.get(QuestionID=q_id)
                    # Use the question type defined in DB rather than guessing with .isdigit()
                    is_mcq = question.QuestionType.lower() == "mcq"

                    StudentAnswers.objects.create(
                        StudentID=student_id,
                        Quiz=current_quiz,
                        Question=question,
                        AnswerType="mcq" if is_mcq else "written",
                        StudentAnswer=None if is_mcq else str(student_ans),
                        SelectedOption=int(student_ans) if is_mcq else None,
                        Flag=0,  # Start at 0 marks until graded
                    )

                QuizTakeStatus.objects.filter(
                    Student_ID=student_id, Quiz=current_quiz
                ).update(IsTaken=1, TakenDate=timezone.now())

            return JsonResponse({"message": "Quiz submitted successfully!"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid method"}, status=400)


def quiz_delivered(request, CourseID):
    students_dict = {}
    questions = {}
    selected_quiz_id = request.GET.get("quiz_id")

    with connection.cursor() as cursor:
        # A. Get Quizzes
        cursor.execute(
            "SELECT QuizID, QuizNumber FROM Quizzes WHERE course_id = %s ORDER BY QuizID DESC",
            [CourseID],
        )
        all_quizzes = [{"id": r[0], "number": r[1]} for r in cursor.fetchall()]
        if not all_quizzes:
            return HttpResponse("No quizzes found.")

        if selected_quiz_id:
            cursor.execute(
                "SELECT QuizID, QuizNumber FROM Quizzes WHERE QuizID = %s",
                [selected_quiz_id],
            )
        else:
            cursor.execute(
                "SELECT QuizID, QuizNumber FROM Quizzes WHERE course_id = %s ORDER BY QuizID DESC LIMIT 1",
                [CourseID],
            )
        quiz_id, quiz_number = cursor.fetchone()

        # B. Fetch Questions
        cursor.execute(
            "SELECT QuestionID, QuestionText, Marks FROM Questions WHERE Quiz_id = %s",
            [quiz_id],
        )
        for q_row in cursor.fetchall():
            questions[q_row[0]] = {"text": q_row[1], "marks": q_row[2] or 0}

        # C. Fetch Answers JOINED with the saved Grades table
        # We use COALESCE(g.MarksObtained, 0) to get the saved grade or 0 if not graded yet
        cursor.execute(
            """
            SELECT 
                sa.StudentID, 
                si.Student_Name, 
                sa.Question_id, 
                sa.AnswerType, 
                sa.StudentAnswer, 
                o.OptionText,
                COALESCE(g.MarksObtained, 0) as SavedMark
            FROM StudentAnswers sa
            JOIN StudentInformation si ON sa.StudentID = si.Student_ID
            LEFT JOIN Options o ON sa.SelectedOption = o.OptionID
            LEFT JOIN QuizGrades g ON sa.StudentID = g.StudentID AND sa.Question_id = g.QuestionID
            WHERE sa.Quiz_id = %s
        """,
            [quiz_id],
        )
        raw_answers = cursor.fetchall()

    # 2. Group Data
    for row in raw_answers:
        sid = row[0]
        if sid not in students_dict:
            students_dict[sid] = {"name": row[1], "answers": {}}

        q_id = row[2]
        ans_type = str(row[3]).lower() if row[3] else ""

        if "written" in ans_type:
            display = row[4] if row[4] else "No answer"
        else:
            display = f"Selected: {row[5]}" if row[5] else "No selection"

        students_dict[sid]["answers"][q_id] = {
            "display": display,
            "current_marks": row[6],  # This is now pulling from QuizGrades!
        }

    # 3. Totals
    for sid, data in students_dict.items():
        data["current_total"] = sum(
            int(a["current_marks"]) for a in data["answers"].values()
        )
        data["max_total"] = sum(int(q["marks"]) for q in questions.values())

    return render(
        request,
        "pages/quiz_delivered.html",
        {
            "all_quizzes": all_quizzes,
            "current_quiz_id": quiz_id,
            "quiz_number": quiz_number,
            "questions": questions,
            "students": students_dict,
            "CourseID": CourseID,
        },
    )


def confirm_grades(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            student_id = data.get("studentId")
            grades = data.get("grades", {})

            with connection.cursor() as cursor:
                for question_id, marks_obtained in grades.items():
                    # 1. Get Marks and the linked Quiz ID from the question
                    cursor.execute(
                        "SELECT Marks, Quiz_id FROM Questions WHERE QuestionID = %s",
                        [question_id],
                    )
                    q_data = cursor.fetchone()
                    if not q_data:
                        continue

                    total_marks, quiz_db_id = q_data

                    # 2. Get QuizNumber and CourseID from the Quizzes table
                    # Note: Your Quizzes model uses 'course_id' as the FK column
                    cursor.execute(
                        "SELECT QuizNumber, course_id FROM Quizzes WHERE QuizID = %s",
                        [quiz_db_id],
                    )
                    quiz_data = cursor.fetchone()
                    if not quiz_data:
                        continue

                    quiz_number, course_id = quiz_data

                    # 3. Check if record exists
                    cursor.execute(
                        """
                        SELECT COUNT(*) FROM QuizGrades 
                        WHERE StudentID = %s AND QuestionID = %s
                    """,
                        [student_id, question_id],
                    )

                    exists = cursor.fetchone()[0] > 0

                    if exists:
                        # Update existing record
                        cursor.execute(
                            """
                            UPDATE QuizGrades 
                            SET MarksObtained = %s, TotalMarks = %s, QuizNumber = %s, CourseID = %s
                            WHERE StudentID = %s AND QuestionID = %s
                        """,
                            [
                                marks_obtained,
                                total_marks,
                                quiz_number,
                                course_id,
                                student_id,
                                question_id,
                            ],
                        )
                    else:
                        # Insert new record using the correct columns from your model
                        cursor.execute(
                            """
                            INSERT INTO QuizGrades (StudentID, CourseID, QuizNumber, QuestionID, MarksObtained, TotalMarks) 
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                            [
                                student_id,
                                course_id,
                                quiz_number,
                                question_id,
                                marks_obtained,
                                total_marks,
                            ],
                        )

            return JsonResponse(
                {"message": "Grades confirmed successfully!"}, status=200
            )
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid method"}, status=405)


@csrf_exempt
def HomeWork_delivered(request, CourseID):
    with connection.cursor() as cursor:
        # 1. Fetch Course Info
        cursor.execute(
            """
            SELECT course_id, course_name, course_level 
            FROM Courses 
            WHERE course_id = %s
        """,
            [CourseID],
        )
        CourseRecord = cursor.fetchall()

        # 2. Fetch Submissions JOINED with their actual saved Grades
        # We use LEFT JOIN so we still see the submission even if it isn't graded yet
        cursor.execute(
            """
            SELECT 
                s.Student_Name, 
                h.Student_ID, 
                h.AssignmentNumber, 
                h.DeliveredDate, 
                h.TotalMark,
                h.id,
                g.MarksObtained  -- This is the saved grade [Index 6]
            FROM HomeworkDelivered h
            INNER JOIN StudentInformation s ON h.Student_ID = s.Student_ID
            LEFT JOIN HomeWorkGrades g ON h.Student_ID = g.Student_ID 
                AND h.course_id = g.course_id 
                AND h.AssignmentNumber = g.AssignmentNumber
            WHERE h.course_id = %s
            ORDER BY h.DeliveredDate DESC
        """,
            [CourseID],
        )
        Submissions = cursor.fetchall()

    return render(
        request,
        "pages/Homework3.html",
        {
            "CourseRecord": CourseRecord,
            "Submissions": Submissions,
            "CourseID": CourseID,
        },
    )


from django.views.decorators.clickjacking import xframe_options_exempt


@xframe_options_exempt
def ViewAssignmentFile(request, submission_id):
    with connection.cursor() as cursor:
        # Fetch the binary description from HomeworkDelivered table
        cursor.execute(
            "SELECT FileContent FROM HomeworkDelivered WHERE id = %s", [submission_id]
        )
        record = cursor.fetchone()

    if record and record[0]:
        # Return the binary data as a PDF response
        response = HttpResponse(record[0], content_type="application/pdf")
        # 'inline' tells the browser to try and show it inside the iframe
        response["description-Disposition"] = 'inline; filename="submission.pdf"'
        return response

    return HttpResponse("File not found.", status=404)


@csrf_exempt
def SaveAssignmentGrade(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            student_id = data.get("studentId")
            grade = data.get("grades")
            submission_id = data.get("AssignmentID")
            course_id = data.get("CourseID")
            total_mark = data.get("TotalMark")

            # --- NEW VALIDATION ---
            # Convert to float/int to compare values safely
            if float(grade) > float(total_mark):
                return JsonResponse(
                    {
                        "error": f"Invalid Grade: {grade} exceeds the maximum points ({total_mark})."
                    },
                    status=400,
                )
            # -----------------------

            if not all([student_id, grade, submission_id, course_id]):
                return JsonResponse(
                    {"error": "Missing required data fields"}, status=400
                )

            with connection.cursor() as cursor:
                # 1. Get the Assignment Number
                cursor.execute(
                    """
                    SELECT AssignmentNumber 
                    FROM HomeworkDelivered 
                    WHERE id = %s
                """,
                    [submission_id],
                )

                res = cursor.fetchone()
                if not res:
                    return JsonResponse(
                        {"error": "Submission record not found"}, status=404
                    )

                assign_num = res[0]

                # 2. Check if grade exists (Upsert Logic)
                cursor.execute(
                    """
                    SELECT id FROM HomeWorkGrades 
                    WHERE Student_ID = %s AND course_id = %s AND AssignmentNumber = %s
                """,
                    [student_id, course_id, assign_num],
                )

                existing_grade = cursor.fetchone()

                if existing_grade:
                    # UPDATE
                    cursor.execute(
                        """
                        UPDATE HomeWorkGrades 
                        SET MarksObtained = %s, TotalMarks = %s
                        WHERE id = %s
                    """,
                        [grade, total_mark, existing_grade[0]],
                    )
                else:
                    # INSERT
                    cursor.execute(
                        """
                        INSERT INTO HomeWorkGrades 
                        (Student_ID, course_id, AssignmentNumber, MarksObtained, TotalMarks)
                        VALUES (%s, %s, %s, %s, %s)
                    """,
                        [student_id, course_id, assign_num, grade, total_mark],
                    )

                # 3. Update Delivery Flag
                cursor.execute(
                    "UPDATE HomeworkDelivered SET Flag = 1 WHERE id = %s",
                    [submission_id],
                )

            return JsonResponse({"message": "Grade saved successfully!"}, status=200)

        except ValueError:
            return JsonResponse({"error": "Grade must be a number."}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request method"}, status=405)
