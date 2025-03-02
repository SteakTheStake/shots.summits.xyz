# app/utils/webhooks.py

import hmac
import hashlib
import requests
from datetime import datetime
from config import Config

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
    Verify that the request came from Discord using the signature
    """
    message = timestamp + body
    hex_key = bytes.fromhex(Config.DISCORD_PUBLIC_KEY)
    signature_bytes = bytes.fromhex(signature)

    calculated_signature = hmac.new(
        hex_key, message.encode(), hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(calculated_signature, signature)
