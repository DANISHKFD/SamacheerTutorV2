# ============================================================
# app.py — Main Flask application entry point
# Registers blueprints and starts the development server
# ============================================================

from flask import Flask, jsonify
from flask_cors import CORS
from routes.chat import chat_bp
from routes.exam_papers import exam_papers_bp
from config import Config

def create_app():
    """Application factory — creates and configures the Flask app."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Cap request size (mainly guards the PDF upload endpoint)
    app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB

    # Allow cross-origin requests from the frontend (served from file:// or localhost)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Register blueprints under /api
    app.register_blueprint(chat_bp, url_prefix="/api")
    app.register_blueprint(exam_papers_bp, url_prefix="/api")

    @app.route("/health")
    def health():
        return {"status": "ok", "message": "AI Tutor backend is running!"}

    # ── JSON error handlers ──────────────────────────────────
    # Without these, Flask returns its default HTML error pages for things
    # like a wrong URL, wrong HTTP method, or an oversized upload — which
    # breaks the frontend's `response.json()` parsing and surfaces as a
    # misleading "could not connect to backend" message instead of the
    # real cause.
    @app.errorhandler(404)
    def not_found(_e):
        return jsonify({"error": "That endpoint doesn't exist."}), 404

    @app.errorhandler(405)
    def method_not_allowed(_e):
        return jsonify({"error": "That HTTP method isn't allowed for this endpoint."}), 405

    @app.errorhandler(413)
    def payload_too_large(_e):
        return jsonify({"error": "File too large. Maximum upload size is 20 MB."}), 413

    @app.errorhandler(500)
    def internal_error(_e):
        # Only reached when DEBUG is off (see config.py) — in debug mode
        # Flask's interactive debugger takes over unhandled exceptions
        # instead, which is what you want during local development.
        return jsonify({"error": "Something went wrong on the server. Please try again."}), 500

    if not Config.GEMINI_API_KEY:
        print(
            "[app] WARNING: GEMINI_API_KEY is not set. Chat requests will fail until "
            "you copy backend/.env.example to backend/.env and add your key."
        )

    return app


if __name__ == "__main__":
    app = create_app()
    print("🚀 AI Tutor backend started at http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
