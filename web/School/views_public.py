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
