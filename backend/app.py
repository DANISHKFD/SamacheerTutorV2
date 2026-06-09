# ============================================================
# app.py — Main Flask application entry point
# Registers blueprints and starts the development server
# ============================================================

from flask import Flask
from flask_cors import CORS
from routes.chat import chat_bp
from config import Config

def create_app():
    """Application factory — creates and configures the Flask app."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Allow cross-origin requests from the frontend (served from file:// or localhost)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Register the chat blueprint under /api
    app.register_blueprint(chat_bp, url_prefix="/api")

    @app.route("/health")
    def health():
        return {"status": "ok", "message": "AI Tutor backend is running!"}

    return app


if __name__ == "__main__":
    app = create_app()
    print("🚀 AI Tutor backend started at http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
