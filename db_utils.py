# db_utils.py
import sqlite3
from datetime import datetime

def init_db():
    with sqlite3.connect("screenshots.db") as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS screenshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                discord_username TEXT NOT NULL,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                group_id INTEGER,
                FOREIGN KEY (group_id) REFERENCES screenshot_groups(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS screenshot_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                created_by TEXT NOT NULL,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS screenshot_tags (
                screenshot_id INTEGER,
                tag_id INTEGER,
                FOREIGN KEY (screenshot_id) REFERENCES screenshots(id),
                FOREIGN KEY (tag_id) REFERENCES tags(id),
                PRIMARY KEY (screenshot_id, tag_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_roles (
                discord_id TEXT PRIMARY KEY,
                role TEXT NOT NULL DEFAULT 'user',
                assigned_by TEXT,
                assigned_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS deletion_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                deleted_by TEXT NOT NULL,
                original_uploader TEXT NOT NULL,
                deletion_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reason TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                reported_by TEXT NOT NULL,
                reason TEXT NOT NULL,
                report_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending'
            )
        """)

def init_user_table():
    """Initialize user table for username/password authentication."""
    with sqlite3.connect("screenshots.db") as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                discord_id TEXT
            )
        """)

def ensure_default_roles():
    """
    Ensures default admin and moderator roles are set in the database.
    Should be called during application initialization.
    """
    default_admin = {
        'discord_id': '278344153761316864',  # example
        'username': 'StakeTheSteak',
        'role': 'admin'
    }

    default_moderators = [
        # Add default moderators here as needed
        # {'discord_id': 'some_id', 'username': 'mod_name', 'role': 'moderator'},
    ]

    with sqlite3.connect("screenshots.db") as conn:
        # Ensure admin exists
        conn.execute("""
            INSERT OR IGNORE INTO user_roles (discord_id, role, assigned_by)
            VALUES (?, ?, ?)
        """, (default_admin['discord_id'], default_admin['role'], 'system'))

        # Ensure moderators exist
        for mod in default_moderators:
            conn.execute("""
                INSERT OR IGNORE INTO user_roles (discord_id, role, assigned_by)
                VALUES (?, ?, ?)
            """, (mod['discord_id'], mod['role'], 'system'))
