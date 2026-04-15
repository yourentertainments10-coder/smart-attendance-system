from flask import Blueprint, render_template, request, send_file, flash
from services.report_generator import generate_daily_report, generate_monthly_report, generate_defaulters_report, generate_excel_report
from utils.date_utils import get_current_date
from datetime import datetime
import io
import os
from database.db_connection import get_db
from werkzeug.utils import secure_filename
from routes.auth_routes import login_required
report_bp = Blueprint('reports', __name__, template_folder='templates')
@login_required
@report_bp.route('/reports')
def reports_page():
    db = get_db()

    rows = db.execute('''
        SELECT DISTINCT date FROM attendance
        ORDER BY date DESC
        LIMIT 5
    ''').fetchall()

    # ✅ Proper structure for frontend
    recent_reports = [
        {
            "name": f"Daily Report {row['date']}",
            "url": f"/reports/daily?date={row['date']}",
            "date": row['date']
        }
        for row in rows
    ]

    return render_template('reports.html', recent_reports=recent_reports)

@report_bp.route('/reports/daily', methods=['GET','POST'])
def daily_report():
    date = request.form.get('date', get_current_date())
    fmt = request.form.get('format', 'pdf')
    try:
        if fmt == 'excel':
            data, filename = generate_excel_report('daily')
        else:
            data, filename = generate_daily_report(date)
        return send_file(
            io.BytesIO(data),
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf' if fmt == 'pdf' else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        flash(f'Error generating report: {str(e)}')
        return render_template('reports.html')

@report_bp.route('/reports/monthly', methods=['POST'])
def monthly_report():
    month = request.form.get('month', datetime.now().strftime('%Y-%m'))
    fmt = request.form.get('format', 'pdf')
    try:
        if fmt == 'excel':
            data, filename = generate_excel_report('monthly')
        else:
            data, filename = generate_monthly_report(month)
        return send_file(
            io.BytesIO(data),
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf' if fmt == 'pdf' else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        flash(f'Error generating report: {str(e)}')
        return render_template('reports.html')

@report_bp.route('/reports/defaulters', methods=['POST'])
def defaulters_report():
    days = request.form.get('days', '3')
    fmt = request.form.get('format', 'pdf')
    
    db = get_db()
    defaulters = db.execute('''
        SELECT s.student_id, s.name
        FROM students s
        WHERE s.student_id NOT IN (
            SELECT DISTINCT student_id
            FROM attendance
            WHERE date >= date('now', ?)
        )
    ''', (f'-{days} days',)).fetchall()
    
    try:
        if fmt == 'excel':
            filename = f"defaulters_{days}days.xlsx"
            data = generate_excel_report(defaulters, "defaulters")
        else:
            filename = f"defaulters_{days}days.txt"
            data = "\n".join([f"{row['student_id']} - {row['name']}" for row in defaulters]).encode()
        
        return send_file(
            io.BytesIO(data),
            as_attachment=True,
            download_name=filename,
            mimetype='text/plain' if fmt != 'excel' else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        flash(f'Error generating report: {str(e)}')
        from flask import redirect, url_for
        return redirect(url_for('reports.reports_page'))

