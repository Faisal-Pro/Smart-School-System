"""Role based access control for the whole site.

Every URL has a name (see urls.py). Each name is public, or allowed for
some roles: admin, teacher, student, parent. Anything not listed below is
admin-only, so a forgotten page is never open by accident.
"""

import logging

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import Resolver404, resolve

log = logging.getLogger("access")

SKIP_PREFIXES = ("/static/", "/media/", "/admin/", "/favicon.ico")

PUBLIC = {
    "MainPage",
    "ParentLogInPage",
    "ParentLogIn2",
    "StudentLogInPage",
    "StudentLogIn",
    "StudentLogIn2",
    "TeacherLogInPage",
    "TeacherLogIn2",
    "AdminLogIn",
    "Logout",
    "StudentFaceLoginPage",
    "announcements2",
    "serve_announcement_file",
}

RULES = {}


def _allow(roles, *names):
    for name in names:
        RULES[name] = set(roles)


_allow(
    {"teacher", "student", "parent", "admin"},
    "get_records",
    "CourseContent",
    "get_course_contents",
)

_allow(
    {"student", "parent", "admin"},
    "StudentSchedulePage",
    "StudentInformation",
    "CoursePageStudent",
    "course_list",
    "index2",
    "CourseAnnouncement",
    "HomeWork",
    "StudentDashboard",
    "Grade",
    "CourseAttendanceHistory",
    "FinalGrade",
)

_allow(
    {"student", "admin"},
    "take_quiz",
    "submit_quiz",
    "HomeworkDelivered",
    "RegisterFace",
    "CaptureFrame",
    "StudentFaceLogInPage",
    "SubmitAttendanceAI",
    "check_attendance_status",
)

_allow(
    {"teacher", "admin"},
    "UploadMaterialPage",
    "UploadMaterial",
    "CoursePage",
    "materials_view",
    "upload_material_view",
    "index3",
    "AddAnnouncementsCoursePage",
    "AddAnnouncementsCourse",
    "upload_assignment_Page",
    "upload_assignment",
    "DeleteMaterial",
    "UpdateMaterialPage",
    "UpdateMaterial",
    "ViewStudentsCourse",
    "quiz-insertion",
    "GenerateQuizPage",
    "quiz_delivered",
    "confirm_grades",
    "GenerateReport",
    "HomeWorkDelivered2",
    "TeacherSchedule",
    "GenerateGrades",
    "SaveAssignmentGrade",
    "SaveFinalGrade",
    "ViewAssignmentFile",
    "activate_attendance_session",
    "DeactivateAttendance",
    "get_attendance_history",
    "TeacherInformation",
)

_allow({"teacher", "student", "parent", "admin"}, "announcements")
_allow({"teacher"}, "TeacherDashboard")
_allow({"parent"}, "ParentDashboard")

# Not listed anywhere -> admin only (dashboard, add/view/update/delete ...).

STUDENT_KWARGS = {"Student_ID", "StudentID", "Student_Id", "student_id", "ID"}
TEACHER_KWARGS = {"Teacher_Id", "teacher_id", "Teacher_ID"}
# for these pages the teacher's own id arrives as ID
TEACHER_ID_URLS = {"announcements"}


def check_access(url_name, kwargs, session):
    """Return ('allow' | 'login' | 'forbidden', allowed_roles)."""
    if url_name in PUBLIC:
        return "allow", set()
    allowed = RULES.get(url_name, {"admin"})
    role = session.get("role")
    if not role:
        return "login", allowed
    if role not in allowed:
        return "forbidden", allowed
    if role == "student":
        own = session.get("user_id")
        for key in STUDENT_KWARGS & set(kwargs):
            if kwargs[key] != own:
                return "forbidden", allowed
    elif role == "parent":
        child = session.get("student_id")
        for key in STUDENT_KWARGS & set(kwargs):
            if kwargs[key] != child:
                return "forbidden", allowed
    elif role == "teacher":
        own = session.get("user_id")
        keys = TEACHER_KWARGS & set(kwargs)
        if url_name in TEACHER_ID_URLS:
            keys = keys | ({"ID"} & set(kwargs))
        for key in keys:
            if kwargs[key] != own:
                return "forbidden", allowed
    return "allow", allowed


def _login_target(allowed):
    if allowed == {"admin"}:
        return "AdminLogIn"
    if "student" in allowed:
        return "StudentLogInPage"
    if "teacher" in allowed:
        return "TeacherLogInPage"
    return "MainPage"


class AccessControlMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info
        if path.startswith(SKIP_PREFIXES):
            return self.get_response(request)
        try:
            match = resolve(path)
        except Resolver404:
            return self.get_response(request)

        decision, allowed = check_access(match.url_name, match.kwargs, request.session)
        if decision == "allow":
            return self.get_response(request)

        enforce = getattr(settings, "ACCESS_ENFORCE", True)
        log.warning(
            "[ACCESS] %s would be %s (url=%s, role=%s)",
            match.url_name,
            decision,
            path,
            request.session.get("role"),
        )
        if not enforce:
            return self.get_response(request)

        wants_json = (
            "application/json" in request.headers.get("Accept", "")
            or request.content_type == "application/json"
        )
        if decision == "login":
            if wants_json:
                return JsonResponse({"error": "login required"}, status=401)
            return redirect(_login_target(allowed))
        role = request.session.get("role")
        who = f"You are signed in as <b>{role}</b>." if role else "You are not signed in."
        html = (
            "<!doctype html><meta charset='utf-8'><title>Access denied</title>"
            "<body style='font-family:sans-serif;background:#f1f5f9;display:grid;"
            "place-items:center;min-height:100vh;margin:0'>"
            "<div style='background:#fff;padding:40px;border-radius:16px;max-width:420px;"
            "text-align:center;box-shadow:0 10px 30px rgba(0,0,0,.08)'>"
            "<h1 style='margin:0 0 8px'>403</h1>"
            "<p>You do not have permission to open this page.</p>"
            f"<p style='color:#64748b'>{who}</p>"
            "<a href='/Logout/' style='display:inline-block;margin:6px;padding:10px 18px;"
            "background:#0d4a6f;color:#fff;border-radius:8px;text-decoration:none'>Log out</a>"
            "<a href='/' style='display:inline-block;margin:6px;padding:10px 18px;"
            "background:#e2e8f0;color:#0f172a;border-radius:8px;text-decoration:none'>Back to Home</a>"
            "</div></body>"
        )
        return HttpResponse(html, status=403)
