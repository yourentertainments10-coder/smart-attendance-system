from flask import Blueprint, request, render_template, redirect, url_for, flash
from utils.camera_utils import register_student

student_bp = Blueprint('student', __name__, template_folder='../templates')


from flask import Blueprint, request, render_template, redirect, url_for, flash
from utils.camera_utils import register_student
from database.db_connection import get_db

student_bp = Blueprint('student', __name__, template_folder='../templates')

@student_bp.route('/register_student', methods=['GET', 'POST'])
def register_student_route():
    if request.method == 'POST':
        student_id = request.form['student_id']
        name = request.form['name']
        folder_name = f"{student_id}_{name.replace(' ', '_')}"

        try:
            saved = register_student(folder_name)

            # ✅ INSERT INTO DATABASE
            db = get_db()
            db.execute(
                "INSERT OR IGNORE INTO students (student_id, name, folder_name) VALUES (?, ?, ?)",
                (student_id, name, folder_name)
            )
            db.commit()

            flash(f'Successfully captured {saved} images for {name}!')

            return redirect(url_for('student.register_student_route'))

        except Exception as e:
            flash(f'Error: {str(e)}')

    return render_template('register_student.html')
