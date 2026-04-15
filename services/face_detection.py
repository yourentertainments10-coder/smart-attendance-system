import cv2


def detect_faces(frame):
    original_h, original_w = frame.shape[:2]
    target_w, target_h = 640, 480

    frame_resized = cv2.resize(frame, (target_w, target_h))
    gray = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4)

    scale_x = original_w / float(target_w)
    scale_y = original_h / float(target_h)

    scaled_faces = []
    for (x, y, w, h) in faces:
        scaled_faces.append((
            int(x * scale_x),
            int(y * scale_y),
            int(w * scale_x),
            int(h * scale_y),
        ))

    return scaled_faces
