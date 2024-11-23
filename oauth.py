# oauth.py
from functools import wraps
from flask import session, redirect, url_for, request
from requests_oauthlib import OAuth2Session
import os

# OAuth2 settings
DISCORD_CLIENT_ID = "1180699631693348914"
DISCORD_CLIENT_SECRET = "your_client_secret"  # Get this from Discord Developer Portal
DISCORD_REDIRECT_URI = "http://localhost:5500/callback"  # Adjust for production
DISCORD_BOT_TOKEN = "your_bot_token"

# Discord OAuth2 endpoints
DISCORD_AUTHORIZATION_BASE_URL = "https://discord.com/api/oauth2/authorize"
DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"
DISCORD_API_BASE_URL = "https://discord.com/api"

def token_updater(token):
    session['oauth2_token'] = token

def make_session(token=None, state=None):
    return OAuth2Session(
        client_id=DISCORD_CLIENT_ID,
        token=token,
        state=state,
        redirect_uri=DISCORD_REDIRECT_URI,
        scope=['identify', 'guilds'],
        token_updater=token_updater
    )
    