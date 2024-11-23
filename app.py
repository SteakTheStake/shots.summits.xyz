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

def create_app():
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    app.config.from_object(Config)
    init_db()
    
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
            def callback():
                user = discord.get(f'{Config.DISCORD_API_BASE_URL}/users/@me').json()
                session['discord_username'] = user['username']
            flash('Successfully logged in!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'Login failed: {str(e)}', 'danger')
        return redirect(url_for('index'))

    @app.route('/logout')
    def logout():
        session.clear()
        flash('Successfully logged out!', 'success')
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
            tags = request.form.get('tags', '').split(',')
            group_name = request.form.get('group_name', '')

            for file in files:
                if file and not allowed_file(file.filename):
                    flash(f'Invalid file type: {file.filename}', 'danger')
                    return redirect(request.url)
                if file.content_length > 10 * 1024 * 1024:
                    flash(f'File too large: {file.filename}', 'danger')
                    return redirect(request.url)

            try:
                uploaded_files = handle_upload(files, discord_username, tags, group_name)
                flash(f'Successfully uploaded {len(uploaded_files)} files', 'success')
                return redirect(url_for('index'))
            except Exception as e:
                flash(f'Error uploading files: {str(e)}', 'danger')
                return redirect(request.url)

        return render_template('upload.html', discord_username=session.get('discord_username'))

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

def make_session(token=None, state=None):
    return OAuth2Session(
        client_id=Config.DISCORD_CLIENT_ID,
        token=token,
        state=state,
        redirect_uri=Config.DISCORD_REDIRECT_URI,
        scope=['identify', 'guilds']
    )

def create_app():
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    app.config.from_object(Config)
    init_db()
    
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
    
    def handle_upload(files, discord_username, tags, group_name):
        uploaded_files = []
        with sqlite3.connect('screenshots.db') as conn:
            if group_name:
                cursor = conn.execute(
                    'INSERT INTO screenshot_groups (name, created_by) VALUES (?, ?) RETURNING id',
                    (group_name, discord_username)
                )
                group_id = cursor.fetchone()[0]
            else:
                group_id = None

            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(f'shot{int(datetime.now().timestamp())}.webp')
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

                    img = Image.open(file)
                    img.save(filepath, 'WEBP')

                    cursor = conn.execute(
                        'INSERT INTO screenshots (filename, discord_username, group_id) VALUES (?, ?, ?) RETURNING id',
                        (filename, discord_username, group_id)
                    )
                    screenshot_id = cursor.fetchone()[0]

                    for tag in tags:
                        tag = tag.strip().lower()
                        if tag:
                            conn.execute('INSERT OR IGNORE INTO tags (name) VALUES (?)', (tag,))
                            cursor = conn.execute('SELECT id FROM tags WHERE name = ?', (tag,))
                            tag_id = cursor.fetchone()[0]
                            conn.execute(
                                'INSERT INTO screenshot_tags (screenshot_id, tag_id) VALUES (?, ?)',
                                (screenshot_id, tag_id)
                            )

                    uploaded_files.append(filename)

            conn.commit()
        return uploaded_files
    
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
        
    @app.route('/login')
    def login():
        discord = make_session()
        authorization_url, state = discord.authorization_url(app.config['DISCORD_AUTHORIZATION_BASE_URL'])
        session['oauth2_state'] = state
        return redirect(authorization_url)

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

    @app.route('/logout')
    def logout():
        session.clear()
        flash('Successfully logged out!', 'success')
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
            tags = request.form.get('tags', '').split(',')
            group_name = request.form.get('group_name', '')

            for file in files:
                if file and not allowed_file(file.filename):
                    flash(f'Invalid file type: {file.filename}', 'danger')
                    return redirect(request.url)
                if file.content_length > 10 * 1024 * 1024:
                    flash(f'File too large: {file.filename}', 'danger')
                    return redirect(request.url)

            try:
                uploaded_files = handle_upload(files, discord_username, tags, group_name)
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
    app.run(port=5500)