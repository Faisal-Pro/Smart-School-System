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


def AddannouncementsPage(request):
    return render(request, "pages/add_announcement.html")


def AddAnnouncementsCoursePage(request, Teacher_Id, Course_Id):
    context = {"TeacherID": Teacher_Id, "CourseID": Course_Id}

    return render(request, "pages/AddCourseAnnouncement.html", context)


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
