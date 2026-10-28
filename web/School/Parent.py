from django.db import connection
from django.shortcuts import render
from .security import verify_password, login_session


def Request(request):
    return render(request, "pages/ParentLogIn.html")


from django.db import connection
from django.shortcuts import redirect, render

from .security import login_session, verify_password


def _parent_context(parent_id):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT Parent_Name, Parent_ID, Parent_Image, Student_ID_id
            FROM ParentInformation WHERE Parent_ID = %s
        """,
            [parent_id],
        )
        row = cursor.fetchone()
        if not row:
            return None
        parent_name, pid, parent_image, student_id = row
        cursor.execute(
            """
            SELECT Student_Name, Student_Image, Student_ID
            FROM StudentInformation WHERE Student_ID = %s
        """,
            [student_id],
        )
        s = cursor.fetchone()
        cursor.execute(
            """
            SELECT c.course_id, c.course_name, c.course_level, c.image_url
            FROM Courses c
            INNER JOIN StudentCourses sc ON c.course_id = sc.course_id
            WHERE sc.Student_ID = %s
        """,
            [student_id],
        )
        courses = [
            {
                "CourseID": r[0],
                "CourseName": r[1],
                "Courselevel": r[2],
                "CourseImage": r[3],
            }
            for r in cursor.fetchall()
        ]
        cursor.execute(
            """
            SELECT COUNT(*) FROM CourseAnnouncementReadStatus
            WHERE Student_ID = %s AND IsRead = 0
        """,
            [student_id],
        )
        unread = cursor.fetchone()[0]
    return {
        "ParentRecord": [
            {"ParentName": parent_name, "ParentID": pid, "ParentImage": parent_image}
        ],
        "StudentRecord": [
            {
                "StudentName": s[0] if s else "Unknown",
                "StudentImage": s[1] if s else "",
                "StudentID": s[2] if s else 0,
            }
        ],
        "CourseRecord": courses,
        "AnnouncementNum": [[unread]],
    }


def LogInAccount(request):
    if request.method == "POST":
        typed_id = (request.POST.get("id") or "").strip()
        typed_password = request.POST.get("password") or ""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT Parent_ID, Student_ID_id, Passwordd
                FROM ParentInformation WHERE Parent_ID = %s
            """,
                [typed_id],
            )
            row = cursor.fetchone()
            if not row:
                return render(
                    request, "pages/ParentLogIn.html", {"error": "ID not found"}
                )
            parent_id, student_id, db_password = row
            ok, new_hash = verify_password(typed_password, db_password)
            if not ok:
                return render(
                    request, "pages/ParentLogIn.html", {"error": "Incorrect password"}
                )
            if new_hash:
                cursor.execute(
                    "UPDATE ParentInformation SET Passwordd = %s WHERE Parent_ID = %s",
                    [new_hash, parent_id],
                )
        login_session(request, "parent", parent_id, student_id=student_id)
        return redirect("ParentDashboard")
    return render(request, "pages/ParentLogIn.html")


def Dashboard(request):
    context = _parent_context(request.session.get("user_id"))
    if context is None:
        return redirect("ParentLogInPage")
    return render(request, "pages/Parent.html", context)
