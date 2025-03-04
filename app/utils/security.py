# app/utils/security.py

from flask import session, flash, redirect, url_for
from functools import wraps
import sqlite3

from config import Config

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("discord_id") and not session.get("guest_id"):
            flash("You must be logged in", "danger")
            return redirect(url_for("login"))

        # Check if this user is banned
        user_id = session.get("discord_id") or session.get("guest_id")
        with sqlite3.connect(Config.DATABASE_PATH) as conn:
            conn.row_factory = sqlite3.Row
            is_banned = conn.execute(
                "SELECT 1 FROM banned_users WHERE user_id=?",
                (str(user_id),)
            ).fetchone()
            if is_banned:
                flash("You are banned and cannot perform this action.", "danger")
                return redirect(url_for("main.index"))

        return f(*args, **kwargs)
    return decorated_function



def get_user_role(discord_id=None, guest_id=None):
    """
    Retrieve the role (admin, moderator, user, guest) for a given user.
    """
    with sqlite3.connect(Config.DATABASE_PATH) as conn:
        cursor = conn.execute(
            "SELECT role FROM user_roles WHERE discord_id = ?", 
            (discord_id,)
        )
        if guest_id:
            return "user"
        result = cursor.fetchone()
    return result[0] if result else "user"


def requires_role(required_role):
    """
    Decorator to require that the user has at least the specified role
    in the role hierarchy.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "discord_id" not in session and "guest_id" not in session:
                flash("Please log in or continue as guest.", "danger")
                return redirect(url_for("auth.login"))

            # Distinguish between Discord user or guest
            discord_id = session.get("discord_id")
            guest_id = session.get("guest_id")
            user_role = get_user_role(discord_id, guest_id)

            role_hierarchy = {
                "admin": 3,
                "moderator": 2,
                "user": 1,
                "guest": 1,  
            }

            if role_hierarchy.get(user_role, 0) >= role_hierarchy.get(required_role, 0):
                return f(*args, **kwargs)
            else:
                flash("Insufficient permissions.", "danger")
                return redirect(url_for("main.index"))
        return decorated_function
    return decorator


def ensure_default_roles():
    """
    Inserts a default admin or moderator roles if needed.
    """
    import sqlite3
    with sqlite3.connect(Config.DATABASE_PATH) as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO user_roles (discord_id, role, assigned_by)
            VALUES (?, ?, ?)
            """,
            ("278344153761316864", "admin", "system"),
        )
        # Insert default moderators if desired
        default_moderators = []
        for mod in default_moderators:
            conn.execute(
                """
                INSERT OR IGNORE INTO user_roles (discord_id, role, assigned_by)
                VALUES (?, ?, ?)
                """,
                (mod["discord_id"], mod["role"], "system"),
            )
