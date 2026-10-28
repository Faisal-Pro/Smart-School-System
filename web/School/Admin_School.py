from django.contrib.auth import authenticate
from django.db import connection
from django.shortcuts import redirect, render

from .models import StudentInformation, TeacherInformation, ParentInformation, Courses
from .analytics_utils import get_student_risk_report
from .security import login_session

RISK_THRESHOLD = 60  # same limit as the 'Critical Intervention' label


def AdminLogin(request):
    error = None
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("username", "").strip(),
            password=request.POST.get("password", ""),
        )
        if user is not None and user.is_staff:
            login_session(request, "admin", user.pk)
            return redirect("DirectAdminPage")
        error = "Invalid username or password."
    return render(request, "pages/AdminLogIn.html", {"error": error})


def Logout(request):
    request.session.flush()
    return redirect("MainPage")


def _students_at_risk():
    """Number of students whose risk is critical in at least one course."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT DISTINCT Student_ID, course_id FROM StudentCourses")
        pairs = cursor.fetchall()
    at_risk = set()
    for student_id, course_id in pairs:
        if student_id in at_risk:
            continue
        try:
            report = get_student_risk_report(student_id, course_id)
        except Exception:
            continue
        if report["risk_score"] > RISK_THRESHOLD:
            at_risk.add(student_id)
    return len(at_risk)


def Request(request):
    context = {
        "total_students": StudentInformation.objects.count(),
        "total_teachers": TeacherInformation.objects.count(),
        "total_parents": ParentInformation.objects.count(),
        "total_courses": Courses.objects.count(),
        "students_at_risk": _students_at_risk(),
    }
    return render(request, "pages/AdminDashboard.html", context)
