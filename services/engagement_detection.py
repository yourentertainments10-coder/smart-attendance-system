import mediapipe as mp
import cv2

mp_face_mesh = mp.solutions.face_mesh.FaceMesh(
    static_image_mode=True,
    max_num_faces=1,
    refine_landmarks=True
)

def process_landmarks(frame):
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    try: results = mp_face_mesh.process(rgb)
    except Exception as e:
        print("Frame processing error:", e)
        return None

    if not results.multi_face_landmarks:
        return None

    landmarks = results.multi_face_landmarks

    # Simple engagement logic (face facing camera)
    score = 0

    for face in landmarks:
        nose = face.landmark[1]
        left_eye = face.landmark[33]
        right_eye = face.landmark[263]
        left_ear = face.landmark[234]
        right_ear = face.landmark[454]

        # 🟢 Face direction
        face_center = (left_ear.x + right_ear.x) / 2
        if abs(nose.x - face_center) < 0.05:
            score += 0.4   # facing camera

        # 🟢 Eye level (rough openness proxy)
        eye_diff = abs(left_eye.y - right_eye.y)
        if eye_diff < 0.02:
            score += 0.3   # eyes aligned → likely open

        # 🟢 Stability (head not tilted too much)
        if abs(left_eye.x - right_eye.x) > 0.1:
            score += 0.3

    score = min(score, 1.0)

    # color coding
    if score > 0.7:
        color = (0, 255, 0)
    elif score > 0.5:
        color = (0, 255, 255)
    else:
        color = (0, 0, 255)

    return landmarks, score, color
