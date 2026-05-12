import cv2
import numpy as np
import os
import mediapipe as mp
from collections import defaultdict

try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    print("WARNING: face-recognition not available. Using landmark fallback.")
    import mediapipe as mp
    mp_face_mesh = mp.solutions.face_mesh.FaceMesh(static_image_mode=True)
    FACE_RECOGNITION_AVAILABLE = False

FACE_SIZE = (160, 160)
ATTENDANCE_THRESHOLD = 0.65


CLASS_MONITOR_THRESHOLD = 0.60

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
dataset = []  # [(name, embedding_or_vector)]

def preprocess_face(image):
    if image is None or image.size == 0:
        return None
    return cv2.resize(image, FACE_SIZE)


PRINT_ONCE = True

def get_face_embedding(image):
    global PRINT_ONCE
    preprocessed = preprocess_face(image)
    if preprocessed is None:
        return None

    if FACE_RECOGNITION_AVAILABLE:
        rgb = cv2.cvtColor(preprocessed, cv2.COLOR_BGR2RGB)
        encodings = face_recognition.face_encodings(rgb)
        emb = encodings[0] if encodings else None

        if emb is not None:
            if PRINT_ONCE:
                print(f" CNN embedding working (length={len(emb)})")
                PRINT_ONCE = False

        return emb
    else:
        # Fallback to landmarks
        img_rgb = cv2.cvtColor(preprocessed, cv2.COLOR_BGR2RGB)
        results = mp_face_mesh.process(img_rgb)
        if not results.multi_face_landmarks:
            return None
        landmarks = results.multi_face_landmarks[0]
        vector = []
        for lm in landmarks.landmark:
            vector.extend([lm.x, lm.y, lm.z])
        emb = np.array(vector)
        print(f"Landmark fallback length: {len(emb)} (dim~1400 expected)")
        return emb


def load_dataset(force_reload=False):
    global dataset
    if len(dataset) > 0 and not force_reload:
        print(f"Dataset already loaded ({len(dataset)} entries)")
        return

    dataset = []

    base_path = os.path.join(BASE_DIR, "..", "datasets", "student_faces")
    print(f"Loading from: {base_path}")

    if not os.path.exists(base_path):
        print(f"? Path not found: {base_path}")
        print("Dataset size: 0")
        return

    for student in os.listdir(base_path):
        student_path = os.path.join(base_path, student)
        if not os.path.isdir(student_path):
            continue
        for img_name in os.listdir(student_path):
            img_path = os.path.join(student_path, img_name)
            img = cv2.imread(img_path)
            if img is None:
                continue
            emb = get_face_embedding(img)
            if emb is not None:
                dataset.append((student, emb))

    print(f"Dataset loaded: {len(dataset)} embeddings (using {'CNN' if FACE_RECOGNITION_AVAILABLE else 'landmark fallback'})")


def recognize_student(face_img, threshold=ATTENDANCE_THRESHOLD, debug=False):
    if face_img is None:
        if debug:
            print("?? Empty face crop")
        return "Unknown"

    embedding = get_face_embedding(face_img)
    if embedding is None:
        if debug:
            print("?? No embedding")
        return "Unknown"

    if len(dataset) == 0:
        if debug:
            print("? Dataset empty")
        return "Unknown"

    # Store all distances grouped by student
    student_distances = defaultdict(list)

    for name, stored_emb in dataset:
        if stored_emb is None:
            continue

        dist = np.linalg.norm(embedding - stored_emb)
        student_distances[name].append(dist)

    if len(student_distances) == 0:
        return "Unknown"

    # Compute average of best few distances per student
    best_student = "Unknown"
    best_score = float("inf")
    second_best = float("inf")

    for student, dists in student_distances.items():
        dists.sort()

        top_matches = dists[:5] if len(dists) >= 5 else dists
        avg_dist = np.mean(top_matches)

        if avg_dist < best_score:
            second_best = best_score
            best_score = avg_dist
            best_student = student
        elif avg_dist < second_best:
            second_best = avg_dist

    confidence_gap = second_best - best_score

    if debug:
        print(f"Best: {best_student} | score: {best_score:.3f} | second: {second_best:.3f} | gap: {confidence_gap:.3f}")

    # STRICT acceptance conditions
    if best_score <= threshold and confidence_gap > 0.03:
        return best_student
    else:
        return "Unknown"