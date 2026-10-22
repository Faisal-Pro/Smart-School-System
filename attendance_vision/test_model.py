import cv2
import mediapipe as mp
import numpy as np
import os
import urllib.request
from tensorflow.keras.models import load_model #type: ignore
from collections import deque

BaseOptions = mp.tasks.BaseOptions
FaceLandmarker = mp.tasks.vision.FaceLandmarker
FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

model_path = "face_landmarker.task"
if not os.path.exists(model_path):
    print("[INFO] Downloading Face Landmarker model...")
    url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
    urllib.request.urlretrieve(url, model_path)

options = FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=model_path),
    running_mode=VisionRunningMode.VIDEO,
    num_faces=1
)
landmarker = FaceLandmarker.create_from_options(options)

try:
    id_model = load_model('face_id_deep.h5')
    print("[SUCCESS] Identity CNN Loaded.")
except:
    id_model = None
    print("[WARNING] face_id_deep.h5 not found. Identity will be 'Unknown'.")

gaze_history = deque(maxlen=10)
violation_counter = 0

def analyze_face(landmarks):
    """
    Calculates Head Pose and Eye Gaze.
    """
    nose = landmarks[4]
    l_cheek = landmarks[234]
    r_cheek = landmarks[454]
    top = landmarks[10]
    bottom = landmarks[152]

    head_x = (nose.x - l_cheek.x) / (r_cheek.x - l_cheek.x) - 0.5
    head_y = (nose.y - top.y) / (bottom.y - top.y) - 0.55 

    l_iris = landmarks[468]
    l_inner = landmarks[133]
    l_outer = landmarks[33]
    
    eye_width = l_inner.x - l_outer.x
    eye_ratio = (l_iris.x - l_outer.x) / eye_width if eye_width != 0 else 0.5

    return head_x, head_y, eye_ratio

cam = cv2.VideoCapture(0)

while cam.isOpened():
    ret, frame = cam.read()
    if not ret: break
    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape
    
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    timestamp = int(cam.get(cv2.CAP_PROP_POS_MSEC))
    result = landmarker.detect_for_video(mp_image, timestamp)
    
    status = "SECURE"
    color = (0, 255, 0)
    identity = "Scanning..."

    if result.face_landmarks:
        landmarks = result.face_landmarks[0]

        hx, hy, er = analyze_face(landmarks)
        gaze_history.append((hx, hy, er))

        avg_hx = sum(i[0] for i in gaze_history) / len(gaze_history)
        avg_hy = sum(i[1] for i in gaze_history) / len(gaze_history)
        avg_er = sum(i[2] for i in gaze_history) / len(gaze_history)

        head_ok = abs(avg_hx) < 0.15 and abs(avg_hy) < 0.18
        eyes_ok = 0.35 < avg_er < 0.65 
        
        if not head_ok or not eyes_ok:
            violation_counter += 1
            status = "!! LOOKING AWAY !!" if not head_ok else "!! EYES WANDERING !!"
        else:
            violation_counter = max(0, violation_counter - 1)

        if id_model and violation_counter % 10 == 0: 
            try:
                x_pts = [lm.x * w for lm in landmarks]
                y_pts = [lm.y * h for lm in landmarks]

                roi = frame[int(min(y_pts)-10):int(max(y_pts)+10), int(min(x_pts)-10):int(max(x_pts)+10)]
                roi_gray = cv2.resize(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY), (128, 128)).reshape(1,128,128,1)
                pred = id_model.predict(roi_gray, verbose=0)
                identity = f"ID_{np.argmax(pred)}" if np.max(pred) > 0.8 else "UNKNOWN"
            except: pass

        alert_active = violation_counter > 15
        color = (0, 0, 255) if alert_active else (0, 255, 0)

        for idx in [468, 473]:
            pt = landmarks[idx]
            cv2.circle(frame, (int(pt.x*w), int(pt.y*h)), 2, (255, 255, 255), -1)

        tx = int(w/2 + avg_hx * w * 2)
        ty = int(h/2 + avg_hy * h * 2)
        cv2.drawMarker(frame, (tx, ty), color, cv2.MARKER_CROSS, 20, 2)


    cv2.rectangle(frame, (0, 0), (w, 50), (10, 10, 10), -1)
    cv2.putText(frame, f"STATUS: {status} | USER: {identity}", (20, 35), 2, 0.7, color, 2)

    cv2.imshow('Strict Deep Proctor Pro', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cam.release()
landmarker.close()
cv2.destroyAllWindows()