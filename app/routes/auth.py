# app/routes/auth.py
from flask import Blueprint, redirect, url_for, request, session, flash, jsonify
from requests_oauthlib import OAuth2Session
from config import Config
from app.utils.security import login_required
from app.utils.webhooks import send_discord_webhook

auth_bp = Blueprint('auth', __name__, template_folder='../templates')

def make_session(token=None, state=None):
    """
    Helper that creates and returns an OAuth2Session for Discord
    """
    return OAuth2Session(
        client_id=Config.DISCORD_CLIENT_ID,
        token=token,
        state=state,
        redirect_uri=Config.DISCORD_REDIRECT_URI,
        scope=Config.DISCORD_BOT_SCOPES
    )

@auth_bp.route("/login")
def login():
    discord = make_session()
    authorization_url, state = discord.authorization_url(Config.DISCORD_AUTHORIZATION_BASE_URL)
    session["oauth2_state"] = state
    return redirect(authorization_url)

@auth_bp.route("/logout")
def logout():
    if "discord_id" in session:
        session.pop("discord_id", None)
        session.pop("username", None)
        session.pop("avatar", None)
        flash("Successfully logged out from Discord!", "success")
    else:
        flash("No Discord login found. You remain a guest user.", "info")

    return redirect(url_for("main.index"))

@auth_bp.route("/callback")
def callback():
    if request.values.get("error"):
        flash(request.values["error"], "danger")
        return redirect(url_for("main.index"))

    try:
        discord = make_session(state=session.get("oauth2_state"))
        token = discord.fetch_token(
            Config.DISCORD_TOKEN_URL,
            client_secret=Config.DISCORD_CLIENT_SECRET,
            authorization_response=request.url,
        )
        session["oauth2_token"] = token

        # Use the token to fetch user info
        discord = make_session(token=session["oauth2_token"])
        user = discord.get(f"{Config.DISCORD_API_BASE_URL}/users/@me").json()

        session["discord_id"] = user["id"]
        session["username"] = f"{user['username']}"
        session["avatar"] = user["avatar"]

        # Optionally send a webhook
        send_discord_webhook(session["username"], "Login")

        flash("Successfully logged in!", "success")
        return redirect(url_for("main.index"))

    except Exception as e:
        flash(f"Login failed: {str(e)}", "danger")
        return redirect(url_for("main.index"))

@auth_bp.route("/dev")
def dev_login():
    # Ensure this route is only accessible if DEVELOPER_MODE is True
    if not Config.DEVELOPER_MODE:
        flash("Developer login is only available in developer mode.", "danger")
        return redirect(url_for("main.index"))

    # Simulate a Discord user login
    session["discord_id"] = "278344153761316864"  # Example Discord ID
    session["username"] = "Developer"
    session["avatar"] = "https://cdn.discordapp.com/embed/avatars/0.png"  # Example avatar URL

    # Optionally send a webhook
    send_discord_webhook(session["username"], "Developer Login")

    flash("Developer login successful!", "success")
    return redirect(url_for("main.index"))