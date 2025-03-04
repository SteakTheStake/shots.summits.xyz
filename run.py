# run.py
from app import create_app

app = create_app()

@app.context_processor
def inject_notifications():
    user_id = session.get("discord_id") or session.get("guest_id")
    if not user_id:
        return {"unread_notifications": 0}
    with sqlite3.connect(Config.DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM notifications WHERE user_id=? AND is_read=0",
            (user_id,)
        ).fetchone()
        count = row["cnt"] if row else 0
    return {"unread_notifications": count}

if __name__ == "__main__":
    # Typically you'd set host and port here, or rely on .env config:
    app.run(host="0.0.0.0", port=8001)
