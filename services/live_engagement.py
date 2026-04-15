
import cv2
import numpy as np
import time
from ultralytics import YOLO
import mediapipe as mp

from services.face_recognition_service import recognize_student, CLASS_MONITOR_THRESHOLD
from services.face_detection import detect_faces
from services.engagement_detection import process_landmarks
from models.engagement_model import record_engagement
from utils.date_utils import get_current_date

model = YOLO("yolov8n.pt")
PROCESS_EVERY_N_FRAMES = 3
SAVE_INTERVAL = 20
MIN_DETECTION_CONFIDENCE = 0.55
MIN_FACE_SIZE = 80
FACE_PADDING_RATIO = 0.2
STUDENT_STALE_TIMEOUT = 3
SMOOTHING_ALPHA = 0.3
FACE_SIZE = (160, 160)

active_students_state = {}


def calculate_engagement(face_crop, landmarks_data, phone_detected=False):
    score = 0.0
    if face_crop is not None and face_crop.size > 0:
        score += 0.3
    if landmarks_data:
        _, eng_score, _ = landmarks_data
        score += eng_score * 0.4
    if not phone_detected:
        score += 0.3
    return min(score, 1.0)


def _box_center(box):
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def _squared_distance(box_a, box_b):
    ax, ay = _box_center(box_a)
    bx, by = _box_center(box_b)
    return (ax - bx) ** 2 + (ay - by) ** 2


def _match_phones_to_people(persons, phone_boxes):
    for person in persons:
        person["phone_detected"] = False

    for phone_box in phone_boxes:
        nearest_person = None
        nearest_distance = None
        phone_width = max(phone_box[2] - phone_box[0], 1)
        phone_height = max(phone_box[3] - phone_box[1], 1)
        max_distance = max(phone_width, phone_height, 80) ** 2

        for person in persons:
            distance = _squared_distance(person["bbox"], phone_box)
            if nearest_distance is None or distance < nearest_distance:
                nearest_distance = distance
                nearest_person = person

        if nearest_person is not None and nearest_distance is not None and nearest_distance <= max_distance:
            nearest_person["phone_detected"] = True


def _padded_face_crop(person_crop, face_box):
    fx, fy, fw, fh = face_box
    pad_x = int(fw * FACE_PADDING_RATIO)
    pad_y = int(fh * FACE_PADDING_RATIO)
    x1 = max(0, fx - pad_x)
    y1 = max(0, fy - pad_y)
    x2 = min(person_crop.shape[1], fx + fw + pad_x)
    y2 = min(person_crop.shape[0], fy + fh + pad_y)
    crop = person_crop[y1:y2, x1:x2]
    return crop, (x1, y1, x2, y2)


def preprocess_face(face_crop):
    if face_crop is None or face_crop.size == 0:
        return None
    face_crop = cv2.resize(face_crop, FACE_SIZE)
    face_crop = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)
    return face_crop


def process_class_frame(frame):
    results = model(frame, verbose=False)
    persons = []
    phone_boxes = []

    for r in results:
        boxes = r.boxes
        if boxes is None:
            continue

        for box in boxes:
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            if conf < 0.55:
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0])
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(frame.shape[1], x2)
            y2 = min(frame.shape[0], y2)

            if cls == 67:  # cellphone
                phone_boxes.append((x1, y1, x2, y2))
                continue
            if cls != 0:  # person
                continue

            person_crop = frame[y1:y2, x1:x2]
            if person_crop.size == 0:
                continue

            local_faces = detect_faces(person_crop)
            if len(local_faces) == 0:
                continue

            fx, fy, fw, fh = max(local_faces, key=lambda f: f[2]*f[3])
            if fw < 80 or fh < 80:
                continue

            face_crop, padded_face_box = _padded_face_crop(person_crop, (fx, fy, fw, fh))
            if face_crop.size == 0:
                continue

            persons.append({
                "face_crop": face_crop,
                "bbox": (x1, y1, x2, y2),
                "face_bbox": (x1 + padded_face_box[0], y1 + padded_face_box[1], x1 + padded_face_box[2], y1 + padded_face_box[3]),
                "phone_detected": False,
            })

    _match_phones_to_people(persons, phone_boxes)
    return persons


def get_active_students():
    global active_students_state 
    return active_students_state


def gen_class_frames():
    global active_students_state

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("❌ Class monitor camera failed")
        return

    print("✅ Class engagement monitor started")

    frame_count = 0
    active_students = {}
    last_saved = {}
    engagement_history = {}

    try:
        while True:
            success, frame = cap.read()
            if not success or frame is None:
                continue

            frame_count += 1
            now = time.time()

            if frame_count % PROCESS_EVERY_N_FRAMES != 0:
                for idx, (name, data) in enumerate(active_students.items()):
                    color = (0, 0, 255) if data["phone"] else (0, 255, 0)
                    cv2.putText(frame, f"{name}: {int(data['score'] * 100)}%", (10, 30 + idx * 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                ret, buffer = cv2.imencode('.jpg', frame)
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n' + b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                continue

            persons = process_class_frame(frame)
            unknown_count = 0

            for person in persons:
                face_crop = person["face_crop"]
                if face_crop is None or face_crop.size == 0:
                    continue

                face_crop = preprocess_face(face_crop)
                if face_crop is None:
                    continue

                name = recognize_student(face_crop, threshold=CLASS_MONITOR_THRESHOLD)
                if name in (None, "Unknown"):
                    unknown_count += 1
                    continue

                x1, y1, x2, y2 = person["bbox"]
                color = (0, 0, 255) if person["phone_detected"] else (0, 255, 0)

                landmarks_data = None
                if face_crop is not None and face_crop.size > 0:
                    landmarks_data = process_landmarks(face_crop)

                raw_score = calculate_engagement(face_crop, landmarks_data, person["phone_detected"])
                previous_score = active_students.get(name, {}).get("score", raw_score)
                score = (1 - SMOOTHING_ALPHA) * previous_score + SMOOTHING_ALPHA * raw_score

                active_students[name] = {"score": score,"phone": person["phone_detected"],"last_seen": now,}
                

                if name not in engagement_history:
                    engagement_history[name] = []
                engagement_history[name].append(score)

                if name not in last_saved or now - last_saved[name] > SAVE_INTERVAL:
                    avg_engagement = sum(engagement_history[name]) / len(engagement_history[name])
                    try:
                        record_engagement(name.split('_')[0], avg_engagement)
                    except Exception as e:
                        print("db write skipped",e)
                    last_saved[name] = now
                    engagement_history[name] = engagement_history[name][-10:]

                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                label = f"{name}: {int(score * 100)}%"
                if person["phone_detected"]:
                    label += " 📱"
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            # Cleanup stale students
            active_students = {n: d for n, d in active_students.items() if now - d['last_seen'] <= STUDENT_STALE_TIMEOUT}
            engagement_history = {n: h for n, h in engagement_history.items() if n in active_students}
            last_saved = {n: t for n, t in last_saved.items() if n in active_students}

            current_time = time.time()
            for n, d in active_students.items():
                active_students_state[n] = {"engagement": round(d["score"], 1),"last_seen": d["last_seen"]}
                # Cleanup stale\n            active_students_state = {k: v for k, v in active_students_state.items() if current_time - v["last_seen"] < 3}

            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n' + b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    finally:
        cap.release()
        cv2.destroyAllWindows()

