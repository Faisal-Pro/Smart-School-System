"""Smoke tests for the Smart School System.

Run with:  python manage.py test
Each test starts from the same demo data created by `seed_demo`.
"""
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase

from .analytics_utils import get_student_risk_report, get_ai_prediction

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
        self.assertEqual(page.context["total_students"], 12)
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
