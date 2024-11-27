import os
from PIL import Image
from flask import (
    Flask,
    Response,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
)
from functools import wraps
from requests_oauthlib import OAuth2Session
from werkzeug.utils import secure_filename
from datetime import datetime
import sqlite3
import hmac
import hashlib
from oauth import (
    make_session,
)
from config import Config

def init_db():
    with sqlite3.connect("screenshots.db") as conn:
        conn.execute(
            """
        CREATE TABLE IF NOT EXISTS screenshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            discord_username TEXT NOT NULL,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            group_id INTEGER,
            FOREIGN KEY (group_id) REFERENCES screenshot_groups(id)
        )
        """
        )
        conn.execute(
            """
        CREATE TABLE IF NOT EXISTS screenshot_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_by TEXT NOT NULL,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        )
        conn.execute(
            """
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
        """
        )
        conn.execute(
            """
        CREATE TABLE IF NOT EXISTS screenshot_tags (
            screenshot_id INTEGER,
            tag_id INTEGER,
            FOREIGN KEY (screenshot_id) REFERENCES screenshots(id),
            FOREIGN KEY (tag_id) REFERENCES tags(id),
            PRIMARY KEY (screenshot_id, tag_id)
        )
        """
        )
        conn.execute("""
        CREATE TABLE IF NOT EXISTS user_roles (
            discord_id TEXT PRIMARY KEY,
            role TEXT NOT NULL DEFAULT 'user',
            assigned_by TEXT,
            assigned_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS deletion_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            deleted_by TEXT NOT NULL,
            original_uploader TEXT NOT NULL,
            deletion_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reason TEXT
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            reported_by TEXT NOT NULL,
            reason TEXT NOT NULL,
            report_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending'
        )
        """)

def send_discord_webhook(username: str, action: str, details: dict = None):
    """
    Send a webhook to Discord about login/upload events
    """
    timestamp = datetime.utcnow().isoformat()

    embed = {
        "title": f"Screenshot App {action}",
        "description": f"User: {username}",
        "color": 0x00FF00 if action == "Login" else 0x0000FF,
        "timestamp": timestamp,
        "fields": [],
    }

    if details:
        for key, value in details.items():
            embed["fields"].append({"name": key, "value": str(value), "inline": True})

    payload = {
        "embeds": [embed],
        "username": "Screenshot App Bot",
        "avatar_url": "https://your-app-icon-url.png",
    }

    try:
        response = request.post(Config.DISCORD_WEBHOOK_URL, json=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to send Discord webhook: {e}")


def verify_discord_signature(signature: str, timestamp: str, body: str) -> bool:
    """
    Verify that the request came from Discord
    """
    message = timestamp + body
    hex_key = bytes.fromhex(Config.DISCORD_PUBLIC_KEY)
    signature_bytes = bytes.fromhex(signature)

    calculated_signature = hmac.new(
        hex_key, message.encode(), hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(calculated_signature, signature)

def ensure_default_roles():
    """
    Ensures default admin and moderator roles are set in the database.
    Should be called during application initialization.
    """
    default_admin = {
        'discord_id': '278344153761316864',
        'username': 'StakeTheSteak',
        'role': 'admin'
    }
    
    default_moderators = [
        # Add default moderators here as needed
        # {'discord_id': 'mod_id', 'username': 'mod_name', 'role': 'moderator'},
    ]
    
    with sqlite3.connect("screenshots.db") as conn:
        # Ensure admin exists
        conn.execute("""
            INSERT OR IGNORE INTO user_roles (discord_id, role, assigned_by)
            VALUES (?, ?, ?)
        """, (default_admin['discord_id'], default_admin['role'], 'system'))
        
        # Ensure moderators exist
        for mod in default_moderators:
            conn.execute("""
                INSERT OR IGNORE INTO user_roles (discord_id, role, assigned_by)
                VALUES (?, ?, ?)
            """, (mod['discord_id'], mod['role'], 'system'))
            
def create_app():
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    app.config.from_object(Config)
    init_db()
    ensure_default_roles()
    
    # Create necessary directories
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["THUMBNAIL_FOLDER"], exist_ok=True)

    def allowed_file(filename):
        return (
            "." in filename
            and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]
        )

    def login_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'discord_id' not in session:
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
        
    def get_user_role(discord_id):
        with sqlite3.connect("screenshots.db") as conn:
            cursor = conn.execute(
                "SELECT role FROM user_roles WHERE discord_id = ?",
                (discord_id,)
            )
            result = cursor.fetchone()
            return result[0] if result else 'user'
        
    def requires_role(required_role):
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if 'discord_id' not in session:
                    flash('Please log in first.', 'danger')
                    return redirect(url_for('login'))

                user_role = get_user_role(session['discord_id'])
                role_hierarchy = {
                    'admin': 3,
                    'moderator': 2,
                    'user': 1
                }

                if role_hierarchy.get(user_role, 0) >= role_hierarchy.get(required_role, 0):
                    return f(*args, **kwargs)
                else:
                    flash('Insufficient permissions.', 'danger')
                    return redirect(url_for('index'))
            return decorated_function
        return decorator
    
    def handle_upload(files, discord_username):
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
                        resources = request.form.get('resources', '')

                        # Combine common and specific tags
                        all_tags = list(set([tag.strip().lower() for tag in common_tags + specific_tags if tag.strip()]))

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
                            conn.execute('INSERT OR IGNORE INTO tags (name) VALUES (?)', (tag,))
                            cursor = conn.execute('SELECT id FROM tags WHERE name = ?', (tag,))
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
        
    @app.route('/debug-config')
    def debug_config():
        from config import Config  # Import Config class
        
        config_vars = {
            'CLIENT_ID': Config.DISCORD_CLIENT_ID,
            'REDIRECT_URI': Config.DISCORD_REDIRECT_URI,
            'WEBHOOK_URL': Config.DISCORD_WEBHOOK_URL,
            'HAS_CLIENT_SECRET': bool(Config.DISCORD_CLIENT_SECRET),
            'HAS_PUBLIC_KEY': bool(Config.DISCORD_PUBLIC_KEY),
            'HAS_BOT_TOKEN': bool(Config.DISCORD_BOT_TOKEN)
        }
        return jsonify(config_vars)
    
    @app.route('/login')
    def login():
        discord = make_session()
        authorization_url, state = discord.authorization_url(app.config['DISCORD_AUTHORIZATION_BASE_URL'])
        session['oauth2_state'] = state
        return redirect(authorization_url)

    @app.route('/logout')
    def logout():
        session.clear()
        flash('Successfully logged out!', 'success')
        return redirect(url_for('index'))
    
    @app.route('/delete/<filename>', methods=['POST'])
    @login_required
    def delete_image(filename):
        with sqlite3.connect("screenshots.db") as conn:
            # Check if user owns the image or is admin/moderator
            cursor = conn.execute(
                "SELECT discord_username FROM screenshots WHERE filename = ?",
                (filename,)
            )
            result = cursor.fetchone()
    
            if not result:
                flash('Image not found.', 'danger')
                return redirect(url_for('index'))
    
            uploader = result[0]
            user_role = get_user_role(session['discord_id'])
    
            if uploader == session['discord_username'] or user_role in ['admin', 'moderator']:
                try:
                    # Log deletion
                    conn.execute(
                        """INSERT INTO deletion_log 
                        (filename, deleted_by, original_uploader, reason) 
                        VALUES (?, ?, ?, ?)""",
                        (filename, session['discord_username'], uploader, 
                        request.form.get('reason', 'User requested deletion'))
                    )
    
                    # Delete from database
                    conn.execute("DELETE FROM screenshots WHERE filename = ?", (filename,))
    
                    # Delete file
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    if os.path.exists(filepath):
                        os.remove(filepath)
    
                    flash('Image deleted successfully.', 'success')
                except Exception as e:
                    flash(f'Error deleting image: {str(e)}', 'danger')
            else:
                flash('Permission denied.', 'danger')
    
        return redirect(url_for('index'))
    
    @app.route('/admin/dashboard')
    @login_required
    @requires_role('admin')
    def admin_dashboard():
        with sqlite3.connect("screenshots.db") as conn:
            conn.row_factory = sqlite3.Row
    
            # Get statistics
            stats = {
                'total_images': conn.execute("SELECT COUNT(*) FROM screenshots").fetchone()[0],
                'total_users': conn.execute(
                    "SELECT COUNT(DISTINCT discord_username) FROM screenshots"
                ).fetchone()[0],
                'recent_uploads': conn.execute(
                    "SELECT * FROM screenshots ORDER BY upload_date DESC LIMIT 10"
                ).fetchall(),
                'deletion_log': conn.execute(
                    "SELECT * FROM deletion_log ORDER BY deletion_date DESC LIMIT 10"
                ).fetchall()
            }
    
            # Get user roles
            users = conn.execute("""
                SELECT ur.discord_id, ur.role, ur.assigned_date,
                        COUNT(s.id) as upload_count
                FROM user_roles ur
                LEFT JOIN screenshots s ON ur.discord_id = s.discord_username
                GROUP BY ur.discord_id
            """).fetchall()
    
        return render_template('admin_dashboard.html', stats=stats, users=users)
    
    @app.route('/admin/manage_roles', methods=['POST'])
    @login_required
    @requires_role('admin')
    def manage_roles():
        discord_id = request.form.get('discord_id')
        new_role = request.form.get('role')
    
        if new_role not in ['user', 'moderator', 'admin']:
            flash('Invalid role specified.', 'danger')
            return redirect(url_for('admin_dashboard'))
    
        with sqlite3.connect("screenshots.db") as conn:
            conn.execute("""
                INSERT OR REPLACE INTO user_roles (discord_id, role, assigned_by)
                VALUES (?, ?, ?)
            """, (discord_id, new_role, session['discord_username']))
    
        flash(f'Role updated successfully for user {discord_id}', 'success')
        return redirect(url_for('admin_dashboard'))
    
    @app.route('/mod/review')
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
    
    @app.route('/mod/report/<filename>', methods=['POST'])
    @login_required
    def report_image(filename):
        reason = request.form.get('reason', '').strip()
        if not reason:
            flash('Please provide a reason for reporting.', 'danger')
            return redirect(url_for('view_image', image_filename=filename))
    
        with sqlite3.connect("screenshots.db") as conn:
            conn.execute("""
                INSERT INTO reports (filename, reported_by, reason)
                VALUES (?, ?, ?)
            """, (filename, session['discord_username'], reason))
    
        flash('Image reported successfully. Moderators will review it.', 'success')
        return redirect(url_for('view_image', image_filename=filename))
    
    
    @app.route('/')
    def index():
        with sqlite3.connect("screenshots.db") as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT s.*, g.name as group_name, GROUP_CONCAT(t.name) as tags
                FROM screenshots s
                LEFT JOIN screenshot_groups g ON s.group_id = g.id
                LEFT JOIN screenshot_tags st ON s.id = st.screenshot_id
                LEFT JOIN tags t ON st.tag_id = t.id
                GROUP BY s.id
                ORDER BY s.upload_date DESC
            """)
            screenshots = cursor.fetchall()
        return render_template('index.html', screenshots=screenshots)
    
    # Add this to your app.py temporarily to debug
    @app.route('/config-check')
    def config_check():
        return {
            'client_id': app.config['DISCORD_CLIENT_ID'],
            'redirect_uri': app.config['DISCORD_REDIRECT_URI'],
            'api_base': app.config['DISCORD_API_BASE_URL'],
            'auth_base': app.config['DISCORD_AUTHORIZATION_BASE_URL'],
            'token_url': app.config['DISCORD_TOKEN_URL']
        }
    
    @app.route('/callback')
    def callback():
        if request.values.get('error'):
            flash(request.values['error'], 'danger')
            return redirect(url_for('index'))

        try:
            discord = make_session(state=session.get('oauth2_state'))
            token = discord.fetch_token(
                app.config['DISCORD_TOKEN_URL'],
                client_secret=app.config['DISCORD_CLIENT_SECRET'],
                authorization_response=request.url
            )
            session['oauth2_token'] = token

            discord = make_session(token=session.get('oauth2_token'))
            user = discord.get(f'{app.config["DISCORD_API_BASE_URL"]}/users/@me').json()

            session['discord_id'] = user['id']
            session['discord_username'] = f"{user['username']}#{user['discriminator']}"
            session['discord_avatar'] = user['avatar']

            flash('Successfully logged in!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'Login failed: {str(e)}', 'danger')
        return redirect(url_for('index'))

    

    @app.route('/upload', methods=['GET', 'POST'])
    @login_required
    def upload():
        if request.method == 'POST':
            if 'screenshots[]' not in request.files:
                flash('No files uploaded', 'danger')
                return redirect(request.url)
    
            files = request.files.getlist('screenshots[]')
            discord_username = session['discord_username']
    
            # Basic validation
            for file in files:
                if file and not allowed_file(file.filename):
                    flash(f'Invalid file type: {file.filename}', 'danger')
                    return redirect(request.url)
                if file.content_length and file.content_length > 24 * 1024 * 1024:  # Added content_length check
                    flash(f'File too large: {file.filename}', 'danger')
                    return redirect(request.url)
    
            try:
                uploaded_files = handle_upload(files, discord_username)
                flash(f'Successfully uploaded {len(uploaded_files)} files', 'success')
                return redirect(url_for('index'))
            except Exception as e:
                flash(f'Error uploading files: {str(e)}', 'danger')
                return redirect(request.url)
    
        return render_template('upload.html')
    
    @app.route("/shots/<image_filename>")
    def view_image(image_filename):
        image_path = os.path.join(app.config["UPLOAD_FOLDER"], image_filename)
        if os.path.exists(image_path):
            with sqlite3.connect("screenshots.db") as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT s.*, g.name as group_name, GROUP_CONCAT(t.name) as tags
                    FROM screenshots s
                    LEFT JOIN screenshot_groups g ON s.group_id = g.id
                    LEFT JOIN screenshot_tags st ON s.id = st.screenshot_id
                    LEFT JOIN tags t ON st.tag_id = t.id
                    WHERE s.filename = ?
                    GROUP BY s.id
                    """,
                    (image_filename,),
                )
                image_data = cursor.fetchone()
            return render_template(
                "image_view.html", image_filename=image_filename, image_data=image_data
            )
        return "Image not found", 404
    
    print("Discord Client ID:", os.getenv('DISCORD_CLIENT_ID'))
    print("Discord Redirect URI:", os.getenv('DISCORD_REDIRECT_URI'))
    return app

if __name__ == "__main__":
    app = create_app()
    app.run()