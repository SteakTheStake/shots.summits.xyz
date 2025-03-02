# auth_utils.py
from functools import wraps
from flask import session, flash, redirect, url_for
import sqlite3

def get_user_role(discord_id):
    with sqlite3.connect("screenshots.db") as conn:
        cursor = conn.execute(
            "SELECT role FROM user_roles WHERE discord_id = ?",
            (discord_id,)
        )
        result = cursor.fetchone()
        return result[0] if result else 'user'

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'discord_id' not in session and 'username' not in session:
            flash("Please log in first.", "danger")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def requires_role(required_role):
    """
    Decorator to require a certain role or higher in role_hierarchy.
    e.g. 'admin' = 3, 'moderator' = 2, 'user' = 1
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            discord_id = session.get('discord_id')
            if not discord_id:
                flash('Please log in first.', 'danger')
                return redirect(url_for('login'))

            user_role = get_user_role(discord_id)
            role_hierarchy = {
                'admin': 3,
                'moderator': 2,
                'user': 1
            }

            if role_hierarchy.get(user_role, 0) >= role_hierarchy.get(required_role, 0):
                return f(*args, **kwargs)
            else:
                flash('Insufficient permissions.', 'danger')
                return redirect(url_for('index'))
        return decorated_function
    return decorator
