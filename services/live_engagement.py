import cv2
import numpy as np
import time
from ultralytics import YOLO
import mediapipe as mp

from services.face_recognition_service import recognize_student, CLASS_MONITOR_THRESHOLD
from services.face_detection import detect_faces
from services.engagement_detection import process_landmarks
from services.face_tracker import SimpleFaceTracker
from models.engagement_model import record_engagement
from utils.date_utils import get_current_date
import numpy as np

model = YOLO("yolov8n.pt")
model.fuse()
FRAME_SKIP = 3
PROCESS_EVERY_N_FRAMES = 1
SAVE_INTERVAL = 20
MIN_DETECTION_CONFIDENCE = 0.55
# Minimum face width/height in ORIGINAL frame pixels. Tuned for a 640x480
# webcam; lower it if back-of-room faces are being skipped, raise it if tiny
# unreliable crops get through.
MIN_FACE_SIZE = 60
FACE_PADDING_RATIO = 0.2
STUDENT_STALE_TIMEOUT = 3
SMOOTHING_ALPHA = 0.3
# YOLO runs on this small size for speed; face crops always come from the
# full-resolution frame (boxes are mapped back).
DETECTION_SIZE = (416, 320)
# Print best/second/gap distances for every recognition attempt.
# Leave True while verifying Phase 2 accuracy, then set False.
DEBUG_RECOGNITION = True


active_students_state = {}
active_students = {}
engagement_history = {}
last_saved = {}
recognized_cache = {}
last_recognition_attempt = {}

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





def process_class_frame(frame):
    """
    Detect persons/phones on a downscaled copy (speed), but take every face
    crop from the ORIGINAL full-resolution frame. All returned boxes are in
    original-frame coordinates.
    """
    small = cv2.resize(frame, DETECTION_SIZE)
    scale_x = frame.shape[1] / DETECTION_SIZE[0]
    scale_y = frame.shape[0] / DETECTION_SIZE[1]

    results = model(small, verbose=False, imgsz=320)
    persons = []
    phone_boxes = []
    yolo_person_count = 0

    for r in results:
        boxes = r.boxes
        if boxes is None:
            continue

        for box in boxes:
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            if conf < MIN_DETECTION_CONFIDENCE:
                continue

            sx1, sy1, sx2, sy2 = map(int, box.xyxy[0])
            # Map back to original-frame coordinates
            x1 = max(0, int(sx1 * scale_x))
            y1 = max(0, int(sy1 * scale_y))
            x2 = min(frame.shape[1], int(sx2 * scale_x))
            y2 = min(frame.shape[0], int(sy2 * scale_y))

            if cls == 67:  # cellphone
                phone_boxes.append((x1, y1, x2, y2))
                continue
            if cls != 0:  # person
                continue

            yolo_person_count += 1
            person_crop = frame[y1:y2, x1:x2]
            if person_crop.size == 0:
                continue

            local_faces = detect_faces(person_crop)
            if len(local_faces) == 0:
                continue

            fx, fy, fw, fh = max(local_faces, key=lambda f: f[2]*f[3])
            if fw < MIN_FACE_SIZE or fh < MIN_FACE_SIZE:
                continue

            face_crop, padded_face_box = _padded_face_crop(person_crop, (fx, fy, fw, fh))
            if face_crop.size == 0:
                continue

            persons.append({
                "face_crop": face_crop,
                "bbox": (x1, y1, x2, y2),
                "face_bbox": (x1 + padded_face_box[0], y1 + padded_face_box[1], x1 + padded_face_box[2], y1 + padded_face_box[3])
            })

    # Close-up fallback: a face filling the webcam often has no visible torso,
    # so YOLO finds no "person" and the pipeline would go dark. Detect faces
    # directly on the full frame instead.
    if yolo_person_count == 0:
        for (fx, fy, fw, fh) in detect_faces(frame):
            if fw < MIN_FACE_SIZE or fh < MIN_FACE_SIZE:
                continue
            face_crop, padded_face_box = _padded_face_crop(frame, (fx, fy, fw, fh))
            if face_crop.size == 0:
                continue
            persons.append({
                "face_crop": face_crop,
                "bbox": (fx, fy, fx + fw, fy + fh),
                "face_bbox": padded_face_box
            })

    _match_phones_to_people(persons, phone_boxes)
    return persons


def get_active_students():
    global active_students_state 
    return active_students_state


def gen_class_frames():
    global active_students_state
    global active_students
    global engagement_history
    global last_saved
    global recognized_cache
    global last_recognition_attempt

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FPS, 10)
    print("Starting fresh monitor stream...")

    if not cap.isOpened():
        print(" Class monitor camera failed")
        return

    print(" Class engagement monitor started")

    # Centroids are now in original-frame pixels (was 416x320), so the
    # matching radius scales up accordingly. Tracker tuning proper is Phase 3.
    tracker = SimpleFaceTracker(max_distance=120)
    frame_count = 0
    active_tracks = {}  # track_id: {'name':str, 'score':float, 'phone':bool, 'history':list}
    last_saved = {}
    recognized_cache = {}


    try:
        while True:
            success, frame = cap.read()
            if not success or frame is None:
                continue

            frame_count += 1

            if frame_count % FRAME_SKIP != 0:
                continue

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
            tracked_persons = tracker.update(persons)

            for tracked in tracked_persons:
                track_id = tracked['track_id']
                face_crop = tracked['face_crop']

                phone_detected = tracked.get('phone_detected', False)

                if face_crop is None or face_crop.size == 0:
                    continue

                face_rgb = face_crop


                cached_name = recognized_cache.get(track_id)

                if (
                    cached_name is None or cached_name == "Unknown"
                ) and (
                    track_id not in last_recognition_attempt or
                    now - last_recognition_attempt[track_id] > 2
                ):

                    last_recognition_attempt[track_id] = now

                    detected_name = recognize_student(
                        face_rgb,
                        threshold=CLASS_MONITOR_THRESHOLD,
                        debug=DEBUG_RECOGNITION
                    )

                    # Only overwrite cache if valid recognition
                    if detected_name != "Unknown":
                        recognized_cache[track_id] = detected_name

                name = recognized_cache.get(track_id, "Unknown")

                x1, y1, x2, y2 = tracked['bbox']
                color = (0, 0, 255) if phone_detected else (0, 255, 0)

                landmarks_data = None
                if face_crop is not None and face_crop.size > 0:
                    landmarks_data = process_landmarks(face_crop)

                raw_score = calculate_engagement(face_crop, landmarks_data, phone_detected)
                previous_score = active_students.get(name, {}).get("score", raw_score)
                score = (1 - SMOOTHING_ALPHA) * previous_score + SMOOTHING_ALPHA * raw_score
                if name != "Unknown":
                    active_students[name] = {"score": score, "phone": phone_detected, "last_seen": now}
                
                if name not in engagement_history:
                    engagement_history[name] = []
                engagement_history[name].append(score)

                if name not in last_saved or now - last_saved[name] > SAVE_INTERVAL:
                    avg_engagement = sum(engagement_history[name]) / len(engagement_history[name])
                    if name != "Unknown":
                        try:
                            record_engagement(name.split('_')[0], avg_engagement)
                        except Exception as e:
                            print("db write skipped",e)
                    last_saved[name] = now
                    engagement_history[name] = engagement_history[name][-10:]

                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                label = f"{name}: {int(score * 100)}%"
                if phone_detected:
                    label += " 📱"
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            # Cleanup stale students
            active_students = {n: d for n, d in active_students.items() if now - d['last_seen'] <= STUDENT_STALE_TIMEOUT}
            engagement_history = {n: h for n, h in engagement_history.items() if n in active_students}
            last_saved = {n: t for n, t in last_saved.items() if n in active_students}
            active_track_ids = {t['track_id'] for t in tracked_persons}
            recognized_cache = {
                tid: name for tid, name in recognized_cache.items()
                if tid in active_track_ids
                    }

            current_time = time.time()
            for n, d in active_students.items():
                active_students_state[n] = {"engagement": round(d["score"], 1),"last_seen": d["last_seen"]}
                # Cleanup stale
                active_students_state = {
                    k: v for k, v in active_students_state.items()
                    if current_time - v["last_seen"] < 3
                    }

            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n' + b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    finally:
        cap.release()
        cv2.destroyAllWindows()
