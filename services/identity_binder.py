"""
Binds recognized student identities to tracker IDs — carefully.

The tracker can swap IDs when students sit close or cross paths; a single
recognition can be wrong on a bad frame. This layer makes identity sticky
but self-correcting:

- A track earns a name only after VOTES_TO_BIND recognitions agree (voting).
- A bound track is re-verified every REVERIFY_INTERVAL seconds; two
  consecutive failed verifications unbind it (recovers from ID swaps).
- One name, one track: if two tracks claim the same student, the closer
  match keeps the name and the other is unbound.
"""
import time
from collections import Counter

from services.face_recognition_service import recognize_student, CLASS_MONITOR_THRESHOLD

VOTES_TO_BIND = 3
RECOGNITION_COOLDOWN = 2.0   # seconds between recognition attempts per track
REVERIFY_INTERVAL = 12.0     # seconds between re-checks of a bound identity
MISMATCHES_TO_UNBIND = 2     # consecutive failed re-verifications


class IdentityBinder:
    def __init__(self, threshold=CLASS_MONITOR_THRESHOLD, debug=False):
        self.threshold = threshold
        self.debug = debug
        self.tracks = {}  # track_id -> state

    def _state(self, track_id):
        return self.tracks.setdefault(track_id, {
            "name": None,
            "votes": Counter(),
            "last_attempt": 0.0,
            "last_verify": 0.0,
            "mismatches": 0,
            "last_distance": None,
        })

    def _recognize(self, face_crop, allowed_names):
        return recognize_student(
            face_crop,
            threshold=self.threshold,
            debug=self.debug,
            allowed_names=allowed_names,
            return_score=True,
        )

    def _unbind(self, state, reason=""):
        if self.debug and state["name"]:
            print(f"Identity unbound: {state['name']} ({reason})")
        state["name"] = None
        state["votes"].clear()
        state["mismatches"] = 0
        state["last_distance"] = None

    def _bind(self, track_id, state, name, distance, now):
        # One name, one track: challenge any other track holding this name.
        for other_id, other in self.tracks.items():
            if other_id == track_id or other["name"] != name:
                continue
            other_dist = other["last_distance"]
            if distance is not None and (other_dist is None or distance < other_dist):
                self._unbind(other, reason=f"track {track_id} is a closer match")
            else:
                # Existing binding wins; drop our votes so we don't thrash.
                state["votes"].clear()
                return
        state["name"] = name
        state["votes"].clear()
        state["mismatches"] = 0
        state["last_distance"] = distance
        state["last_verify"] = now
        if self.debug:
            print(f"Identity bound: track {track_id} -> {name} (dist {distance:.3f})")

    def update(self, track_id, face_crop, allowed_names=None, now=None):
        """
        Feed the current face crop for a track; returns the track's bound
        name or "Unknown". Recognition itself runs at most once per
        cooldown/verify interval — cheap to call every frame.
        """
        if now is None:
            now = time.time()
        state = self._state(track_id)

        if state["name"] is None:
            # Voting phase
            if now - state["last_attempt"] >= RECOGNITION_COOLDOWN:
                state["last_attempt"] = now
                name, distance = self._recognize(face_crop, allowed_names)
                if name != "Unknown":
                    state["votes"][name] += 1
                    state["last_distance"] = distance
                    if state["votes"][name] >= VOTES_TO_BIND:
                        self._bind(track_id, state, name, distance, now)
        else:
            # Re-verification phase
            if now - state["last_verify"] >= REVERIFY_INTERVAL:
                state["last_verify"] = now
                name, distance = self._recognize(face_crop, allowed_names)
                if name == state["name"]:
                    state["mismatches"] = 0
                    state["last_distance"] = distance
                else:
                    # Unknown or a different student both count: a binding
                    # that stops verifying should not keep logging events.
                    state["mismatches"] += 1
                    if state["mismatches"] >= MISMATCHES_TO_UNBIND:
                        self._unbind(state, reason=f"failed re-verification ({name})")

        return state["name"] or "Unknown"

    def prune(self, active_track_ids):
        """Drop state for tracks the tracker no longer reports."""
        self.tracks = {tid: st for tid, st in self.tracks.items()
                       if tid in active_track_ids}

    def bound_names(self):
        return {st["name"] for st in self.tracks.values() if st["name"]}
