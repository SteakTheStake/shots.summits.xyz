from requests_oauthlib import OAuth2Session
from flask import session, Blueprint
from config import Config

oauth_bp = Blueprint('oauth', __name__)  # Flask Blueprint for modular routing

def token_updater(token):
    session['oauth2_token'] = token

def make_session(token=None, state=None):
    """Create and configure the OAuth2 session."""
    return OAuth2Session(
        client_id=Config.DISCORD_CLIENT_ID,
        token=token,
        state=state,
        redirect_uri=Config.DISCORD_REDIRECT_URI,
        scope=Config.OAUTH2_SCOPES,
        token_updater=token_updater
    )
