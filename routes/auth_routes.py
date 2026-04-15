from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from models.auth_model import get_user, get_user_by_id, update_user_password
from werkzeug.security import check_password_hash
import functools

auth_bp = Blueprint('auth', __name__, template_folder='templates')

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
        username = request.form['username']
        password = request.form['password']
        user = get_user(username)
        if user and check_password_hash(user['password_hash'], password):
            session['logged_in'] = True
            session['user_id'] = user['id']
            return redirect(url_for('analytics.analytics_page'))
        flash('Invalid credentials')
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('user_id', None)
    flash('Logged out successfully')
    return redirect(url_for('auth.login'))


@auth_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    user_id = session.get('user_id')
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        if new_password != confirm_password:
            flash('New passwords do not match')
            return render_template('change_password.html')
        
        if len(new_password) < 6:
            flash('New password must be at least 6 characters')
            return render_template('change_password.html')
        
        user = get_user_by_id(user_id)
        if not check_password_hash(user['password_hash'], current_password):
            flash('Current password incorrect')
            return render_template('change_password.html')
        
        from werkzeug.security import generate_password_hash
        new_hash = generate_password_hash(new_password)
        update_user_password(user_id, new_hash)
        flash('Password changed successfully')
        return redirect(url_for('analytics.analytics_page'))
    print(user)
    print(dict(user))
    return render_template('change_password.html')


@auth_bp.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        username = request.form['username']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        if new_password != confirm_password:
            flash('New passwords do not match')
            return render_template('reset_password.html')
        
        if len(new_password) < 6:
            flash('New password must be at least 6 characters')
            return render_template('reset_password.html')
        
        user = get_user(username)
        if not user:
            flash('Username not found')
            return render_template('reset_password.html')
        
        from werkzeug.security import generate_password_hash
        new_hash = generate_password_hash(new_password)
        update_user_password(user['id'], new_hash)
        flash('Password reset successfully. Please login with new password.')
        return redirect(url_for('auth.login'))
    
    return render_template('reset_password.html')
