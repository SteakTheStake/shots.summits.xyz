# routes/main_routes.py
import os
import sqlite3
from flask import render_template, request, flash, redirect, url_for, session
from . import main_bp
from auth_utils import login_required
from upload_utils import handle_upload, allowed_file

@main_bp.route('/')
def index():
    with sqlite3.connect("screenshots.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("""
            SELECT s.*, g.name as group_name, GROUP_CONCAT(t.name) as tags
            FROM screenshots s
            LEFT JOIN screenshot_groups g ON s.group_id = g.id
            LEFT JOIN screenshot_tags st ON s.id = st.screenshot_id
            LEFT JOIN tags t ON st.tag_id = t.id
            GROUP BY s.id
            ORDER BY s.upload_date DESC
        """)
        screenshots = cursor.fetchall()
    return render_template('index.html', screenshots=screenshots)

@main_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        if 'screenshots[]' not in request.files:
            flash('No files uploaded', 'danger')
            return redirect(request.url)

        files = request.files.getlist('screenshots[]')
        discord_username = session.get('discord_username') or session.get('username')

        # Basic validation
        for file in files:
            if file and not allowed_file(file.filename):
                flash(f'Invalid file type: {file.filename}', 'danger')
                return redirect(request.url)
            if file.content_length and file.content_length > 24 * 1024 * 1024:
                flash(f'File too large: {file.filename}', 'danger')
                return redirect(request.url)

        try:
            uploaded_files = handle_upload(files, discord_username)
            flash(f'Successfully uploaded {len(uploaded_files)} files', 'success')
            return redirect(url_for('main_bp.index'))
        except Exception as e:
            flash(f'Error uploading files: {str(e)}', 'danger')
            return redirect(request.url)

    return render_template('upload.html')

@main_bp.route("/shots/<image_filename>")
def view_image(image_filename):
    image_path = os.path.join('uploads', image_filename)
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
        return render_template("image_view.html", image_filename=image_filename, image_data=image_data)
    return "Image not found", 404
