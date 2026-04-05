import sqlite3
from utils.date_utils import get_current_date, get_current_time

DATABASE = 'smart_attendance.db'

def mark_attendance(student_id, recognized_name):
    db = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES)
    db.row_factory = sqlite3.Row
    date = get_current_date()
    time = get_current_time()
    try:
        db.execute("""
            INSERT INTO attendance (student_id, date, time, recognized_name) 
            VALUES (?, ?, ?, ?)
        """, (student_id, date, time, recognized_name))
        db.commit()
        print(f"Attendance marked for {recognized_name} at {time}")
        db.close()
        return True
    except sqlite3.IntegrityError:
        print(f"Duplicate attendance for {student_id} on {date}")
        db.rollback()
        db.close()
        return False

def mark_attendance_engagement(student_id, recognized_name, avg_engagement):
    db = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES)
    date = get_current_date()
    try:
        db.execute("""
            INSERT INTO engagement (student_id, date, avg_engagement) 
            VALUES (?, ?, ?)
        """, (student_id, date, avg_engagement))
        db.commit()
        print(f"Engagement {avg_engagement:.2f} saved for {recognized_name}")
        db.close()
        return True
    except sqlite3.IntegrityError:
        print(f"Duplicate engagement for {student_id} on {date}")
        db.rollback()
        db.close()
        return False


