from django.contrib.auth import authenticate
from django.shortcuts import redirect, render

from .models import StudentInformation, TeacherInformation, ParentInformation, Courses
from .security import login_session


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


def Request(request):
    context = {
        "total_students": StudentInformation.objects.count(),
        "total_teachers": TeacherInformation.objects.count(),
        "total_parents": ParentInformation.objects.count(),
        "total_courses": Courses.objects.count(),
    }
    return render(request, "pages/AdminDashboard.html", context)
