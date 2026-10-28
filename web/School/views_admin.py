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


def add_course_Page(request):
    # Get the next ID automatically
    max_id = Courses.objects.aggregate(Max("course_id"))["course_id__max"]
    next_id = (max_id or 0) + 1
    return render(request, "pages/add_course.html", {"LastRecord": next_id})


def AddTeacherCoursPage(request):
    return render(request, "pages/AddTeacherCourse.html")


def AddStudentCourse(request):
    return render(request, "pages/AddStudentCourse.html")


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


def GenerateReportPage(request):
    return render(request, "pages/GenerateReport2.html")


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
