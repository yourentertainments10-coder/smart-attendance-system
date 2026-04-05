import os

class Config:
    DATABASE = os.path.join(os.path.dirname(__file__), 'smart_attendance.db')
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-smart-attendance-key'
