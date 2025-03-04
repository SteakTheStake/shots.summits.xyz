import sqlite3
import os
from app.utils.security import login_required
from config import Config
from config import Config
from flask import (
    Blueprint, render_template, request,
    session, flash, redirect, url_for
)
from app.utils.security import login_required, get_user_role
from app.utils.file_utils import handle_upload, allowed_file

main_bp = Blueprint('main', __name__, template_folder='../templates')

@main_bp.route("/")
def index():
    with sqlite3.connect(Config.DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row

        # 1) Fetch the screenshots rows
        base_query = """
            SELECT s.id, s.filename, COALESCE(s.discord_username, s.guest_username) as uploader_name,
                   g.name as group_name, GROUP_CONCAT(t.name) AS tags,
                   s.upload_date
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
            # Convert 'tags' from CSV to list
            row_dict["tags"] = row["tags"].split(",") if row["tags"] else []

            screenshot_id = row["id"]

            # 2) Fetch comments for each screenshot
            comment_rows = conn.execute("""
                SELECT c.*, c.username, c.comment_text, c.created_at
                FROM comments c
                WHERE c.screenshot_id = ?
                ORDER BY c.created_at ASC
            """, (screenshot_id,)).fetchall()
            row_dict["comments"] = [dict(cr) for cr in comment_rows]

            # 3) Check if current user liked
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

        # Preapproved tags, users, etc.
        tags = conn.execute("SELECT id, name FROM tags ORDER BY name").fetchall()
        users = sorted({r["uploader_name"] for r in screenshots_rows})

    # 5) Pass screenshots_data to the template
    return render_template(
        "index.html",
        screenshots=screenshots_data,
        preapproved_tags=tags,
        users=users,
        user_role=get_user_role(session.get('discord_id'), session.get('guest_id'))
    )

def get_discord_avatar_url(discord_id, avatar):
    return f"https://cdn.discordapp.com/avatars/{discord_id}/{avatar}.png"

@main_bp.route("/shots/<image_filename>")
def view_image(image_filename):
    """
    Adjusted to also fetch the like count and comments for this screenshot.
    """
    image_path = os.path.join(Config.UPLOAD_FOLDER, image_filename)
    if not os.path.exists(image_path):
        return "Image not found", 404

    with sqlite3.connect(Config.DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row

        # 1) Basic screenshot data
        image_data = conn.execute("""
            SELECT s.*, g.name as group_name, GROUP_CONCAT(t.name) as tags
            FROM screenshots s
            LEFT JOIN screenshot_groups g ON s.group_id = g.id
            LEFT JOIN screenshot_tags st ON s.id = st.screenshot_id
            LEFT JOIN tags t ON st.tag_id = t.id
            WHERE s.filename = ?
            GROUP BY s.id
        """, (image_filename,)).fetchone()

        if not image_data:
            return "Image data not found in DB", 404

        screenshot_id = image_data["id"]

        # 2) Like count
        like_count = conn.execute("""
            SELECT COUNT(*) FROM likes WHERE screenshot_id=?
        """, (screenshot_id,)).fetchone()[0]

        # 3) Fetch comments
        comment_rows = conn.execute("""
            SELECT c.* 
            FROM comments c
            WHERE c.screenshot_id = ?
            ORDER BY c.created_at ASC
        """, (screenshot_id,)).fetchall()
        comments_list = [dict(cr) for cr in comment_rows]

    return render_template(
        "image_view.html",
        image_filename=image_filename,
        image_data=image_data,
        like_count=like_count,
        comments=comments_list,
        user_role=get_user_role(session.get('discord_id'), session.get('guest_id'))
    )


@main_bp.route("/delete/<filename>", methods=["POST"])
@login_required
def delete_image(filename):
    """
    Deletes an image if the current user is the uploader or is an admin/mod.
    """
    from flask import session

    discord_id = session.get("discord_id")
    guest_id = session.get("guest_id")
    role = get_user_role(discord_id, guest_id)

    with sqlite3.connect(Config.DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT discord_username, guest_username FROM screenshots WHERE filename = ?",
            (filename,),
        ).fetchone()

        if not row:
            flash("Image not found.", "danger")
            return redirect(url_for("main.index"))

        # Who was the uploader?
        uploader = row["discord_username"] or row["guest_username"]

        # Compare with the user in session
        if uploader == session.get("username") or role in ["admin", "moderator"]:
            try:
                # Log the deletion
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
    """
    Handles uploading new screenshots (with your existing handle_upload logic).
    """
    if request.method == "POST":
        if "screenshots[]" not in request.files:
            flash("No files uploaded", "danger")
            return redirect(request.url)

        files = request.files.getlist("screenshots[]")
        uploader_name = session.get("username")

        for file in files:
            if file and not allowed_file(file.filename):
                flash(f"Invalid file type: {file.filename}", "danger")
                return redirect(request.url)
            if file.content_length and file.content_length > 24 * 1024 * 1024:
                flash(f"File too large: {file.filename}", "danger")
                return redirect(request.url)

        try:
            uploaded_files = handle_upload(files, uploader_name, session)
            flash(f"Successfully uploaded {len(uploaded_files)} files", "success")
        except Exception as e:
            flash(f"Error uploading files: {str(e)}", "danger")
            return redirect(request.url)

        return redirect(url_for("main.index"))

    # If GET, show a form or something:
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
            new_status = "unliked"
        else:
            # Not yet liked => insert a like row
            conn.execute(
                "INSERT INTO likes (screenshot_id, user_id) VALUES (?, ?)",
                (screenshot_id, user_id)
            )
            new_status = "liked"

        conn.commit()

        # Get the new like count
        like_count = conn.execute(
            "SELECT COUNT(*) FROM likes WHERE screenshot_id=?",
            (screenshot_id,)
        ).fetchone()[0]

    return jsonify({"status": new_status, "like_count": like_count})


@main_bp.route("/comment/<int:screenshot_id>", methods=["POST"])
@login_required
def add_comment(screenshot_id):
    """
    Inserts a new comment. If it's an AJAX request, return JSON with the new comment;
    otherwise, redirect back (for non-JS fallback).
    """
    from flask import request, jsonify, session
    import sqlite3

    user_id = session.get("discord_id") or session.get("guest_id")
    username = session.get("username")
    comment_text = request.form.get("comment_text", "").strip()

    if not comment_text:
        # In a real app, you'd handle this more gracefully
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

        # Retrieve the newly inserted comment
        new_comment_row = conn.execute("""
            SELECT id, username, comment_text, created_at
            FROM comments
            WHERE rowid = last_insert_rowid()
        """).fetchone()

        # Count how many total comments this screenshot now has
        comment_count = conn.execute("""
            SELECT COUNT(*) FROM comments WHERE screenshot_id = ?
        """, (screenshot_id,)).fetchone()[0]

    # If AJAX:
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


@main_bp.route("/report/<filename>", methods=["POST"])
@login_required
def report_image(filename):
    """
    Stores the user's report reason in a 'reports' table (or handle however you'd like).
    """
    from flask import request, session

    reason = request.form.get("reason", "").strip()
    if not reason:
        flash("Report reason is required.", "danger")
        return redirect(request.referrer or url_for("main.index"))

    user_id = session.get("discord_id") or session.get("guest_id")
    username = session.get("username") or "unknown"

    with sqlite3.connect(Config.DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row

        # Check if image exists
        row = conn.execute(
            "SELECT id FROM screenshots WHERE filename = ?",
            (filename,)
        ).fetchone()

        if not row:
            flash("Image not found for reporting.", "danger")
            return redirect(url_for("main.index"))

        screenshot_id = row["id"]

        # Insert into your 'reports' table. Example schema:
        # CREATE TABLE reports (
        #   id INTEGER PRIMARY KEY AUTOINCREMENT,
        #   screenshot_id INTEGER,
        #   user_id TEXT,
        #   username TEXT,
        #   reason TEXT,
        #   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        # );
        conn.execute("""
            INSERT INTO reports (screenshot_id, user_id, username, reason)
            VALUES (?, ?, ?, ?)
        """, (screenshot_id, user_id, username, reason))
        conn.commit()

    flash("Your report was submitted successfully.", "success")
    return redirect(request.referrer or url_for("main.index"))