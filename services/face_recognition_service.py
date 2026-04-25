import cv2
import numpy as np
import os
import mediapipe as mp


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


CLASS_MONITOR_THRESHOLD = 0.55

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

    min_dist = float("inf")
    best_match = "Unknown"

    for name, stored_emb in dataset:
        if stored_emb is None:
            continue
        dist = np.linalg.norm(embedding - stored_emb)
        if dist < min_dist:
            min_dist = dist
            best_match = name

    if debug:
        confidence = max(0, 1 - min_dist)
        print(f"Best match: {best_match} | dist: {min_dist:.3f} | confidence: {confidence:.2f}")

    if min_dist <= threshold:
        return best_match
    else:
        return "Unknown"




