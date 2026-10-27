from django.db import connection
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib import messages as dj_messages
from .models import TeacherInformation
from .security import verify_password, login_session
from django.shortcuts import render, redirect


def activate_attendance_session(request, course_id):
    try:
        with connection.cursor() as cursor:
            # --- STEP 1: CLEAR OLD DATA FOR TODAY ---
            # This ensures that if you re-click 'Take Attendance', it resets the gate.
            cursor.execute(
                """
                DELETE FROM AttendanceList 
                WHERE Course_ID = %s AND Date = date('now', 'localtime')
            """,
                [course_id],
            )

            # --- STEP 2: FETCH STUDENTS ---
            cursor.execute(
                "SELECT Student_ID FROM StudentCourses WHERE course_id = %s",
                [course_id],
            )
            students = cursor.fetchall()

            if not students:
                return JsonResponse(
                    {"status": "error", "message": "No students enrolled"}
                )

            # --- STEP 3: INSERT FRESH 'ABSENT' SLOTS ---
            for student in students:
                cursor.execute(
                    """
                    INSERT INTO AttendanceList (Student_ID, Course_ID, Teacher_ID, Status, Date)
                    VALUES (%s, %s, %s, 'Absent', date('now', 'localtime'))
                """,
                    [student[0], course_id, 0],
                )

        return JsonResponse({"status": "success"})
    except Exception as e:
        print(f"Activation Error: {e}")
        return JsonResponse({"status": "error", "message": str(e)})


def deactivate_attendance_session(request, course_id):
    try:
        with connection.cursor() as cursor:
            # Change 'Absent' to 'Final_Absent' or something else.
            # As long as the status is NOT 'Absent', the student gate closes.
            cursor.execute(
                """
                UPDATE AttendanceList 
                SET Status = 'Official_Absent'
                WHERE Course_ID = %s AND Status = 'Absent' AND Date = date('now', 'localtime')
            """,
                [course_id],
            )

        return JsonResponse({"status": "success", "message": "Gate closed"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})


# --- 2. LOGIN & DASHBOARD ---
def Request(request):
    return render(request, "pages/TeacherLogIn.html")


def _teacher_context(teacher):
    course_data = []
    with connection.cursor() as cursor:
        search_term = f"%{teacher.Course_Handle.strip()}%"
        cursor.execute(
            """
            SELECT course_id, course_name, course_level, image_url
            FROM Courses
            WHERE UPPER(course_name) LIKE UPPER(%s)
        """,
            [search_term],
        )
        for r in cursor.fetchall():
            course_data.append(
                {
                    "CourseID": r[0],
                    "CourseName": r[1],
                    "Courselevel": r[2],
                    "CourseImage": r[3] if r[3] else "",
                }
            )
        cursor.execute(
            "SELECT COUNT(*) FROM AnnouncementReadStatus WHERE Teacher_Id = %s AND IsRead = 0",
            [teacher.Teacher_Id],
        )
        announcement_num = cursor.fetchone()[0]
    return {
        "AnnouncementNum": announcement_num,
        "TeacherRecord": [
            {
                "TeacherName": teacher.Teacher_Name,
                "TeacherImage": teacher.Teacher_Image,
                "TeacherID": teacher.Teacher_Id,
            }
        ],
        "CourseRecord": course_data,
    }


def LogInAccount(request):
    if request.method == "POST":
        teacher_id_input = request.POST.get("id", "").strip()
        password_input = request.POST.get("password", "").strip()
        try:
            teacher = TeacherInformation.objects.get(Teacher_Id=teacher_id_input)
        except (TeacherInformation.DoesNotExist, ValueError):
            dj_messages.error(request, "Instructor ID not found.")
            return render(request, "pages/TeacherLogIn.html")
        ok, new_hash = verify_password(password_input, teacher.Passwordd)
        if not ok:
            dj_messages.error(request, "Incorrect Password.")
            return render(request, "pages/TeacherLogIn.html")
        if new_hash:
            teacher.Passwordd = new_hash
            teacher.save(update_fields=["Passwordd"])
        login_session(request, "teacher", teacher.Teacher_Id)
        return redirect("TeacherDashboard")
    return render(request, "pages/TeacherLogIn.html")


def Dashboard(request):
    teacher = TeacherInformation.objects.filter(
        Teacher_Id=request.session.get("user_id")
    ).first()
    if teacher is None:
        return redirect("TeacherLogInPage")
    return render(request, "pages/Teacher.html", _teacher_context(teacher))
