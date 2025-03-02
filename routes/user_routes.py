# routes/user_routes.py
import sqlite3
from flask import render_template, request, flash, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from auth_utils import login_required
from . import user_bp

@user_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        discord_id = request.form.get('discord_id', '')

        if not username or not password:
            flash('Username and password are required', 'danger')
            return redirect(url_for('user_bp.register'))

        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('user_bp.register'))

        hashed_password = generate_password_hash(password)

        try:
            with sqlite3.connect("screenshots.db") as conn:
                # Check if username already exists
                cursor = conn.execute("SELECT * FROM users WHERE username = ?", (username,))
                if cursor.fetchone():
                    flash('Username already exists', 'danger')
                    return redirect(url_for('user_bp.register'))

                # Insert new user
                conn.execute(
                    "INSERT INTO users (username, password, discord_id) VALUES (?, ?, ?)",
                    (username, hashed_password, discord_id)
                )
                flash('Registration successful', 'success')
                return redirect(url_for('user_bp.login'))

        except sqlite3.IntegrityError:
            flash('Registration failed', 'danger')
            return redirect(url_for('user_bp.register'))

    return render_template('register.html')

@user_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        try:
            with sqlite3.connect("screenshots.db") as conn:
                cursor = conn.execute("SELECT * FROM users WHERE username = ?", (username,))
                user = cursor.fetchone()

                # Suppose user schema is: [id, username, password, discord_id]
                if user and check_password_hash(user[2], password):
                    session['username'] = username
                    session['login_type'] = 'username'
                    flash('Successfully logged in!', 'success')
                    return redirect(url_for('main_bp.index'))
                else:
                    flash('Invalid username or password', 'danger')
                    return redirect(url_for('user_bp.login'))
        except Exception as e:
            flash(f'Login error: {str(e)}', 'danger')
            return redirect(url_for('user_bp.login'))

    return render_template('login.html')

@user_bp.route('/logout')
def logout():
    session.clear()
    flash('Successfully logged out!', 'success')
    return redirect(url_for('main_bp.index'))
