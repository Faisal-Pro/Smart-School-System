import cv2
import tensorflow as tf
import numpy as np
import csv
from datetime import datetime, timedelta
from screeninfo import get_monitors  # Import screeninfo to get screen dimensions
from django.shortcuts import render
import ctypes  # Add this import

# Function to extract features
def extract_features(image):
    feature = np.array(image)
    feature = feature.reshape(1, 100, 100, 1)
    return feature / 255.0

# Function to draw rounded rectangle
def draw_rounded_rectangle(img, pt1, pt2, color, thickness, radius=20):
    x1, y1 = pt1
    x2, y2 = pt2
    cv2.line(img, (x1 + radius, y1), (x2 - radius, y1), color, thickness)
    cv2.line(img, (x1, y1 + radius), (x1, y2 - radius), color, thickness)
    cv2.ellipse(img, (x1 + radius, y1 + radius), (radius, radius), 180, 0, 90, color, thickness)
    cv2.line(img, (x2 - radius, y1), (x2, y1 + radius), color, thickness)
    cv2.line(img, (x2, y1 + radius), (x2, y2 - radius), color, thickness)
    cv2.ellipse(img, (x2 - radius, y1 + radius), (radius, radius), 270, 0, 90, color, thickness)
    cv2.line(img, (x1 + radius, y2), (x2 - radius, y2), color, thickness)
    cv2.line(img, (x1, y1 + radius), (x1, y2 - radius), color, thickness)
    cv2.ellipse(img, (x1 + radius, y2 - radius), (radius, radius), 90, 0, 90, color, thickness)
    cv2.line(img, (x2 - radius, y2), (x2, y2 - radius), color, thickness)
    cv2.ellipse(img, (x2 - radius, y2 - radius), (radius, radius), 0, 0, 90, color, thickness)

def Test(request):
    # Load the trained model
    model = tf.keras.models.load_model("TrainedModel.h5")

    # Load Haar Cascade for face detection
    haar_file = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    face_cascade = cv2.CascadeClassifier(haar_file)
    webcam = cv2.VideoCapture(0)

    # Get screen dimensions
    monitor = get_monitors()[0]  # Get the first monitor
    screen_width = monitor.width
    screen_height = monitor.height

    # Set the webcam resolution to screen size
    webcam.set(cv2.CAP_PROP_FRAME_WIDTH, screen_width)
    webcam.set(cv2.CAP_PROP_FRAME_HEIGHT, screen_height)

    # Create a fullscreen window
    cv2.namedWindow("Attendance", cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty("Attendance", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    # Bring the OpenCV window to the front
    hwnd = ctypes.windll.user32.FindWindowW(None, "Attendance")
    if hwnd:  # Check if the window handle is found
        ctypes.windll.user32.ShowWindow(hwnd, 5)  # SW_SHOW
        ctypes.windll.user32.SetForegroundWindow(hwnd)

    labels = {0: '20170455', 1: '20190675', 2: 'Unknown'}

    start_time = datetime.now()
    end_time = start_time + timedelta(minutes=1.5)
    data = [['Name', 'ID', 'Time']]

    while True:
        ret, im = webcam.read()
        if not ret:
            break

        overlay = im.copy()
        output = im.copy()

        gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(im, 1.3, 5)
        current_time = datetime.now().strftime('%H:%M:%S')
        remaining_time = (end_time - datetime.now()).total_seconds()

        if remaining_time <= 0:
            break

        countdown_text = f"Time left: {int(remaining_time // 60)}:{int(remaining_time % 60):02}"
        cv2.rectangle(overlay, (10, 10), (300, 60), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.4, im, 0.6, 0, im)

        cv2.putText(im, countdown_text, (20, 45), cv2.FONT_HERSHEY_DUPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

        try:
            for (p, q, r, s) in faces:
                image = gray[q:q + s, p:p + r]
                draw_rounded_rectangle(im, (p, q), (p + r, q + s), (0, 255, 0), 3, radius=15)

                image = cv2.resize(image, (100, 100))
                img = extract_features(image)
                pred = model.predict(img)
                prediction_label = labels[pred.argmax()]
                prediction_confidence = np.max(pred)  # Highest confidence score

                label_bg = overlay.copy()
                cv2.rectangle(label_bg, (p - 10, q - 30), (p + 150, q), (50, 50, 50), -1)
                cv2.addWeighted(label_bg, 0.6, im, 0.4, 0, im)

                cv2.putText(im, prediction_label, (p, q - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
                if prediction_label == 'Unknown':
                    continue
                else:
                    data.append([' ', prediction_label, current_time])

            cv2.imshow("Attendance", im)
            key = cv2.waitKey(1)
            if key == ord('q'):
                break

        except cv2.error:
            pass

    # Save attendance data to CSV
    with open('Attendance.csv', mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(data)

    webcam.release()
    cv2.destroyAllWindows()
    
    return render(request, 'Pages/UploadMaterials.html')
