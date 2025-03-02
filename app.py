# app.py
import os
from flask import Flask
from config import Config
from db_utils import init_db, init_user_table, ensure_default_roles
from routes import main_bp, admin_bp, mod_bp, user_bp

def create_app():
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    app.config.from_object(Config)

    # Initialize DB
    init_user_table()
    init_db()
    ensure_default_roles()

    # Create necessary directories
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["THUMBNAIL_FOLDER"], exist_ok=True)

    # Register Blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(mod_bp)
    app.register_blueprint(user_bp)

    return app

if __name__ == "__main__":
    app = create_app()
    # Debug mode for development; remove in production
    app.run(debug=True)
