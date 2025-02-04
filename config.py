# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev')
    
    # Discord OAuth2
    DISCORD_CLIENT_ID = os.getenv('DISCORD_CLIENT_ID')
    DISCORD_CLIENT_SECRET = os.getenv('DISCORD_CLIENT_SECRET')
    DISCORD_REDIRECT_URI = os.getenv('DISCORD_REDIRECT_URI')
    DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
    DISCORD_PUBLIC_KEY = os.getenv('DISCORD_PUBLIC_KEY')
    
    # Discord API endpoints
    DISCORD_API_BASE_URL = 'https://discord.com/api'
    DISCORD_AUTHORIZATION_BASE_URL = 'https://discord.com/api/oauth2/authorize'
    DISCORD_TOKEN_URL = 'https://discord.com/api/oauth2/token'
    
    # Upload settings
    UPLOAD_FOLDER = "static/images"
    THUMBNAIL_FOLDER = "static/thumbnails"
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
    MAX_CONTENT_LENGTH = 24 * 1024 * 1024  # 10MB limit
    
    workers = int(os.environ.get('GUNICORN_PROCESSES', '2'))
    threads = int(os.environ.get('GUNICORN_THREADS', '4'))
    timeout = int(os.environ.get('GUNICORN_TIMEOUT', '120'))
    bind = os.environ.get('GUNICORN_BIND', '0.0.0.0:8080')
    forwarded_allow_ips = '*'
    secure_scheme_headers = { 'X-Forwarded-Proto': 'https' }

    @property
    def OAUTH2_SCOPES(self):
        return ['identify', 'guilds']