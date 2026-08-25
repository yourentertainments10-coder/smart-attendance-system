"""
Per-frame behavior classification for one student's face crop.

Produces ONE raw state per call; the debouncing that turns noisy per-frame
states into committed timeline events lives in engagement_events.py.

All geometry works on FaceMesh landmarks in CROP-normalized coordinates
(0..1 over the face crop) — thresholds here are calibrated for tight face
crops, NOT full frames.

State priority (not_visible is decided by the event layer, from absence):
    phone > head_down > looking_away > talking > partially_visible > attentive
"""
import time
from collections import deque

import cv2
import mediapipe as mp

STATE_ATTENTIVE = "attentive"
STATE_LOOKING_AWAY = "looking_away"
STATE_HEAD_DOWN = "head_down"
STATE_TALKING = "talking"
STATE_PHONE = "phone"
STATE_PARTIALLY_VISIBLE = "partially_visible"
STATE_NOT_VISIBLE = "not_visible"

# --- Tunable thresholds (see IMPLEMENTATION_PLAN.md Phase 4) -----------------
# Yaw proxy: nose-tip x offset from the ear midpoint, as a fraction of the
# ear-to-ear span. ~0 facing camera; grows as the head turns.
YAW_AWAY_RATIO = 0.22
# Pitch proxy: (chin - eyes) / (eyes - forehead) vertical distances. Looking
# down foreshortens the lower face, shrinking the ratio. Measured on the
# gallery: frontal faces span 1.82-2.35, so 1.30 leaves a solid margin.
PITCH_DOWN_RATIO = 1.30
# Talking: std-dev of the mouth-open ratio over the sliding window.
TALK_WINDOW_SECONDS = 2.5
TALK_MIN_SAMPLES = 5
TALK_STD_THRESHOLD = 0.012
# -----------------------------------------------------------------------------

# FaceMesh landmark indices
NOSE_TIP = 1
FOREHEAD = 10
CHIN = 152
LEFT_EYE = 33
RIGHT_EYE = 263
LEFT_EAR = 234
RIGHT_EAR = 454
LIP_TOP = 13
LIP_BOTTOM = 14

MAX_MESH_INSTANCES = 8


def _new_mesh():
    return mp.solutions.face_mesh.FaceMesh(
        static_image_mode=False,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )


def _std(values):
    n = len(values)
    mean = sum(values) / n
    return (sum((v - mean) ** 2 for v in values) / n) ** 0.5


class BehaviorClassifier:
    """
    One FaceMesh per track in video mode (fast tracking path). A shared
    single instance would interleave different students' faces and confuse
    MediaPipe's internal tracker, so instances are kept per track and
    pruned with the tracks.
    """

    def __init__(self):
        self.tracks = {}  # track_id -> {"mesh", "mouth_history", "last_used"}

    def _track(self, track_id, now):
        if track_id not in self.tracks:
            if len(self.tracks) >= MAX_MESH_INSTANCES:
                oldest = min(self.tracks, key=lambda t: self.tracks[t]["last_used"])
                self.tracks[oldest]["mesh"].close()
                del self.tracks[oldest]
            self.tracks[track_id] = {
                "mesh": _new_mesh(),
                "mouth_history": deque(),
                "last_used": now,
            }
        self.tracks[track_id]["last_used"] = now
        return self.tracks[track_id]

    def _is_talking(self, track, mouth_ratio, now):
        history = track["mouth_history"]
        history.append((now, mouth_ratio))
        while history and now - history[0][0] > TALK_WINDOW_SECONDS:
            history.popleft()
        if len(history) < TALK_MIN_SAMPLES:
            return False, 0.0
        std = _std([r for _, r in history])
        return std > TALK_STD_THRESHOLD, std

    def classify(self, track_id, face_crop, phone_detected=False, now=None):
        """
        Returns {"state", "landmarks", "yaw_ratio", "pitch_ratio", "mouth_std"}.
        landmarks is the FaceMesh multi_face_landmarks list (or None), so the
        caller can reuse it for engagement scoring without a second mesh run.
        """
        if now is None:
            now = time.time()
        result = {"state": STATE_ATTENTIVE, "landmarks": None,
                  "yaw_ratio": None, "pitch_ratio": None, "mouth_std": None}

        track = self._track(track_id, now)
        landmarks_list = None
        if face_crop is not None and face_crop.size > 0:
            rgb = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)
            try:
                mesh_out = track["mesh"].process(rgb)
                landmarks_list = mesh_out.multi_face_landmarks
            except Exception as e:
                print("Behavior mesh error:", e)

        if phone_detected:
            # Phone outranks everything visible; still record landmarks below
            result["state"] = STATE_PHONE

        if not landmarks_list:
            if result["state"] != STATE_PHONE:
                # A face box exists (we got a crop) but the mesh can't resolve
                # a face in it -> obstructed / turned too far / unclear.
                result["state"] = STATE_PARTIALLY_VISIBLE
            return result

        result["landmarks"] = landmarks_list
        lm = landmarks_list[0].landmark

        nose = lm[NOSE_TIP]
        forehead = lm[FOREHEAD]
        chin = lm[CHIN]
        left_ear = lm[LEFT_EAR]
        right_ear = lm[RIGHT_EAR]
        left_eye = lm[LEFT_EYE]
        right_eye = lm[RIGHT_EYE]

        ear_span = abs(right_ear.x - left_ear.x)
        ear_mid_x = (left_ear.x + right_ear.x) / 2.0
        yaw_ratio = (nose.x - ear_mid_x) / ear_span if ear_span > 1e-6 else 0.0

        eyes_mid_y = (left_eye.y + right_eye.y) / 2.0
        upper = eyes_mid_y - forehead.y
        lower = chin.y - eyes_mid_y
        pitch_ratio = lower / upper if upper > 1e-6 else None

        face_height = abs(chin.y - forehead.y)
        mouth_open = abs(lm[LIP_BOTTOM].y - lm[LIP_TOP].y)
        mouth_ratio = mouth_open / face_height if face_height > 1e-6 else 0.0
        talking, mouth_std = self._is_talking(track, mouth_ratio, now)

        result["yaw_ratio"] = round(yaw_ratio, 3)
        result["pitch_ratio"] = round(pitch_ratio, 3) if pitch_ratio else None
        result["mouth_std"] = round(mouth_std, 4)

        if result["state"] == STATE_PHONE:
            return result
        if pitch_ratio is not None and pitch_ratio < PITCH_DOWN_RATIO:
            result["state"] = STATE_HEAD_DOWN
        elif abs(yaw_ratio) > YAW_AWAY_RATIO:
            result["state"] = STATE_LOOKING_AWAY
        elif talking:
            result["state"] = STATE_TALKING
        else:
            result["state"] = STATE_ATTENTIVE
        return result

    def prune(self, active_track_ids):
        for track_id in list(self.tracks.keys()):
            if track_id not in active_track_ids:
                self.tracks[track_id]["mesh"].close()
                del self.tracks[track_id]

    def close_all(self):
        self.prune(set())
