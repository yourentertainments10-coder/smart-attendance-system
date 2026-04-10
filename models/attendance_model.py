import sqlite3
from database.db_connection import get_db
from utils.date_utils import get_current_date, get_current_time

def mark_attendance(student_id, recognized_name):
    from utils.date_utils import get_current_date, get_current_time
    db = get_db()
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
        return True
    except sqlite3.IntegrityError:
        print(f"Duplicate attendance for {student_id} on {date}")
        db.rollback()
        return False




