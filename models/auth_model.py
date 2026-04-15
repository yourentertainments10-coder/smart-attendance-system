from database.db_connection import get_db

def get_user(username):
    """Get user by username"""
    db = get_db()
    user = db.execute(
        'SELECT id, username, password_hash FROM users WHERE username = ?',
        (username,)
    ).fetchone()
    return user

def create_user(username, password_hash):
    """Create new user"""
    db = get_db()
    db.execute(
        'INSERT INTO users (username, password_hash) VALUES (?, ?)',
        (username, password_hash)
    )
    db.commit()

def update_user_password(user_id, new_hash):
    """Update user password"""
    db = get_db()
    db.execute(
        'UPDATE users SET password_hash = ? WHERE id = ?',
        (new_hash, user_id)
    )
    db.commit()

def get_user_by_id(user_id):
    """Get user by ID"""
    db = get_db()
    user = db.execute(
        'SELECT id, username FROM users WHERE id = ?',
        (user_id,)
    ).fetchone()
    return user
