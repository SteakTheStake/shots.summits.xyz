# app/__init__.py
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Import your configuration
from config import Config

# If you're using SQLAlchemy globally, initialize it here.
# Or, if you prefer a session-per-request pattern, do that in db.py
db = SQLAlchemy()

def create_app():
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    app.config.from_object(Config)

    # Initialize DB schema if needed
    db.init_app(app)

    # If you need an init_db() routine (like for migrations or ensuring tables):
    from init_db import init_db
    with app.app_context():
        init_db()

    # Additional setup can go here (e.g., ensure_default_roles)
    from app.utils.security import ensure_default_roles
    ensure_default_roles()

    # Create necessary folders (upload, thumbnails, etc.)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["THUMBNAIL_FOLDER"], exist_ok=True)

    # Register Blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.routes.mod import mod_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(mod_bp)

    return app
