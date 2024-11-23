# oauth.py
from requests_oauthlib import OAuth2Session
from flask import session
from config import Config

def token_updater(token):
    session['oauth2_token'] = token

def make_session(token=None, state=None):
    return OAuth2Session(
        client_id=Config.DISCORD_CLIENT_ID,
        token=token,
        state=state,
        redirect_uri=Config.DISCORD_REDIRECT_URI,
        scope=['identify', 'guilds'],
        token_updater=token_updater
    )