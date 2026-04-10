import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

INSTANCE_PATH = os.path.join(BASE_DIR, 'instance')

# Ensure instance folder exists
os.makedirs(INSTANCE_PATH, exist_ok=True)

DATABASE = os.path.join(INSTANCE_PATH, 'smart_attendance.db')

SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-smart-attendance-key'