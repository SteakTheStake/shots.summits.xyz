# app/routes/mod.py
import sqlite3
from flask import Blueprint, render_template, request, flash, redirect, url_for
from config import Config
from app.utils.security import login_required, requires_role

mod_bp = Blueprint('mod', __name__, template_folder='../templates')

@mod_bp.route("/mod/review")
@login_required
@requires_role("moderator")
def mod_review():
    with sqlite3.connect(Config.DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row
        recent_uploads = conn.execute(
            """
            SELECT s.*, COUNT(st.tag_id) as tag_count
            FROM screenshots s
            LEFT JOIN screenshot_tags st ON s.id = st.screenshot_id
            GROUP BY s.id
            ORDER BY s.upload_date DESC
            LIMIT 50
            """
        ).fetchall()

    return render_template("mod_review.html", uploads=recent_uploads)


@mod_bp.route("/mod/report/<filename>", methods=["POST"])
@login_required
def report_image(filename):
    reason = request.form.get("reason", "").strip()
    if not reason:
        flash("Please provide a reason for reporting.", "danger")
        return redirect(url_for("main.view_image", image_filename=filename))

    with sqlite3.connect(Config.DATABASE_PATH) as conn:
        conn.execute(
            """
            INSERT INTO reports (filename, reported_by, reason)
            VALUES (?, ?, ?)
            """,
            (filename, "TODO-username-here", reason),  
        )
    flash("Image reported successfully. Moderators will review it.", "success")
    return redirect(url_for("main.view_image", image_filename=filename))
