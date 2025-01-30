import sqlite3
import os

def init_db():
    database_path = "f2.db"
    
    # Create the database and tables
    with sqlite3.connect(database_path) as conn:
        # Create your tables (same as before)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS screenshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            discord_username TEXT NOT NULL,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            group_id INTEGER,
            FOREIGN KEY (group_id) REFERENCES screenshot_groups(id)
        )
        """
        )
        conn.execute(
            """
        CREATE TABLE IF NOT EXISTS screenshot_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_by TEXT NOT NULL,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        )
        conn.execute(
            """
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
        """
        )
        conn.execute(
            """
        CREATE TABLE IF NOT EXISTS screenshot_tags (
            screenshot_id INTEGER,
            tag_id INTEGER,
            FOREIGN KEY (screenshot_id) REFERENCES screenshots(id),
            FOREIGN KEY (tag_id) REFERENCES tags(id),
            PRIMARY KEY (screenshot_id, tag_id)
        )
        """
        )
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
        
        # Make sure to commit the changes
        conn.commit()
    
    # Set file permissions after creating the database
    try:
        # 0o666 sets read/write permissions for all users (owner, group, others)
        # In octal: 666 means rw-rw-rw-
        os.chmod(database_path, 0o666)
        print(f"Successfully set permissions for {database_path}")
    except Exception as e:
        print(f"Error setting permissions: {e}")
    
    # Also ensure the directory has proper permissions
    try:
        db_directory = os.path.dirname(os.path.abspath(database_path))
        # 0o775 gives read/write/execute to owner and group, read/execute to others
        # In octal: 775 means rwxrwxr-x
        os.chmod(db_directory, 0o775)
        print(f"Successfully set permissions for directory: {db_directory}")
    except Exception as e:
        print(f"Error setting directory permissions: {e}")

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")
