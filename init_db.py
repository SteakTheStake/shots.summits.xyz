# init_db.py
import os
from sqlalchemy import create_engine
from models import Base

def init_db():
    # Use a default database path if DATABASE_PATH is not set
    default_path = "/var/www/summitmc.xyz/f2/f2.db"
    database_path = os.environ.get('DATABASE_PATH', default_path)
    database_path = os.path.abspath(database_path)
    # Create database URL
    database_url = f"sqlite:///{database_path}"
    
    # Create engine and tables
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    
    # Set file permissions
    try:
        os.chmod(database_path, 0o666)  # rw-rw-rw-
        print(f"Successfully set permissions for {database_path}")
    except Exception as e:
        print(f"Error setting permissions: {e}")
    
    # Set directory permissions
    try:
        db_directory = os.path.dirname(database_path)
        os.chmod(db_directory, 0o775)  # rwxrwxr-x
        print(f"Successfully set permissions for directory: {db_directory}")
    except Exception as e:
        print(f"Error setting directory permissions: {e}")

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")