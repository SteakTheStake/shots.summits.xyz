# app.py
from PIL import Image
from flask import Flask, render_template, request, redirect, url_for, flash
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from pathlib import Path
import os
from datetime import datetime
import json
from typing import List, Dict
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


def create_app():
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    app.secret_key = "DAA212C5778B3F8A4C2A8E6CC4768"
    init_db()

    # Configuration
    app.config["UPLOAD_FOLDER"] = "static/images"
    app.config["THUMBNAIL_FOLDER"] = "static/thumbnails"
    app.config["ALLOWED_EXTENSIONS"] = {"png", "jpg", "jpeg", "webp"}
    app.config["CREDENTIALS"] = {"user": generate_password_hash("upload")}

    # Create necessary directories
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["THUMBNAIL_FOLDER"], exist_ok=True)

    def allowed_file(filename):
        return (
            "." in filename
            and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]
        )

    def requires_auth(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            auth = request.authorization
            if not auth or not check_auth(auth.username, auth.password):
                return authenticate()
            return f(*args, **kwargs)

        return decorated

    def check_auth(username, password):
        return username in app.config["CREDENTIALS"] and check_password_hash(
            app.config["CREDENTIALS"][username], password
        )

    def authenticate():
        return (
            "Could not verify your access level for that URL.\n"
            "You have to login with proper credentials",
            401,
            {"WWW-Authenticate": 'Basic realm="Login Required"'},
        )

    def create_thumbnail(image_path, size=(400, 400)):
        try:
            with Image.open(image_path) as img:
                img.thumbnail(size)
                thumbnail_name = os.path.basename(image_path)
                thumbnail_path = os.path.join(
                    app.config["THUMBNAIL_FOLDER"], thumbnail_name
                )
                img.save(thumbnail_path, "WEBP")
                return thumbnail_name
        except Exception as e:
            print(f"Error creating thumbnail: {e}")
            return None

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
                if file.content_length > 6 * 1024 * 1024:  # 6MB limit
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
    app.run(debug=True, port=5500)
