# routes/admin_routes.py
import sqlite3
from flask import render_template, request, flash, redirect, url_for, session
from auth_utils import login_required, requires_role
from . import admin_bp

@admin_bp.route('/dashboard')
@login_required
@requires_role('admin')
def admin_dashboard():
    with sqlite3.connect("screenshots.db") as conn:
        conn.row_factory = sqlite3.Row
        stats = {
            'total_images': conn.execute("SELECT COUNT(*) FROM screenshots").fetchone()[0],
            'total_users': conn.execute("SELECT COUNT(DISTINCT discord_username) FROM screenshots").fetchone()[0],
            'recent_uploads': conn.execute("""
                SELECT * FROM screenshots ORDER BY upload_date DESC LIMIT 10
            """).fetchall(),
            'deletion_log': conn.execute("""
                SELECT * FROM deletion_log ORDER BY deletion_date DESC LIMIT 10
            """).fetchall()
        }

        users = conn.execute("""
            SELECT ur.discord_id, ur.role, ur.assigned_date,
                   COUNT(s.id) as upload_count
            FROM user_roles ur
            LEFT JOIN screenshots s ON ur.discord_id = s.discord_username
            GROUP BY ur.discord_id
        """).fetchall()

    return render_template('admin_dashboard.html', stats=stats, users=users)

@admin_bp.route('/manage_roles', methods=['POST'])
@login_required
@requires_role('admin')
def manage_roles():
    discord_id = request.form.get('discord_id')
    new_role = request.form.get('role')

    if new_role not in ['user', 'moderator', 'admin']:
        flash('Invalid role specified.', 'danger')
        return redirect(url_for('admin_bp.admin_dashboard'))

    with sqlite3.connect("screenshots.db") as conn:
        conn.execute("""
            INSERT OR REPLACE INTO user_roles (discord_id, role, assigned_by)
            VALUES (?, ?, ?)
        """, (discord_id, new_role, session['discord_username']))

    flash(f'Role updated successfully for user {discord_id}', 'success')
    return redirect(url_for('admin_bp.admin_dashboard'))
