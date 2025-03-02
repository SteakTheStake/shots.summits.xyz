# upload_utils.py
import os
import sqlite3
from datetime import datetime
from PIL import Image
from flask import current_app as app, request, flash
from werkzeug.utils import secure_filename

def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]
    )

def handle_upload(files, discord_username):
    """
    Handle uploading multiple screenshot files.
    Returns a list of successfully uploaded filenames.
    """
    uploaded_files = []
    processed_files = set()

    with sqlite3.connect('screenshots.db') as conn:
        for index, file in enumerate(files):
            if not file or not file.filename:
                continue

            # Generate unique filename
            timestamp = datetime.now().timestamp()
            random_suffix = os.urandom(4).hex()
            filename = secure_filename(f'shot_{timestamp}_{random_suffix}.webp')

            if filename in processed_files:
                continue

            if allowed_file(file.filename):
                try:
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

                    # Get the metadata for this specific image
                    group_name = request.form.get('group_name', '')
                    common_tags = request.form.get('common_tags', '').split(',')
                    specific_tags = request.form.get(f'tags_{index}', '').split(',')

                    # Combine common and specific tags
                    all_tags = list({
                        tag.strip().lower()
                        for tag in (common_tags + specific_tags)
                        if tag.strip()
                    })

                    # Handle group creation if provided
                    group_id = None
                    if group_name:
                        cursor = conn.execute(
                            'INSERT INTO screenshot_groups (name, created_by) VALUES (?, ?) RETURNING id',
                            (group_name, discord_username)
                        )
                        group_id = cursor.fetchone()[0]

                    # Save and convert image
                    with Image.open(file) as img:
                        file.seek(0)
                        img.save(filepath, 'WEBP', quality=85)

                    # Insert screenshot record
                    cursor = conn.execute(
                        'INSERT INTO screenshots (filename, discord_username, group_id) VALUES (?, ?, ?) RETURNING id',
                        (filename, discord_username, group_id)
                    )
                    screenshot_id = cursor.fetchone()[0]

                    # Handle tags
                    for tag in all_tags:
                        conn.execute(
                            'INSERT OR IGNORE INTO tags (name) VALUES (?)',
                            (tag,)
                        )
                        cursor = conn.execute(
                            'SELECT id FROM tags WHERE name = ?',
                            (tag,)
                        )
                        tag_id = cursor.fetchone()[0]
                        conn.execute(
                            'INSERT INTO screenshot_tags (screenshot_id, tag_id) VALUES (?, ?)',
                            (screenshot_id, tag_id)
                        )

                    processed_files.add(filename)
                    uploaded_files.append(filename)

                except Exception as e:
                    print(f"Error processing file {file.filename}: {str(e)}")
                    continue

        conn.commit()
    return uploaded_files
