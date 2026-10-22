from django.db import models

class Info(models.Model):
    Fname = models.CharField(max_length=250)
    id = models.CharField(max_length=10, primary_key=True)
    
    def __str__(self):
        return f"{self.id} - {self.Fname}"



class Courses(models.Model):
    course_name = models.CharField(max_length=250)
    course_id = models.IntegerField(primary_key=True)
    course_level = models.CharField(max_length=250)
    image_url = models.CharField(max_length=250) # <--- This is the name the DB knows
    link_url = models.CharField(max_length=250, default="#")
    class Meta:
        db_table = 'Courses'

class MidtermGrades(models.Model):
    Student_ID = models.IntegerField()
    Course_ID = models.IntegerField()
    Teacher_ID = models.IntegerField()
    MarksObtained = models.FloatField()
    TotalMarks = models.FloatField(default=20.0)  # Matches your real-life data scale
    ExamDate = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'MidtermGrades'

    def __str__(self):
        return f"Student {self.Student_ID} - Course {self.Course_ID}: {self.MarksObtained}/{self.TotalMarks}"

class AttendanceGate(models.Model):
    # Links the gate to a specific course
    course = models.ForeignKey('Courses', on_delete=models.CASCADE)
    # The actual toggle
    is_open = models.BooleanField(default=False)
    # Track when it was opened (useful for security/auto-close)
    opened_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        status = "OPEN" if self.is_open else "CLOSED"
        return f"{self.course.course_name} - {status}"


class New_previous_Profiles(models.Model):
    Student_ID = models.IntegerField()
    Teacher_ID = models.IntegerField()
    Student_url = models.CharField(max_length=250)
    Teacher_url = models.CharField(max_length=250)


    def __str__(self):
        return f"Student ID: {self.Student_ID}, Teacher ID: {self.Teacher_ID}"
    
class StudentInformation(models.Model):
    Student_Name = models.CharField(max_length=250)
    Student_ID = models.IntegerField(primary_key=True)
    Student_Age = models.CharField(max_length=250)
    Student_Level = models.CharField(max_length=250)
    Student_Gender = models.CharField(max_length=250)
    Student_Image = models.CharField(max_length=250)
    Student_Nationality = models.CharField(max_length=50, default="Unknown")
    Student_NationalID = models.CharField(max_length=20, unique=True, null=True, blank=True)
    Passwordd = models.CharField(max_length=250)
    student_cgpa = models.FloatField(null=True, blank=True, default = 0.0)
    entry_year = models.IntegerField(null=True, blank=True, default = 2024)

    class Meta:
        db_table = 'StudentInformation'  # <--- Add this line!
    def __str__(self):
        return self.Student_Name 

class StudentCourses(models.Model):
    # This matches the "s.Student_ID" in your SQL query
    Student_ID = models.IntegerField()
    course_name = models.CharField(max_length=255)
    course_id = models.IntegerField()
    grade = models.FloatField(null=True, blank=True)
    semester = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        db_table = 'StudentCourses' # This is the critical line that fixes the errorQL

class ParentInformation(models.Model):
    Parent_Name = models.CharField(max_length=250)
    Parent_ID = models.IntegerField(primary_key=True)
    Parent_NationalID = models.CharField(max_length=20, unique=True, null=True, blank=True) # New Field
    Parent_Image = models.CharField(max_length=250)
    Student_ID = models.ForeignKey(StudentInformation, on_delete=models.CASCADE)
    Passwordd = models.CharField(max_length=250, default="12345") # Ensure default is set

    class Meta:
        db_table = 'ParentInformation'  # <--- Add this line!
    def __str__(self):
        return self.Parent_Name

class TeacherInformation(models.Model):
    Teacher_Name = models.CharField(max_length=250)
    Teacher_Id = models.IntegerField(primary_key=True)
    Teacher_Age = models.CharField(max_length=250)
    Teacher_Gender = models.CharField(max_length=250)
    Teacher_NationalID = models.CharField(max_length=14, unique=True, null=True)
    Course_Handle = models.CharField(max_length=250)
    Teacher_Image = models.CharField(max_length=250)
    Passwordd = models.CharField(max_length=100, default='12345')

    class Meta:
        db_table = 'TeacherInformation'  # <--- Add this line!

    def __str__(self):
        return self.Teacher_Name 
    
class TeacherCourses(models.Model):
    teacher_id = models.IntegerField()
    course_id = models.IntegerField()

    class Meta:
        db_table = 'TeacherCourses' # Matches your Raw SQL query name

    def __str__(self):
        return f"Teacher {self.teacher_id} - Course {self.course_id}"
    
class StudentTeacherCommunications(models.Model):
    Message_text = models.CharField(max_length=4000)
    Message_ID = models.AutoField(primary_key=True) 
    Message_Date = models.CharField(max_length=250)
    Message_Hour = models.IntegerField()
    Message_Minute = models.IntegerField()
    Message_Source = models.IntegerField()
    Student_ID = models.ForeignKey(StudentInformation, on_delete=models.CASCADE)
    Teacher_ID = models.ForeignKey(TeacherInformation, on_delete=models.CASCADE)

    def __str__(self):
        return f"Message ID: {self.Message_ID}"


class CourseContents(models.Model):
    MaterialID = models.AutoField(primary_key=True) 
    PublisherImage = models.CharField(max_length=250)
    PublisherName = models.CharField(max_length=250)
    DateOfPublish = models.CharField(max_length=250)
    DescriptionText = models.CharField(max_length=4000)
    MaterialPath = models.CharField(max_length=250)
    MaterialIcon = models.CharField(max_length=250)
    course_id = models.ForeignKey(Courses, on_delete=models.CASCADE)


    def __str__(self):
        return self.MaterialID 
    
class Announcements(models.Model):
    publisher_name = models.CharField(max_length=250)
    description = models.TextField()
    pdf_file = models.FileField(upload_to='announcements/pdfs/', null=True, blank=True)
    video_file = models.FileField(upload_to='announcements/videos/', null=True, blank=True)
    date_posted = models.DateTimeField(auto_now_add=True)
    publisher_image = models.ImageField(upload_to='announcements/images/', null=True, blank=True)
    admin_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'Announcements' # Forcing the table name like we did before

    def __str__(self):
        return self.publisher_name
    
class Quizzes(models.Model):
    QuizID = models.AutoField(primary_key=True)
    QuizName = models.CharField(max_length=255)
    # Add this line to link the Quiz to a Teacher
    Teacher = models.ForeignKey('TeacherInformation', on_delete=models.CASCADE, db_column='Teacher_Id', null=True)
    course = models.ForeignKey('Courses', on_delete=models.CASCADE, db_column='course_id')
    QuizNumber = models.IntegerField(default=1) # You used this in your SQL too

    class Meta:
        db_table = 'Quizzes'

class Questions(models.Model):
    QuestionID = models.AutoField(primary_key=True)
    Quiz = models.ForeignKey(Quizzes, on_delete=models.CASCADE)
    QuestionText = models.TextField()
    QuestionType = models.CharField(max_length=50) # 'mcq' or 'written'
    Marks = models.IntegerField()

class Options(models.Model):
    OptionID = models.AutoField(primary_key=True)
    Question = models.ForeignKey(Questions, on_delete=models.CASCADE)
    OptionText = models.CharField(max_length=255)
    IsCorrect = models.BooleanField(default=False)

class StudentAnswers(models.Model):
    StudentID = models.IntegerField() # Or ForeignKey to StudentInformation
    Quiz = models.ForeignKey(Quizzes, on_delete=models.CASCADE)
    Question = models.ForeignKey(Questions, on_delete=models.CASCADE)
    AnswerType = models.CharField(max_length=50)
    StudentAnswer = models.TextField(null=True, blank=True)
    SelectedOption = models.IntegerField(null=True, blank=True)
    Flag = models.IntegerField(default=0)

class Assignments(models.Model):
    AssignmentId = models.AutoField(primary_key=True)
    FileContent = models.BinaryField(null=True)
    DescriptionContent = models.TextField()
    DeadlineDate = models.DateTimeField()
    AssignementNumber = models.IntegerField()
    PublisherImage = models.BinaryField(null=True)
    CreatedAt = models.DateTimeField(auto_now_add=True)
    course = models.ForeignKey('Courses', on_delete=models.CASCADE)
    Teacher_Id = models.IntegerField()
    TotalMark = models.IntegerField(default=100)
    Flag = models.IntegerField(default=1)

    class Meta:
        db_table = 'Assignments' # Forces the table name to be exactly "Assignments"

class HomeworkDelivered(models.Model):
    id = models.AutoField(primary_key=True)
    course_id = models.IntegerField()
    Student_ID = models.IntegerField()
    AssignmentId = models.IntegerField()
    DeliveredDate = models.DateTimeField(auto_now_add=True)
    FileContent = models.BinaryField()
    AssignmentNumber = models.IntegerField()
    TotalMark = models.IntegerField()
    Flag = models.IntegerField(default=0)

    class Meta:
        db_table = 'HomeworkDelivered'

class SubmittedAssignmentFlag(models.Model):
    AssignmentId = models.IntegerField()
    Flag = models.IntegerField(default=0)
    course_id = models.IntegerField()
    Student_ID = models.IntegerField()

    class Meta:
        db_table = 'SubmittedAssignmentFlag'

class HomeWorkGrades(models.Model):
    Student_ID = models.IntegerField()
    course_id = models.IntegerField()
    AssignmentNumber = models.IntegerField()
    MarksObtained = models.FloatField()
    TotalMarks = models.FloatField()
    Feedback = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'HomeWorkGrades'

class QuizGrades(models.Model):
    StudentID = models.IntegerField()
    CourseID = models.IntegerField()
    QuizNumber = models.IntegerField()
    QuestionID = models.IntegerField() # Usually grades are stored per question or per quiz
    MarksObtained = models.FloatField()
    TotalMarks = models.FloatField()

    class Meta:
        db_table = 'QuizGrades'

class QuizTakeStatus(models.Model):
    Student_ID = models.IntegerField()
    # Link to the Quiz
    Quiz = models.ForeignKey('Quizzes', on_delete=models.CASCADE, db_column='QuizID')
    IsTaken = models.IntegerField(default=0) # 0 for No, 1 for Yes
    TakenDate = models.DateTimeField(null=True, blank=True)
    course_id = models.IntegerField()

    class Meta:
        db_table = 'QuizTakeStatus'

class TeacherSchedule(models.Model):
    teacher_id = models.IntegerField()  # Links to your TeacherInformation ID
    day = models.CharField(max_length=20)   # e.g., 'Monday'
    start_time = models.CharField(max_length=20) # e.g., '08:00 AM'
    end_time = models.CharField(max_length=20)   # e.g., '10:00 AM'
    course_name = models.CharField(max_length=250)
    room = models.CharField(max_length=50)

    class Meta:
        db_table = 'TeacherSchedule'  # This matches your raw SQL query

    def __str__(self):
        return f"{self.course_name} on {self.day}"

class CourseAnnouncementReadStatus(models.Model):
    Student_ID = models.IntegerField()
    Announcement_ID = models.IntegerField()
    IsRead = models.BooleanField(default=False)

    class Meta:
        db_table = 'CourseAnnouncementReadStatus'

class FinalGrade(models.Model):
    # Defining the fields based on your SELECT query
    student_id = models.IntegerField()  # Usually a ForeignKey, but using Integer for raw SQL compatibility
    course_id = models.IntegerField()
    total_assignment = models.FloatField(db_column='TotalAssignment')
    total_quiz_mark = models.FloatField(db_column='TotalQuizMark')
    midterm = models.FloatField(db_column='MidTerm')
    final = models.FloatField(db_column='Final')
    class_participation = models.FloatField(db_column='ClassParticipation')
    class_attendance = models.FloatField(db_column='ClassAttendance')
    credit = models.IntegerField(db_column='Credit')
    student_status = models.CharField(max_length=50, db_column='StudentStatus')
    total = models.FloatField(db_column='Total')

    class Meta:
        db_table = 'School_finalgrade'  # This is the most likely name in your SQLite DB

class AttendanceList(models.Model):
    Student_ID = models.CharField(max_length=100)
    Course_ID = models.IntegerField()
    Teacher_ID = models.IntegerField()
    Date = models.DateField(auto_now_add=True)
    Status = models.CharField(max_length=10) # 'Present' or 'Absent'

    class Meta:
        db_table = 'AttendanceList' # This forces the name to match your code

class AnnouncementReadStatus(models.Model):
    # We use IntegerFields to match the raw IDs you are passing in your loops
    Teacher_Id = models.IntegerField(null=True, blank=True)
    Student_ID = models.IntegerField(null=True, blank=True)
    AnnouncementId = models.IntegerField()
    IsRead = models.IntegerField(default=0)
    ReadDate = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'AnnouncementReadStatus' # This matches your SQL query exactly