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

@main_bp.route("/shots/<image_filename>")  # instead of /app/static/images/<image_filename>
def view_image(image_filename):
    """
    Adjusted to also fetch like count and comments for this screenshot.
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

@main_bp.route("/profile")
@login_required
def profile():
    # Use session username for filtering uploads
    current_username = session.get("username")
    if not current_username:
        flash("You must be logged in to view your profile.", "danger")
        return redirect(url_for("main.index"))

    stats = {
        "likes_received": 0,
        "likes_given": 0,
        "comments_received": 0,
        "comments_posted": 0,
    }
    notifications = []
    unread_notifications_count = 0

    with sqlite3.connect(Config.DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row

        # 1) Likes RECEIVED on user's uploads
        # Use COALESCE to match the uploader name as stored in your index route.
        row = conn.execute("""
            SELECT COUNT(*) AS cnt
            FROM likes l
            JOIN screenshots s ON l.screenshot_id = s.id
            WHERE COALESCE(s.discord_username, s.guest_username) = ?
        """, (current_username,)).fetchone()
        stats["likes_received"] = row["cnt"] if row else 0

        # 2) Likes GIVEN by this user (stored in likes.user_id)
        row = conn.execute("""
            SELECT COUNT(*) AS cnt
            FROM likes
            WHERE user_id = ?
        """, (session.get("discord_id") or session.get("guest_id"),)).fetchone()
        stats["likes_given"] = row["cnt"] if row else 0

        # 3) Comments RECEIVED on this user's uploads
        row = conn.execute("""
            SELECT COUNT(*) AS cnt
            FROM comments c
            JOIN screenshots s ON c.screenshot_id = s.id
            WHERE COALESCE(s.discord_username, s.guest_username) = ?
        """, (current_username,)).fetchone()
        stats["comments_received"] = row["cnt"] if row else 0

        # 4) Comments POSTED by this user.
        # Assuming the comments table stores the poster’s username in the "username" column.
        row = conn.execute("""
            SELECT COUNT(*) AS cnt
            FROM comments
            WHERE username = ?
        """, (current_username,)).fetchone()
        stats["comments_posted"] = row["cnt"] if row else 0

        # 5) Fetch notifications (if using a notifications table)
        noti_rows = conn.execute("""
            SELECT id, message, created_at, is_read
            FROM notifications
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (session.get("discord_id") or session.get("guest_id"),)).fetchall()
        notifications = [dict(r) for r in noti_rows]
        unread_notifications_count = sum(1 for n in notifications if not n["is_read"])

    user_role = get_user_role(session.get("discord_id"), session.get("guest_id"))

    return render_template(
        "profile.html",
        stats=stats,
        notifications=notifications,
        unread_count=unread_notifications_count,
        user_role=user_role
    )


@main_bp.context_processor
def inject_notifications():
    user_id = session.get("discord_id") or session.get("guest_id")
    if not user_id:
        return {"unread_notifications": 0}
    try:
        with sqlite3.connect(Config.DATABASE_PATH) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM notifications WHERE user_id=? AND is_read=0",
                (user_id,)
            ).fetchone()
            count = row["cnt"] if row else 0
    except Exception as e:
        # In case the table does not exist or another error occurs
        count = 0
    return {"unread_notifications": count}

@main_bp.route("/manage_tags/<int:screenshot_id>", methods=["POST"])
@login_required
def manage_tags(screenshot_id):
    """
    Allows an admin or moderator to ADD or REMOVE tags from an existing screenshot.
    Expects form data: 'tags_to_add' (comma-separated or repeated form fields),
                       'tags_to_remove' (optional).
    """
    discord_id = session.get("discord_id")
    guest_id = session.get("guest_id")
    user_role = get_user_role(discord_id, guest_id)

    # Only admins or mods can do this (unless you want to allow the uploader also).
    if user_role not in ["admin", "moderator"]:
        flash("You do not have permission to modify tags.", "danger")
        return redirect(request.referrer or url_for("main.index"))

    tags_to_add = request.form.get("tags_to_add", "").strip()
    tags_to_remove = request.form.get("tags_to_remove", "").strip()

    # Split on commas or spaces – adjust as you prefer
    tags_to_add_list = [t.strip() for t in tags_to_add.split(",") if t.strip()]
    tags_to_remove_list = [t.strip() for t in tags_to_remove.split(",") if t.strip()]

    with sqlite3.connect(Config.DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row

        # 1) Check if screenshot exists
        row = conn.execute("SELECT id FROM screenshots WHERE id=?", (screenshot_id,)).fetchone()
        if not row:
            flash("Screenshot not found.", "danger")
            return redirect(url_for("main.index"))

        # 2) Insert any new tags into the `tags` table if they do not exist
        for tag_name in tags_to_add_list:
            if not tag_name:
                continue
            # Check if the tag already exists
            existing_tag = conn.execute("SELECT id FROM tags WHERE name=?", (tag_name,)).fetchone()
            if existing_tag:
                tag_id = existing_tag["id"]
            else:
                # Insert new tag
                cur = conn.execute("INSERT INTO tags (name) VALUES (?)", (tag_name,))
                tag_id = cur.lastrowid

            # Now ensure a row in `screenshot_tags`
            # Check if row already exists
            existing_link = conn.execute("""
                SELECT 1 FROM screenshot_tags
                WHERE screenshot_id=? AND tag_id=?
            """, (screenshot_id, tag_id)).fetchone()
            if not existing_link:
                conn.execute("""
                    INSERT INTO screenshot_tags (screenshot_id, tag_id)
                    VALUES (?, ?)
                """, (screenshot_id, tag_id))

        # 3) Remove tags if specified
        for tag_name in tags_to_remove_list:
            if not tag_name:
                continue
            # Find the tag's id
            existing_tag = conn.execute("SELECT id FROM tags WHERE name=?", (tag_name,)).fetchone()
            if existing_tag:
                tag_id = existing_tag["id"]
                # Remove link
                conn.execute("""
                    DELETE FROM screenshot_tags
                    WHERE screenshot_id=? AND tag_id=?
                """, (screenshot_id, tag_id))
                # Potentially also remove the tag entirely if you want
                # but only if it's not used by any other screenshot
                # conn.execute("""
                #     DELETE FROM tags WHERE id=? AND NOT EXISTS (
                #         SELECT 1 FROM screenshot_tags WHERE tag_id=?
                #     )
                # """, (tag_id, tag_id))

        conn.commit()

    flash("Tags updated successfully.", "success")
    return redirect(request.referrer or url_for("main.index"))


@main_bp.route("/remove_comment/<int:comment_id>", methods=["POST"])
@login_required
def remove_comment(comment_id):
    """
    Allows an admin or moderator to remove any comment,
    or the original commenter to remove their own comment (optional).
    """
    discord_id = session.get("discord_id")
    guest_id = session.get("guest_id")
    user_role = get_user_role(discord_id, guest_id)
    current_user = session.get("username")

    with sqlite3.connect(Config.DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row
        comment_row = conn.execute("""
            SELECT user_id, username, comment_text
            FROM comments
            WHERE id=?
        """, (comment_id,)).fetchone()

        if not comment_row:
            flash("Comment not found.", "danger")
            return redirect(url_for("main.index"))

        comment_user_id = comment_row["user_id"]
        comment_username = comment_row["username"]

        # Check permission:
        # - If admin or moderator => okay
        # - OR if you want to allow the original commenter to remove it:
        #   if user_id == comment_user_id
        #   (i.e. current_user_id or username matches)
        if user_role not in ["admin", "moderator"]:
            # If you want to allow the user themself to remove their own comment:
            # user_id = discord_id or guest_id
            # if str(user_id) != str(comment_user_id):
            #     flash("You don't have permission to remove this comment.", "danger")
            #     return redirect(request.referrer or url_for("main.index"))
            #
            # else:
            #    # allow
            #    pass
            flash("Only admins or moderators can remove comments.", "danger")
            return redirect(request.referrer or url_for("main.index"))

        # If we reach here, proceed to delete
        conn.execute("DELETE FROM comments WHERE id=?", (comment_id,))
        conn.commit()

    flash("Comment removed successfully.", "success")
    return redirect(request.referrer or url_for("main.index"))


@main_bp.route("/ban_user", methods=["POST"])
@login_required
def ban_user():
    """
    Allows admin or moderator to ban a user by user_id (discord or guest).
    Expects form data: 'user_id_to_ban'.
    """
    from datetime import datetime

    discord_id = session.get("discord_id")
    guest_id = session.get("guest_id")
    user_role = get_user_role(discord_id, guest_id)
    if user_role not in ["admin", "moderator"]:
        flash("You do not have permission to ban users.", "danger")
        return redirect(request.referrer or url_for("main.index"))

    user_id_to_ban = request.form.get("user_id_to_ban", "").strip()
    if not user_id_to_ban:
        flash("No user ID provided to ban.", "danger")
        return redirect(request.referrer or url_for("main.index"))

    # Optional: prevent banning yourself or other weird checks
    if str(user_id_to_ban) == str(discord_id) or str(user_id_to_ban) == str(guest_id):
        flash("You cannot ban yourself.", "danger")
        return redirect(request.referrer or url_for("main.index"))

    with sqlite3.connect(Config.DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row
        # Check if user is already banned
        existing_ban = conn.execute("""
            SELECT 1 FROM banned_users WHERE user_id=?
        """, (user_id_to_ban,)).fetchone()

        if existing_ban:
            flash("That user is already banned.", "warning")
        else:
            conn.execute("INSERT INTO banned_users (user_id) VALUES (?)", (user_id_to_ban,))
            conn.commit()
            flash("User has been banned.", "success")

    return redirect(request.referrer or url_for("main.index"))

def init_db():
    import sqlite3
    from config import Config

    # 2. Provide a default path if DATABASE_PATH is not in the environment
    default_db_path = "/var/www/summitmc.xyz/f2/f2.db"
    db_path = os.getenv("DATABASE_PATH", default_db_path)
    db_path = os.path.abspath(db_path)

    # 3. Ensure directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    print(f"Initializing database at: {db_path}")

    # 4. Create and connect to the SQLite database
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        
        # -- 4a. Create screenshots table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS screenshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                discord_username TEXT,
                guest_username TEXT,
                group_id INTEGER,
                uploader_type TEXT,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # -- 4b. Create screenshot_groups table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS screenshot_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # -- 4c. Create tags table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """)

        # -- 4d. Create screenshot_tags linking table (many-to-many)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS screenshot_tags (
                screenshot_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                PRIMARY KEY (screenshot_id, tag_id),
                FOREIGN KEY (screenshot_id) REFERENCES screenshots(id),
                FOREIGN KEY (tag_id) REFERENCES tags(id)
            )
        """)

        # -- 4e. Create user_roles table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_id TEXT NOT NULL,
                role TEXT NOT NULL,
                assigned_by TEXT,
                assigned_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # -- 4f. Create deletion_log table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS deletion_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                deleted_by TEXT,
                original_uploader TEXT,
                reason TEXT,
                deletion_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # -- 4g. Create reports table (optional, if you use it)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                reported_by TEXT,
                reason TEXT,
                reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS likes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                screenshot_id INTEGER NOT NULL,
                user_id TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(screenshot_id, user_id)
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                screenshot_id INTEGER NOT NULL,
                user_id TEXT,
                username TEXT,
                comment_text TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS banned_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                ban_reason TEXT,
                banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS screenshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                user_id TEXT NOT NULL,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS likes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                screenshot_id INTEGER,
                user_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                screenshot_id INTEGER,
                user_id TEXT,
                username TEXT,
                comment_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_read BOOLEAN DEFAULT 0
            );
        """)
        conn.commit()

        # 4h. Seed default tags
        default_tags = [
            # Game Versions & Modding
            'vanilla',
            'bedrock',
            'java',
            
            # Graphics & Visuals
            'no shaders',
            'Ray Tracing',
            'Distant Horizons',
            'realism',
            'styleized',
            'high res',
            'low res',
            
            # Gameplay Elements
            'survival',
            
            # Resource Packs
            'stylized pack',
            'Patrix',
            'Vanilla PBR Styled Pack',
            'Summit',
        ]
        for tag in default_tags:
            conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
        
        conn.commit()
        print("All tables created or verified successfully and default tags seeded.")

    # 5. (Optional) Set file permissions
    try:
        os.chmod(db_path, 0o666)  # rw-rw-rw-
        print(f"Successfully set file permissions for: {db_path}")
    except Exception as e:
        print(f"Error setting file permissions: {e}")

    # 6. (Optional) Set directory permissions
    try:
        db_directory = os.path.dirname(db_path)
        os.chmod(db_directory, 0o775)  # rwxrwxr-x
        print(f"Successfully set directory permissions for: {db_directory}")
    except Exception as e:
        print(f"Error setting directory permissions: {e}")


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")

# Register this function to run before the first request.
@main_bp.before_app_request
def initialize_database():
    init_db()