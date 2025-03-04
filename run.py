# run.py
from app import create_app
from flask import session
import sqlite3
from config import Config  # or wherever you're pulling Config from

app = create_app()

@app.context_processor
def inject_notifications():
    user_id = session.get("discord_id") or session.get("guest_id")
    if not user_id:
        return {"unread_notifications": 0}
    try:
        with sqlite3.connect(Config.DATABASE_PATH) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM notifications WHERE user_id=? AND is_read=0",
                (user_id,)
            ).fetchone()
            count = row["cnt"] if row else 0
    except Exception as e:
        count = 0
    return {"unread_notifications": count}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001)
