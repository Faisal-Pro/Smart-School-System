import os
import cv2
import base64
import numpy as np
import json
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from .security import verify_password, login_session

# --- CONFIG ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_PATH = os.path.join(BASE_DIR, "dataset")

# Initialize the Deep Learning Recognizer and Face Detector
# These are built-in to OpenCV; no extra .xml or .onnx downloads required for LBPH
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)
recognizer = cv2.face.LBPHFaceRecognizer_create()


def get_face_roi(img):
    """
    Helper to detect and crop the face.
    This prevents the AI from 'matching' the background/room.
    """
    if img is None:
        return None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Detect faces
    faces = face_cascade.detectMultiScale(gray, 1.2, 5, minSize=(100, 100))

    if len(faces) == 0:
        return None  # No face detected (this stops 'hand-only' logins)

    # Get the coordinates of the first face
    x, y, w, h = faces[0]
    face_crop = gray[y : y + h, x : x + w]

    # Standardize size so the recognizer compares apples to apples
    return cv2.resize(face_crop, (200, 200))


# ================= REGISTRATION API =================
@csrf_exempt
def capture_frame_api(request, student_id):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            image_data = data.get("image")
            count = int(data.get("count", 0))

            path = os.path.join(DATASET_PATH, f"student_{student_id}")
            if not os.path.exists(path):
                os.makedirs(path)

            # We capture the master image on the very first frame
            if count == 0:
                _, imgstr = image_data.split(";base64,")
                nparr = np.frombuffer(base64.b64decode(imgstr), np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                face = get_face_roi(frame)
                if face is not None:
                    # Save only the face texture (the ROI) as master
                    cv2.imwrite(os.path.join(path, "master.jpg"), face)
                    print(f"--- SUCCESS: Master Face Saved for ID {student_id} ---")
                    return JsonResponse({"status": "success"})
                else:
                    return JsonResponse(
                        {"status": "error", "message": "No face detected"}
                    )

            return JsonResponse({"status": "success"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})

    return JsonResponse({"status": "failed"})


@csrf_exempt
def face_login_process(request):
    if request.method != "POST":
        return render(request, "pages/StudentLogIn.html")

    data = request.POST.get("image")
    course_id = request.POST.get("course_id")
    # If student_id is missing from POST, try to get it from the session
    student_id = request.POST.get("student_id") or request.session.get("student_id")

    if not data:
        return JsonResponse({"status": "no_data"})

    # --- 1. DECODING ---
    try:
        _, imgstr = data.split(";base64,")
        nparr = np.frombuffer(base64.b64decode(imgstr), np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})

    # --- 2. ROI ---
    current_face = get_face_roi(frame)
    if current_face is None:
        return JsonResponse({"status": "not_recognized", "message": "No face detected"})

    # --- 3. INFERENCE ---
    best_student_id = None
    lowest_confidence = 200.0

    for folder in os.listdir(DATASET_PATH):
        if not folder.startswith("student_"):
            continue
        sid = folder.split("_")[1]
        master_path = os.path.join(DATASET_PATH, folder, "master.jpg")
        if not os.path.exists(master_path):
            continue

        master_face = cv2.imread(master_path, cv2.IMREAD_GRAYSCALE)
        recognizer.train([master_face], np.array([int(sid)]))
        label, confidence = recognizer.predict(current_face)

        if confidence < lowest_confidence:
            lowest_confidence = confidence
            best_student_id = sid

    # --- 4. IMPROVED DECISION LOGIC ---
    # If the AI is confident (Conf < 75)
    if lowest_confidence < 75:

        # If we have an expected ID, they must match (Security check)
        if student_id and student_id != "None":
            if str(best_student_id) != str(student_id):
                print(
                    f"[REJECTED] ID Mismatch: Expected {student_id}, Got {best_student_id}"
                )
                return JsonResponse({"status": "not_recognized"})

        # If we reached here, it's either a match or we're in "Discovery" mode
        final_sid = (
            student_id if student_id and student_id != "None" else best_student_id
        )

        # SCENARIO A: ATTENDANCE
        if course_id and course_id != "None":
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE AttendanceList SET Status = 'Present'
                        WHERE Student_ID = %s AND Course_ID = %s 
                        AND Status = 'Absent' AND Date = date('now', 'localtime')
                    """,
                        [final_sid, course_id],
                    )
                return JsonResponse(
                    {"status": "success", "mode": "attendance", "sid": final_sid}
                )
            except Exception as e:
                return JsonResponse({"status": "db_error", "message": str(e)})

        # SCENARIO B: LOGIN
        else:
            login_session(request, "student", final_sid)
            print(f"[SUCCESS] Face Login: {final_sid}")
            return JsonResponse(
                {"status": "success", "mode": "login", "sid": final_sid}
            )

    print(f"[REJECTED] Low Confidence: {lowest_confidence}")
    return JsonResponse({"status": "not_recognized"})


# ================= VIEWS =================
def register_face_page(request, student_id):
    return render(request, "pages/register_face.html", {"StudentID": student_id})


def Request(request):
    return render(request, "pages/StudentLogIn.html")


def attendance_verification_page(request, course_id, student_id):
    context = {
        "CourseID": course_id,
        "StudentID": student_id,
    }
    return render(request, "pages/attendancecamera.html", context)


def check_attendance_status(request, course_id):
    try:
        with connection.cursor() as cursor:
            # We check for ANY 'Absent' status for this course today
            # Using date('now', 'localtime') ensures it matches your computer's clock
            cursor.execute(
                """
                SELECT COUNT(*) FROM AttendanceList 
                WHERE Course_ID = %s 
                AND Status = 'Absent' 
                AND Date = date('now', 'localtime')
            """,
                [course_id],
            )

            count = cursor.fetchone()[0]
            return JsonResponse({"is_active": count > 0})
    except Exception as e:
        return JsonResponse({"is_active": False})


def LogInAccount(request):
    if request.method == "POST":
        sid = (request.POST.get("id") or "").strip()
        pwd = request.POST.get("password") or ""
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT Student_ID, Passwordd FROM StudentInformation WHERE Student_ID=%s",
                [sid],
            )
            row = cursor.fetchone()
        if row:
            ok, new_hash = verify_password(pwd, row[1])
            if ok:
                if new_hash:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "UPDATE StudentInformation SET Passwordd=%s WHERE Student_ID=%s",
                            [new_hash, row[0]],
                        )
                login_session(request, "student", row[0])
                return redirect(f"/StudentDashboard/{row[0]}/")
    return redirect("StudentLogInPage")


def register_face_view(request, student_id):
    return redirect("AdminDashboard")
