import sqlite3
import os
from datetime import datetime
from utils.date_utils import get_current_date, get_current_time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_PATH = os.path.join(BASE_DIR, "instance", "smart_attendance.db")


def record_engagement(student_id, avg_engagement):
    """
    Record a continuous engagement sample for a student.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO engagement (student_id, avg_engagement, date, timestamp)
        VALUES (?, ?, ?, datetime('now'))
    """, (student_id, avg_engagement, datetime.now().date()))

    conn.commit()
    conn.close()
    print(f"✅ Engagement saved for {student_id}")
    return True


def get_engagement_stats(limit=10):
    """
    Get top students by average engagement.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT student_id, AVG(avg_engagement)*100 as avg_eng
            FROM engagement
            GROUP BY student_id
            ORDER BY avg_eng DESC
            LIMIT ?
        """, (limit,))
        stats = cursor.fetchall()
        conn.close()
        return [{'id': row[0], 'avg': round(row[1], 1)} for row in stats]
    except Exception as e:
        print(f"Engagement stats error: {e}")
        conn.close()
        return []


def insert_event(student_id, event_type, start_time):
    """
    Open a new behavior event ("YYYY-MM-DD HH:MM:SS" start_time, end_time
    stays NULL until closed). Returns the event row id.
    """
    date = start_time.split(" ")[0]
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        cursor = conn.execute("""
            INSERT INTO engagement_events (student_id, date, event_type, start_time)
            VALUES (?, ?, ?, ?)
        """, (student_id, date, event_type, start_time))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def close_event(event_id, end_time):
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        conn.execute("UPDATE engagement_events SET end_time = ? WHERE id = ?",
                     (end_time, event_id))
        conn.commit()
    finally:
        conn.close()


def close_dangling_events():
    """
    Zero out events left open by a crashed/killed monitor session so they
    don't read as hours-long states. Called once at monitor start.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        conn.execute("""
            UPDATE engagement_events SET end_time = start_time
            WHERE end_time IS NULL
        """)
        conn.commit()
    finally:
        conn.close()


def get_timeline(student_id, date):
    """
    Ordered behavior events for one student on one date, with durations.
    end_time None means the event is still active.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        rows = conn.execute("""
            SELECT event_type, start_time, end_time
            FROM engagement_events
            WHERE student_id = ? AND date = ?
            ORDER BY start_time
        """, (student_id, date)).fetchall()
    finally:
        conn.close()

    timeline = []
    for event_type, start_time, end_time in rows:
        duration = None
        if end_time:
            try:
                fmt = "%Y-%m-%d %H:%M:%S"
                duration = int((datetime.strptime(end_time, fmt)
                                - datetime.strptime(start_time, fmt)).total_seconds())
            except ValueError:
                pass
        timeline.append({
            "event_type": event_type,
            "start_time": start_time,
            "end_time": end_time,
            "duration_seconds": duration,
        })
    return timeline


if __name__ == "__main__":
    print("Engagement model ready")

