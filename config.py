# config.py
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base

# Load environment variables
load_dotenv()

# Get database URL and ensure it's absolute
database_path = os.path.abspath(os.environ.get('DATABASE_PATH'))
database_url = f"sqlite:///{database_path}"
print(f"Loading database URL: {database_url}")


# Create engine with correct permissions handling
engine = create_engine(
    database_url,
    connect_args={
        "check_same_thread": False,  # Required for SQLite
    }
)

# Create session factory with thread safety for Gunicorn
SessionLocal = scoped_session(sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
))

Base = declarative_base()
Base.query = SessionLocal.query_property()

class Config:
    # Your existing configuration...
    SQLALCHEMY_DATABASE_URI = database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DATABASE_PATH = os.path.abspath(
        os.getenv("DATABASE_PATH", "C:/var/www/summitmc.xyz/f2/f2.db")
    )
    ADMIN_IDS = set(
        id_str.strip() for id_str in os.environ.get("ADMIN_IDS", "").split(",") if id_str.strip()
    )
    MODERATOR_IDS = set(
        id_str.strip() for id_str in os.environ.get("MODERATOR_IDS", "").split(",") if id_str.strip()
    )

    SECRET_KEY = os.environ.get("SECRET_KEY", "some-random-key")
    
    # Developer mode
    DEVELOPER_MODE = os.getenv("DEVELOPER_MODE", "False").lower() == "true"
    
    # Discord OAuth2
    DISCORD_CLIENT_ID = os.getenv('DISCORD_CLIENT_ID')
    DISCORD_CLIENT_SECRET = os.getenv('DISCORD_CLIENT_SECRET')
    DISCORD_REDIRECT_URI = os.getenv('DISCORD_REDIRECT_URI')
    DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
    DISCORD_PUBLIC_KEY = os.getenv('DISCORD_PUBLIC_KEY')
    DISCORD_BOT_SCOPES = ["identify", "email", 'guilds']
    
    # Discord API endpoints
    DISCORD_API_BASE_URL = 'https://discord.com/api'
    DISCORD_AUTHORIZATION_BASE_URL = 'https://discord.com/api/oauth2/authorize'
    DISCORD_TOKEN_URL = 'https://discord.com/api/oauth2/token'
    
    # Upload settings
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "app", "static", "images")
    # GUEST_UPLOAD_FOLDER = "static/guest_uploads"
    THUMBNAIL_FOLDER = "app/static/thumbnails"
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
    MAX_CONTENT_LENGTH = 24 * 1024 * 1024  # 10MB limit
    
    # Gunicorn settings
    workers = int(os.environ.get('GUNICORN_PROCESSES', '2'))
    threads = int(os.environ.get('GUNICORN_THREADS', '4'))
    timeout = int(os.environ.get('GUNICORN_TIMEOUT', '120'))
    bind = os.environ.get('GUNICORN_BIND', '0.0.0.0:8080')
    forwarded_allow_ips = '*'
    secure_scheme_headers = { 'X-Forwarded-Proto': 'https' }

    @property
    def OAUTH2_SCOPES(self):
        return ['identify', 'guilds']

# Database session dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()