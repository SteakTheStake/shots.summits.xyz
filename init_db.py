# init_db.py
import os
import sqlite3
from dotenv import load_dotenv

def init_db():
    """
    Creates (if missing) the core tables needed by the screenshot app,
    seeds default tags, and sets permissions on the database file and directory.
    """

    # 1. Load environment variables
    load_dotenv()

    # 2. Provide a default path if DATABASE_PATH is not in the environment
    default_db_path = "/var/www/summitmc.xyz/f2/f2.db"
    db_path = os.getenv("DATABASE_PATH", default_db_path)
    db_path = os.path.abspath(db_path)

    # 3. Ensure directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    print(f"Initializing database at: {db_path}")

    # 4. Create and connect to the SQLite database
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        
        # -- 4a. Create screenshots table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS screenshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                discord_username TEXT,
                guest_username TEXT,
                group_id INTEGER,
                uploader_type TEXT,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # -- 4b. Create screenshot_groups table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS screenshot_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # -- 4b. Create tag_request table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tag_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tag_name TEXT NOT NULL,
                requester_id TEXT NOT NULL,
                requester_type TEXT NOT NULL,
                requested_at DATETIME NOT NULL,
                status TEXT DEFAULT 'pending'
            );
        """)

        # -- 4c. Create tags table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """)

        # -- 4d. Create screenshot_tags linking table (many-to-many)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS screenshot_tags (
                screenshot_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                PRIMARY KEY (screenshot_id, tag_id),
                FOREIGN KEY (screenshot_id) REFERENCES screenshots(id),
                FOREIGN KEY (tag_id) REFERENCES tags(id)
            )
        """)

        # -- 4e. Create user_roles table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_id TEXT NOT NULL,
                role TEXT NOT NULL,
                assigned_by TEXT,
                assigned_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # -- 4f. Create deletion_log table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS deletion_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                deleted_by TEXT,
                original_uploader TEXT,
                reason TEXT,
                deletion_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # -- 4g. Create reports table (optional, if you use it)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                reported_by TEXT,
                reason TEXT,
                reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS likes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                screenshot_id INTEGER NOT NULL,
                user_id TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(screenshot_id, user_id)
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                screenshot_id INTEGER NOT NULL,
                user_id TEXT,
                username TEXT,
                comment_text TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS banned_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                ban_reason TEXT,
                banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 4h. Seed default tags
        default_tags = [
            # Game Versions & Modding
            'vanilla',
            'bedrock',
            'java',
            
            # Graphics & Visuals
            'no shaders',
            'Ray Tracing',
            'Distant Horizons',
            'realism',
            'styleized',
            'high res',
            'low res',
            
            # Gameplay Elements
            'survival',
            
            # Resource Packs
            'stylized pack',
            'Patrix',
            'Vanilla PBR Styled Pack',
            'Summit',
        ]
        for tag in default_tags:
            conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
        
        conn.commit()
        print("All tables created or verified successfully and default tags seeded.")

    # 5. (Optional) Set file permissions
    try:
        os.chmod(db_path, 0o666)  # rw-rw-rw-
        print(f"Successfully set file permissions for: {db_path}")
    except Exception as e:
        print(f"Error setting file permissions: {e}")

    # 6. (Optional) Set directory permissions
    try:
        db_directory = os.path.dirname(db_path)
        os.chmod(db_directory, 0o775)  # rwxrwxr-x
        print(f"Successfully set directory permissions for: {db_directory}")
    except Exception as e:
        print(f"Error setting directory permissions: {e}")


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")
