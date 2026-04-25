import cv2
import numpy as np
try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    print("WARNING: face-recognition not installed. Using MediaPipe fallback.")
    import mediapipe as mp
    mp_face_detection = mp.solutions.face_detection
    mp_drawing = mp.solutions.drawing_utils
    FACE_RECOGNITION_AVAILABLE = False

def detect_faces(frame):
    if FACE_RECOGNITION_AVAILABLE:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb,model="hog")
        boxes = []
        for (top, right, bottom, left) in face_locations:
            x = left
            y = top
            w = right - left
            h = bottom - top
            boxes.append((x, y, w, h))
        return boxes
    else:
        # MediaPipe fallback (already in requirements)
        with mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5) as face_detection:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_detection.process(rgb)
            boxes = []
            if results.detections:
                for detection in results.detections:
                    bbox = detection.location_data.relative_bounding_box
                    h, w, _ = frame.shape
                    x = int(bbox.xmin * w)
                    y = int(bbox.ymin * h)
                    ww = int(bbox.width * w)
                    hh = int(bbox.height * h)
                    boxes.append((x, y, ww, hh))
            return boxes
