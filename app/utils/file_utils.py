# app/utils/file_utils.py

import os
import re
from datetime import datetime
import sqlite3
from flask import request, flash, redirect
from werkzeug.utils import secure_filename
from PIL import Image
import random
from config import Config
from functools import wraps

def allowed_file(filename):
    """
    Check if the file extension is allowed.
    """
    allowed_exts = Config.ALLOWED_EXTENSIONS  # Or however you store them
    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower() in allowed_exts
    )


def is_valid_resource_url(url):
    """
    Basic sanity check for URLs
    """
    return url.startswith("http://") or url.startswith("https://")


def _validate_tag_ids(conn, tag_ids):
    """
    Return only tag_ids that actually exist in the DB
    """
    if not tag_ids:
        return []
    placeholder = ",".join(["?"] * len(tag_ids))
    rows = conn.execute(
        f"SELECT id FROM tags WHERE id IN ({placeholder})",
        tuple(tag_ids),
    ).fetchall()
    return [r["id"] for r in rows]


def handle_upload(files, uploader_name, session):
    """
    Main logic to handle multiple file uploads, 
    create DB records, associate tags, etc.
    """
    uploaded_files = []
    processed_files = set()

    with sqlite3.connect(Config.DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row

        # 1) Validate & store "Resources Used" from request form
        resources_input = request.form.get("resources", "").strip()
        if resources_input:
            resources_list = [r.strip() for r in resources_input.split(",")]
            for resource in resources_list:
                if not is_valid_resource_url(resource):
                    flash(f"Invalid resource link: {resource}", "error")
                    return redirect(request.url)

        # 2) Parse the common_tags as IDs from a comma-separated string
        common_tags_str = request.form.get("common_tags", "")
        if common_tags_str:
            common_tag_ids = [t.strip() for t in common_tags_str.split(",") if t.strip()]
        else:
            common_tag_ids = []

        valid_common_tag_ids = _validate_tag_ids(conn, common_tag_ids)
        
        group_name = request.form.get("group_name", "").strip()
        group_id = None
        if group_name:
            cursor = conn.execute(
                """
                INSERT INTO screenshot_groups (name, created_by)
                VALUES (?, ?) RETURNING id
                """,
                (group_name, uploader_name)
            )
            group_id = cursor.fetchone()["id"]
        
        # Determine uploader's username and type
        if "discord_id" in session:
            uploader_type = "discord"
            username = session["username"]
        else:
            uploader_type = "guest"
            username = session.get("guest_username")

        # Sanitize username for directory
        sanitized_username = secure_filename(username)
        user_dir = os.path.join(Config.UPLOAD_FOLDER, sanitized_username)
        os.makedirs(user_dir, exist_ok=True)

        # Get current count of user's uploads
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM screenshots WHERE discord_username = ? OR guest_username = ?",
            (username, username)
        )
        current_count = cursor.fetchone()[0]

        # Process each file
        for index, file in enumerate(files):
            if not file or not file.filename:
                continue

            # Generate sequential number and filename
            seq_number = current_count + index + 1
            date_str = datetime.now().strftime("%m-%d-%Y")
            new_filename = f"{date_str}_{seq_number:04d}.webp".lstrip("/\\")
            filepath = os.path.join(user_dir, new_filename)

            if new_filename in processed_files:
                continue

            if allowed_file(file.filename):
                try:  # <- START OF TRY BLOCK
                    # Convert and save the image
                    with Image.open(file) as img:
                        img.save(filepath, "WEBP", quality=95)

                    # Database insertion
                    cursor.execute(
                        """
                        INSERT INTO screenshots
                            (filename, discord_username, guest_username, group_id, uploader_type)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            f"{sanitized_username}/{new_filename}",
                            username if uploader_type == "discord" else None,
                            username if uploader_type == "guest" else None,
                            group_id,
                            uploader_type
                        )
                    )
                    screenshot_id = cursor.lastrowid

                    # Gather file-specific tags
                    specific_tag_ids = request.form.getlist(f"tags_{index}")
                    valid_specific_tag_ids = _validate_tag_ids(conn, specific_tag_ids)

                    # Merge the common and file-specific tag IDs
                    all_tag_ids = set(valid_common_tag_ids + valid_specific_tag_ids)

                    # Insert screenshot_tags
                    for tag_id in all_tag_ids:
                        cursor.execute(
                            """
                            INSERT INTO screenshot_tags
                                (screenshot_id, tag_id)
                            VALUES (?, ?)
                            """,
                            (screenshot_id, tag_id)
                        )

                except Exception as e:  # <- EXCEPT MUST ALIGN WITH TRY
                    print(f"Saving to: {filepath}")
                    print(f"Saving file as: {sanitized_username}/{new_filename}")
                    print(f"Error processing {file.filename}: {e}")
                    flash(f"Failed to upload {file.filename}: {e}", "danger")
                    conn.rollback()
                    continue
                conn.commit()
    
    return uploaded_files
