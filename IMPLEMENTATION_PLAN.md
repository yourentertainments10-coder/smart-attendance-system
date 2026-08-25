# Engagement Monitoring — Implementation Plan (Phases 1–4)

Goal: reliable per-student identification during class monitoring, and a teacher-readable
per-student behavior timeline. No architectural rewrite — targeted repairs inside the
existing structure. The attendance flow is NOT touched except registration capture quality.

Order matters: each phase depends on the one before it. Do not start Phase 3 until
Phase 2 recognition is verifiably accurate, or you will be tuning identity-binding
logic on top of bad matches.

---

## Phase 1 — Registration quality (fixes the reference data) — ✅ IMPLEMENTED
(Remaining manual step: re-capture photos for 101_Anuj_S via the register page
with "Re-capture photos" ticked, then re-run `python scripts/check_gallery.py`.)

**Why first:** every downstream match compares against these images. Bad gallery = nothing
else can work.

### 1.1 Capture full-resolution, undistorted crops
File: `utils/camera_utils_fixed.py` → `register_student()`
- Remove the `cv2.resize(face_crop, (160, 160))` on save. Save the padded crop at native
  resolution, aspect ratio preserved.
- Keep the +20px padding (dlib needs context around the face).

### 1.2 Validate every capture before saving
Same function:
- After cropping, immediately run `face_recognition.face_encodings()` on the crop
  (with `known_face_locations` — see Phase 2.2). Only save the image if an encoding
  is produced. This guarantees every gallery image is usable.
- Keep a counter of rejected frames; if rejection rate is high, the lighting/camera
  is bad and the UI should say so.

### 1.3 Guided, varied capture
Same function — replace the rapid 20-frame burst:
- Space captures ~0.5 s apart.
- On-screen prompts in stages: look straight (8 imgs) → turn slightly left (3) →
  slightly right (3) → chin up/down (3) → lean back / step back (3).
- This is what makes recognition survive angle/distance changes later.

### 1.4 Allow repairing a partial registration
Files: `utils/camera_utils_fixed.py`, `routes/student_routes.py`
- Current behavior: if the folder exists, capture is silently skipped (this is how
  `101_Anuj_S` ended up with 1 image). Change to: if the folder has < 15 valid images,
  offer append/re-capture instead of skipping. Simplest UI: a "Re-capture photos"
  action on the register page for an existing ID.

### 1.5 Embedding cache
File: `services/face_recognition_service.py` → `load_dataset()`
- On load, compute encodings once and save them (e.g. `datasets/student_faces/<folder>/embeddings.npy`
  plus the source filenames). On subsequent loads, load the `.npy` directly; recompute
  only for folders whose image set changed (compare filenames/mtimes).
- Startup goes from ~40 slow encodes to instant, and registration reload stays cheap.

### 1.6 Data cleanup (one-time)
- Delete the empty `datasets/student_faces/_/` folder.
- Re-register `101_Anuj_S` with the new capture flow (it currently has 1 image).

**Done when:** a verification script (can be a small standalone `scripts/check_gallery.py`)
shows every student with ≥ 15 images and 100% of stored images produce an encoding.

---

## Phase 2 — Recognition pipeline (fixes accuracy)

### 2.1 Stop cropping faces from the shrunken frame
File: `services/live_engagement.py` → `process_class_frame()`
- Keep YOLO running on the resized 416×320 frame (speed is fine).
- Compute `scale_x, scale_y` and map every person/face/phone box back to the ORIGINAL
  frame. Do face detection and face cropping on the full-resolution frame.
- All drawing/labels also move to original-frame coordinates (the stream then shows
  the full-res frame, which also looks better).

### 2.2 Stop the silent re-detection inside `face_encodings`
File: `services/face_recognition_service.py`
- Delete `preprocess_face()`'s square 160×160 resize entirely. Pass the crop as-is.
- In `get_face_embedding()`, call
  `face_recognition.face_encodings(rgb, known_face_locations=[(0, w, h, 0)])`
  where `(w, h)` are the crop dimensions. This skips dlib's internal HOG re-detection
  (the main source of "no embedding → Unknown").
- Optional: if the crop's shorter side is < 80 px, upscale 2× with
  `cv2.resize(..., interpolation=cv2.INTER_CUBIC)` before encoding — cheap and helps
  distant faces.

### 2.3 Fix the size gates
File: `services/live_engagement.py`
- The `fw < 80 or fh < 80` check was tuned for the 416×320 frame. After 2.1, re-tune
  it against the native resolution (start at ~60 px on a 1280×720 feed and adjust
  by testing at the back-of-classroom distance you care about).

### 2.4 Close-up fallback (fixes the single-student test)
File: `services/live_engagement.py` → `process_class_frame()`
- If YOLO returns zero persons, run `detect_faces()` on the full frame directly and
  treat each face as a person with `bbox = face box`. This handles the case where a
  face fills the webcam and no torso is visible, which is exactly your current
  single-camera test setup.

### 2.5 Thresholds — leave alone, then verify
- Keep `CLASS_MONITOR_THRESHOLD = 0.60` and the gap check. Only revisit after 2.1–2.4
  are in, using the `debug=True` distance printout of `recognize_student()`.

**Done when:** with the monitor running, you (re-registered) are recognized correctly in
a test matrix: near / mid / far distance × lights on / dimmed × facing / ~30° turned.
Log `best / second / gap` for each cell; best-score should sit well under 0.55 for
the true identity in most cells.

---

## Phase 3 — Identity binding (fixes "events on the wrong student")

### 3.1 Restrict candidates to today's attendees
Files: `models/attendance_model.py` (new helper), `services/face_recognition_service.py`
- New helper: `get_present_folder_names(date)` → list of `folder_name` for students
  with an attendance row today.
- `recognize_student()` gains an optional `allowed_names` parameter; when set, only
  those students' embeddings are compared. The monitor passes today's attendee list.
- Smaller candidate set → fewer confusions, and the threshold becomes safer.

### 3.2 Vote before binding a name to a track
File: `services/live_engagement.py` (or a new small `services/identity_binder.py` if
the generator function is getting long)
- Replace the write-once `recognized_cache` with per-track vote state:
  `{track_id: {"votes": Counter, "name": None, "last_verify": t}}`.
- A track gets a name only after K = 3 recognitions agree (recognition attempts stay
  throttled at one per ~2 s per track, as now).

### 3.3 Periodic re-verification
- Every 10–15 s per bound track, run recognition again. One mismatch → ignore
  (could be a bad frame). Two consecutive mismatches → unbind to "Unknown" and
  restart voting. This is what recovers from tracker ID swaps.

### 3.4 One name, one track
- Before binding (and on re-verify), if another live track already holds that name,
  compare the two tracks' current match distances; the better one keeps the name,
  the other is unbound. Never allow two simultaneous tracks with the same student.

### 3.5 Tracker fixes
File: `services/face_tracker.py`
- Bug: in the zero-detections branch of `update()`, tracks age (`disappeared += 1`)
  but the deletion check never runs — add it there too.
- Raise `max_age` (2 s is aggressive; a student leaning down to write loses their
  track). Suggest 5 s, since identity re-binding (3.2) now protects against
  stale-track mislabeling.
- Optional, only if swaps persist in testing: match on IoU instead of pure centroid
  distance. Do not add embedding-based re-ID yet — voting + re-verify should suffice
  for classroom seating (people mostly stay put).

**Done when:** two-person test — both registered, swap seats, cross in front of the
camera, one leaves and returns — and neither identity ever sticks to the wrong person
for more than one re-verification cycle (~15 s), and no name appears twice at once.

---

## Phase 4 — Behavior states + timeline (delivers the feature)

### 4.1 New DB table (migration, additive only)
File: `database/schema.sql` (+ one-time `ALTER`/`CREATE` on the live DB)
```sql
CREATE TABLE IF NOT EXISTS engagement_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    date TEXT NOT NULL,
    event_type TEXT NOT NULL,        -- attentive | looking_away | head_down |
                                     -- talking | phone | partially_visible | not_visible
    start_time TEXT NOT NULL,
    end_time TEXT,                   -- NULL while the state is still active
    FOREIGN KEY(student_id) REFERENCES students(student_id)
);
CREATE INDEX IF NOT EXISTS idx_events_student_date ON engagement_events(student_id, date);
```
- Existing `engagement` score table stays untouched and keeps being written — the
  event table sits alongside it. `date` doubles as the session key for now; a real
  `class_sessions` table can come later if needed.

### 4.2 Per-frame behavior classification
New file: `services/behavior_classifier.py`
- Input per student per processed frame: full-res face crop, FaceMesh landmarks,
  face box vs. person box, phone flag. Output: ONE raw state.
- Signals (all MediaPipe FaceMesh, thresholds calibrated on CROP coordinates —
  the current `engagement_detection.py` thresholds are full-frame and must be redone):
  - **Yaw** (looking away): nose-tip x offset vs. ear midpoint, sustained.
  - **Pitch** (head down): nose-tip y vs. eye line, or face box sitting low in the
    person box with no visible eyes.
  - **Talking (likely)**: mouth-open ratio (upper/lower lip landmark distance ÷ face
    height) — variance over a ~2 s sliding window above a floor. Label it
    "talking (likely)" in reports; lip motion can't distinguish talking from yawning.
  - **Partially visible**: FaceMesh fails on the crop but a face box exists, or the
    face box is abnormally small relative to the person box.
  - **Not visible**: person tracked but no face found for the debounce window; or the
    student (bound identity) has no track at all.
  - **Phone**: existing YOLO class-67 flag, unchanged.
- Priority when several are true: `not_visible > phone > head_down > looking_away >
  talking > partially_visible > attentive`.
- Performance: ONE persistent FaceMesh instance with `static_image_mode=False`,
  `max_num_faces=1`, reused across frames (replaces the current per-call static-mode
  usage in `engagement_detection.py`). Run it per face crop as now, but through the
  shared instance.

### 4.3 Per-student state machine with debounce
New file: `services/engagement_events.py`
- Per bound student: `{current_state, candidate_state, candidate_since, event_start}`.
- A raw state only COMMITS after persisting ≥ 4 s (single knob, tune 3–5 s).
  On commit: close the previous event (`end_time = now`), insert the new one.
- Student disappears entirely ≥ 8 s → commit `not_visible`. Reappears → resume normal
  classification.
- Monitor stream stops (the generator's `finally`) → close all open events.
- Keep `calculate_engagement`'s numeric score pipeline as-is; optionally later derive
  the score FROM states (attentive=1.0, talking=0.6, looking_away=0.4, phone=0.1 …)
  so the two never disagree — but that's a follow-up, not part of this phase.

### 4.4 Model + API + minimal UI
Files: `models/engagement_model.py`, `routes/class_monitor_routes.py` or
`routes/report_routes.py`, `templates/reports.html`
- Model: `insert_event`, `close_event`, `get_timeline(student_id, date)`.
- Endpoint: `/api/timeline/<student_id>?date=YYYY-MM-DD` → ordered events with
  durations.
- UI: on the reports page, per student per date, render a simple list —
  `10:02–10:14 Attentive · 10:14–10:17 Phone (3 min) · 10:17 Looking away …` —
  plus a per-state total-minutes summary line. A colored horizontal timeline bar is a
  nice-to-have after the list works.

**Done when:** a scripted 3–4 minute self-test (attentive → pick up phone → look away →
duck below camera → return) produces exactly that sequence of events, with sensible
timestamps, no sub-4-second spam events, and the timeline renders on the reports page.

---

## Explicitly out of scope (don't touch)

- Attendance marking flow (`gen_frames_attendance`, `mark_attendance`) — works, leave it.
- Auth, reports/PDF generation, analytics routes.
- Switching to InsightFace/ArcFace — only reconsider AFTER Phase 2 verification, and
  only if distant/angled faces still fail. The swap point would be isolated inside
  `face_recognition_service.py` (detection+alignment+embedding in one call), so
  deferring it costs nothing.

## Suggested effort split

| Phase | Size | Risk |
|---|---|---|
| 1 Registration | Small–medium | Low — isolated to capture + dataset load |
| 2 Recognition | Medium | Low — mechanical coordinate mapping; verify with test matrix |
| 3 Binding | Medium | Medium — needs the two-person live test to tune K / re-verify cadence |
| 4 Events | Medium–large | Medium — threshold calibration on crops is the fiddly part |

Each phase is independently shippable; the system keeps working after every phase.
