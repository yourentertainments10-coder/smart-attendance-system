from flask import Blueprint, jsonify, render_template, Response
from services.live_engagement import gen_class_frames,get_active_students

class_monitor_bp = Blueprint('class_monitor', __name__, template_folder='templates')
from routes.auth_routes import login_required
@login_required
@class_monitor_bp.route('/class_monitor')
def class_monitor():
    return render_template('class_monitor.html')

@class_monitor_bp.route('/class_monitor_feed')
def class_monitor_feed():
    return Response(gen_class_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@class_monitor_bp.route('/api/active_students')
def active_students():
    return jsonify(get_active_students())

@class_monitor_bp.route('/test')
def test():
    return "WORKING"