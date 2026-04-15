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


if __name__ == "__main__":
    print("Engagement model ready")

