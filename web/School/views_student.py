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
import base64
from django.db import connection
from django.shortcuts import render
from django.db import connection
from django.db import connection
from django.views.decorators.clickjacking import xframe_options_exempt


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
