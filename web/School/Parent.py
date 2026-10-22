import base64
from django.conf import settings
from django.db import connection
from django.http import HttpResponse
from django.shortcuts import render
import cv2
import csv
import os
import datetime
import time
import pandas as pd
import numpy as np
from threading import Thread
from PIL import Image
from .models import ParentInformation, StudentInformation, Courses

             
    


def Request(request):
    return render(request, 'Pages/ParentLogIn.html')


        


def LogInAccount(request):
    if request.method == "POST":
        typed_id = request.POST.get('id')
        typed_password = request.POST.get('password')

        with connection.cursor() as cursor:
            # 1. Fetch Parent
            cursor.execute("""
                SELECT Parent_Name, Parent_ID, Parent_Image, Student_ID_id, Passwordd
                FROM ParentInformation 
                WHERE Parent_ID = %s
            """, [typed_id])
            parent_row = cursor.fetchone()

            # Check if parent exists
            if not parent_row:
                return render(request, 'Pages/ParentLogIn.html', {'error': 'ID not found'})

            parent_name, parent_id, parent_image, student_id, db_password = parent_row

            # Check password (Exact match since we removed .lower())
            if str(db_password) != str(typed_password):
                return render(request, 'Pages/ParentLogIn.html', {'error': 'Incorrect password'})

            # 2. Fetch Student Details
            cursor.execute("""
                SELECT Student_Name, Student_Image, Student_ID
                FROM StudentInformation
                WHERE Student_ID = %s 
            """, [student_id])
            student_row = cursor.fetchone()
            
            s_name = student_row[0] if student_row else "Unknown"
            s_img = student_row[1] if student_row else ""
            s_id = student_row[2] if student_row else 0

            # 3. Fetch Courses (Using your 'StudentCourses' table)
            cursor.execute("""
                SELECT c.course_id, c.course_name, c.course_level, c.image_url
                FROM Courses c
                INNER JOIN StudentCourses sc ON c.course_id = sc.course_id
                WHERE sc.Student_ID = %s 
            """, [student_id])        
            course_records = cursor.fetchall()

            course_data = []
            for record in course_records:
                course_data.append({
                    'CourseID': record[0],
                    'CourseName': record[1],
                    'Courselevel': record[2],
                    'CourseImage': record[3]
                })

            # 4. Fetch Unread Announcements
            cursor.execute("""
                SELECT COUNT(*) 
                FROM CourseAnnouncementReadStatus
                WHERE Student_ID = %s AND IsRead = 0
            """, [student_id]) 
            announcement_count = cursor.fetchone()[0]

            # PREPARE CONTEXT (Still inside 'with' or right after it)
            context = {
                'ParentRecord': [{
                    'ParentName': parent_name,
                    'ParentID': parent_id,
                    'ParentImage': parent_image,
                }],
                'StudentRecord': [{
                    'StudentName': s_name,
                    'StudentImage': s_img,
                    'StudentID': s_id,
                }],
                'CourseRecord': course_data,
                'AnnouncementNum': [[announcement_count]]
            }
            
            # Return the page inside the successful login logic
            return render(request, 'Pages/Parent.html', context)

    # If GET request or logic falls through
    return render(request, 'Pages/ParentLogIn.html')