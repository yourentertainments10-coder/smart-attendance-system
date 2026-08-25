from flask import Blueprint, request, render_template, redirect, url_for, flash
from utils.camera_utils_fixed import register_student
from database.db_connection import get_db

student_bp = Blueprint('student', __name__, template_folder='../templates')


@student_bp.route('/register_student', methods=['GET', 'POST'])
def register_student_route():
    if request.method == 'POST':
        student_id = request.form.get('student_id', '').strip()
        name = request.form.get('name', '').strip()
        recapture = request.form.get('recapture') == '1'

        if not student_id or not name:
            flash(' Enter valid Student ID and Name!')
            return redirect(url_for('student.register_student_route'))

        db = get_db()

        existing = db.execute(
            "SELECT * FROM students WHERE student_id = ?",
            (student_id,)
        ).fetchone()

        if existing and not recapture:
            flash(" Student ID already exists! Tick 'Re-capture photos' to add more photos for this student.")
            return redirect(url_for('student.register_student_route'))

        if existing:
            # Re-capture: keep the registered name so photos land in the right folder
            name = existing['name']

        folder_name = f"{student_id}_{name.replace(' ', '_')}"

        try:
            saved = register_student(student_id, name, allow_append=bool(existing))

            if not existing:
                db.execute(
                    "INSERT INTO students (student_id, name, folder_name) VALUES (?, ?, ?)",
                    (student_id, name, folder_name)
                )
                db.commit()

            # Reload dataset
            from services.face_recognition_service import load_dataset
            load_dataset(force_reload=True)

            if saved > 0:
                flash(f" Captured {saved} photos for {name}!", "success")
            elif existing:
                flash(" No new photos captured.")
            else:
                flash(" Student registered, but no photos were captured. Use 'Re-capture photos' to try again.")

        except Exception as e:
            flash(f'Error: {str(e)}')

        return redirect(url_for('student.register_student_route'))

    return render_template('register_student.html')
