import pandas as pd
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from database.db_connection import get_db
from utils.date_utils import get_current_date
from datetime import datetime, timedelta
import io

def generate_daily_report(date=None):
    if not date:
        date = get_current_date()
    db = get_db()
    df = pd.read_sql_query(f"""
        SELECT s.name, a.time, a.recognized_name 
        FROM attendance a 
        JOIN students s ON a.student_id = s.student_id 
        WHERE date = '{date}'
        ORDER BY a.time
    """, db)
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    
    title = Paragraph(f"Daily Attendance Report - {date}", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 12))
    
    data = [['Name', 'Time']] + df.values.tolist()
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(table)
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue(), f"daily_report_{date}.pdf"

def generate_monthly_report(month=None):
    if not month:
        month = datetime.now().strftime('%Y-%m')
    db = get_db()
    df = pd.read_sql_query(f"""
        SELECT s.name, COUNT(*) as days_present 
        FROM attendance a 
        JOIN students s ON a.student_id = s.student_id 
        WHERE strftime('%Y-%m', date) = '{month}'
        GROUP BY s.student_id
        ORDER BY days_present DESC
    """, db)
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    
    title = Paragraph(f"Monthly Attendance Report - {month}", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 12))
    
    data = [['Name', 'Days Present']] + df[['name', 'days_present']].values.tolist()
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(table)
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue(), f"monthly_report_{month}.pdf"

def generate_defaulters_report(days_threshold=3):
    today = datetime.now().date()
    start_date = today - timedelta(days=days_threshold)
    db = get_db()
    df = pd.read_sql_query(f"""
        SELECT s.student_id, s.name, COUNT(a.id) as attended 
        FROM students s 
        LEFT JOIN attendance a ON s.student_id = a.student_id AND date >= '{start_date}'
        GROUP BY s.student_id 
        HAVING attended < {days_threshold}
        ORDER BY attended
    """, db)
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    
    title = Paragraph(f"Defaulters Report (Last {days_threshold} days)", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 12))
    
    data = [['ID', 'Name', 'Attended Days']] + df.values.tolist()
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.red),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(table)
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue(), f"defaulters_{days_threshold}d.pdf"

def generate_excel_report(file_type='daily'):
    db = get_db()
    if file_type == 'daily':
        date = get_current_date()
        query = f"SELECT * FROM attendance WHERE date = '{date}'"
        filename = f"daily_attendance_{date}.xlsx"
    elif file_type == 'monthly':
        month = datetime.now().strftime('%Y-%m')
        query = f"SELECT * FROM attendance WHERE strftime('%Y-%m', date) = '{month}'"
        filename = f"monthly_attendance_{month}.xlsx"
    else:
        query = "SELECT * FROM attendance"
        filename = "full_attendance.xlsx"
    
    df = pd.read_sql_query(query, db)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    buffer.seek(0)
    return buffer.getvalue(), filename

