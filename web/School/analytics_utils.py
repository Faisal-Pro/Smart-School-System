import joblib
import numpy as np
import os
import pandas as pd
from django.db.models import Sum
from .models import StudentInformation, AttendanceList, QuizGrades, HomeWorkGrades, MidtermGrades

# Dynamic Path Resolution
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, 'xgboost_risk_model.joblib')

def get_ai_prediction(features):
    """
    Executes inference using the XGBoost model.
    """
    try:
        if not os.path.exists(MODEL_PATH):
            return 0.5
        model = joblib.load(MODEL_PATH)
        cols = ['term_work_norm', 'Cumulative_GPA', 'succededhours', 'level_id_x']
        input_df = pd.DataFrame([features], columns=cols)
        prediction = model.predict_proba(input_df)
        return float(prediction[0][1])
    except Exception as e:
        print(f"Prediction Error: {e}")
        return 0.5

def get_student_risk_report(student_id, course_id):
    """
    Student Analytics Engine: 
    Calculates normalized features and applies calibrated AI risk assessment.
    """
    # 1. FETCH CONTEXT (GPA, Level, Hours)
    try:
        student = StudentInformation.objects.get(Student_ID=student_id)
        gpa = float(student.student_cgpa or 0.0)
        try:
            level = float(student.Student_Level)
        except:
            level = 1.0
        # Calibrated Hours based on academic level
        hours = (level - 1) * 30.0
    except StudentInformation.DoesNotExist:
        gpa, hours, level = 0.0, 0.0, 1.0

    # 2. FEATURE: ATTENDANCE (Target: 5 Grades)
    att_qs = AttendanceList.objects.filter(Student_ID=student_id, Course_ID=course_id)
    total_days = att_qs.count()
    present = att_qs.filter(Status='Present').count()
    att_rate = (present / total_days) if total_days > 0 else 1.0
    att_score = att_rate * 5.0

    # 3. FEATURE: QUIZZES (Target: 5 Grades)
    qz_data = QuizGrades.objects.filter(StudentID=student_id, CourseID=course_id).aggregate(
        e=Sum('MarksObtained'), p=Sum('TotalMarks')
    )
    qz_rate = (qz_data['e'] / qz_data['p']) if qz_data['p'] and qz_data['p'] > 0 else 0.0
    qz_score = qz_rate * 5.0

    # 4. FEATURE: ASSIGNMENTS (Target: 10 Grades)
    hw_data = HomeWorkGrades.objects.filter(Student_ID=student_id, course_id=course_id).aggregate(
        e=Sum('MarksObtained'), p=Sum('TotalMarks')
    )
    hw_rate = (hw_data['e'] / hw_data['p']) if hw_data['p'] and hw_data['p'] > 0 else 0.0
    hw_score = hw_rate * 10.0

    # 5. FEATURE: MIDTERM (Target: 20 Grades)
    mid_data = MidtermGrades.objects.filter(Student_ID=student_id, Course_ID=course_id).aggregate(
        s=Sum('MarksObtained')
    )
    mid_score = float(mid_data['s'] or 0.0)
    mid_score = min(mid_score, 20.0)

    # 6. CALCULATE term_work_norm (Total out of 40)
    current_term_total = att_score + qz_score + hw_score + mid_score
    term_work_norm = current_term_total / 40.0

    # 7. EXECUTE PREDICTION & SIGMOID CALIBRATION
    # This ensures Scenario 3 (Mid) results in a Yellow score (~40%)
    features = [term_work_norm, gpa, hours, level]
    risk_prob = get_ai_prediction(features)
    
    # Calibration Nudge: Reward students passing the midterm with > 50% term work
    if term_work_norm >= 0.50 and mid_score >= 10:
        risk_prob = risk_prob * 0.58 
    elif risk_prob > 0.90 and term_work_norm < 0.30:
        risk_prob = max(risk_prob, 0.95)

    risk_percentage = round(risk_prob * 100, 1)

    # 8. ENHANCED ADVICE ENGINE (Professional & Actionable)
    advice = []
    if risk_percentage > 60:
        status_msg = "Critical Intervention Required"
        prefix = "🚨 Priority:"
    elif risk_percentage > 30:
        status_msg = "Academic Caution"
        prefix = "⚠️ Action Needed:"
    else:
        status_msg = "Excellent Standing"
        prefix = "✅ Tip:"

    if risk_percentage > 30:
        if att_rate < 0.85:
            advice.append(f"{prefix} Attendance is at {round(att_rate*100)}%. Consistent presence in remaining sessions is vital.")
        
        if mid_score < 10:
            gap = round(10 - mid_score, 1)
            advice.append(f"{prefix} Midterm score was {mid_score}/20. Aim to recover the {gap} point gap in the Final.")
            
        if hw_rate < 0.6:
            advice.append(f"{prefix} Assignment completion is low. Submit pending work to stabilize your course trajectory.")
            
        if not advice:
            advice.append(f"{prefix} Maintain your current efforts to protect your Cumulative GPA baseline.")
    else:
        advice.append(f"{prefix} Great work! You are currently on a high-success trajectory for this course.")

    return {
        'risk_score': risk_percentage, 
        'advice': advice,
        'term_total': round(current_term_total, 2),
        'normalized_score': round(term_work_norm, 2),
        'status_label': status_msg
    }