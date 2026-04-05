from flask import Flask, Response, g
from routes.student_routes import student_bp
from routes.attendance_routes import attendance_bp
from routes.analytics_routes import analytics_bp
from routes.report_routes import report_bp
from utils.camera_utils import gen_frames
from services.face_recognition_service import load_dataset
from database.db_connection import get_db, close_db, init_app
from flask import current_app
load_dataset()

app = Flask(__name__)
app.secret_key = 'smart_attendance_secret_dev_key_change_in_prod'
app.register_blueprint(student_bp)
app.register_blueprint(attendance_bp)
app.register_blueprint(analytics_bp)
app.register_blueprint(report_bp)
init_app(app)

@app.route('/init_db')
def init_db():
    try:
        db = get_db()

        with current_app.open_resource('database/schema.sql') as f:
            db.executescript(f.read().decode('utf-8'))

        with current_app.open_resource('database/seed_data.sql') as f:
            db.executescript(f.read().decode('utf-8'))

        db.commit()

        print('Database initialized successfully!')
        return 'Database initialized ✓ students/attendance tables + seed data.'

    except Exception as e:
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
