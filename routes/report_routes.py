from flask import Blueprint, render_template, request, send_file, flash
from services.report_generator import generate_daily_report, generate_monthly_report, generate_defaulters_report, generate_excel_report
from utils.date_utils import get_current_date
from datetime import datetime
import io
import os
from werkzeug.utils import secure_filename

report_bp = Blueprint('reports', __name__, template_folder='templates')

@report_bp.route('/reports')
def reports_page():
    current_month = datetime.now().strftime('%Y-%m')
    return render_template('reports.html', current_date=get_current_date(), current_month=current_month)

@report_bp.route('/reports/daily', methods=['POST'])
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
    days = int(request.form.get('days', 3))
    fmt = request.form.get('format', 'pdf')
    try:
        if fmt == 'excel':
            data, filename = generate_excel_report('defaulters')
        else:
            data, filename = generate_defaulters_report(days)
        return send_file(
            io.BytesIO(data),
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf' if fmt == 'pdf' else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        flash(f'Error generating report: {str(e)}')
        return render_template('reports.html')

