import os
import requests
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
from urllib.parse import urlparse
import re
from datetime import timedelta
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
from dotenv import load_dotenv
from init_db import init_db
from flask import Flask
from config import Config, Base, engine
from models import Screenshot, ScreenshotGroup, Tag, UserRole
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import create_engine
import random
from flask_sqlalchemy import SQLAlchemy
from uuid import uuid4

# Load .env
load_dotenv()
app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)

MINECRAFT_ADJECTIVES = [
    "Blaze",
    "Creeper",
    "Ender",
    "Ghastly",
    "Zombie",
    "Skeleton",
    "Wither",
    "Potion",
    "Redstone",
    "Diamond",
    "Emerald",
    "Nether",
    "Villager",
    "Piglin",
    "Warped",
    "Crimson",
    "Oak",
    "Birch",
    "Spruce",
    "Jungle",
    "Savanna",
    "Badlands",
    "Mesa",
    "Stronghold",
    "Biomes",
    "Oceanic",
    "Mushroom",
    "Soul",
    "Obsidian",
    "Cobblestone",
    "Iron",
    "Gold",
    "Lapis",
    "Quartz",
    "Glowing",
    "Prismarine",
    "Amethyst",
    "Tundra",
    "Desert",
    "Alpine",
    "Swampy",
    "Elytrian",
    "Cave",
    "Lush",
    "Dripstone",
    "Harrowing",
    "Spooky",
    "Enchanted",
    "Luminescent",
    "Farmland",
    "Mangrove",
    "Frosted",
    "Molten",
    "Endless",
    "Warden",
    "Sculk",
    "Ancient",
    "TNT",
    "Beacon",
    "Turtle",
    "Honeyed",
    "Hive",
    "Sprawling",
    "Mining",
    "Enchanting",
    "Fletching",
    "Smelting",
    "Blast",
    "Trident",
    "Potato",
    "Heroic",
    "Epic",
    "Illager",
    "Crossbow",
    "Axolotl",
    "Fungal",
    "Axian",
    "Fallen",
    "Overworld",
    "Bedrock",
    "Adaptive",
    "Charged",
    "Drowned",
    "Wandering",
    "Volatile",
    "Mooshroom",
    "Slime",
    "Ravager",
    "Phantom",
    "Fierce",
    "Shulker",
    "Guardian",
    "Elder",
    "Tamed",
    "Tactical",
    "Cartographic",
    "Bamboo",
    "Frostwalker",
    "Conduit",
    "Infinite",
    "Glimmering",
    "Verdant",
    "Illuminated",
    "Spiked",
    "Warping",
    "Bewitched",
]

MINECRAFT_NOUNS = [
    "Traveler",
    "Befriender",
    "Explorer",
    "Hunter",
    "Brewer",
    "Architect",
    "Miner",
    "Crafter",
    "Adventurer",
    "Wanderer",
    "Builder",
    "Farmer",
    "Forager",
    "Smith",
    "Tamer",
    "Raider",
    "Lootmaster",
    "Fletcher",
    "Cartographer",
    "Enchanter",
    "Defender",
    "Guardian",
    "Protector",
    "Mage",
    "Archer",
    "Warrior",
    "Ranger",
    "Shaman",
    "Conjurer",
    "Gatherer",
    "Mason",
    "Shepherd",
    "Fisherman",
    "Librarian",
    "Armorer",
    "Butcher",
    "Cleric",
    "Nitwit",
    "Bard",
    "Assassin",
    "Trickster",
    "Cultivator",
    "Blacksmith",
    "Mechanic",
    "Inventor",
    "Stalker",
    "Duelist",
    "Assaulter",
    "Overseer",
    "Mystic",
    "Warlord",
    "Channeler",
    "Druid",
    "Pirate",
    "Captain",
    "Knight",
    "Bandit",
    "Merchant",
    "Trader",
    "Pillager",
    "Illusioner",
    "Messenger",
    "Baker",
    "Chef",
    "Monarch",
    "Vindicator",
    "Beekeeper",
    "Navigator",
    "Treasure Hunter",
    "Shipwright",
    "Potioner",
    "Geologist",
    "Lumberjack",
    "Scribe",
    "Geomancer",
    "Spellbinder",
    "Phantom Slayer",
    "Redstoner",
    "Portal Runner",
    "Planter",
    "Beast Tamer",
    "Warden Watcher",
    "Endwalker",
    "Nether Surfer",
    "Biome Binder",
    "Darkness Diver",
    "Soul Seeker",
    "Lantern Lighter",
    "Disc Collector",
    "Pig Rider",
    "Slime Wrangler",
    "Engineer",
    "Potion Brewer",
    "Dragon Slayer",
    "Potion Drinker",
    "Treasure Diver",
    "Battle Mage",
    "Spelunker",
    "Witch Doctor",
    "Wayfinder",
    "Stonemason",
    "Woodsman",
    "Ringleader",
    "Torchbearer",
]


def generate_guest_username():
    adj = random.choice(MINECRAFT_ADJECTIVES)
    noun = random.choice(MINECRAFT_NOUNS)
    return f"{adj} {noun}"


# Example usage in your application:
def get_current_time():
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT datetime('now')")
        return cursor.fetchone()[0]


# When handling web requests:
def handle_request():
    with db.get_connection() as conn:
        # Do all your database operations here
        # The connection will be reused rather than creating a new one each time
        pass
    
    
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
        "username": "Summit F2",
        "avatar_url": "https://i.imgur.com/mNrcItL.jpeg",
    }

    try:
        response = requests.post(Config.DISCORD_WEBHOOK_URL, json=payload)
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
    with sqlite3.connect(Config.DATABASE_PATH) as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO user_roles (discord_id, role, assigned_by)
            VALUES (?, ?, ?)
            """,
            ("278344153761316864", "admin", "system"),
        )

        default_moderators = []

        # Ensure moderators exist
        for mod in default_moderators:
            conn.execute(
                """
                INSERT OR IGNORE INTO user_roles (discord_id, role, assigned_by)
                VALUES (?, ?, ?)
            """,
                (mod["discord_id"], mod["role"], "system"),
            )




def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # If neither a Discord user nor a guest user is present, block access
        if "discord_id" not in session and "guest_id" not in session:
            flash("Please log in or continue as guest.", "warning")
            return redirect(url_for("index"))
        return f(*args, **kwargs)

    return decorated_function


def get_user_role(discord_id=None, guest_id=None):
    with sqlite3.connect(Config.DATABASE_PATH) as conn:
        cursor = conn.execute("SELECT role FROM user_roles WHERE discord_id = ?", (discord_id,))
        if guest_id:
            return "user"
        result = cursor.fetchone()
    return result[0] if result else "user"



def requires_role(required_role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # If neither discord_id nor guest_id is in session, block
            if "discord_id" not in session and "guest_id" not in session:
                flash("Please log in or continue as guest.", "danger")
                return redirect(url_for("login"))

            # Distinguish between Discord user or guest
            discord_id = session.get("discord_id")
            guest_id = session.get("guest_id")
            user_role = get_user_role(discord_id, guest_id)

            role_hierarchy = {
                "admin": 3,
                "moderator": 2,
                "user": 1,
                "guest": 1,  # Treat guest same as normal user, or create a separate tier
            }

            if role_hierarchy.get(user_role, 0) >= role_hierarchy.get(required_role, 0):
                return f(*args, **kwargs)
            else:
                flash("Insufficient permissions.", "danger")
                return redirect(url_for("index"))

        return decorated_function

    return decorator


def _validate_tag_ids(conn, tag_ids):
    # Example: return only tag_ids that actually exist
    if not tag_ids:
        return []
    placeholder = ",".join(["?"] * len(tag_ids))
    rows = conn.execute(
        f"SELECT id FROM tags WHERE id IN ({placeholder})",
        tuple(tag_ids),
    ).fetchall()
    valid = [r["id"] for r in rows]
    return valid


def is_valid_resource_url(url):
    # Example naive check
    return url.startswith("http://") or url.startswith("https://")


def allowed_file(filename):
    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]
    )

def handle_upload(files, uploader_name):
    uploaded_files = []
    processed_files = set()

    # Open a connection to the database.
    with sqlite3.connect(Config.DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row

        # 1) Validate & store "Resources Used" from request form
        resources_input = request.form.get("resources", "").strip()
        if resources_input:
            resources_list = [r.strip() for r in resources_input.split(",")]
            for resource in resources_list:
                if not is_valid_resource_url(resource):
                    flash(f"Invalid resource link: {resource}", "error")
                    return redirect(request.url)  # Early exit on error

        # 2) Parse the common_tags as IDs
        common_tag_ids = request.form.getlist("common_tags")  # e.g. ["1", "3", ...]
        valid_common_tag_ids = _validate_tag_ids(conn, common_tag_ids)

        # 3) Process each uploaded file
        for index, file in enumerate(files):
            if not file or not file.filename:
                continue
            
            filename = secure_filename(
                f"shot_{datetime.now().timestamp()}_{os.urandom(4).hex()}.webp"
            )
            if filename in processed_files:
                continue
            
            if allowed_file(file.filename):
                try:
                    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                    with Image.open(file) as img:
                        file.seek(0)
                        img.save(filepath, "WEBP", quality=85)

                    # Determine user type and store the correct name
                    if "discord_id" in session:
                        uploader_type = "discord"
                        discord_user = session["username"]  # e.g. "Foo#1234"
                        guest_user = None
                    else:
                        uploader_type = "guest"
                        discord_user = None
                        guest_user = session.get("guest_username")

                    # Insert or create a group if a group name is provided
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
                        (filename, discord_user, guest_user, group_id, uploader_type),
                    )
                    screenshot_id = cursor.lastrowid

                    # Gather file-specific tags for this file
                    specific_tag_ids = request.form.getlist(f"tags_{index}")
                    valid_specific_tag_ids = _validate_tag_ids(conn, specific_tag_ids)

                    # Merge the common and file-specific tag IDs
                    all_tag_ids = set(valid_common_tag_ids + valid_specific_tag_ids)

                    # Insert screenshot_tags records
                    for tag_id in all_tag_ids:
                        conn.execute(
                            "INSERT INTO screenshot_tags (screenshot_id, tag_id) VALUES (?, ?)",
                            (screenshot_id, tag_id),
                        )

                    uploaded_files.append(filename)
                    processed_files.add(filename)

                except Exception as e:
                    print(f"Error processing file {file.filename}: {str(e)}")
                    continue

        # Commit all changes to the database.
        conn.commit()

    return uploaded_files

    


def create_app():
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    app.config.from_object(Config)

    # Attach SQLAlchemy to this newly created app:
    db.init_app(app)

    # Initialize DB schema if needed
    with app.app_context():
        init_db()
        ensure_default_roles()

    # Create necessary directories
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["THUMBNAIL_FOLDER"], exist_ok=True)
    # os.makedirs(app.config["GUEST_UPLOAD_FOLDER"], exist_ok=True)
    # os.makedirs(app.config["GUEST_THUMBNAIL_FOLDER"], exist_ok=True)
    print("Discord Client ID:", os.getenv("DISCORD_CLIENT_ID"))
    print("Discord Redirect URI:", os.getenv("DISCORD_REDIRECT_URI"))
    
    # @app.route start here:    
    @app.route("/debug-config")
    def debug_config():
        from config import Config  # Import Config class
    
        config_vars = {
            "CLIENT_ID": Config.DISCORD_CLIENT_ID,
            "REDIRECT_URI": Config.DISCORD_REDIRECT_URI,
            "WEBHOOK_URL": Config.DISCORD_WEBHOOK_URL,
            "HAS_CLIENT_SECRET": bool(Config.DISCORD_CLIENT_SECRET),
            "HAS_PUBLIC_KEY": bool(Config.DISCORD_PUBLIC_KEY),
            "HAS_BOT_TOKEN": bool(Config.DISCORD_BOT_TOKEN),
        }
        return jsonify(config_vars)
    
    
    @app.route("/login")
    def login():
        discord = make_session()
        authorization_url, state = discord.authorization_url(
            app.config["DISCORD_AUTHORIZATION_BASE_URL"]
        )
        session["oauth2_state"] = state
        return redirect(authorization_url)
    
    
    @app.route("/logout")
    def logout():
        # If user is logged in with Discord, remove those keys
        if "discord_id" in session:
            session.pop("discord_id", None)
            session.pop("username", None)
            session.pop("avatar", None)
            flash("Successfully logged out from Discord!", "success")
        else:
            # If no Discord login, do nothing special
            flash("No Discord login found. You remain a guest user.", "info")
    
        return redirect(url_for("index"))
    
    
    @app.route("/delete/<filename>", methods=["POST"])
    @login_required
    def delete_image(filename):
        with sqlite3.connect(Config.DATABASE_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT discord_username, guest_username FROM screenshots WHERE filename = ?",
                (filename,),
            )
            row = cursor.fetchone()
            if not row:
                flash("Image not found.", "danger")
                return redirect(url_for("index"))
    
            # Figure out whether the uploader was a discord user or a guest
            if row["discord_username"]:
                uploader = row["discord_username"]
            else:
                uploader = row["guest_username"]
    
            # Check roles
            discord_id = session.get("discord_id")
            guest_id = session.get("guest_id")
            user_role = get_user_role(discord_id, guest_id)
    
            # Compare with session['username'], which is assigned to EITHER
            # 'Foo#1234' (Discord) or 'Blaze Traveler' (Guest)
            if uploader == session.get("username") or user_role in ["admin", "moderator"]:
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
    
                    # Delete from the DB
                    conn.execute("DELETE FROM screenshots WHERE filename = ?", (filename,))
    
                    # Delete the file on disk
                    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                    if os.path.exists(filepath):
                        os.remove(filepath)
    
                    conn.commit()
                    flash("Image deleted successfully.", "success")
                except Exception as e:
                    flash(f"Error deleting image: {str(e)}", "danger")
            else:
                flash("Permission denied.", "danger")
    
        return redirect(url_for("index"))
    
    
    @app.route("/admin/dashboard")
    @login_required
    @requires_role("admin")
    def admin_dashboard():
        with sqlite3.connect(Config.DATABASE_PATH) as conn:
            conn.row_factory = sqlite3.Row
    
            stats = {
                "total_images": conn.execute("SELECT COUNT(*) FROM screenshots").fetchone()[
                    0
                ],
                "total_users": conn.execute(
                    "SELECT COUNT(DISTINCT discord_username) FROM screenshots"
                ).fetchone()[0],
                "recent_uploads": conn.execute(
                    "SELECT * FROM screenshots ORDER BY upload_date DESC LIMIT 10"
                ).fetchall(),
                "deletion_log": conn.execute(
                    "SELECT * FROM deletion_log ORDER BY deletion_date DESC LIMIT 10"
                ).fetchall(),
            }
    
            # Only Discord roles are considered in user_roles by default
            users = conn.execute(
                """
                    SELECT ur.discord_id, ur.role, ur.assigned_date,
                        COUNT(s.id) AS upload_count
                    FROM user_roles ur
                    LEFT JOIN screenshots s ON ur.discord_id = s.discord_username
                    GROUP BY ur.discord_id
                    """
            ).fetchall()
    
        return render_template("admin_dashboard.html", stats=stats, users=users)
    
    
    def get_discord_avatar_url(user_id, user_avatar):
        # If no avatar is set, return a default
        if not user_avatar:
            # Return default Discord avatar #0 (there are 5 variants: 0..4)
            return "https://cdn.discordapp.com/embed/avatars/0.png"
    
        # Otherwise check if it's animated
        if user_avatar.startswith("a_"):
            return f"https://cdn.discordapp.com/avatars/{user_id}/{user_avatar}.gif"
        else:
            return f"https://cdn.discordapp.com/avatars/{user_id}/{user_avatar}.png"
    
    
    @app.route("/admin/manage_roles", methods=["POST"])
    @login_required
    @requires_role("admin")
    def manage_roles():
        discord_id = request.form.get("discord_id")
        new_role = request.form.get("role")
    
        if new_role not in ["user", "moderator", "admin"]:
            flash("Invalid role specified.", "danger")
            return redirect(url_for("admin_dashboard"))
    
        with sqlite3.connect(Config.DATABASE_PATH) as conn:
            conn.execute(
                """
                    INSERT OR REPLACE INTO user_roles (discord_id, role, assigned_by)
                    VALUES (?, ?, ?)
                """,
                (discord_id, new_role, session["username"]),
            )
    
        flash(f"Role updated successfully for user {discord_id}", "success")
        return redirect(url_for("admin_dashboard"))
    
    
    @app.route("/mod/review")
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
    
    
    @app.route("/mod/report/<filename>", methods=["POST"])
    @login_required
    def report_image(filename):
        reason = request.form.get("reason", "").strip()
        if not reason:
            flash("Please provide a reason for reporting.", "danger")
            return redirect(url_for("view_image", image_filename=filename))

        with sqlite3.connect(Config.DATABASE_PATH) as conn:
            conn.execute(
                """
                INSERT INTO reports (filename, reported_by, reason)
                VALUES (?, ?, ?)
                """,
                (filename, session.get("username"), reason),
            )

        flash("Image reported successfully. Moderators will review it.", "success")
        return redirect(url_for("view_image", image_filename=filename))

    
    
    def get_discord_avatar_url(user_id, user_avatar):
        if not user_avatar:
            return "https://cdn.discordapp.com/embed/avatars/0.png"
        if user_avatar.startswith("a_"):
            return f"https://cdn.discordapp.com/avatars/{user_id}/{user_avatar}.gif"
        else:
            return f"https://cdn.discordapp.com/avatars/{user_id}/{user_avatar}.png"
    
    
    @app.context_processor
    def utility_processor():
        # This makes the function available to all templates
        return dict(get_discord_avatar_url=get_discord_avatar_url)
    
    
    @app.route("/")
    def index():
        # Set up a guest session if no user is logged in.
        if "discord_id" not in session and "guest_id" not in session:
            session["guest_id"] = str(uuid4())
            session["guest_username"] = generate_guest_username()
            session["username"] = session["guest_username"]
            session.permanent = True

        # Read the tags filter from the URL query parameter.
        tags_param = request.args.get("tags", "")
        # Build a list of tag IDs (as strings) if provided.
        filter_ids = [t.strip() for t in tags_param.split(",") if t.strip()] if tags_param else []

        with sqlite3.connect(Config.DATABASE_PATH) as conn:
            conn.row_factory = sqlite3.Row

            if filter_ids:
                # Build placeholders for the selected tag IDs.
                placeholders = ",".join(["?"] * len(filter_ids))
                query = f"""
                    SELECT
                    s.id,
                    s.filename,
                    COALESCE(s.discord_username, s.guest_username) AS uploader_name,
                    g.name AS group_name,
                    GROUP_CONCAT(t.name) AS tags,
                    SUM(CASE WHEN st.tag_id IN ({placeholders}) THEN 1 ELSE 0 END) AS match_count
                    FROM screenshots s
                    LEFT JOIN screenshot_groups g ON s.group_id = g.id
                    LEFT JOIN screenshot_tags st ON s.id = st.screenshot_id
                    LEFT JOIN tags t ON st.tag_id = t.id
                    GROUP BY s.id
                    HAVING match_count > 0
                    ORDER BY s.upload_date DESC
                """
                screenshots = conn.execute(query, tuple(filter_ids)).fetchall()
            else:
                screenshots = conn.execute(
                    """
                    SELECT
                    s.id,
                    s.filename,
                    COALESCE(s.discord_username, s.guest_username) AS uploader_name,
                    g.name AS group_name,
                    GROUP_CONCAT(t.name) AS tags
                    FROM screenshots s
                    LEFT JOIN screenshot_groups g ON s.group_id = g.id
                    LEFT JOIN screenshot_tags st ON s.id = st.screenshot_id
                    LEFT JOIN tags t ON st.tag_id = t.id
                    GROUP BY s.id
                    ORDER BY s.upload_date DESC
                    """
                ).fetchall()

            users = sorted({ screenshot["uploader_name"] for screenshot in screenshots })
            # Query all tags from the tags table for the modal.
            tags = conn.execute("SELECT id, name FROM tags ORDER BY name").fetchall()

        # Pass the current filter (list of tag IDs) so you can optionally display active filters.
        return render_template("index.html", screenshots=screenshots, preapproved_tags=tags, current_filters=filter_ids)


    # Add this to your app.py temporarily to debug
    @app.route("/config-check")
    def config_check():
        return {
            "client_id": app.config["DISCORD_CLIENT_ID"],
            "redirect_uri": app.config["DISCORD_REDIRECT_URI"],
            "api_base": app.config["DISCORD_API_BASE_URL"],
            "auth_base": app.config["DISCORD_AUTHORIZATION_BASE_URL"],
            "token_url": app.config["DISCORD_TOKEN_URL"],
        }
    
    
    @app.route("/callback")
    def callback():
        if request.values.get("error"):
            flash(request.values["error"], "danger")
            return redirect(url_for("index"))
    
        try:
            discord = make_session(state=session.get("oauth2_state"))
            token = discord.fetch_token(
                app.config["DISCORD_TOKEN_URL"],
                client_secret=app.config["DISCORD_CLIENT_SECRET"],
                authorization_response=request.url,
            )
            session["oauth2_token"] = token
    
            discord = make_session(token=session.get("oauth2_token"))
            user = discord.get(f'{app.config["DISCORD_API_BASE_URL"]}/users/@me').json()
    
            session["discord_id"] = user["id"]
            session["username"] = f"{user['username']}#{user['discriminator']}"
            session["avatar"] = user["avatar"]
    
            flash("Successfully logged in!", "success")
            return redirect(url_for("index"))
        except Exception as e:
            flash(f"Login failed: {str(e)}", "danger")
        return redirect(url_for("index"))
    
    
    @app.route("/upload_form", methods=["GET"])
    @login_required
    def upload_form():
        with sqlite3.connect(Config.DATABASE_PATH) as conn:
            conn.row_factory = sqlite3.Row
            preapproved_tags = conn.execute(
                "SELECT id, name FROM tags ORDER BY name"
            ).fetchall()

        return render_template("upload_form.html", preapproved_tags=preapproved_tags)
    
    
    @app.route("/upload", methods=["GET", "POST"])
    @login_required
    def upload():
        if request.method == "POST":
            if "screenshots[]" not in request.files:
                flash("No files uploaded", "danger")
                return redirect(request.url)

            files = request.files.getlist("screenshots[]")
            uploader_name = session.get("username")

            # Basic validation for each file
            for file in files:
                if file and not allowed_file(file.filename):
                    flash(f"Invalid file type: {file.filename}", "danger")
                    return redirect(request.url)
                if file.content_length and file.content_length > 24 * 1024 * 1024:
                    flash(f"File too large: {file.filename}", "danger")
                    return redirect(request.url)

            try:
                # Call your file upload handler
                uploaded_files = handle_upload(files, uploader_name)
                flash(f"Successfully uploaded {len(uploaded_files)} files", "success")
            except Exception as e:
                flash(f"Error uploading files: {str(e)}", "danger")
                return redirect(request.url)

            return redirect(url_for("index"))

        # GET request: fetch preapproved tags and pass them to the template
        with sqlite3.connect(Config.DATABASE_PATH) as conn:
            conn.row_factory = sqlite3.Row
            preapproved_tags = conn.execute(
                "SELECT id, name FROM tags ORDER BY name"
            ).fetchall()

        return render_template("upload.html", preapproved_tags=preapproved_tags)


    
    
    @app.route("/shots/<image_filename>")
    def view_image(image_filename):
        image_path = os.path.join(app.config["UPLOAD_FOLDER"], image_filename)
        if os.path.exists(image_path):
            with sqlite3.connect(Config.DATABASE_PATH) as conn:
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
    
        
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8001)
