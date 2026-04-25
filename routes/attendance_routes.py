from flask import Blueprint, render_template, Response, current_app, jsonify
from utils.camera_utils_fixed import gen_frames_attendance, latest_status

attendance_bp = Blueprint('attendance', __name__, template_folder='../templates')

@attendance_bp.route('/attendance')
def attendance():
    return render_template('attendance.html')

@attendance_bp.route('/attendance_feed')
def attendance_feed():
    return Response(
        gen_frames_attendance(current_app._get_current_object()),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@attendance_bp.route('/attendance_status')
def attendance_status():
    return jsonify({"message": latest_status})