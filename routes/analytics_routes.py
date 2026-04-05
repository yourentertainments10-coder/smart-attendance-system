from flask import Blueprint, jsonify
from database.db_connection import get_db
from utils.date_utils import get_current_date
from datetime import datetime
import sqlite3
from flask import render_template
analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/analytics')
def analytics_page():
    return render_template('analytics.html')

@analytics_bp.route('/analytics/analytics_data')
def analytics_data():
    db = sqlite3.connect('smart_attendance.db', detect_types=sqlite3.PARSE_DECLTYPES)
    db.row_factory = sqlite3.Row
    
    # Total students
    total_students = db.execute('SELECT COUNT(*) FROM students').fetchone()[0]
    
    # Today
    today = get_current_date()
    present = db.execute('SELECT COUNT(*) FROM attendance WHERE date = ?', (today,)).fetchone()[0]
    absent = total_students - present
    percentage = round((present / total_students * 100), 1) if total_students > 0 else 0
    
    # Daily last 7
    daily = db.execute('''
        SELECT date, COUNT(*) as count 
        FROM attendance 
        GROUP BY date 
        ORDER BY date DESC LIMIT 7
    ''').fetchall()
    daily_data = [{'date': row[0], 'count': row[1]} for row in daily]
    
    # Monthly last 6
    monthly = db.execute('''
        SELECT strftime("%Y-%m", date) as month, COUNT(*) as count 
        FROM attendance 
        GROUP BY month 
        ORDER BY month DESC LIMIT 6
    ''').fetchall()
    monthly_data = [{'month': row[0], 'count': row[1]} for row in monthly]
    
    # Student attendance %
    students_att = db.execute('''
        SELECT s.student_id, s.name, COUNT(a.id) * 100.0 / (julianday('now') - julianday(s.created) + 1) as perc
        FROM students s 
        LEFT JOIN attendance a ON s.student_id = a.student_id
        GROUP BY s.student_id
        ORDER BY perc DESC LIMIT 10
    ''').fetchall()
    student_data = [{'id': row[0], 'name': row[1], 'perc': round(row[2], 1)} for row in students_att]
    
    # Recent attendance records
    recent = db.execute('''
        SELECT s.student_id, s.name, a.date, a.time
        FROM attendance a
        JOIN students s ON a.student_id = s.student_id
        ORDER BY a.date DESC, a.time DESC
        LIMIT 10
    ''').fetchall()
    recent_data = [
        {
            'id': row[0],
            'name': row[1],
            'date': row[2],
            'time': row[3]
        }
        for row in recent
    ]
    
    db.close()
    return jsonify({
        'stats': {
            'total': total_students,
            'present': present,
            'absent': absent,
            'percentage': percentage
        },
        'daily': daily_data,
        'monthly': monthly_data,
        'students': student_data,
        'recent_attendance': recent_data
    })

