import base64
from django.db import connection
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib import messages as dj_messages
from .models import TeacherInformation
from datetime import date

def activate_attendance_session(request, course_id):
    try:
        with connection.cursor() as cursor:
            # --- STEP 1: CLEAR OLD DATA FOR TODAY ---
            # This ensures that if you re-click 'Take Attendance', it resets the gate.
            cursor.execute("""
                DELETE FROM AttendanceList 
                WHERE Course_ID = %s AND Date = date('now')
            """, [course_id])

            # --- STEP 2: FETCH STUDENTS ---
            cursor.execute("SELECT Student_ID FROM StudentCourses WHERE course_id = %s", [course_id])
            students = cursor.fetchall()

            if not students:
                return JsonResponse({'status': 'error', 'message': 'No students enrolled'})

            # --- STEP 3: INSERT FRESH 'ABSENT' SLOTS ---
            for student in students:
                cursor.execute("""
                    INSERT INTO AttendanceList (Student_ID, Course_ID, Teacher_ID, Status, Date)
                    VALUES (%s, %s, %s, 'Absent', date('now'))
                """, [student[0], course_id, 0])

        return JsonResponse({'status': 'success'})
    except Exception as e:
        print(f"Activation Error: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)})
    
def deactivate_attendance_session(request, course_id):
    try:
        with connection.cursor() as cursor:
            # Change 'Absent' to 'Final_Absent' or something else.
            # As long as the status is NOT 'Absent', the student gate closes.
            cursor.execute("""
                UPDATE AttendanceList 
                SET Status = 'Official_Absent'
                WHERE Course_ID = %s AND Status = 'Absent' AND Date = date('now')
            """, [course_id])
            
        return JsonResponse({'status': 'success', 'message': 'Gate closed'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

# --- 2. LOGIN & DASHBOARD ---
def Request(request):
    return render(request, 'Pages/TeacherLogIn.html')

def LogInAccount(request):
    if request.method == 'POST':
        teacher_id_input = request.POST.get('id', '').strip()
        password_input = request.POST.get('password', '').strip()

        try:
            teacher = TeacherInformation.objects.get(Teacher_Id=teacher_id_input)
            name_prefix = str(teacher.Teacher_Name).replace(" ", "")[:3]
            expected_pw = f"{name_prefix}@{teacher.Teacher_NationalID}"

            if password_input == expected_pw or password_input == teacher.Passwordd:
                course_data = []
                with connection.cursor() as cursor:
                    search_term = f"%{teacher.Course_Handle.strip()}%"
                    cursor.execute("""
                        SELECT course_id, course_name, course_level, image_url
                        FROM Courses
                        WHERE UPPER(course_name) LIKE UPPER(%s)
                    """, [search_term])
                    course_records = cursor.fetchall()

                for record in course_records:
                    course_data.append({
                        'CourseID': record[0],
                        'CourseName': record[1],
                        'Courselevel': record[2],
                        'CourseImage': record[3] if record[3] else "" 
                    })

                context = {
                    'TeacherRecord': [{
                        'TeacherName': teacher.Teacher_Name,
                        'TeacherImage': teacher.Teacher_Image,
                        'TeacherID': teacher.Teacher_Id,
                    }], 
                    'CourseRecord': course_data,
                }
                return render(request, 'Pages/Teacher.html', context)
            else:
                dj_messages.error(request, "Incorrect Password.")
        except TeacherInformation.DoesNotExist:
            dj_messages.error(request, "Instructor ID not found.")
    return render(request, 'Pages/TeacherLogIn.html')