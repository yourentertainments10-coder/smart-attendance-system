import os
import sqlite3
from database.db_connection import get_db
from utils.date_utils import get_current_date, get_current_time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_PATH = os.path.join(BASE_DIR, "instance", "smart_attendance.db")


def get_present_folder_names(date=None):
    """
    Folder names (dataset identities) of students marked present on `date`
    (default: today). Uses its own connection — callable from the monitor
    stream, outside any Flask request context.
    """
    if date is None:
        date = get_current_date()
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        rows = conn.execute("""
            SELECT s.folder_name
            FROM attendance a
            JOIN students s ON s.student_id = a.student_id
            WHERE a.date = ?
        """, (date,)).fetchall()
        return {row[0] for row in rows}
    except Exception as e:
        print(f"Present-list query failed: {e}")
        return set()
    finally:
        conn.close()

def mark_attendance(student_id, recognized_name):
    from utils.date_utils import get_current_date, get_current_time
    db = get_db()
    db.row_factory = sqlite3.Row
    date = get_current_date()
    time = get_current_time()
    
    # pehle check karo student exist karta hai ya nahi
    student = db.execute(
        "SELECT * FROM students WHERE student_id = ?",
        (student_id,)
    ).fetchone()

    if not student:
        print(f"❌ Unknown student {student_id} - not registered")
        return False
    
    existing = db.execute('''
        SELECT 1 FROM attendance 
        WHERE student_id = ? AND date = ?
    ''', (student_id, date)).fetchone()

    if existing:
        #print(f"⚠️ Attendance already marked for {recognized_name}")
        return False

    
    db.execute("""
        INSERT INTO attendance (student_id, date, time, recognized_name) 
        VALUES (?, ?, ?, ?)
    """, (student_id, date, time, recognized_name))

    db.commit()
    print(f"✅ Attendance marked for {recognized_name}")
    return True




