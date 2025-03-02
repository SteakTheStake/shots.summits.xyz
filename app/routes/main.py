import sqlite3
import os
from app.utils.security import login_required
from config import Config
from config import Config
from flask import (
    Blueprint, render_template, request,
    session, flash, redirect, url_for
)
from app.utils.security import login_required
from app.utils.file_utils import handle_upload, allowed_file

main_bp = Blueprint('main', __name__, template_folder='../templates')

@main_bp.route("/")
def index():
    with sqlite3.connect(Config.DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row

        # 1) Fetch the screenshots rows
        base_query = """
            SELECT s.id, s.filename, COALESCE(s.discord_username, s.guest_username) as uploader_name,
                   g.name as group_name, GROUP_CONCAT(t.name) AS tags
            FROM screenshots s
            LEFT JOIN screenshot_groups g ON s.group_id = g.id
            LEFT JOIN screenshot_tags st ON s.id = st.screenshot_id
            LEFT JOIN tags t ON st.tag_id = t.id
            GROUP BY s.id
            ORDER BY s.upload_date DESC
        """
        screenshots_rows = conn.execute(base_query).fetchall()

        screenshots_data = []
        current_user_id = session.get('discord_id') or session.get('guest_id')

        for row in screenshots_rows:
            row_dict = dict(row)
            # Convert 'tags' comma‐list to a Python list
            row_dict["tags"] = row["tags"].split(",") if row["tags"] else []

            screenshot_id = row["id"]

            # 2) Fetch comments for this screenshot
            comment_rows = conn.execute("""
                SELECT c.*, c.username, c.comment_text, c.created_at
                FROM comments c
                WHERE c.screenshot_id = ?
                ORDER BY c.created_at ASC
            """, (screenshot_id,)).fetchall()

            # Transform to a list of dicts
            comments_list = [dict(cr) for cr in comment_rows]
            row_dict["comments"] = comments_list

            # 3) Check if user liked
            if current_user_id:
                is_liked = conn.execute("""
                    SELECT 1 FROM likes WHERE screenshot_id=? AND user_id=?
                """, (screenshot_id, current_user_id)).fetchone()
                row_dict["user_liked"] = (is_liked is not None)
            else:
                row_dict["user_liked"] = False

            # 4) Like count
            like_count = conn.execute("""
                SELECT COUNT(*) FROM likes WHERE screenshot_id=?
            """, (screenshot_id,)).fetchone()[0]
            row_dict["like_count"] = like_count

            screenshots_data.append(row_dict)

        # Preapproved tags, users, etc. if needed
        tags = conn.execute("SELECT id, name FROM tags ORDER BY name").fetchall()
        users = sorted({r["uploader_name"] for r in screenshots_rows})
        
    # 5) Pass screenshots_data to the template
    return render_template(
        "index.html",
        screenshots=screenshots_data,
        preapproved_tags=tags,
        users=users
    )

def get_discord_avatar_url(discord_id, avatar):
    return f"https://cdn.discordapp.com/avatars/{discord_id}/{avatar}.png"

@main_bp.route("/shots/<image_filename>")
def view_image(image_filename):
    """
    Adjusted to also fetch the like count and comments for this screenshot.
    """
    import os
    image_path = os.path.join(Config.UPLOAD_FOLDER, image_filename)
    if not os.path.exists(image_path):
        return "Image not found", 404

    with sqlite3.connect(Config.DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row

        # 1) Basic screenshot data
        cursor = conn.execute("""
            SELECT s.*, g.name as group_name, GROUP_CONCAT(t.name) as tags
            FROM screenshots s
            LEFT JOIN screenshot_groups g ON s.group_id = g.id
            LEFT JOIN screenshot_tags st ON s.id = st.screenshot_id
            LEFT JOIN tags t ON st.tag_id = t.id
            WHERE s.filename = ?
            GROUP BY s.id
        """, (image_filename,))
        image_data = cursor.fetchone()
        if not image_data:
            return "Image data not found in DB", 404

        # 2) Like count
        screenshot_id = image_data["id"]
        like_count = conn.execute("""
            SELECT COUNT(*) FROM likes WHERE screenshot_id=?
        """, (screenshot_id,)).fetchone()[0]

        # 3) Fetch comments
        comments_rows = conn.execute("""
            SELECT c.* 
            FROM comments c
            WHERE c.screenshot_id = ?
            ORDER BY c.created_at ASC
        """, (screenshot_id,)).fetchall()
        row_dict["comments"] = [dict(cr) for cr in comments_rows]


    return render_template(
        "image_view.html",
        image_filename=image_filename,
        image_data=image_data,
        comments=comments,
        user_role=some_role_variable
    )

@main_bp.route("/delete/<filename>", methods=["POST"])
@login_required
def delete_image(filename):
    import sqlite3
    from app.utils.security import get_user_role
    from flask import session

    with sqlite3.connect(Config.DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT discord_username, guest_username FROM screenshots WHERE filename = ?",
            (filename,),
        )
        row = cursor.fetchone()
        if not row:
            flash("Image not found.", "danger")
            return redirect(url_for("main.index"))

        # Who was the uploader?
        uploader = row["discord_username"] or row["guest_username"]

        # Check roles
        discord_id = session.get("discord_id")
        guest_id = session.get("guest_id")
        user_role = get_user_role(discord_id, guest_id)

        # Compare with the user in session
        if uploader == session.get("username") or user_role in ["admin", "moderator"]:
            try:
                conn.execute(
                    """
                    INSERT INTO deletion_log (filename, deleted_by, original_uploader, reason)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        filename,
                        session.get("username"),
                        uploader,
                        request.form.get("reason", "User requested deletion"),
                    ),
                )
                conn.execute("DELETE FROM screenshots WHERE filename = ?", (filename,))

                filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
                if os.path.exists(filepath):
                    os.remove(filepath)

                conn.commit()
                flash("Image deleted successfully.", "success")
            except Exception as e:
                flash(f"Error deleting image: {str(e)}", "danger")
        else:
            flash("Permission denied.", "danger")

    return redirect(url_for("main.index"))


@main_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    # Reintroduce the code you had in your original script
    if request.method == "POST":
        # If no files
        if "screenshots[]" not in request.files:
            flash("No files uploaded", "danger")
            return redirect(request.url)

        files = request.files.getlist("screenshots[]")
        uploader_name = session.get("username")

        # Validate
        for file in files:
            if file and not allowed_file(file.filename):
                flash(f"Invalid file type: {file.filename}", "danger")
                return redirect(request.url)
            if file.content_length and file.content_length > 24 * 1024 * 1024:
                flash(f"File too large: {file.filename}", "danger")
                return redirect(request.url)

        try:
            # handle_upload is your custom function that does DB inserts, etc.
            uploaded_files = handle_upload(files, uploader_name, session)
            flash(f"Successfully uploaded {len(uploaded_files)} files", "success")
        except Exception as e:
            flash(f"Error uploading files: {str(e)}", "danger")
            return redirect(request.url)

        return redirect(url_for("main.index"))

    # If GET, maybe show a form or something:
    with sqlite3.connect(Config.DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row
        preapproved_tags = conn.execute(
            "SELECT id, name FROM tags ORDER BY name"
        ).fetchall()

    return render_template("upload_form.html", preapproved_tags=preapproved_tags)

@main_bp.route("/upload_form", methods=["GET"])
@login_required
def upload_form():
    # If you want a separate route to show the form
    with sqlite3.connect(Config.DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row
        preapproved_tags = conn.execute(
            "SELECT id, name FROM tags ORDER BY name"
        ).fetchall()

    return render_template("upload_form.html", preapproved_tags=preapproved_tags)

@main_bp.route("/toggle_like/<int:screenshot_id>", methods=["POST"])
@login_required
def toggle_like(screenshot_id):
    """
    Toggle like/unlike for a single screenshot. Return JSON with the new like_count and status.
    """
    import sqlite3
    from flask import jsonify, session

    user_id = session.get("discord_id") or session.get("guest_id")
    if not user_id:
        return jsonify({"error": "You must be logged in or have a guest session to like images."}), 403

    with sqlite3.connect(Config.DATABASE_PATH) as conn:
        # Check if the user already liked this screenshot
        already_liked = conn.execute(
            "SELECT 1 FROM likes WHERE screenshot_id=? AND user_id=?",
            (screenshot_id, user_id)
        ).fetchone()

        if already_liked:
            # Already liked => remove the row (unlike)
            conn.execute(
                "DELETE FROM likes WHERE screenshot_id=? AND user_id=?",
                (screenshot_id, user_id)
            )
            status = "unliked"
        else:
            # Not yet liked => insert a like row
            conn.execute(
                "INSERT INTO likes (screenshot_id, user_id) VALUES (?, ?)",
                (screenshot_id, user_id)
            )
            status = "liked"

        conn.commit()

        # Get the new like count
        like_count = conn.execute(
            "SELECT COUNT(*) FROM likes WHERE screenshot_id=?",
            (screenshot_id,)
        ).fetchone()[0]

    return jsonify({"status": status, "like_count": like_count})

@main_bp.route("/comment/<int:screenshot_id>", methods=["POST"])
@login_required
def add_comment(screenshot_id):
    """
    Inserts a new comment. If it's an AJAX request, return JSON with the new comment;
    otherwise, redirect back (for non-JS fallback).
    """
    from flask import request, jsonify, session
    import sqlite3
    from datetime import datetime

    user_id = session.get("discord_id") or session.get("guest_id")
    username = session.get("username")
    comment_text = request.form.get("comment_text", "").strip()

    if not comment_text:
        # In a real app, you'd handle this more gracefully
        # for AJAX, you can return an error JSON.
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"error": "Comment text cannot be empty."}), 400
        else:
            flash("Comment text cannot be empty.", "danger")
            return redirect(request.referrer or url_for("main.index"))

    # Insert the comment into DB
    with sqlite3.connect(Config.DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("""
            INSERT INTO comments (screenshot_id, user_id, username, comment_text)
            VALUES (?, ?, ?, ?)
        """, (screenshot_id, user_id, username, comment_text))
        conn.commit()

        # Retrieve the newly inserted comment (e.g. last_insert_rowid or by sorting)
        new_comment_row = conn.execute("""
            SELECT id, username, comment_text, created_at
            FROM comments
            WHERE rowid = last_insert_rowid()
        """).fetchone()

        # Count how many total comments this screenshot now has
        comment_count = conn.execute("""
            SELECT COUNT(*) FROM comments WHERE screenshot_id = ?
        """, (screenshot_id,)).fetchone()[0]

    # If an AJAX request:
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({
            "comment": {
                "id": new_comment_row["id"],
                "username": new_comment_row["username"],
                "comment_text": new_comment_row["comment_text"],
                "created_at": new_comment_row["created_at"]
            },
            "comment_count": comment_count
        })

    # Otherwise, fallback for non-JS case:
    flash("Comment posted successfully!", "success")
    return redirect(request.referrer or url_for("main.index"))
