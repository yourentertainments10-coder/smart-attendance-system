from flask import Blueprint, request, render_template, redirect, url_for, flash
from utils.camera_utils_fixed import register_student

student_bp = Blueprint('student', __name__, template_folder='../templates')


from flask import Blueprint, request, render_template, redirect, url_for, flash
from utils.camera_utils_fixed import register_student
from database.db_connection import get_db

student_bp = Blueprint('student', __name__, template_folder='../templates')
@student_bp.route('/register_student', methods=['GET', 'POST'])
def register_student_route():
    if request.method == 'POST':
        student_id = request.form.get('student_id', '').strip()
        name = request.form.get('name', '').strip()

        if not student_id or not name:
            flash('❌ Enter valid Student ID and Name!')
            return redirect(url_for('student.register_student_route'))

        db = get_db()

        # ✅ CHECK DUPLICATE ID
        existing = db.execute(
            "SELECT * FROM students WHERE student_id = ?",
            (student_id,)
        ).fetchone()

        if existing:
            flash("❌ Student ID already exists! Use a unique ID.")
            return redirect(url_for('student.register_student_route'))

        folder_name = f"{student_id}_{name.replace(' ', '_')}"

        try:
            # ✅ CAPTURE AFTER CHECK
            register_student(student_id, name)

            # ✅ INSERT
            db.execute(
                "INSERT INTO students (student_id, name, folder_name) VALUES (?, ?, ?)",
                (student_id, name, folder_name)
            )
            db.commit()

            # Reload dataset
            from services.face_recognition_service import load_dataset
            load_dataset()

            flash("✅ Student registered successfully!", "success")

        except Exception as e:
            flash(f'Error: {str(e)}')

        return redirect(url_for('student.register_student_route'))

    return render_template('register_student.html')