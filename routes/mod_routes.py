# routes/mod_routes.py
import sqlite3
from flask import render_template, request, flash, redirect, url_for, session
from auth_utils import login_required, requires_role
from . import mod_bp

@mod_bp.route('/review')
@login_required
@requires_role('moderator')
def mod_review():
    with sqlite3.connect("screenshots.db") as conn:
        conn.row_factory = sqlite3.Row
        recent_uploads = conn.execute("""
            SELECT s.*, COUNT(st.tag_id) as tag_count
            FROM screenshots s
            LEFT JOIN screenshot_tags st ON s.id = st.screenshot_id
            GROUP BY s.id
            ORDER BY s.upload_date DESC
            LIMIT 50
        """).fetchall()
    return render_template('mod_review.html', uploads=recent_uploads)

@mod_bp.route('/report/<filename>', methods=['POST'])
@login_required
def report_image(filename):
    reason = request.form.get('reason', '').strip()
    if not reason:
        flash('Please provide a reason for reporting.', 'danger')
        return redirect(url_for('main_bp.view_image', image_filename=filename))

    with sqlite3.connect("screenshots.db") as conn:
        conn.execute("""
            INSERT INTO reports (filename, reported_by, reason)
            VALUES (?, ?, ?)
        """, (filename, session['discord_username'], reason))

    flash('Image reported successfully. Moderators will review it.', 'success')
    return redirect(url_for('main_bp.view_image', image_filename=filename))
