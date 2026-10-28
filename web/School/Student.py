import os
import glob
import cv2
import base64
import json
import numpy as np
from django.conf import settings
from django.core.cache import cache
from django.contrib import messages
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render, redirect
from .security import verify_password, login_session

# ---------------- CONFIG ----------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_PATH = os.path.join(BASE_DIR, "dataset")

# LBPH distance: LOWER = better match. Change it in settings.py (FACE_THRESHOLD = 70)
FACE_THRESHOLD = getattr(settings, "FACE_THRESHOLD", 75)
MAX_SAMPLES = 30  # face photos kept per student
MAX_LOGIN_FAILS = 5  # wrong passwords before a temporary lock
LOCK_SECONDS = 300  # lock time (5 minutes)

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)


# ---------------- HELPERS ----------------
def get_face_roi(img):
    """Detect the face and crop it (so the AI never matches the room/background)."""
    if img is None:
        return None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.2, 5, minSize=(100, 100))
    if len(faces) == 0:
        return None
    x, y, w, h = faces[0]
    return cv2.resize(gray[y : y + h, x : x + w], (200, 200))


def _decode(data):
    """'data:image/jpeg;base64,...' -> OpenCV image (or None)."""
    try:
        _, imgstr = data.split(";base64,")
        nparr = np.frombuffer(base64.b64decode(imgstr), np.uint8)
        return cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    except Exception:
        return None


def _student_dir(sid):
    return os.path.join(DATASET_PATH, f"student_{sid}")


def _load_samples(sid):
    """master.jpg (old enrolment) + sample_*.jpg (new enrolment)."""
    folder = _student_dir(sid)
    files = [os.path.join(folder, "master.jpg")]
    files += sorted(glob.glob(os.path.join(folder, "sample_*.jpg")))
    imgs = []
    for f in files:
        if os.path.exists(f):
            im = cv2.imread(f, cv2.IMREAD_GRAYSCALE)
            if im is not None:
                imgs.append(im)
    return imgs


def _distance(sid, face):
    """Return the LBPH distance between `face` and student `sid` (None = not enrolled)."""
    imgs = _load_samples(sid)
    if not imgs:
        return None
    rec = cv2.face.LBPHFaceRecognizer_create()  # own recognizer per call = thread-safe
    rec.train(imgs, np.zeros(len(imgs), dtype=np.int32))
    _, confidence = rec.predict(face)
    return confidence


def _session_student(request):
    if request.session.get("role") == "student":
        return str(request.session.get("user_id"))
    return None


# ================= REGISTRATION API =================
def capture_frame_api(request, student_id):
    """Called by register_face.html for every camera frame."""
    if request.method != "POST":
        return JsonResponse({"status": "failed"})
    try:
        data = json.loads(request.body)
        frame = _decode(data.get("image") or "")
        count = int(data.get("count", 0))

        folder = _student_dir(student_id)
        os.makedirs(folder, exist_ok=True)

        if count == 0:  # a new enrolment starts: remove the old photos
            for old in glob.glob(os.path.join(folder, "sample_*.jpg")):
                os.remove(old)

        face = get_face_roi(frame)
        if face is None:
            return JsonResponse({"status": "no_face"})

        saved = len(glob.glob(os.path.join(folder, "sample_*.jpg")))
        if saved >= MAX_SAMPLES:
            return JsonResponse({"status": "done", "saved": saved})

        cv2.imwrite(os.path.join(folder, f"sample_{saved + 1:02d}.jpg"), face)
        if saved == 0:
            cv2.imwrite(os.path.join(folder, "master.jpg"), face)
        return JsonResponse(
            {"status": "success", "saved": saved + 1, "total": MAX_SAMPLES}
        )
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})


# ================= FACE LOGIN + ATTENDANCE =================
def face_login_process(request):
    if request.method != "POST":
        return render(request, "pages/StudentLogIn.html")

    data = request.POST.get("image")
    course_id = request.POST.get("course_id")
    if not data:
        return JsonResponse({"status": "no_data"})

    frame = _decode(data)
    if frame is None:
        return JsonResponse({"status": "error", "message": "bad image"})

    face = get_face_roi(frame)
    if face is None:
        return JsonResponse({"status": "not_recognized", "message": "No face detected"})

    attendance = bool(course_id) and course_id != "None"

    # ---- who must the face belong to? ----
    if attendance:
        # attendance: ONLY the logged-in student (never trust an id sent by the browser)
        expected = _session_student(request)
        if expected is None:
            return JsonResponse({"status": "not_logged_in"})
    else:
        expected = (request.POST.get("student_id") or "").strip() or None

    # ---- match ----
    if expected:  # 1:1 verification
        if not expected.isdigit():
            return JsonResponse({"status": "not_recognized"})
        dist = _distance(expected, face)
        if dist is None:
            return JsonResponse({"status": "not_enrolled"})
        matched = expected if dist < FACE_THRESHOLD else None
    else:  # 1:N search (face only login)
        matched, dist = None, 1e9
        if os.path.isdir(DATASET_PATH):
            for folder in os.listdir(DATASET_PATH):
                if not folder.startswith("student_"):
                    continue
                sid = folder.split("_", 1)[1]
                d = _distance(sid, face)
                if d is not None and d < dist:
                    dist, matched = d, sid
        if dist >= FACE_THRESHOLD:
            matched = None

    if matched is None:
        print(f"[FACE] rejected (distance {dist:.1f}, limit {FACE_THRESHOLD})")
        return JsonResponse({"status": "not_recognized"})

    # ---- success ----
    if attendance:
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE AttendanceList SET Status = 'Present'
                    WHERE Student_ID = %s AND Course_ID = %s
                    AND Status = 'Absent' AND Date = date('now', 'localtime')
                    """,
                    [matched, course_id],
                )
            return JsonResponse({"status": "success", "mode": "attendance", "sid": matched})
        except Exception as e:
            return JsonResponse({"status": "db_error", "message": str(e)})

    login_session(request, "student", matched)
    return JsonResponse({"status": "success", "mode": "login", "sid": matched})


# ================= PAGES =================
def register_face_page(request, student_id):
    return render(request, "pages/register_face.html", {"StudentID": student_id})


def Request(request):
    return render(request, "pages/StudentLogIn.html")


def attendance_verification_page(request, course_id, student_id):
    return render(
        request,
        "pages/AttendanceCamera.html",
        {"CourseID": course_id, "StudentID": student_id},
    )


def check_attendance_status(request, course_id):
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*) FROM AttendanceList
                WHERE Course_ID = %s AND Status = 'Absent'
                AND Date = date('now', 'localtime')
                """,
                [course_id],
            )
            return JsonResponse({"is_active": cursor.fetchone()[0] > 0})
    except Exception:
        return JsonResponse({"is_active": False})


# ================= PASSWORD LOGIN (with lock) =================
def _client_key(request, sid):
    ip = request.META.get("REMOTE_ADDR", "?")
    return f"stu_fail_{ip}_{sid}"


def LogInAccount(request):
    if request.method != "POST":
        return redirect("StudentLogInPage")

    sid = (request.POST.get("id") or "").strip()
    pwd = request.POST.get("password") or ""
    key = _client_key(request, sid)

    if cache.get(key, 0) >= MAX_LOGIN_FAILS:
        messages.error(request, "Too many wrong attempts. Try again in 5 minutes.")
        return redirect("StudentLogInPage")

    row = None
    if sid.isdigit():
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
            cache.delete(key)
            login_session(request, "student", row[0])
            return redirect(f"/StudentDashboard/{row[0]}/")

    cache.set(key, cache.get(key, 0) + 1, LOCK_SECONDS)
    messages.error(request, "Wrong ID or password.")
    return redirect("StudentLogInPage")


def register_face_view(request, student_id):
    return redirect("AdminDashboard")
