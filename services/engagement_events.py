"""
Per-student behavior state machine -> engagement_events rows.

The classifier emits a raw state every processed frame; committing each one
would produce useless spam ("looked away for 0.3s"). This layer commits a
state change only after it persists for DEBOUNCE_SECONDS, giving the
teacher-readable timeline:  10:02 attentive -> 10:14 phone -> 10:17 attentive.
"""
import time
from datetime import datetime

from models.engagement_model import insert_event, close_event, close_dangling_events
from services.behavior_classifier import STATE_NOT_VISIBLE

DEBOUNCE_SECONDS = 4.0    # a raw state must hold this long to become an event
DISAPPEAR_SECONDS = 8.0   # unseen for this long -> not_visible


def _ts(epoch):
    return datetime.fromtimestamp(epoch).strftime("%Y-%m-%d %H:%M:%S")


class EngagementEventLogger:
    def __init__(self, debounce=DEBOUNCE_SECONDS):
        # A previous crash can leave events open; zero them out so they
        # don't read as hours-long states.
        try:
            close_dangling_events()
        except Exception as e:
            print("Could not close dangling events:", e)
        self.debounce = debounce
        self.students = {}  # name -> state dict

    def _student(self, name, now):
        return self.students.setdefault(name, {
            "current": None,      # committed state
            "event_id": None,     # open engagement_events row
            "candidate": None,    # raw state waiting out the debounce
            "candidate_since": now,
            "last_seen": now,
        })

    def _commit(self, name, st, state, started_at):
        student_id = name.split("_")[0]
        started = _ts(started_at)
        try:
            if st["event_id"] is not None:
                close_event(st["event_id"], started)
            st["event_id"] = insert_event(student_id, state, started)
        except Exception as e:
            print("Event write skipped:", e)
            st["event_id"] = None
        st["current"] = state
        st["candidate"] = None

    def observe(self, name, raw_state, now=None):
        """Feed one raw classifier state for an identified student."""
        if now is None:
            now = time.time()
        st = self._student(name, now)
        st["last_seen"] = now

        if raw_state == st["current"]:
            st["candidate"] = None
            return
        if raw_state != st["candidate"]:
            st["candidate"] = raw_state
            st["candidate_since"] = now
            return
        if now - st["candidate_since"] >= self.debounce:
            self._commit(name, st, raw_state, st["candidate_since"])

    def tick(self, now=None):
        """Call once per processed frame: students that vanished from the
        camera long enough get a not_visible event (no extra debounce — the
        disappearance gap itself is the evidence)."""
        if now is None:
            now = time.time()
        for name, st in self.students.items():
            if (st["current"] != STATE_NOT_VISIBLE
                    and now - st["last_seen"] >= DISAPPEAR_SECONDS):
                self._commit(name, st, STATE_NOT_VISIBLE, st["last_seen"])

    def close_all(self, now=None):
        """Monitor stream is stopping: end every open event."""
        if now is None:
            now = time.time()
        for st in self.students.values():
            if st["event_id"] is not None:
                try:
                    close_event(st["event_id"], _ts(now))
                except Exception as e:
                    print("Event close skipped:", e)
                st["event_id"] = None
        self.students = {}
