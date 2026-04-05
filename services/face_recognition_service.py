import cv2
import numpy as np
import os
import mediapipe as mp

mp_face_mesh = mp.solutions.face_mesh.FaceMesh(static_image_mode=True)

dataset = []   # [(name, vector)]

# 🔹 Convert landmarks → vector
def get_face_vector(image):
    img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = mp_face_mesh.process(img_rgb)

    if not results.multi_face_landmarks:
        return None

    landmarks = results.multi_face_landmarks[0]

    vector = []
    for lm in landmarks.landmark:
        vector.extend([lm.x, lm.y, lm.z])

    return np.array(vector)


# 🔹 Load dataset (from saved images)
def load_dataset():
    global dataset
    dataset = []

    base_path = "datasets/student_faces"

    for student in os.listdir(base_path):
        student_path = os.path.join(base_path, student)

        for img_name in os.listdir(student_path):
            img_path = os.path.join(student_path, img_name)
            img = cv2.imread(img_path)

            vec = get_face_vector(img)
            if vec is not None:
                dataset.append((student, vec))

    print(f"Loaded {len(dataset)} face vectors")


# 🔹 Recognition
def recognize_student(face_img):
    input_vec = get_face_vector(face_img)

    if input_vec is None:
        return "Unknown"

    min_dist = float("inf")
    best_match = "Unknown"

    for name, vec in dataset:
        dist = np.linalg.norm(input_vec - vec)

        if dist < min_dist:
            min_dist = dist
            best_match = name

    print("Distance:", min_dist)


    # 🔥 Threshold (tune if needed) - tightened to reduce false positives
    if min_dist < 1.3:
        return best_match


    return "Unknown"

load_dataset()
