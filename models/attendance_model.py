import sqlite3
from database.db_connection import get_db
from utils.date_utils import get_current_date, get_current_time

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
        print(f"⚠️ Attendance already marked for {recognized_name}")
        return False

    
    db.execute("""
        INSERT INTO attendance (student_id, date, time, recognized_name) 
        VALUES (?, ?, ?, ?)
    """, (student_id, date, time, recognized_name))

    db.commit()
    print(f"✅ Attendance marked for {recognized_name}")
    return True




