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


def GenerateQuizPage(request, teacher_id, course_id):
    context = {"TecherID": teacher_id, "CourseID": course_id}
    return render(request, "pages/GenerateQuiz.html", context)


def QuizInsertion(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            quiz_name = data.get("quiz_name")
            teacher_id = data.get("TeacherID")
            course_id = data.get("CourseID")
            questions_data = data.get("questions")

            with transaction.atomic():
                # 1. Fetch Objects
                teacher = TeacherModel.objects.get(Teacher_Id=teacher_id)
                course = Courses.objects.get(course_id=course_id)

                # 2. Create the Quiz
                quiz_count = QuizModel.objects.filter(course=course).count()
                new_quiz = QuizModel.objects.create(
                    QuizName=quiz_name,
                    Teacher=teacher,
                    course=course,
                    QuizNumber=quiz_count + 1,
                )

                # 3. Create Questions & Options
                for q_item in questions_data:
                    new_question = QuestionModel.objects.create(
                        Quiz=new_quiz,
                        QuestionText=q_item.get("text"),
                        QuestionType=q_item.get("type"),
                        Marks=q_item.get("mark"),
                    )

                    if q_item.get("type") == "mcq":
                        options = q_item.get("options", [])
                        try:
                            correct_idx = int(q_item.get("correct_option", -1))
                        except:
                            correct_idx = -1

                        for i, opt_text in enumerate(options):
                            OptionModel.objects.create(
                                Question=new_question,
                                OptionText=opt_text.strip(),
                                IsCorrect=(i == correct_idx),
                            )

                # 4. Enroll Students into the TakeStatus table
                all_students = StudentInformation.objects.all()
                for student in all_students:
                    # Using the exact class name from your Traceback
                    QuizTakeStatus.objects.create(
                        Student_ID=student.Student_ID,
                        Quiz=new_quiz,
                        IsTaken=0,
                        course_id=course_id,
                    )

            return JsonResponse({"message": "Quiz created successfully!"}, status=200)

        except Exception as e:
            # This will show you exactly which field is causing trouble if it fails again
            print(f"CRITICAL ERROR: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid method"}, status=400)


def take_quiz(request, StudentID, CourseID):
    Flag = 0
    quiz_name = "No Quiz Available"
    question_data = []

    status_record = (
        QuizTakeStatus.objects.filter(
            Student_ID=StudentID, course_id=CourseID, IsTaken=0
        )
        .select_related("Quiz")
        .first()
    )

    if status_record:
        quiz = status_record.Quiz
        quiz_name = quiz.QuizName
        questions = QuestionModel.objects.filter(Quiz=quiz)

        for q in questions:
            options = OptionModel.objects.filter(Question=q).values_list(
                "OptionID", "OptionText"
            )
            question_data.append(
                {
                    "id": q.QuestionID,
                    "text": q.QuestionText,
                    "type": q.QuestionType,
                    "marks": q.Marks or 0,
                    "options": list(options),
                }
            )
    else:
        # Check if already submitted
        if StudentAnswers.objects.filter(
            StudentID=StudentID, Quiz__course_id=CourseID
        ).exists():
            Flag = 1

    context = {
        "StudentID": StudentID,
        "quiz_name": quiz_name,
        "questions": question_data,
        "Flag": Flag,
        "CourseID": CourseID,
    }
    return render(request, "pages/StudentQuiz.html", context)


def submit_quiz(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            answers = data.get("answers", {})
            student_id = data.get("studentId")

            if not answers:
                return JsonResponse({"error": "No answers received."}, status=400)

            with transaction.atomic():
                # Identify Quiz from the first question
                first_q_id = list(answers.keys())[0]
                sample_q = QuestionModel.objects.get(QuestionID=first_q_id)
                current_quiz = sample_q.Quiz

                for q_id, student_ans in answers.items():
                    question = QuestionModel.objects.get(QuestionID=q_id)
                    # Use the question type defined in DB rather than guessing with .isdigit()
                    is_mcq = question.QuestionType.lower() == "mcq"

                    StudentAnswers.objects.create(
                        StudentID=student_id,
                        Quiz=current_quiz,
                        Question=question,
                        AnswerType="mcq" if is_mcq else "written",
                        StudentAnswer=None if is_mcq else str(student_ans),
                        SelectedOption=int(student_ans) if is_mcq else None,
                        Flag=0,  # Start at 0 marks until graded
                    )

                QuizTakeStatus.objects.filter(
                    Student_ID=student_id, Quiz=current_quiz
                ).update(IsTaken=1, TakenDate=timezone.now())

            return JsonResponse({"message": "Quiz submitted successfully!"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid method"}, status=400)


def quiz_delivered(request, CourseID):
    students_dict = {}
    questions = {}
    selected_quiz_id = request.GET.get("quiz_id")

    with connection.cursor() as cursor:
        # A. Get Quizzes
        cursor.execute(
            "SELECT QuizID, QuizNumber FROM Quizzes WHERE course_id = %s ORDER BY QuizID DESC",
            [CourseID],
        )
        all_quizzes = [{"id": r[0], "number": r[1]} for r in cursor.fetchall()]
        if not all_quizzes:
            return HttpResponse("No quizzes found.")

        if selected_quiz_id:
            cursor.execute(
                "SELECT QuizID, QuizNumber FROM Quizzes WHERE QuizID = %s",
                [selected_quiz_id],
            )
        else:
            cursor.execute(
                "SELECT QuizID, QuizNumber FROM Quizzes WHERE course_id = %s ORDER BY QuizID DESC LIMIT 1",
                [CourseID],
            )
        quiz_id, quiz_number = cursor.fetchone()

        # B. Fetch Questions
        cursor.execute(
            "SELECT QuestionID, QuestionText, Marks FROM Questions WHERE Quiz_id = %s",
            [quiz_id],
        )
        for q_row in cursor.fetchall():
            questions[q_row[0]] = {"text": q_row[1], "marks": q_row[2] or 0}

        # C. Fetch Answers JOINED with the saved Grades table
        # We use COALESCE(g.MarksObtained, 0) to get the saved grade or 0 if not graded yet
        cursor.execute(
            """
            SELECT 
                sa.StudentID, 
                si.Student_Name, 
                sa.Question_id, 
                sa.AnswerType, 
                sa.StudentAnswer, 
                o.OptionText,
                COALESCE(g.MarksObtained, 0) as SavedMark
            FROM StudentAnswers sa
            JOIN StudentInformation si ON sa.StudentID = si.Student_ID
            LEFT JOIN Options o ON sa.SelectedOption = o.OptionID
            LEFT JOIN QuizGrades g ON sa.StudentID = g.StudentID AND sa.Question_id = g.QuestionID
            WHERE sa.Quiz_id = %s
        """,
            [quiz_id],
        )
        raw_answers = cursor.fetchall()

    # 2. Group Data
    for row in raw_answers:
        sid = row[0]
        if sid not in students_dict:
            students_dict[sid] = {"name": row[1], "answers": {}}

        q_id = row[2]
        ans_type = str(row[3]).lower() if row[3] else ""

        if "written" in ans_type:
            display = row[4] if row[4] else "No answer"
        else:
            display = f"Selected: {row[5]}" if row[5] else "No selection"

        students_dict[sid]["answers"][q_id] = {
            "display": display,
            "current_marks": row[6],  # This is now pulling from QuizGrades!
        }

    # 3. Totals
    for sid, data in students_dict.items():
        data["current_total"] = sum(
            int(a["current_marks"]) for a in data["answers"].values()
        )
        data["max_total"] = sum(int(q["marks"]) for q in questions.values())

    return render(
        request,
        "pages/quiz_delivered.html",
        {
            "all_quizzes": all_quizzes,
            "current_quiz_id": quiz_id,
            "quiz_number": quiz_number,
            "questions": questions,
            "students": students_dict,
            "CourseID": CourseID,
        },
    )
