import cv2
import numpy as np
from services.face_detection import detect_faces
import mediapipe as mp
mp_face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
from services.engagement_detection import process_landmarks
import os
import re
import time
from models.attendance_model import mark_attendance
from services.face_recognition_service import recognize_student

last_marked = {}
latest_status = ""
cooldown_active = False
cooldown_start = 0
last_seen_time = 0
FACE_TIMEOUT = 2


def gen_frames():
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        #print(" Camera failed to open")
        return

    #print(" Camera started")
    try:
        while True:
            try:
                success, frame = cap.read()
            except cv2.error as e:
                #print("Camera stream stopped:", e)
                break

            if not success:
                #print(" Frame not captured")
                time.sleep(0.1)
                continue
            if frame is None:
                continue

            faces = detect_faces(frame)
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            frame_bytes = buffer.tobytes()
            time.sleep(0.03)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    finally:
        cap.release()
        cv2.destroyAllWindows()


TARGET_IMAGES = 20
CAPTURE_INTERVAL = 0.5  # seconds between saved images
# Guided capture: pose variation is what makes recognition survive
# angle/lighting/distance changes later.
CAPTURE_STAGES = [
    ("Look STRAIGHT at the camera", 8),
    ("Turn head slightly LEFT", 3),
    ("Turn head slightly RIGHT", 3),
    ("Tilt chin UP, then DOWN", 3),
    ("Lean BACK from the camera", 3),
]


def _existing_gallery_images(path):
    if not os.path.exists(path):
        return []
    return [f for f in os.listdir(path)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))]


def register_student(student_id, name, allow_append=False):
    from services.face_recognition_service import (
        get_face_embedding, load_dataset, MIN_GALLERY_IMAGES
    )

    folder_name = f"{student_id}_{name.replace(' ', '_')}"
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base_dir, "..", "datasets", "student_faces", folder_name)

    existing_images = _existing_gallery_images(path)
    if existing_images and len(existing_images) >= MIN_GALLERY_IMAGES and not allow_append:
        print(f"Folder already has {len(existing_images)} images: {path}. Skipping duplicate capture.")
        return 0

    os.makedirs(path, exist_ok=True)

    # Continue numbering after the highest existing index so append never overwrites
    next_index = 0
    for f in existing_images:
        m = re.match(r"img(\d+)\.", f)
        if m:
            next_index = max(next_index, int(m.group(1)) + 1)

    to_capture = TARGET_IMAGES - len(existing_images)
    if to_capture <= 0:
        print(f"{folder_name} already has {len(existing_images)} images, nothing to capture.")
        return 0

    # One prompt per image; when appending, skip the straight-on prompts the
    # student most likely already has.
    prompts = []
    for text, count in CAPTURE_STAGES:
        prompts.extend([text] * count)
    prompts = prompts[TARGET_IMAGES - to_capture:]

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print(" Camera busy - close /attendance or /class_monitor first!")
        return 0

    saved = 0
    rejected = 0
    last_capture_time = 0.0
    print(f"Capturing {to_capture} face images for {folder_name}. Press 'q' to quit early.")

    while saved < to_capture:
        ret, frame = cap.read()
        if not ret or frame is None:
            time.sleep(0.05)
            continue

        display = frame.copy()
        now = time.time()
        faces = detect_faces(frame)

        if len(faces) > 0:
            x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
            pad = 20
            x1 = max(0, x - pad)
            y1 = max(0, y - pad)
            x2 = min(frame.shape[1], x + w + pad)
            y2 = min(frame.shape[0], y + h + pad)
            cv2.rectangle(display, (x1, y1), (x2, y2), (255, 0, 0), 2)

            if (x2 - x1) > 50 and (y2 - y1) > 50 and now - last_capture_time >= CAPTURE_INTERVAL:
                # Full-resolution crop, aspect preserved — no 160x160 squish.
                face_crop = frame[y1:y2, x1:x2]
                # Only keep images that actually produce an embedding, so every
                # gallery image is guaranteed usable for recognition.
                if get_face_embedding(face_crop) is not None:
                    filename = os.path.join(path, f"img{next_index}.jpg")
                    cv2.imwrite(filename, face_crop)
                    next_index += 1
                    saved += 1
                    last_capture_time = now
                    print(f"Saved {saved}/{to_capture}: {filename}")
                else:
                    rejected += 1

        prompt = prompts[saved] if saved < len(prompts) else prompts[-1]
        cv2.putText(display, prompt, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        cv2.putText(display, f"Saved: {saved}/{to_capture}  Press q to quit", (10, 65),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        if rejected >= 10 and rejected > saved * 2:
            cv2.putText(display, "Poor image quality - improve lighting / move closer",
                        (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        cv2.imshow('Register Student - Show Face', display)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    total = len(_existing_gallery_images(path))
    print(f"Registration complete: {saved} new images ({rejected} rejected), "
          f"{total} total for {folder_name}")
    load_dataset(force_reload=True)
    return saved


def gen_frames_attendance(app):
    global last_marked, cooldown_active, cooldown_start, last_seen_time,latest_status
    global status_message
    COOLDOWN_TIME = 3
    MESSAGE_GAP = 2


    with app.app_context():
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            print(" Camera failed")
            return

        print(" Attendance system running")
        cooldown_active = False
        cooldown_start = 0
        last_seen_time = 0
        recent_predictions = []
        last_shown = {}
        frame_count = 0
        last_recog = "Unknown"

        try:
            while True:
                try:
                    success, frame = cap.read()
                except cv2.error as e:
                    #print("Attendance camera stream stopped:", e)
                    break

                current_time = time.time()
                frame_count += 1
                fresh_recognition = False
               
                if not success:
                    time.sleep(0.1)
                    continue
                if frame is None:
                    continue

                faces = detect_faces(frame)
                recog = "Unknown"
                if len(faces) > 0:
                    (x, y, w, h) = faces[0]
                    pad = 20
                    x = max(0, x - pad)
                    y = max(0, y - pad)
                    w = w + 2 * pad
                    h = h + 2 * pad
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
                    face_crop = frame[y:y + h, x:x + w]               
                    if frame_count % 3 == 0:
                        fresh_recognition = True
                        recog_single = recognize_student(face_crop) or "Unknown"

                        recent_predictions.append(recog_single)
                        if len(recent_predictions) > 5:
                            recent_predictions.pop(0)

                        last_recog = max(set(recent_predictions), key=recent_predictions.count)

                    recog = last_recog
                    color = (0, 255, 0) if "Unknown" not in recog else (0, 0, 255)
                    cv2.putText(frame, f"Recognized: {recog}", (x, y - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                    if fresh_recognition and "Unknown" not in recog:
                        last_seen_time = time.time()
                        cv2.putText(frame, f"Welcome {recog}", (x, y + 50),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

                if fresh_recognition and "Unknown" not in recog:
                    now = time.time()
                    student_id = recog.split('_')[0]
                    
                    if student_id in last_shown and now - last_shown[student_id] < MESSAGE_GAP:
                        pass
                    else:
                        last_shown[student_id] = now
   
                    if student_id in last_marked and now - last_marked[student_id] < MESSAGE_GAP:
                        cv2.putText(frame, "ALREADY MARKED", (50, 80),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 3)

                        status_message = "ALREADY MARKED "
                        cooldown_active = True
                        cooldown_start = now

                    else:
                        attendance_ok = mark_attendance(student_id, recog)

                        if attendance_ok:
                            last_marked[student_id] = now
                            status_message = "ATTENDANCE MARKED"
                            latest_status = "ATTENDANCE MARKED"
                        else:
                            status_message = "ALREADY MARKED "
                            latest_status = "ATTENDANCE MARKED"                            

                        cooldown_active = True
                        cooldown_start = now

                if cooldown_active:
                    elapsed = time.time() - cooldown_start

                    if elapsed < COOLDOWN_TIME:
                        cv2.putText(frame, status_message, (50, 80),
                                 cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0,255,0), 3)

                        cv2.putText(frame, "NEXT STUDENT ->", (50, 130),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,0), 2)
                    else:
                        cooldown_active = False       

                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                frame_bytes = buffer.tobytes()
                time.sleep(0.03)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        except Exception as e:
            print("Frame processing error:", e)
        finally:
            cap.release()
            cv2.destroyAllWindows()
