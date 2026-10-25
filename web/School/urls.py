from django.urls import path, include
from . import views
from . import Student
from . import Teacher
from . import Parent
from . import Admin_School
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("", views.index, name="MainPage"),
    path("ParentLogInPage/", Parent.Request, name="ParentLogInPage"),
    path("ParentLogIn2/", Parent.LogInAccount, name="ParentLogIn2"),
    path("StudentLogInPage/", Student.Request, name="StudentLogInPage"),
    path("StudentLogIn/", Student.face_login_process, name="StudentLogIn"),
    path("StudentLogIn2/", Student.LogInAccount, name="StudentLogIn2"),
    path("TeacherLogInPage/", Teacher.Request, name="TeacherLogInPage"),
    path("TeacherLogIn2/", Teacher.LogInAccount, name="TeacherLogIn2"),
    path("DirectAdminPage/", Admin_School.Request, name="DirectAdminPage"),
    path("AddParentForm/", views.AddParentForm, name="AddParentForm"),
    path(
        "StudentSchedulePage/<int:Student_ID>/",
        views.StudentSchedulePage,
        name="StudentSchedulePage",
    ),
    path("AdminLogIn/", Admin_School.AdminLogin, name="AdminLogIn"),
    path("Logout/", Admin_School.Logout, name="Logout"),
    path(
        "UploadMaterialPage/<int:Teacher_Id>/<int:course_id>/",
        views.UploadMaterialPage,
        name="UploadMaterialPage",
    ),
    path("get_records/<int:course_id>/", views.get_records, name="get_records"),
    path("course-content/<int:course_id>/", views.get_records, name="CourseContent"),
    path(
        "course/<int:course_id>/", views.get_course_contents, name="get_course_contents"
    ),
    path("AddCoursePage/", views.AddCoursePage, name="AddCoursePage"),
    path("add_student/", views.add_student, name="add_student"),
    path("add_parent/", views.add_parent, name="add_parent"),
    path("add_student_page/", views.add_student_page, name="add_student_page"),
    path("add_parent_page/", views.add_parent_page, name="add_parent_page"),
    path("redirectAddStudent/", views.redirectAddStudent, name="redirectAddStudent"),
    path("AddStudentForm/", views.AddStudentForm, name="AddStudentForm"),
    path("add-teacher/", views.add_teacher_page, name="AddTeacherPage"),
    path(
        "StudentInformation/<int:Student_ID>/",
        views.student_info_view,
        name="StudentInformation",
    ),
    path(
        "UploadMaterial/<int:Teacher_Id>/<int:course_id>/",
        views.UploadMaterial,
        name="UploadMaterial",
    ),
    path(
        "CoursePageStudent/<int:Student_ID>/<int:course_id>/",
        views.CoursePageStudent,
        name="CoursePageStudent",
    ),
    path("courses/<int:Student_ID>/", views.course_list, name="course_list"),
    path(
        "CoursePage/<int:teacher_id>/<int:course_id>/",
        views.CoursePage,
        name="CoursePage",
    ),
    path("materials_view/", views.materials_view, name="materials_view"),
    path(
        "materials_view/<int:Teacher_Id>/<int:course_id>/",
        views.materials_view,
        name="materials_view",
    ),
    path(
        "upload_material_view/", views.upload_material_view, name="upload_material_view"
    ),
    path(
        "index3/<int:Teacher_Id>/<int:Course_Id>/<str:CourseName>/",
        views.index3,
        name="index3",
    ),
    path("index2/<int:Student_Id>", views.index2, name="index2"),
    path("AddStudentCourse/", views.AddStudentCourse, name="AddStudentCourse"),
    path("AddTeacherCoursPage/", views.AddTeacherCoursPage, name="AddTeacherCoursPage"),
    path("AddStudentCourse3/", views.AddStudentCourse3, name="AddStudentCourse3"),
    path("AssignStudentCourse/", views.AssignStudentCourse, name="AssignStudentCourse"),
    path("fetchcoursesLists/", views.fetchcoursesLists, name="fetchcoursesLists"),
    path(
        "AssignStudentCourse2/", views.AssignStudentCourse2, name="AssignStudentCourse2"
    ),
    path("upload_media/", views.upload_media, name="upload_media"),
    path("media-list/", views.media_list, name="media_list"),
    path("announcements/<int:ID>/", views.announcement_list, name="announcements"),
    path("Addannouncements/", views.Addannouncements, name="Addannouncements"),
    path(
        "AddannouncementsPage/", views.AddannouncementsPage, name="AddannouncementsPage"
    ),
    path(
        "AddAnnouncementsCoursePage/<int:Teacher_Id>/<int:Course_Id>/",
        views.AddAnnouncementsCoursePage,
        name="AddAnnouncementsCoursePage",
    ),
    path(
        "AddAnnouncementsCourse/<int:Teacher_Id>/<int:Course_Id>/",
        views.AddAnnouncementsCourse,
        name="AddAnnouncementsCourse",
    ),
    path("announcements2/", views.announcement_list2, name="announcements2"),
    path(
        "CourseAnnouncement/<int:StudentID>/<int:Course_Id>/",
        views.CourseAnnouncement,
        name="CourseAnnouncement",
    ),
    path(
        "upload_assignment_Page/<int:Teacher_Id>/<int:Course_Id>/",
        views.upload_assignment_Page,
        name="upload_assignment_Page",
    ),
    path(
        "upload_assignment/<int:Teacher_Id>/<int:Course_Id>/",
        views.upload_assignment,
        name="upload_assignment",
    ),
    path("HomeWork/<int:Course_ID>/<int:StudentID>/", views.HomeWork, name="HomeWork"),
    path("AssignTeacherCourse/", views.AssignTeacherCourse, name="AssignTeacherCourse"),
    path(
        "delete-material/<int:material_id>/",
        views.DeleteMaterial,
        name="DeleteMaterial",
    ),
    path(
        "StudentDashboard/<int:Student_ID>/",
        views.StudentDashboard,
        name="StudentDashboard",
    ),
    path(
        "UpdateMaterialPage/<int:Teacher_Id>/<int:course_id>/<int:content_id>/",
        views.UpdateMaterialPage,
        name="UpdateMaterialPage",
    ),
    path(
        "UpdateMaterial/<int:Teacher_Id>/<int:course_id>/<int:content_id>/",
        views.UpdateMaterial,
        name="UpdateMaterial",
    ),
    path("add_course_Page/", views.add_course_Page, name="add_course_Page"),
    path("add_course/", views.add_course, name="add_course"),
    path(
        "ViewStudentsCourse/<int:Course_ID>/",
        views.ViewStudentsCourse,
        name="ViewStudentsCourse",
    ),
    path("HomeworkDelivered/", views.HomeworkDelivered, name="HomeworkDelivered"),
    path("Grade/<int:Course_ID>/<int:StudentID>/", views.Grade, name="Grade"),
    path(
        "CourseAttendanceHistory/<int:Course_ID>/<int:StudentID>/",
        views.CourseAttendanceHistory,
        name="CourseAttendanceHistory",
    ),
    path("quiz-insertion/", views.QuizInsertion, name="quiz-insertion"),
    path(
        "take_quiz/<int:StudentID>/<int:CourseID>/", views.take_quiz, name="take_quiz"
    ),
    path(
        "GenerateQuizPage/<int:teacher_id>/<int:course_id>/",
        views.GenerateQuizPage,
        name="GenerateQuizPage",
    ),
    path("submit_quiz/", views.submit_quiz, name="submit_quiz"),
    path("quiz_delivered/<int:CourseID>/", views.quiz_delivered, name="quiz_delivered"),
    path("confirm_grades/", views.confirm_grades, name="confirm_grades"),
    path("GenerateReport/", views.GenerateReportPage, name="GenerateReport"),
    path(
        "HomeWorkDelivered2/<int:CourseID>/",
        views.HomeWork_delivered,
        name="HomeWorkDelivered2",
    ),
    path("FinalGrade/<int:StudentID>/", views.FinalGrade, name="FinalGrade"),
    path(
        "TeacherSchedule/<int:teacher_id>/",
        views.TeacherSchedule,
        name="TeacherSchedule",
    ),
    path("GenerateGrades/<int:CourseID>/", views.GenerateGrades, name="GenerateGrades"),
    path("SaveAssignmentGrade/", views.SaveAssignmentGrade, name="SaveAssignmentGrade"),
    path("SaveFinalGrade/", views.SaveFinalGrade, name="SaveFinalGrade"),
    path("save_teacher/", views.SaveTeacher, name="SaveTeacher"),
    path(
        "TeacherInformation/<int:Teacher_ID>/",
        views.TeacherInformation,
        name="TeacherInformation",
    ),
    path("view_students/", views.view_students, name="view_students"),
    path("view_teachers/", views.view_teachers, name="view_teachers"),
    path("view_parents/", views.view_parents, name="view_parents"),
    path("delete-teacher/<int:t_id>/", views.delete_teacher, name="delete_teacher"),
    path("delete-parent/<int:parent_id>/", views.delete_parent, name="delete_parent"),
    path(
        "delete-student/<int:student_id>/", views.delete_student, name="delete_student"
    ),
    path(
        "update_student/<int:student_id>/", views.update_student, name="update_student"
    ),
    path("update-teacher/<int:t_id>/", views.update_teacher_page, name="UpdateTeacher"),
    path("update-parent/<int:parent_id>/", views.update_parent, name="update_parent"),
    path("view_courses/", views.view_courses, name="view_courses"),
    path("delete_course/<int:course_id>/", views.delete_course, name="delete_course"),
    path("update_course/<int:course_id>/", views.update_course, name="update_course"),
    path(
        "announcement/file/<int:announcement_id>/<str:file_type>/",
        views.serve_announcement_file,
        name="serve_announcement_file",
    ),
    path(
        "delete_announcement/<int:announcement_id>/",
        views.delete_announcement,
        name="delete_announcement",
    ),
    path(
        "update_announcement/<int:announcement_id>/",
        views.update_announcement,
        name="update_announcement",
    ),
    path(
        "course-materials/<int:Teacher_Id>/<int:course_id>/",
        views.materials_view,
        name="materials_view",
    ),
    path(
        "ViewAssignmentFile/<int:submission_id>/",
        views.ViewAssignmentFile,
        name="ViewAssignmentFile",
    ),
    path(
        "register-face/<int:student_id>/",
        Student.register_face_view,
        name="RegisterFace",
    ),
    path(
        "register-face-guide/<int:student_id>/",
        Student.register_face_page,
        name="RegisterFace",
    ),
    path(
        "capture-frame/<int:student_id>/",
        Student.capture_frame_api,
        name="CaptureFrame",
    ),
    path("StudentFaceLogin/", Student.face_login_process, name="StudentFaceLoginPage"),
    path(
        "verify-attendance/<int:course_id>/<int:student_id>/",
        Student.attendance_verification_page,
        name="StudentFaceLogInPage",
    ),
    path(
        "submit-attendance-ai/", Student.face_login_process, name="SubmitAttendanceAI"
    ),
    path(
        "check-attendance-status/<int:course_id>/",
        Student.check_attendance_status,
        name="check_attendance_status",
    ),
    path(
        "activate-attendance-session/<int:course_id>/",
        Teacher.activate_attendance_session,
        name="activate_attendance_session",
    ),
    path(
        "deactivate-attendance-session/<str:course_id>/",
        Teacher.deactivate_attendance_session,
        name="DeactivateAttendance",
    ),
    path(
        "attendance/<str:Name>/<str:Student_Id>/",
        views.attendance_history,
        name="get_attendance_history",
    ),
]


urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
