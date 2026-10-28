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
from .views_teacher import CourseContent


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
