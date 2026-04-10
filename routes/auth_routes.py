from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
import functools

auth_bp = Blueprint('auth', __name__, template_folder='templates')

USERNAME = 'admin'
PASSWORD = 'admin123'

def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Please log in first.')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == USERNAME and request.form['password'] == PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('analytics.analytics_page'))  # Redirect to analytics dashboard
        flash('Invalid credentials')
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('Logged out successfully')
    return redirect(url_for('auth.login'))
