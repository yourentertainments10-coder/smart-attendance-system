import cv2
import numpy as np
from services.face_detection import detect_faces
import mediapipe as mp
mp_face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
from services.engagement_detection import process_landmarks
import os
import time
from models.attendance_model import mark_attendance
from models.engagement_model import record_engagement
from services.face_recognition_service import recognize_student
from utils.date_utils import get_current_date
def gen_frames():
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("❌ Camera failed to open")
        return
    print("✅ Camera started")
    while True:
        success, frame = cap.read()
        if not success:
            print("❌ Frame not captured")
            break
        faces = detect_faces(frame)
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
        engagement_data = process_landmarks(frame)
        if engagement_data and engagement_data[0]:
            landmarks, engagement_score, mesh_color = engagement_data
            for face_landmarks in landmarks:
                mp_drawing.draw_landmarks(
                    image=frame,
                    landmark_list=face_landmarks,
                    connections=mp_face_mesh.FACEMESH_TESSELATION,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=mp_drawing_styles.get_default_face_mesh_tesselation_style()
                )
            cv2.putText(frame, f"Engagement: {int(engagement_score*100)}%", (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.8, mesh_color, 2)
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    cap.release()
    cv2.destroyAllWindows()

def register_student(folder_name):
    path = f"datasets/student_faces/{folder_name}"
    os.makedirs(path, exist_ok=True)
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("❌ Camera failed to open")
        return 0
    saved = 0
    print(f"Capturing 20 face images for {folder_name}. Press 'q' to quit early.")
    while saved < 20:
        ret, frame = cap.read()
        if not ret:
            continue
        faces = detect_faces(frame)
        if len(faces) > 0:
            (x, y, w, h) = faces[0]
            pad = 20
            x = max(0, x - pad)
            y = max(0, y - pad)
            w = w + 2*pad
            h = h + 2*pad
            if w > 50 and h > 50:
                face_crop = frame[y:y+h, x:x+w]
                # Resize + improve quality
                face_crop = cv2.resize(face_crop, (300, 300))
                face_crop = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)
                face_crop = cv2.cvtColor(face_crop, cv2.COLOR_RGB2BGR)
                filename = f"{path}/img{saved}.jpg"
                cv2.imwrite(filename, face_crop)
                saved += 1
                print(f"Saved {saved}/20: {filename}")

        cv2.putText(frame, f'Saved: {saved}/20 Press q to quit', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.imshow('Register Student - Show Face', frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        time.sleep(0.2)
    cap.release()
    cv2.destroyAllWindows()
    print(f"Registration complete: {saved} images saved for {folder_name}")
    return saved

def gen_frames_attendance(app):
    with app.app_context():
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            print("❌ Camera failed")
            return
        print("✅ Attendance system running")
        engagement_history = []
        recent_predictions = []
        last_marked = {}
        while True:
            try:
                success, frame = cap.read()
                if not success:
                    break
                faces = detect_faces(frame)
                recog = "Unknown"
                if len(faces) > 0:
                    (x, y, w, h) = faces[0]
                    pad = 20
                    x = max(0, x - pad)
                    y = max(0, y - pad)
                    w = w + 2*pad
                    h = h + 2*pad
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
                    face_crop = frame[y:y+h, x:x+w]
                    recog_single = recognize_student(face_crop)
                    if recog_single is None:
                        recog_single = "Unknown"

                    recent_predictions.append(recog_single)
                    if len(recent_predictions) > 5:
                        recent_predictions.pop(0)

                    # majority voting
                    recog = max(set(recent_predictions), key=recent_predictions.count)

                    print("Recognized:", recog)
                    color = (0,255,0) if "Unknown" not in recog else (0,0,255)
                    cv2.putText(frame, f"Recognized: {recog}", (x, y-10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                    # Engagement tracking
                    engagement_data = process_landmarks(frame)
                    if engagement_data:
                        _, eng_score, _ = engagement_data
                        engagement_history.append(eng_score)

                # MARK ATTENDANCE
                if "Unknown" not in recog:
                    now = time.time()
                    if now - last_marked.get(recog, 0) > 60:
                        student_id = recog.split('_')[0]
                        if engagement_history:
                            avg_engagement = sum(engagement_history) / len(engagement_history)
                        else:
                            avg_engagement = 0.0
                        attendance_ok = mark_attendance(student_id, recog)
                        engagement_ok = record_engagement(student_id, avg_engagement)

                        if attendance_ok:
                            last_marked[recog] = now
                            cv2.putText(frame, "ATTENDANCE ✓", (10, 70),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,255), 2)

                        if not engagement_ok:
                            print("⚠️ Engagement not saved")

                        engagement_history = []  # Reset

                # Encode and stream
                ret, buffer = cv2.imencode('.jpg', frame)
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            except Exception as e:
                print("Frame processing error:", e)
                continue
        cap.release()
