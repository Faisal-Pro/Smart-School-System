from pyexpat.errors import messages
from django.conf import settings
from django.db import connection
from django.shortcuts import render
import cv2
import csv
import os
import time
import pandas as pd
import numpy as np
from threading import Thread
from PIL import Image




def Re():
    takeImages()

                
def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        pass
    try:
        import unicodedata
        unicodedata.numeric(s)
        return True
    except (TypeError, ValueError):
        pass
    return False

def getImagesAndLabels(path):
    # path of all the files in the folder
    imagePaths = [os.path.join(path, f) for f in os.listdir(path)]
    faces = []
    # empty ID list
    Ids = []
    for imagePath in imagePaths:
        pilImage = Image.open(imagePath).convert('L')
        imageNp = np.array(pilImage, 'uint8')
        Id = int(os.path.split(imagePath)[-1].split(".")[1])
        faces.append(imageNp)
        Ids.append(Id)
    return faces, Ids


def TrainImages(request, Path, Label):
        #if request.method == 'POST':
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        faces, Id = getImagesAndLabels(Path)
        Thread(target = recognizer.train(faces, np.array(Id))).start()
        Thread(target = counter_img(Path)).start()
        recognizer.save(Label+os.sep+"Trainner.yml")
        print("All Images are trained")

       


def counter_img(path):
    imgcounter = 1
    imagePaths = [os.path.join(path, f) for f in os.listdir(path)]
    for imagePath in imagePaths:
        print(str(imgcounter) + " Images Trained", end="\r")
        time.sleep(0.008)
        imgcounter += 1


def StudentRegisteration(request):

    
    if request.method == 'POST':
        student_name = request.POST.get('student_name')
        student_id = request.POST.get('student_id')
        student_age = request.POST.get('student_age')
        student_level = request.POST.get('student_level')
        student_gender = request.POST.get('student_gender')
        student_image = request.POST.get('student_image')
        Pass = 1234

    # Basic validation
    if not student_name or not student_id or not student_age or not student_level or not student_gender or not student_image:
        messages.error(request, "All fields are required.")
        return render(request, 'Pages/AddStudent.html')

    try:
        # Convert student_id to int
        student_id = int(student_id)
    except ValueError:
        messages.error(request, "Student ID must be an integer.")
        return render(request, 'Pages/AddStudent.html')

    # Using raw SQL to insert data
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO StudentInformation 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, [student_name, student_id, student_age, student_level, student_gender, student_image, Pass])


    Id = student_id
    name = student_name
    Actor = 1
    Student_Path = "Student/TrainingImageStudent"
    Teacher_Path = "Teacher/TrainingImageTeacher"
    Parent_Path =  "Parent/TrainingImageParent"
    Student_Details = "Student/StudentDetails/StudentDetails.csv"
    Teacher_Details = "Teacher/TeacherDetails/TeacherDetails.csv"
    Parent_Details= "Parent/ParentDetails/ParentDetails.csv"
    Student_Labels = "Student/TrainingImageLabelStudent"
    Teacher_Labels = "Teacher/TrainingImageLabelTeacher"
    Parent_Labels = "Parent/TrainingImageLabelParent"

    if is_number(Id):
        cam = cv2.VideoCapture(0)
        harcascadePath = "haarcascade_default.xml"
        detector = cv2.CascadeClassifier(harcascadePath)
        sampleNum = 0

        while True:
            ret, img = cam.read()
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = detector.detectMultiScale(gray, 1.3, 5, minSize=(30,30),flags = cv2.CASCADE_SCALE_IMAGE)
            for(x,y,w,h) in faces:
                cv2.rectangle(img, (x, y), (x+w, y+h), (10, 159, 255), 2)
                sampleNum = sampleNum+1
                #saving the captured face in the dataset folder TrainingImag
                Path = ""
                Details = ""
                Labels = ""

                if Actor == 1:
                    cv2.imwrite(Student_Path + os.sep +name + "."+str(Id) + '.' +
                    str(sampleNum) + ".jpg", gray[y:y+h, x:x+w])
                    Path = Student_Path
                    Details = Student_Details
                    Labels = Student_Labels
                elif Actor == 2:
                    cv2.imwrite(Teacher_Path + os.sep +name + "."+Id + '.' +
                    str(sampleNum) + ".jpg", gray[y:y+h, x:x+w])
                    Path = Teacher_Path
                    Details = Teacher_Details
                    Labels = Teacher_Labels
                else:
                    cv2.imwrite(Parent_Path + os.sep +name + "."+Id + '.' +
                    str(sampleNum) + ".jpg", gray[y:y+h, x:x+w])
                    Path = Parent_Path
                    Details = Parent_Details
                    Labels = Parent_Labels 

        
                cv2.imshow('frame', img)
            if cv2.waitKey(100) & 0xFF == ord('q'):
                break
            elif sampleNum > 150:
                break
        cam.release()
        cv2.destroyAllWindows()
        row = [Id, name]
        with open(Details, 'a+') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerow(row)
        csvFile.close()
    else:
        if(is_number(Id)):
            print("Enter Alphabetical Name")
        if(name.isalpha()):
            print("Enter Numeric ID") 

    
    TrainImages(request, Path, Labels)

    return render(request, 'Pages/Main.html')




def ParentRegisteration(request):

    
    if request.method == 'POST':
        parent_name = request.POST.get('Parent_name')
        parent_id = request.POST.get('Parent_id')
        parent_image = request.POST.get('Parent_image')
        kid_id = request.POST.get('Kid_id')


    # Basic validation
    if not parent_name or not parent_id or not parent_image or not kid_id:
        messages.error(request, "All fields are required.")
        return render(request, 'Pages/AddParent.html')

    try:
        # Convert student_id to int
        parent_id = int(parent_id)
    except ValueError:
        messages.error(request, "Parent ID must be an integer.")
        return render(request, 'Pages/AddParent.html')

    # Using raw SQL to insert data
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO ParentInformation 
            VALUES (%s, %s, %s, %s)
        """, [parent_name, parent_id, parent_image, kid_id])


    Id = parent_id
    name = parent_name
    Actor = 3
    Student_Path = "Student/TrainingImageStudent"
    Teacher_Path = "Teacher/TrainingImageTeacher"
    Parent_Path =  "Parent/TrainingImageParent"
    Student_Details = "Student/StudentDetails/StudentDetails.csv"
    Teacher_Details = "Teacher/TeacherDetails/TeacherDetails.csv"
    Parent_Details= "Parent/ParentDetails/ParentDetails.csv"
    Student_Labels = "Student/TrainingImageLabelStudent"
    Teacher_Labels = "Teacher/TrainingImageLabelTeacher"
    Parent_Labels = "Parent/TrainingImageLabelParent"

    if is_number(Id):
        cam = cv2.VideoCapture(0)
        harcascadePath = "haarcascade_default.xml"
        detector = cv2.CascadeClassifier(harcascadePath)
        sampleNum = 0

        while True:
            ret, img = cam.read()
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = detector.detectMultiScale(gray, 1.3, 5, minSize=(30,30),flags = cv2.CASCADE_SCALE_IMAGE)
            for(x,y,w,h) in faces:
                cv2.rectangle(img, (x, y), (x+w, y+h), (10, 159, 255), 2)
                sampleNum = sampleNum+1
                #saving the captured face in the dataset folder TrainingImag
                Path = ""
                Details = ""
                Labels = ""

                if Actor == 1:
                    cv2.imwrite(Student_Path + os.sep +name + "."+str(Id) + '.' +
                    str(sampleNum) + ".jpg", gray[y:y+h, x:x+w])
                    Path = Student_Path
                    Details = Student_Details
                    Labels = Student_Labels
                elif Actor == 2:
                    cv2.imwrite(Teacher_Path + os.sep +name + "."+Id + '.' +
                    str(sampleNum) + ".jpg", gray[y:y+h, x:x+w])
                    Path = Teacher_Path
                    Details = Teacher_Details
                    Labels = Teacher_Labels
                else:
                    cv2.imwrite(Parent_Path + os.sep +name + "."+str(Id) + '.' +
                    str(sampleNum) + ".jpg", gray[y:y+h, x:x+w])
                    Path = Parent_Path
                    Details = Parent_Details
                    Labels = Parent_Labels 

        
                cv2.imshow('frame', img)
            if cv2.waitKey(100) & 0xFF == ord('q'):
                break
            elif sampleNum > 200:
                break
        cam.release()
        cv2.destroyAllWindows()
        row = [Id, name]
        with open(Details, 'a+') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerow(row)
        csvFile.close()
    else:
        if(is_number(Id)):
            print("Enter Alphabetical Name")
        if(name.isalpha()):
            print("Enter Numeric ID") 

    
    TrainImages(request, Path, Labels)

    return render(request, 'Pages/Main.html')








def counter_img(path):
    imgcounter = 1
    imagePaths = [os.path.join(path, f) for f in os.listdir(path)]
    for imagePath in imagePaths:
        print(str(imgcounter) + " Images Trained", end="\r")
        time.sleep(0.008)
        imgcounter += 1


def TeacherRegisteration(request):

    
    if request.method == 'POST':
        teacher_name = request.POST.get('teacher_name')
        teacher_id = request.POST.get('teacher_id')
        teacher_age = request.POST.get('teacher_age')
        teacher_gender = request.POST.get('teacher_gender')
        Course_Handle = request.POST.get('Course_handle')
        teacher_image = request.POST.get('teacher_image')
        Pass = 123

    # Basic validation
    if not teacher_name or not teacher_id or not teacher_age or not teacher_gender or not Course_Handle or not teacher_image:
        messages.error(request, "All fields are required.")
        return render(request, 'Pages/AddTeacher.html')

    try:
        # Convert student_id to int
        teacher_id = int(teacher_id)
        teacher_name = str(teacher_name)
    except ValueError:
        messages.error(request, "Student ID must be an integer.")
        return render(request, 'Pages/AddTeacher.html')

    # Using raw SQL to insert data
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO TeacherInformation 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, [teacher_name, teacher_id, teacher_age, teacher_gender, Course_Handle, teacher_image, Pass])


    return render(request, 'Pages/Main.html')











def takeImages(request):

    print("In the function")
    Id = input("Enter an ID: ")
    name = input("Enter a Name: ")
    Actor = input("Enter a Status/student,teacher or parent:  ")

    if(is_number(Id) and name.isalpha()):
        cam = cv2.VideoCapture(0)
        harcascadePath = "haarcascade_default.xml"
        detector = cv2.CascadeClassifier(harcascadePath)
        sampleNum = 0

        while True:
            ret, img = cam.read()
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = detector.detectMultiScale(gray, 1.3, 5, minSize=(30,30),flags = cv2.CASCADE_SCALE_IMAGE)
            for(x,y,w,h) in faces:
                cv2.rectangle(img, (x, y), (x+w, y+h), (10, 159, 255), 2)
                sampleNum = sampleNum+1
                #saving the captured face in the dataset folder TrainingImag
                Student_Path = "Student/TrainingImageStudent"
                Teacher_Path = "Teacher/TrainingImageTeacher"
                Parent_Path =  "Parent/TrainingImageParent"
                Student_Details = "Student/StudentDetails/StudentDetails.csv"
                Teacher_Details = "Teacher/TeacherDetails/TeacherDetails.csv"
                Parent_Details= "Parent/ParentDetails/ParentDetails.csv"
                Student_Labels = "Student/TrainingImageLabelStudent"
                Teacher_Labels = "Teacher/TrainingImageLabelTeacher"
                Parent_Labels = "Parent/TrainingImageLabelParent"

                Path = ""
                Details = ""
                Labels = ""

                if Actor == 1:
                    cv2.imwrite(Student_Path + os.sep +name + "."+Id + '.' +
                    str(sampleNum) + ".jpg", gray[y:y+h, x:x+w])
                    Path = Student_Path
                    Details = Student_Details
                    Labels = Student_Labels
                elif Actor == 2:
                    cv2.imwrite(Teacher_Path + os.sep +name + "."+Id + '.' +
                    str(sampleNum) + ".jpg", gray[y:y+h, x:x+w])
                    Path = Teacher_Path
                    Details = Teacher_Details
                    Labels = Teacher_Labels
                else:
                    cv2.imwrite(Parent_Path + os.sep +name + "."+Id + '.' +
                    str(sampleNum) + ".jpg", gray[y:y+h, x:x+w])
                    Path = Parent_Path
                    Details = Parent_Details
                    Labels = Parent_Labels 

        
                cv2.imshow('frame', img)
            if cv2.waitKey(100) & 0xFF == ord('q'):
                break
            elif sampleNum > 200:
                break
        cam.release()
        cv2.destroyAllWindows()
        row = [Id, name]
        with open(Details, 'a+') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerow(row)
        csvFile.close()
    else:
        if(is_number(Id)):
            print("Enter Alphabetical Name")
        if(name.isalpha()):
            print("Enter Numeric ID") 

    
    TrainImages(request, Path, Labels)

    return render(request, 'Pages/Main.html')

def Request(request):
    return render(request, 'Pages/AdminLogIn.html') 





