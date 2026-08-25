import cv2
import numpy as np
import os
import pickle
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

ATTENDANCE_THRESHOLD = 0.65


CLASS_MONITOR_THRESHOLD = 0.60

# Gallery policy: a student needs at least this many valid images to be
# considered properly registered (see register_student / check_gallery).
MIN_GALLERY_IMAGES = 15
CACHE_FILENAME = "embeddings_cache.pkl"
# Bump whenever preprocessing/embedding changes so cached embeddings rebuild.
PIPELINE_VERSION = 2
# Crops with a shorter side below this get a 2x upscale before encoding.
MIN_EMBED_SIZE = 80

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
dataset = []  # [(name, embedding_or_vector)]

def preprocess_face(image):
    if image is None or image.size == 0:
        return None
    # Native resolution, aspect preserved — the old square 160x160 resize
    # distorted faces and threw away detail. Small (distant) faces get a
    # cheap 2x upscale, which measurably helps dlib's encoder.
    h, w = image.shape[:2]
    if min(h, w) < MIN_EMBED_SIZE:
        image = cv2.resize(image, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)
    return image


PRINT_ONCE = True

def get_face_embedding(image):
    global PRINT_ONCE
    preprocessed = preprocess_face(image)
    if preprocessed is None:
        return None

    if FACE_RECOGNITION_AVAILABLE:
        rgb = cv2.cvtColor(preprocessed, cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]
        # The crop IS the face, so tell dlib where it is instead of letting it
        # re-run HOG detection on a tight crop (which frequently finds nothing
        # and was the main source of "no embedding" -> Unknown).
        encodings = face_recognition.face_encodings(
            rgb, known_face_locations=[(0, w, h, 0)]
        )
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


IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png")
EMBEDDING_MODE = "cnn" if FACE_RECOGNITION_AVAILABLE else "landmark"


def load_folder_embeddings(student_path):
    """
    Return {filename: embedding_or_None} for one student folder, computing
    embeddings only for images that are new or changed since the last run.
    Failed encodings are cached as None so they aren't retried every load.
    """
    cache_path = os.path.join(student_path, CACHE_FILENAME)
    cached = {"mode": EMBEDDING_MODE, "version": PIPELINE_VERSION, "files": {}}
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "rb") as f:
                loaded = pickle.load(f)
            if (loaded.get("mode") == EMBEDDING_MODE
                    and loaded.get("version") == PIPELINE_VERSION):
                cached = loaded
        except Exception as e:
            print(f"Embedding cache unreadable, rebuilding ({e})")

    images = [f for f in os.listdir(student_path)
              if f.lower().endswith(IMAGE_EXTENSIONS)]
    result = {}
    changed = False

    for img_name in images:
        img_path = os.path.join(student_path, img_name)
        mtime = os.path.getmtime(img_path)
        entry = cached["files"].get(img_name)
        if entry is not None and entry["mtime"] == mtime:
            result[img_name] = entry["embedding"]
            continue
        img = cv2.imread(img_path)
        emb = get_face_embedding(img) if img is not None else None
        cached["files"][img_name] = {"mtime": mtime, "embedding": emb}
        result[img_name] = emb
        changed = True

    stale = set(cached["files"]) - set(images)
    for img_name in stale:
        del cached["files"][img_name]
        changed = True

    if changed:
        try:
            with open(cache_path, "wb") as f:
                pickle.dump(cached, f)
        except Exception as e:
            print(f"Embedding cache write failed for {student_path}: {e}")

    return result


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
        for emb in load_folder_embeddings(student_path).values():
            if emb is not None:
                dataset.append((student, emb))

    print(f"Dataset loaded: {len(dataset)} embeddings (using {'CNN' if FACE_RECOGNITION_AVAILABLE else 'landmark fallback'})")


def recognize_student(face_img, threshold=ATTENDANCE_THRESHOLD, debug=False,
                      allowed_names=None, return_score=False):
    """
    allowed_names: optional set of folder names to restrict matching to
    (e.g. today's attendees) — a smaller candidate set means fewer confusions.
    return_score: when True, returns (name, best_distance) instead of name.
    """
    def _result(name, score):
        return (name, score) if return_score else name

    if face_img is None:
        if debug:
            print("?? Empty face crop")
        return _result("Unknown", None)

    embedding = get_face_embedding(face_img)
    if embedding is None:
        if debug:
            print("?? No embedding")
        return _result("Unknown", None)

    if len(dataset) == 0:
        if debug:
            print("? Dataset empty")
        return _result("Unknown", None)

    # Store all distances grouped by student
    student_distances = defaultdict(list)

    for name, stored_emb in dataset:
        if stored_emb is None:
            continue
        if allowed_names is not None and name not in allowed_names:
            continue

        dist = np.linalg.norm(embedding - stored_emb)
        student_distances[name].append(dist)

    if len(student_distances) == 0:
        return _result("Unknown", None)

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
        return _result(best_student, best_score)
    else:
        return _result("Unknown", best_score)