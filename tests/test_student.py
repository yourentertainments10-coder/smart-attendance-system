import sys
import os
import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.student_model import create_student, get_student_by_id, get_all_students, delete_student
from database.db_connection import get_db
import sqlite3

from app import app
@pytest.fixture
def setup_db():
    with app.app_context():
        db = get_db()
        db.execute('DELETE FROM students')  # Clean slate
        db.commit()
        yield db
        db.execute('DELETE FROM students')
        db.commit()


def test_create_and_get_student(setup_db):
    # Test insert
    result = create_student('STU001', 'John Doe', 'john_doe')
    assert result is not None
    assert result['student_id'] == 'STU001'

    # Test fetch
    student = get_student_by_id('STU001')
    assert student is not None
    assert student['name'] == 'John Doe'
    assert student['folder_name'] == 'john_doe'


def test_delete_student(setup_db):
    create_student('STU002', 'Jane Smith', 'jane_smith')
    success = delete_student('STU002')
    assert success is True

    student = get_student_by_id('STU002')
    assert student is None