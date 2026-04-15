import cv2
import numpy as np
import os
import mediapipe as mp

mp_face_mesh = mp.solutions.face_mesh.FaceMesh(static_image_mode=True)
FACE_SIZE = (160, 160)
ATTENDANCE_THRESHOLD = 0.6
CLASS_MONITOR_THRESHOLD = 0.6

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
dataset = []   # [(name, vector)]


def preprocess_face(image):
    if image is None or image.size == 0:
        return None
    return cv2.resize(image, FACE_SIZE)


def get_face_vector(image):
    image = preprocess_face(image)
    if image is None:
        return None
    img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = mp_face_mesh.process(img_rgb)

    if not results.multi_face_landmarks:
        return None

    landmarks = results.multi_face_landmarks[0]
    vector = []
    for lm in landmarks.landmark:
        vector.extend([lm.x, lm.y, lm.z])

    return np.array(vector)


def load_dataset():
    global dataset
    dataset = []

    base_path = os.path.join(BASE_DIR, "..", "datasets", "student_faces")
    print(f"Loading from: {base_path}")

    if not os.path.exists(base_path):
        print(f"? Path not found: {base_path}")
        print("Dataset size: 0")
        return

    for student in os.listdir(base_path):
        student_path = os.path.join(base_path, student)
        for img_name in os.listdir(student_path):
            img_path = os.path.join(student_path, img_name)
            img = cv2.imread(img_path)
            vec = get_face_vector(img)
            if vec is not None:
                dataset.append((student, vec))

    print("Dataset size:", len(dataset))


def recognize_student(face_img, threshold=ATTENDANCE_THRESHOLD, debug=True):
    face_img = preprocess_face(face_img)
    if face_img is None:
        if debug:
            print("?? Empty face crop")
        return "Unknown"
    if debug:
        print("Face shape:", face_img.shape)

    input_vec = get_face_vector(face_img)
    if input_vec is None:
        if debug:
            print("?? No face detected")
        return "Unknown"

    if len(dataset) == 0:
        if debug:
            print("? Dataset empty")
        return "Unknown"

    min_dist = float("inf")
    best_match = "Unknown"

    for name, vec in dataset:
        if vec is None:
            continue
        dist = np.linalg.norm(input_vec - vec)
        if dist < min_dist:
            min_dist = dist
            best_match = name

    if debug:
        print("Distance:", min_dist)
    if min_dist < 0.6:
        return best_match
    return "Unknown"


load_dataset()
print("Dataset loaded:", len(dataset))

