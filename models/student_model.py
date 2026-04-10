from database.db_connection import get_db
from flask import g

def create_student(student_id, name, folder_name):
    """Create a new student with error handling."""
    try:
        db = get_db()
        db.execute(
            'INSERT INTO students (student_id, name, folder_name) VALUES (?, ?, ?)',
            (student_id, name, folder_name)
        )
        db.commit()
        return {'student_id': student_id, 'name': name, 'folder_name': folder_name}
    except Exception as e:
        print(f"Error creating student: {e}")
        return None

def get_student_by_id(student_id):
    """Get student by student_id, returns dict."""
    db = get_db()
    student = db.execute(
        'SELECT * FROM students WHERE student_id = ?',
        (student_id,)
    ).fetchone()
    if student:
        return dict(student)
    return None

def get_all_students():
    """Get all students as list of dicts."""
    db = get_db()
    students = db.execute('SELECT * FROM students ORDER BY name').fetchall()
    return [dict(student) for student in students]

def delete_student(student_id):
    """Delete student by student_id."""
    try:
        db = get_db()
        result = db.execute('DELETE FROM students WHERE student_id = ?', (student_id,)).rowcount
        db.commit()
        return result > 0
    except Exception as e:
        print(f"Error deleting student: {e}")
        return False
