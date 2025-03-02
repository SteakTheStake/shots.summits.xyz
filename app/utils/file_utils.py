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

        # 3) Process each uploaded file
        for index, file in enumerate(files):
            if not file or not file.filename:
                continue

            # Construct a unique filename
            new_filename = secure_filename(
                f"shot_{datetime.now().timestamp()}_{os.urandom(4).hex()}.webp"
            )
            if new_filename in processed_files:
                continue

            if allowed_file(file.filename):
                try:
                    filepath = os.path.join(Config.UPLOAD_FOLDER, new_filename)
                    # Convert to webp
                    with Image.open(file) as img:
                        file.seek(0)
                        img.save(filepath, "WEBP", quality=85)

                    # Distinguish user type
                    if "discord_id" in session:
                        uploader_type = "discord"
                        discord_user = session["username"]  # e.g. "Foo#1234"
                        guest_user = None
                    else:
                        uploader_type = "guest"
                        discord_user = None
                        guest_user = session.get("guest_username")

                    # Possibly store group if provided
                    group_name = request.form.get("group_name", "")
                    group_id = None
                    if group_name:
                        cursor = conn.execute(
                            """
                            INSERT INTO screenshot_groups (name, created_by)
                            VALUES (?, ?) RETURNING id
                            """,
                            (group_name, uploader_name),
                        )
                        group_id = cursor.fetchone()[0]

                    # Insert screenshot record
                    cursor = conn.execute(
                        """
                        INSERT INTO screenshots
                            (filename, discord_username, guest_username, group_id, uploader_type)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (new_filename, discord_user, guest_user, group_id, uploader_type),
                    )
                    screenshot_id = cursor.lastrowid

                    # Gather file-specific tags
                    specific_tag_ids = request.form.getlist(f"tags_{index}")
                    valid_specific_tag_ids = _validate_tag_ids(conn, specific_tag_ids)

                    # Merge the common and file-specific tag IDs
                    all_tag_ids = set(valid_common_tag_ids + valid_specific_tag_ids)

                    # Insert screenshot_tags
                    for tag_id in all_tag_ids:
                        conn.execute(
                            """
                            INSERT INTO screenshot_tags (screenshot_id, tag_id)
                            VALUES (?, ?)
                            """,
                            (screenshot_id, tag_id),
                        )

                    uploaded_files.append(new_filename)
                    processed_files.add(new_filename)

                except Exception as e:
                    print(f"Error processing file {file.filename}: {str(e)}")
                    continue

        # Commit all changes
        conn.commit()

    return uploaded_files
