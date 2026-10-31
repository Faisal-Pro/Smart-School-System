"""Smoke tests for the Smart School System.

Run with:  python manage.py test
Each test starts from the same demo data created by `seed_demo`.
"""
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase

from .analytics_utils import get_student_risk_report, get_ai_prediction
from .models import CourseAnnouncement, CourseAnnouncementReadStatus

DEMO_PASSWORD = "demo1234"


class SchoolTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", "--reset", stdout=StringIO())

    def login_as(self, role, user_id, **extra):
        """Put a role in the session without going through the login form."""
        session = self.client.session
        session["role"] = role
        session["user_id"] = user_id
        for key, value in extra.items():
            session[key] = value
        session.save()


class AccessControlTests(SchoolTestCase):
    def test_anonymous_user_is_sent_to_login(self):
        response = self.client.get("/StudentDashboard/1001/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("LogIn", response["Location"])

    def test_student_cannot_open_another_students_page(self):
        self.login_as("student", 1001)
        response = self.client.get("/StudentDashboard/1002/")
        self.assertEqual(response.status_code, 403)

    def test_student_cannot_open_admin_page(self):
        self.login_as("student", 1001)
        response = self.client.get("/DirectAdminPage/")
        self.assertEqual(response.status_code, 403)

    def test_forbidden_page_offers_logout(self):
        self.login_as("student", 1001)
        response = self.client.get("/DirectAdminPage/")
        self.assertContains(response, "/Logout/", status_code=403)


class LoginTests(SchoolTestCase):
    def test_teacher_login_goes_to_dashboard(self):
        response = self.client.post(
            "/TeacherLogIn2/", {"id": "101", "password": DEMO_PASSWORD}
        )
        self.assertRedirects(response, "/TeacherDashboard/")

    def test_parent_login_goes_to_dashboard(self):
        response = self.client.post(
            "/ParentLogIn2/", {"id": "2001", "password": DEMO_PASSWORD}
        )
        self.assertRedirects(response, "/ParentDashboard/")

    def test_wrong_password_is_rejected(self):
        response = self.client.post(
            "/TeacherLogIn2/", {"id": "101", "password": "not-the-password"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("user_id", self.client.session)

    def test_admin_login_and_dashboard_numbers(self):
        User.objects.create_user("boss", "boss@example.com", "S0me-Strong-pass", is_staff=True)
        response = self.client.post(
            "/AdminLogIn/", {"username": "boss", "password": "S0me-Strong-pass"}
        )
        self.assertRedirects(response, "/DirectAdminPage/")
        page = self.client.get("/DirectAdminPage/")
        self.assertEqual(page.context["total_students"], 13)
        self.assertEqual(page.context["total_teachers"], 10)
        self.assertEqual(page.context["total_courses"], 14)
        self.assertIn("students_at_risk", page.context)


class PagesTests(SchoolTestCase):
    def test_student_pages_open(self):
        self.login_as("student", 1001)
        for url in (
            "/StudentDashboard/1001/",
            "/StudentInformation/1001/",
            "/courses/1001/",
            "/FinalGrade/1001/",
            "/CoursePageStudent/1001/1/",  # shows the AI risk report
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_student_timetable_is_built_from_schedule(self):
        self.login_as("student", 1001)
        response = self.client.get("/StudentSchedulePage/1001/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["Timetable"])

    def test_teacher_pages_open(self):
        self.login_as("teacher", 101)
        for url in (
            "/TeacherDashboard/",
            "/TeacherSchedule/101/",
            "/course-materials/101/1/",
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_parent_dashboard_opens(self):
        self.login_as("parent", 2001, student_id=1001)
        self.assertEqual(self.client.get("/ParentDashboard/").status_code, 200)


class RiskModelTests(SchoolTestCase):
    def test_risk_is_a_percentage(self):
        report = get_student_risk_report(1001, 1)
        self.assertGreaterEqual(report["risk_score"], 0)
        self.assertLessEqual(report["risk_score"], 100)
        self.assertTrue(report["advice"])

    def test_weak_student_scores_higher_than_strong_student(self):
        strong = get_student_risk_report(1001, 1)["risk_score"]
        weak = get_student_risk_report(1003, 1)["risk_score"]
        self.assertGreater(weak, strong)

    def test_model_really_runs_and_is_not_the_0_5_fallback(self):
        # features: term_work_norm, Cumulative_GPA, succededhours, level_id_x
        strong = get_ai_prediction([0.9, 3.5, 90, 3])
        weak = get_ai_prediction([0.1, 1.0, 10, 1])
        self.assertNotEqual(strong, 0.5)
        self.assertNotEqual(weak, 0.5)
        self.assertGreater(weak, strong)


class CourseAnnouncementTests(SchoolTestCase):
    AJAX = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}

    def test_teacher_can_post_using_the_form_field_name_content(self):
        self.login_as("teacher", 101)
        response = self.client.post(
            "/AddAnnouncementsCourse/101/1/", {"content": "Posted from the form"}, **self.AJAX
        )
        self.assertEqual(response.status_code, 200)

    def test_teacher_posts_and_enrolled_student_reads_it(self):
        self.login_as("teacher", 101)
        response = self.client.post(
            "/AddAnnouncementsCourse/101/1/",
            {"description": "Bring your calculator on Sunday"},
            **self.AJAX,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            CourseAnnouncement.objects.filter(
                course_id=1, description="Bring your calculator on Sunday"
            ).exists()
        )
        new_id = CourseAnnouncement.objects.get(
            description="Bring your calculator on Sunday"
        ).id
        unread = CourseAnnouncementReadStatus.objects.filter(
            Student_ID=1001, Announcement_ID=new_id, IsRead=False
        )
        self.assertEqual(unread.count(), 1)

        self.client.logout()
        self.login_as("student", 1001)
        page = self.client.get("/CourseAnnouncement/1001/1/")
        self.assertContains(page, "Bring your calculator on Sunday")
        self.assertEqual(unread.count(), 0)  # opening the page marks it as read

    def test_teacher_cannot_post_in_a_course_he_does_not_teach(self):
        self.login_as("teacher", 101)  # teaches courses 1 and 4
        response = self.client.post(
            "/AddAnnouncementsCourse/101/2/", {"description": "Hello"}, **self.AJAX
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(CourseAnnouncement.objects.filter(description="Hello").exists())

    def test_student_cannot_read_announcements_of_a_course_he_is_not_in(self):
        self.login_as("student", 1001)  # level 1: courses 1-4 only
        response = self.client.get("/CourseAnnouncement/1001/8/")
        self.assertEqual(response.status_code, 403)


class TeacherRiskPanelTests(SchoolTestCase):
    def test_teacher_sees_students_sorted_by_risk(self):
        self.login_as("teacher", 101)
        page = self.client.get("/CourseRisk/101/1/")
        self.assertEqual(page.status_code, 200)
        scores = [r["score"] for r in page.context["rows"]]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertGreater(len(scores), 0)

    def test_teacher_cannot_open_another_teachers_panel(self):
        self.login_as("teacher", 101)
        self.assertEqual(self.client.get("/CourseRisk/102/2/").status_code, 403)

    def test_student_cannot_open_the_panel(self):
        self.login_as("student", 1001)
        self.assertEqual(self.client.get("/CourseRisk/101/1/").status_code, 403)


class FaisalDemoStudentTests(SchoolTestCase):
    def test_faisal_is_enrolled_in_three_ai_courses(self):
        from .models import StudentCourses

        names = set(
            StudentCourses.objects.filter(Student_ID=1013).values_list(
                "course_name", flat=True
            )
        )
        self.assertEqual(
            names,
            {
                "Data Structures and Algorithms",
                "Database Management Systems",
                "Artificial Intelligence & ML",
            },
        )

    def test_faisal_can_log_in(self):
        response = self.client.post(
            "/StudentLogIn2/", {"id": "1013", "password": DEMO_PASSWORD}
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/StudentDashboard/1013/", response["Location"])
