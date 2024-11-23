# app.py
import os
from PIL import Image
from flask import Flask, Response, render_template, request, redirect, url_for, flash
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from pathlib import Path
from datetime import datetime
from typing import List, Dict
import sqlite3
import hmac
import hashlib
import json

DISCORD_WEBHOOK_URL = "YOUR_WEBHOOK_URL"
DISCORD_APP_ID = "1180699631693348914"
DISCORD_PUBLIC_KEY = "ca889b7eda1b9025ed5e4fb5a578211aae03be303444bf804ac2279cd2779267"


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


def send_discord_webhook(username: str, action: str, details: dict = None):
    """
    Send a webhook to Discord about login/upload events
    """
    timestamp = datetime.utcnow().isoformat()

    embed = {
        "title": f"Screenshot App {action}",
        "description": f"User: {username}",
        "color": 0x00FF00 if action == "Login" else 0x0000FF,
        "timestamp": timestamp,
        "fields": [],
    }

    if details:
        for key, value in details.items():
            embed["fields"].append({"name": key, "value": str(value), "inline": True})

    payload = {
        "embeds": [embed],
        "username": "Screenshot App Bot",
        "avatar_url": "https://your-app-icon-url.png",  # Optional: Add your app's icon
    }

    try:
        response = request.post(DISCORD_WEBHOOK_URL, json=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to send Discord webhook: {e}")


def verify_discord_signature(signature: str, timestamp: str, body: str) -> bool:
    """
    Verify that the request came from Discord
    """
    message = timestamp + body
    hex_key = bytes.fromhex(DISCORD_PUBLIC_KEY)
    signature_bytes = bytes.fromhex(signature)

    calculated_signature = hmac.new(
        hex_key, message.encode(), hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(calculated_signature, signature)


def create_app():
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    # ... existing setup code ...

    def requires_auth(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            auth = request.authorization
            if not auth or not check_auth(auth.username, auth.password):
                return authenticate()

            # Send Discord webhook for successful login
            send_discord_webhook(
                username=auth.username,
                action="Login",
                details={
                    "IP": request.remote_addr,
                    "User Agent": request.user_agent.string,
                },
            )
            return f(*args, **kwargs)

        return decorated

    @app.route("/discord-interaction", methods=["POST"])
    def discord_interaction():
        # Verify request is from Discord
        signature = request.headers.get("X-Signature-Ed25519")
        timestamp = request.headers.get("X-Signature-Timestamp")

        if not signature or not timestamp:
            return "Invalid request", 401

        body = request.get_data().decode("utf-8")

        if not verify_discord_signature(signature, timestamp, body):
            return "Invalid signature", 401

        data = request.json

        # Handle Discord interactions
        if data["type"] == 1:  # PING
            return jsonify({"type": 1})  # PONG

        # Handle other interaction types here
        return jsonify({"type": 4, "data": {"content": "Command received!"}})
    @app.route("/", methods=["GET"])
    def index():
        with sqlite3.connect("screenshots.db") as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT s.filename, s.discord_username, s.upload_date, 
                        g.name as group_name,
                        GROUP_CONCAT(t.name) as tags
                FROM screenshots s
                LEFT JOIN screenshot_groups g ON s.group_id = g.id
                LEFT JOIN screenshot_tags st ON s.id = st.screenshot_id
                LEFT JOIN tags t ON st.tag_id = t.id
                GROUP BY s.id
                ORDER BY s.upload_date DESC
                """
            )
            screenshots = cursor.fetchall()
        return render_template("index.html", screenshots=screenshots)

    @app.route("/shots/<image_filename>")
    def view_image(image_filename):
        image_path = os.path.join(app.config["UPLOAD_FOLDER"], image_filename)
        if os.path.exists(image_path):
            with sqlite3.connect("screenshots.db") as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT s.*, g.name as group_name, GROUP_CONCAT(t.name) as tags
                    FROM screenshots s
                    LEFT JOIN screenshot_groups g ON s.group_id = g.id
                    LEFT JOIN screenshot_tags st ON s.id = st.screenshot_id
                    LEFT JOIN tags t ON st.tag_id = t.id
                    WHERE s.filename = ?
                    GROUP BY s.id
                    """,
                    (image_filename,),
                )
                image_data = cursor.fetchone()
            return render_template(
                "image_view.html", image_filename=image_filename, image_data=image_data
            )
        return "Image not found", 404

    @app.template_filter("fileexists")
    def fileexists_filter(filename):
        try:
            static_path = os.path.join("static", "images", filename)
            return os.path.isfile(static_path)
        except Exception as e:
            return False

    @app.route('/upload', methods=['GET', 'POST'])
    @requires_auth
    def upload():
        if request.method == 'POST':
            if 'screenshots[]' not in request.files:
                flash('No files uploaded', 'danger')
                return redirect(request.url)
                
            files = request.files.getlist('screenshots[]')
            discord_username = request.form.get('discord_username', 'Anonymous')
            tags = request.form.get('tags', '').split(',')
            group_name = request.form.get('group_name', '')
            
            # Validate files
            for file in files:
                if file and not allowed_file(file.filename):
                    flash(f'Invalid file type: {file.filename}', 'danger')
                    return redirect(request.url)
                if file.content_length > 10 * 1024 * 1024:  # 10MB limit
                    flash(f'File too large: {file.filename}', 'danger')
                    return redirect(request.url)
                    
            try:
                uploaded_files = handle_upload(files, discord_username, tags, group_name)
                flash(f'Successfully uploaded {len(uploaded_files)} files', 'success')
                return redirect(url_for('index'))
            except Exception as e:
                flash(f'Error uploading files: {str(e)}', 'danger')
                return redirect(request.url)
                
        return render_template('upload.html')
    
    def handle_upload(files, discord_username, tags, group_name):
        uploaded_files = []
        with sqlite3.connect('screenshots.db') as conn:
            if group_name:
                cursor = conn.execute(
                    'INSERT INTO screenshot_groups (name, created_by) VALUES (?, ?) RETURNING id',
                    (group_name, discord_username)
                )
                group_id = cursor.fetchone()[0]
            else:
                group_id = None
                
            for file in files:
                if file and allowed_file(file.filename):
                    # Generate unique filename
                    filename = secure_filename(f'shot{int(datetime.now().timestamp())}.webp')
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    
                    # Convert and save as webp
                    img = Image.open(file)
                    img.save(filepath, 'WEBP')
                    
                    # Save to database
                    cursor = conn.execute(
                        'INSERT INTO screenshots (filename, discord_username, group_id) VALUES (?, ?, ?) RETURNING id',
                        (filename, discord_username, group_id)
                    )
                    screenshot_id = cursor.fetchone()[0]
                    
                    # Handle tags
                    for tag in tags:
                        tag = tag.strip().lower()
                        if tag:
                            conn.execute('INSERT OR IGNORE INTO tags (name) VALUES (?)', (tag,))
                            cursor = conn.execute('SELECT id FROM tags WHERE name = ?', (tag,))
                            tag_id = cursor.fetchone()[0]
                            conn.execute(
                                'INSERT INTO screenshot_tags (screenshot_id, tag_id) VALUES (?, ?)',
                                (screenshot_id, tag_id)
                            )
                            
                    uploaded_files.append(filename)
                    
            conn.commit()
        return uploaded_files

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(port=5500)