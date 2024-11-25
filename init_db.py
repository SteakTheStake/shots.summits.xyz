import sqlite3

def init_db():
    with sqlite3.connect("screenshots.db") as conn:
        conn.execute(
            """
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

        conn.commit()

# Run this function to initialize the database
if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")