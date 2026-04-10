from flask import Flask, Response, g, session
from routes.auth_routes import auth_bp
from routes.student_routes import student_bp
from routes.attendance_routes import attendance_bp
from routes.analytics_routes_fixed import analytics_bp
from routes.report_routes import report_bp
from utils.camera_utils_fixed import gen_frames
from services.face_recognition_service import load_dataset
from database.db_connection import get_db, close_db, init_app
from flask import current_app
load_dataset()

app = Flask(__name__)
app.secret_key = 'smart_attendance_secret_dev_key_change_in_prod'
app.register_blueprint(auth_bp)
app.register_blueprint(student_bp)
app.register_blueprint(attendance_bp)
app.register_blueprint(analytics_bp)
app.register_blueprint(report_bp)
init_app(app)

# Auto-initialize database on startup
with app.app_context():
    db = get_db()
    try:
        with open('database/schema.sql', 'r') as f:
            db.executescript(f.read())
        with open('database/seed_data.sql', 'r') as f:
            db.executescript(f.read())
        db.commit()
        print('✓ Database auto-initialized (tables created)')
    except Exception as e:
        print(f'Note: DB init skipped - {e}')


import os
@app.route('/init_db')
def init_db():
    print("DB PATH:", current_app.config.get('DATABASE', 'NOT SET'))
    try:
        db = get_db()

        base_dir = os.path.dirname(os.path.abspath(__file__))

        schema_path = os.path.join(base_dir, 'database', 'schema.sql')
        seed_path = os.path.join(base_dir, 'database', 'seed_data.sql')

        with open(schema_path, 'r') as f:
            db.executescript(f.read())

        with open(seed_path, 'r') as f:
            db.executescript(f.read())

        db.commit()

        print('Database initialized successfully!')
        return 'Database initialized ✓ students/attendance tables + seed data.'

    except Exception as e:
        print(e)
        return f"Database initialization failed: {str(e)}"
@app.route("/")
def home():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Smart Attendance System</title>
</head>
<body>
    <h1>Smart Attendance System</h1>
    <nav>
        <a href="/camera">Live Camera</a> |
        <a href="/register_student">Register Student</a> |
        <a href="/attendance">Take Attendance</a> |
        <a href="/analytics">Analytics Dashboard</a> |
        <a href="/reports">Reports</a>
    </nav>
    <img src="/camera" width="640" height="480">
</body>
</html>
    """


@app.route("/camera")
def camera():
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    app.run(debug=True)
