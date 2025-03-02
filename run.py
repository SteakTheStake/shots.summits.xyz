# run.py
from app import create_app

app = create_app()

if __name__ == "__main__":
    # Typically you'd set host and port here, or rely on .env config:
    app.run(host="0.0.0.0", port=8001)
