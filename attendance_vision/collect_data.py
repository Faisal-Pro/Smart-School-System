import cv2
import os
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(BASE_DIR, 'dataset')
IMG_SIZE = (128, 128)
CAPTURE_DELAY = 0.2 

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

def collect_faces(student_id):
    path = os.path.join(DATASET_PATH, f'student_{student_id}')
    if not os.path.exists(path): 
        os.makedirs(path)

    cam = cv2.VideoCapture(0)
    count = 0
    last_capture_time = time.time()
    
    print(f"[SYSTEM] Starting SLOW Data Acquisition for ID: {student_id}")
    print(f"[INFO] Capturing 1 photo every {CAPTURE_DELAY} seconds.")
    print("[HINT] Slowly rotate your head to different angles.")

    while count < 100:
        ret, frame = cam.read()
        if not ret: break
        
        frame = cv2.flip(frame, 1)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = face_cascade.detectMultiScale(gray, 1.2, 7, minSize=(150, 150))

        current_time = time.time()

        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 165, 0), 2)
            
            if current_time - last_capture_time >= CAPTURE_DELAY:
                cx, cy = x + w//2, y + h//2
                side = max(w, h)
                x1, y1 = max(0, cx - side//2), max(0, cy - side//2)
                
                face_roi = gray[y1:y1+side, x1:x1+side]
                
                if face_roi.size > 0:

                    face_normalized = cv2.equalizeHist(face_roi)
                    face_final = cv2.resize(face_normalized, IMG_SIZE)
                    
                    count += 1
                    cv2.imwrite(os.path.join(path, f"{count}.jpg"), face_final)
                    
                    last_capture_time = current_time 
                    
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 255, 255), -1)

            cv2.putText(frame, f"SAMPLES: {count}/100", (20, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

            progress_w = int((count / 100) * frame.shape[1])
            cv2.rectangle(frame, (0, frame.shape[0]-10), (progress_w, frame.shape[0]), (0, 255, 0), -1)

        cv2.imshow('SLOW DATA COLLECTION', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q') or count >= 100:
            break

    cam.release()
    cv2.destroyAllWindows()
    print(f"[SUCCESS] Collected 100 high-quality samples.")

if __name__ == "__main__":
    sid = input("Enter Student ID: ")
    if sid:
        collect_faces(sid)