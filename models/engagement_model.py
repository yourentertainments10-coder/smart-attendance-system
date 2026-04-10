import sqlite3
from database.db_connection import get_db
from utils.date_utils import get_current_date, get_current_time

def record_engagement(student_id, avg_engagement):
    """
    Record average engagement score for a student on current date.
    """
    db = get_db()
    date = get_current_date()
    
    try:
        # Update or insert average for the day
        db.execute('''
            INSERT INTO engagement (student_id, date, avg_engagement)
            VALUES (?, ?, ?)
            ON CONFLICT(student_id, date) DO UPDATE SET
            avg_engagement = excluded.avg_engagement
        ''', (student_id, date, avg_engagement))
        db.commit()
        return True
    except Exception as e:
        print(f"Engagement record error: {e}")
        db.rollback()
        return False

def get_engagement_stats(limit=10):
    """
    Get top students by average engagement.
    """
    db = get_db()
    try:
        stats = db.execute('''
            SELECT student_id, AVG(avg_engagement)*100 as avg_eng
            FROM engagement 
            GROUP BY student_id
            ORDER BY avg_eng DESC 
            LIMIT ?
        ''', (limit,)).fetchall()
        return [{'id': row['student_id'], 'avg': round(row['avg_eng'], 1)} for row in stats]
    except:
        return []


if __name__ == "__main__":
    print("Engagement model ready")
