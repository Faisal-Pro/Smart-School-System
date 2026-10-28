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


def SaveFinalGrade(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            print("Received data:", data)

            student_id = data.get("StudentID")
            studentGrades = data.get("Grades")
            assignment = data.get("Assignment")
            quiz = data.get("Quiz")
            midterm = data.get("MidTerm")
            finalExam = data.get("Final")
            participation = data.get("Participation")
            attendance = data.get("Attendance")
            CourseID = data.get("CourseID")
            Credit = ""
            StudentStatus = ""

            # Assign credit and status based on grades
            if studentGrades >= 90:
                Credit = "A"
                StudentStatus = "Passed"
            elif studentGrades >= 80:
                Credit = "B"
                StudentStatus = "Passed"
            elif studentGrades >= 70:
                Credit = "C"
                StudentStatus = "Passed"
            elif studentGrades >= 60:
                Credit = "D"
                StudentStatus = "Passed"
            else:
                Credit = "F"
                StudentStatus = "Failed"

            print("Student ID:", student_id, "Total mark:", studentGrades)

            # Use a single cursor for all database operations
            with connection.cursor() as cursor:
                # Check if the student grade already exists
                cursor.execute(
                    """
                    SELECT Student_ID
                    FROM FinalGrade
                    WHERE Student_ID = %s 
                """,
                    [student_id],
                )
                StudentGrade = cursor.fetchone()

                if StudentGrade:
                    # Update the existing record
                    cursor.execute(
                        """
                        UPDATE FinalGrade   
                        SET TotalQuizMark = %s,
                            TotalAssignment = %s,
                            MidTerm = %s,
                            Final = %s,
                            ClassParticipation = %s,
                            ClassAttendance = %s,
                            Total = %s,
                            course_id = %s,
                            Credit = %s,
                            StudentStatus = %s
                        WHERE Student_ID = %s
                    """,
                        [
                            quiz,
                            assignment,
                            midterm,
                            finalExam,
                            participation,
                            attendance,
                            studentGrades,
                            CourseID,
                            Credit,
                            StudentStatus,
                            student_id,
                        ],
                    )
                else:
                    # Insert a new record
                    cursor.execute(
                        """
                        INSERT INTO FinalGrade 
                        (TotalQuizMark, TotalAssignment, MidTerm, Final, ClassParticipation, ClassAttendance, Total, Student_ID, course_id, Credit, StudentStatus)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                        [
                            quiz,
                            assignment,
                            midterm,
                            finalExam,
                            participation,
                            attendance,
                            studentGrades,
                            student_id,
                            CourseID,
                            Credit,
                            StudentStatus,
                        ],
                    )

            # Return a success response
            return JsonResponse(
                {"message": "Grades confirmed successfully!"}, status=200
            )

        except Exception as e:
            print("Error:", e)
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request method"}, status=405)


def GenerateGrades(request, CourseID):
    with connection.cursor() as cursor:
        cursor.execute("""
                SELECT Student_Name, Student_Image, Student_ID, Class
                FROM StudentInformation
                ORDER BY Class, Student_ID ASC;
                    """)
        StudentRecord = cursor.fetchall()

    Student_data = []
    if StudentRecord:
        for Record in StudentRecord:
            Student_Name = Record[0]
            Student_Image = Record[1]
            Student_ID = Record[2]
            Class = Record[3]
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                            SELECT 
                                SUM(MarksObtained) AS TotalMarksObtained
                            FROM 
                                HomeWorkGrades
                            WHERE 
                                Student_ID = %s

                            """,
                    [Student_ID],
                )
                AssignmentGrade = cursor.fetchall()

                cursor.execute(
                    """
                            SELECT 
                                SUM(MarksObtained) AS TotalMarksObtained
                            FROM 
                                QuizGrades
                            WHERE 
                                StudentID = %s
                            """,
                    [Student_ID],
                )
                QuizGrade = cursor.fetchall()

                cursor.execute(
                    """
                        SELECT 
                            SUM(AttendanceList.Mark) AS TotalMark
                        FROM 
                            AttendanceList 
                        WHERE
                            AttendanceList.course_id = 1201 AND AttendanceList.Student_ID = %s
                            """,
                    [Student_ID],
                )
                AttendanceGrade = cursor.fetchall()

            Student_data.append(
                {
                    "StudentName": Student_Name,
                    "StudentImage": base64.b64encode(Student_Image).decode("utf-8"),
                    "StudentID": Student_ID,
                    "Class": Class,
                    "TotalAssignmentGrade": AssignmentGrade[0][0],
                    "TotalQuizGrade": QuizGrade[0][0],
                    "TotalAttendanceGrade": AttendanceGrade[0][0],
                    "CourseID": CourseID,
                }
            )

    context = {
        "StudentRecord": Student_data,
    }
    return render(request, "pages/GenerateGrades.html", context)


def TeacherSchedule(request, teacher_id):
    with connection.cursor() as cursor:
        # 1. Fetch Teacher Info
        # Ensure 'TeacherInformation' matches your models.py Meta db_table
        cursor.execute(
            "SELECT Teacher_Name, Teacher_Image FROM TeacherInformation WHERE Teacher_Id = %s",
            [teacher_id],
        )
        teacher_row = cursor.fetchone()

        teacher_data = {}
        if teacher_row:
            raw_img = teacher_row[1]
            img_b64 = (
                base64.b64encode(raw_img).decode("utf-8")
                if raw_img and isinstance(raw_img, bytes)
                else ""
            )

            teacher_data = {
                "TeacherName": teacher_row[0],
                "TeacherImage": raw_img or "",
            }

        # 2. Fetch Schedule Info
        # This matches the 'db_table' we set in models.py
        cursor.execute(
            """
            SELECT day, start_time, end_time, course_name, room 
            FROM TeacherSchedule 
            WHERE teacher_id = %s
        """,
            [teacher_id],
        )
        schedule_rows = cursor.fetchall()

        schedules_list = []
        for r in schedule_rows:
            schedules_list.append(
                {"day": r[0], "start": r[1], "end": r[2], "course": r[3], "room": r[4]}
            )

        context = {
            "TeacherRecord": [teacher_data] if teacher_data else [],
            "Schedules": schedules_list,
        }
    return render(request, "pages/TeacherSchedule.html", context)


def CourseContent(request):
    return render(request, "pages/CoursePage.html")


def Upload(request):
    return render(request, "pages/add_course.html")


def upload_assignment_Page(request, Teacher_Id, Course_Id):
    Teacher_data = []
    Course_data = []

    with connection.cursor() as cursor:
        # 1. Fetch Teacher Info (Default table name)
        cursor.execute(
            """
            SELECT Teacher_Name, Teacher_Image, Teacher_Id
            FROM TeacherInformation
            WHERE Teacher_Id = %s 
        """,
            [Teacher_Id],
        )
        TeacherRecord = cursor.fetchall()

        if TeacherRecord:
            for Record in TeacherRecord:
                # Handle Image: Teacher_Image is a CharField (URL/Path) in your model
                Teacher_data.append(
                    {
                        "TeacherName": Record[0],
                        "TeacherImage": Record[1],  # String path from CharField
                        "TeacherID": Record[2],
                    }
                )

        # 2. Fetch Courses for this Teacher (Uses 'Courses' table from your Meta class)
        cursor.execute(
            """
            SELECT c.course_id, c.course_name, c.course_level, c.image_url
            FROM TeacherCourses tc
            INNER JOIN Courses c ON c.course_id = tc.course_id
            WHERE tc.Teacher_Id = %s 
        """,
            [Teacher_Id],
        )

        CourseRecords = cursor.fetchall()
        for Record in CourseRecords:
            Course_data.append(
                {
                    "CourseID": Record[0],
                    "CourseName": Record[1],
                    "Courselevel": Record[2],
                    "image_url": Record[3],  # image_url from your model
                }
            )

    # Fallback check
    if not Teacher_data:
        return HttpResponse("Teacher not found in database.")

    context = {
        "TeacherID": Teacher_Id,
        "CourseID": Course_Id,
        "TeacherRecords": Teacher_data,
        "CourseRecord": Course_data,
    }

    return render(request, "pages/UploadAssignment.html", context)


def CoursePage(request, teacher_id, course_id):
    with connection.cursor() as cursor:
        # 1. Fetch Materials for this specific course
        cursor.execute(
            """
            SELECT PublisherImage, PublisherName, DateOfPublish,
                   DescriptionText, MaterialPath
            FROM CourseContents
            WHERE course_id = %s
            ORDER BY MaterialID
        """,
            [course_id],
        )

        course_contents = cursor.fetchall()

    # 2. Process File Types (mimetypes logic)
    formatted_contents = []
    for description in course_contents:
        pub_img, pub_name, date, desc, path = description

        # Determine the file type based on the extension (e.g., .mp4, .pdf)
        file_type, _ = mimetypes.guess_type(path) if path else (None, None)

        if file_type:
            if file_type.startswith("image"):
                content_type = "image"
            elif file_type.startswith("video"):
                content_type = "video"
            elif file_type.startswith("audio"):
                content_type = "audio"
            elif file_type == "application/pdf":
                content_type = "pdf"
            else:
                content_type = "file"  # General file icon
        else:
            content_type = "unknown"

        formatted_contents.append(
            {
                "publisher_image": pub_img,
                "publisher_name": pub_name,
                "date_of_publish": date,
                "description_text": desc,
                "material_path": path,
                "content_type": content_type,
            }
        )

    # 3. Render the page
    # Passing IDs back ensures your "Upload" and "Back" buttons work correctly
    return render(
        request,
        "pages/CoursePage.html",
        {
            "course_contents": formatted_contents,
            "teacher_id": teacher_id,
            "course_id": course_id,
        },
    )


def get_course_contents(request, course_id):
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

        course_contents = cursor.fetchall()

    if course_contents:
        print(course_id)
        return render(request, "pages/Try.html", {"course_contents": course_contents})
    else:
        return HttpResponse("Null record")


def ViewStudentsCourse(request, Course_ID):
    with connection.cursor() as cursor:
        # Note: I'm using "StudentInformation" which is the Django default.
        # If your database shell showed just "StudentInformation", change it back.
        cursor.execute(
            """
            SELECT 
                SI.Student_Image, 
                SI.Student_Name, 
                SI.Student_ID, 
                SI.Student_Level
            FROM StudentInformation SI
            INNER JOIN StudentCourses SC ON SI.Student_ID = SC.Student_ID
            WHERE SC.course_id = %s
        """,
            [Course_ID],
        )

        StudentRecords = cursor.fetchall()

        # This will print in your VS Code / CMD terminal
        print(f"--- DEBUG: Course {Course_ID} ---")
        print(f"Total Rows Found: {len(StudentRecords)}")

        for r in StudentRecords:
            print(f"Found Student: {r[1]} (ID: {r[2]})")

    Student_data = []
    for Record in StudentRecords:
        raw_img = Record[0]
        try:
            if isinstance(raw_img, bytes):
                encoded_img = base64.b64encode(raw_img).decode("utf-8")
            else:
                encoded_img = str(raw_img)
        except:
            encoded_img = ""

        Student_data.append(
            {
                "StudentImage": encoded_img,
                "StudentName": Record[1],
                "StudentID": Record[2],
                "StudentLevel": Record[3] if Record[3] else "Not Set",
            }
        )

    return render(
        request,
        "pages/StudentInformationCourse.html",
        {"StudentRecords": Student_data, "Course_ID": Course_ID},
    )


def upload_assignment(request, Teacher_Id, Course_Id):
    if request.method == "POST":
        # 1. Extract data from the POST request
        file = request.FILES["fileInput"]
        description = request.POST["description"]
        deadline_date = request.POST["deadlineDate"]
        deadline_hour = request.POST["deadlineHour"]
        deadline_minute = request.POST["deadlineMinute"]
        TotalMark = request.POST["TotalMark"]

        # 2. Format the Date and Deadline string
        current_date = datetime.now()
        UploadDate = str(current_date.strftime("%b %d"))
        # Formatting deadline as 'YYYY-MM-DD HH:MM:SS'
        deadline = f"{deadline_date} {deadline_hour}:{deadline_minute}:00"

        with connection.cursor() as cursor:
            # 3. Fetch the Teacher's Profile Image
            cursor.execute(
                """
                SELECT Teacher_Image FROM TeacherInformation 
                WHERE Teacher_Id = %s
            """,
                [Teacher_Id],
            )
            Record = cursor.fetchone()  # fetchone is cleaner here than fetchall
            PublisherImage = Record[0] if Record and Record[0] else None

            # 4. Calculate the Assignment Number for this course
            cursor.execute(
                """
                SELECT COUNT(*) FROM Assignments 
                WHERE course_id = %s
            """,
                [Course_Id],
            )
            CountRecord = cursor.fetchone()
            Num = (CountRecord[0] + 1) if CountRecord else 1

            # 5. Insert the new assignment including the 'Flag' column
            # We add 'Flag' at the end to satisfy the NOT NULL constraint
            sql = """
                INSERT INTO Assignments (
                    FileContent, DescriptionContent, DeadlineDate, 
                    AssignementNumber, course_id, Teacher_Id, 
                    PublisherImage, CreatedAt, TotalMark, Flag
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            cursor.execute(
                sql,
                [
                    file.read(),  # The PDF binary data
                    description,  # Text description
                    deadline,  # Formatted date/time string
                    Num,  # Assignment #1, #2, etc.
                    Course_Id,  # Foreign Key to Course
                    Teacher_Id,  # Foreign Key to Teacher
                    PublisherImage,  # Teacher's profile pic
                    UploadDate,  # Date string (e.g., 'Dec 17')
                    TotalMark,  # The point value
                    1,  # Flag: 1 means Active/Visible
                ],
            )

        return JsonResponse(
            {"success": True, "message": "Assignment uploaded successfully!"}
        )

    return JsonResponse({"success": False, "message": "Invalid request method."})


def HomeworkDelivered(request):
    if request.method == "POST":
        student_id = request.POST.get("student_id")
        course_id = request.POST.get("course_id")
        assignment_id = request.POST.get("assignment_id")
        file = request.FILES.get("file")
        BinaryFile = file.read()

        print("CourseID, StudentID: ", course_id, student_id)
        print("The assignment id = ", assignment_id)

        check_query = """
            SELECT COUNT(*) FROM HomeworkDelivered 
            WHERE course_id = %s AND Student_ID = %s AND AssignmentId = %s;
        """

        with connection.cursor() as cursor:
            cursor.execute(check_query, [course_id, student_id, assignment_id])
            result = cursor.fetchone()
            record_exists = result[0] > 0

        if record_exists:
            update_query = update_query = """
                UPDATE HomeworkDelivered
                SET FileContent = %s, DeliveredDate = CURRENT_TIMESTAMP
                WHERE course_id = %s AND Student_ID = %s AND AssignmentId = %s;
            """
            with connection.cursor() as cursor:
                cursor.execute(
                    update_query, [BinaryFile, course_id, student_id, assignment_id]
                )

            message = "File updated successfully!"
        else:
            insert_query = """
                INSERT INTO HomeworkDelivered (course_id, Student_ID, AssignmentId, DeliveredDate, FileContent, AssignmentNumber, TotalMark, Flag)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP, %s, %s, %s, 0);
            """
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM Assignments")
                result = cursor.fetchone()
                AssignmentNumber = result[0]
                cursor.execute(
                    "SELECT TotalMark FROM Assignments WHERE AssignmentId = %s ",
                    [assignment_id],
                )
                result = cursor.fetchone()
                TotalMark = result[0]
                cursor.execute(
                    insert_query,
                    [
                        course_id,
                        student_id,
                        assignment_id,
                        BinaryFile,
                        AssignmentNumber,
                        TotalMark,
                    ],
                )

                cursor.execute(
                    """
                INSERT INTO SubmittedAssignmentFlag (AssignmentId, Flag, course_id, Student_ID)
                Values(%s, 1, %s, %s)
            """,
                    [assignment_id, course_id, student_id],
                )

            message = "Homework submitted successfully!"

        return JsonResponse(
            {
                "message": message,
                "assignment_id": assignment_id,
                "student_id": student_id,
                "file_name": file.name,
            }
        )

    return JsonResponse({"error": "Invalid request method"}, status=405)


def CourseAttendanceHistory(request, Course_ID, StudentID):
    Attendance_data = []

    # 1. FETCH COURSE NAME USING DJANGO ORM (Much more reliable for finding the name)
    try:
        # This will use your 'Courses' table and 'course_id' primary key automatically
        course_obj = Courses.objects.get(course_id=Course_ID)
        course_name = course_obj.course_name
    except Courses.DoesNotExist:
        # If this hits, the ID in your URL does not exist in the 'Courses' table
        course_name = f"ID {Course_ID} Not Found"

    with connection.cursor() as cursor:
        # 2. Fetch Attendance Records using Raw SQL
        try:
            cursor.execute(
                """
                SELECT Student_ID_id, Attendance_Date, 
                       AttendanceTime, AttendanceStatus, LectureNumber 
                FROM AttendanceList 
                WHERE course_id_id = %s AND Student_ID_id = %s
                ORDER BY Attendance_Date DESC
            """,
                [Course_ID, StudentID],
            )

            AttendanceRecord = cursor.fetchall()

            for Record in AttendanceRecord:
                Attendance_data.append(
                    {
                        "Student_ID": Record[0],
                        "CourseName": course_name,
                        "Attendance_Date": Record[1],
                        "AttendanceTime": Record[2],
                        "AttendanceStatus": Record[3],  # Corrected Index
                        "LectureNumber": Record[4],  # Corrected Index
                    }
                )
        except Exception as e:
            print(f"DATABASE ERROR: {e}")

    context = {
        "AttendanceRecord": Attendance_data,
        "CourseName": course_name,
        "StudentID": StudentID,
        "CourseID": Course_ID,
    }

    return render(request, "pages/CourseAttendanceHistory.html", context)


def confirm_grades(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            student_id = data.get("studentId")
            grades = data.get("grades", {})

            with connection.cursor() as cursor:
                for question_id, marks_obtained in grades.items():
                    # 1. Get Marks and the linked Quiz ID from the question
                    cursor.execute(
                        "SELECT Marks, Quiz_id FROM Questions WHERE QuestionID = %s",
                        [question_id],
                    )
                    q_data = cursor.fetchone()
                    if not q_data:
                        continue

                    total_marks, quiz_db_id = q_data

                    # 2. Get QuizNumber and CourseID from the Quizzes table
                    # Note: Your Quizzes model uses 'course_id' as the FK column
                    cursor.execute(
                        "SELECT QuizNumber, course_id FROM Quizzes WHERE QuizID = %s",
                        [quiz_db_id],
                    )
                    quiz_data = cursor.fetchone()
                    if not quiz_data:
                        continue

                    quiz_number, course_id = quiz_data

                    # 3. Check if record exists
                    cursor.execute(
                        """
                        SELECT COUNT(*) FROM QuizGrades 
                        WHERE StudentID = %s AND QuestionID = %s
                    """,
                        [student_id, question_id],
                    )

                    exists = cursor.fetchone()[0] > 0

                    if exists:
                        # Update existing record
                        cursor.execute(
                            """
                            UPDATE QuizGrades 
                            SET MarksObtained = %s, TotalMarks = %s, QuizNumber = %s, CourseID = %s
                            WHERE StudentID = %s AND QuestionID = %s
                        """,
                            [
                                marks_obtained,
                                total_marks,
                                quiz_number,
                                course_id,
                                student_id,
                                question_id,
                            ],
                        )
                    else:
                        # Insert new record using the correct columns from your model
                        cursor.execute(
                            """
                            INSERT INTO QuizGrades (StudentID, CourseID, QuizNumber, QuestionID, MarksObtained, TotalMarks) 
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                            [
                                student_id,
                                course_id,
                                quiz_number,
                                question_id,
                                marks_obtained,
                                total_marks,
                            ],
                        )

            return JsonResponse(
                {"message": "Grades confirmed successfully!"}, status=200
            )
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid method"}, status=405)


def HomeWork_delivered(request, CourseID):
    with connection.cursor() as cursor:
        # 1. Fetch Course Info
        cursor.execute(
            """
            SELECT course_id, course_name, course_level 
            FROM Courses 
            WHERE course_id = %s
        """,
            [CourseID],
        )
        CourseRecord = cursor.fetchall()

        # 2. Fetch Submissions JOINED with their actual saved Grades
        # We use LEFT JOIN so we still see the submission even if it isn't graded yet
        cursor.execute(
            """
            SELECT 
                s.Student_Name, 
                h.Student_ID, 
                h.AssignmentNumber, 
                h.DeliveredDate, 
                h.TotalMark,
                h.id,
                g.MarksObtained  -- This is the saved grade [Index 6]
            FROM HomeworkDelivered h
            INNER JOIN StudentInformation s ON h.Student_ID = s.Student_ID
            LEFT JOIN HomeWorkGrades g ON h.Student_ID = g.Student_ID 
                AND h.course_id = g.course_id 
                AND h.AssignmentNumber = g.AssignmentNumber
            WHERE h.course_id = %s
            ORDER BY h.DeliveredDate DESC
        """,
            [CourseID],
        )
        Submissions = cursor.fetchall()

    return render(
        request,
        "pages/Homework3.html",
        {
            "CourseRecord": CourseRecord,
            "Submissions": Submissions,
            "CourseID": CourseID,
        },
    )


@xframe_options_exempt
def ViewAssignmentFile(request, submission_id):
    with connection.cursor() as cursor:
        # Fetch the binary description from HomeworkDelivered table
        cursor.execute(
            "SELECT FileContent FROM HomeworkDelivered WHERE id = %s", [submission_id]
        )
        record = cursor.fetchone()

    if record and record[0]:
        # Return the binary data as a PDF response
        response = HttpResponse(record[0], content_type="application/pdf")
        # 'inline' tells the browser to try and show it inside the iframe
        response["description-Disposition"] = 'inline; filename="submission.pdf"'
        return response

    return HttpResponse("File not found.", status=404)


def SaveAssignmentGrade(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            student_id = data.get("studentId")
            grade = data.get("grades")
            submission_id = data.get("AssignmentID")
            course_id = data.get("CourseID")
            total_mark = data.get("TotalMark")

            # --- NEW VALIDATION ---
            # Convert to float/int to compare values safely
            if float(grade) > float(total_mark):
                return JsonResponse(
                    {
                        "error": f"Invalid Grade: {grade} exceeds the maximum points ({total_mark})."
                    },
                    status=400,
                )
            # -----------------------

            if not all([student_id, grade, submission_id, course_id]):
                return JsonResponse(
                    {"error": "Missing required data fields"}, status=400
                )

            with connection.cursor() as cursor:
                # 1. Get the Assignment Number
                cursor.execute(
                    """
                    SELECT AssignmentNumber 
                    FROM HomeworkDelivered 
                    WHERE id = %s
                """,
                    [submission_id],
                )

                res = cursor.fetchone()
                if not res:
                    return JsonResponse(
                        {"error": "Submission record not found"}, status=404
                    )

                assign_num = res[0]

                # 2. Check if grade exists (Upsert Logic)
                cursor.execute(
                    """
                    SELECT id FROM HomeWorkGrades 
                    WHERE Student_ID = %s AND course_id = %s AND AssignmentNumber = %s
                """,
                    [student_id, course_id, assign_num],
                )

                existing_grade = cursor.fetchone()

                if existing_grade:
                    # UPDATE
                    cursor.execute(
                        """
                        UPDATE HomeWorkGrades 
                        SET MarksObtained = %s, TotalMarks = %s
                        WHERE id = %s
                    """,
                        [grade, total_mark, existing_grade[0]],
                    )
                else:
                    # INSERT
                    cursor.execute(
                        """
                        INSERT INTO HomeWorkGrades 
                        (Student_ID, course_id, AssignmentNumber, MarksObtained, TotalMarks)
                        VALUES (%s, %s, %s, %s, %s)
                    """,
                        [student_id, course_id, assign_num, grade, total_mark],
                    )

                # 3. Update Delivery Flag
                cursor.execute(
                    "UPDATE HomeworkDelivered SET Flag = 1 WHERE id = %s",
                    [submission_id],
                )

            return JsonResponse({"message": "Grade saved successfully!"}, status=200)

        except ValueError:
            return JsonResponse({"error": "Grade must be a number."}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request method"}, status=405)
