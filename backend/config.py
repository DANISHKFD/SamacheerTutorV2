# ============================================================
# config.py — Central configuration
#
# Loads .env from the backend/ directory (or project root)
# and exposes settings as class attributes.
# ============================================================

import os
from dotenv import load_dotenv

# Load .env file (search from this file's directory upward)
_env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(_env_path)


class Config:
    # ── Gemini ───────────────────────────────────────────
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # ── FAISS index storage directory ────────────────────
    # Stored inside backend/ so it's close to the Python code
    INDEX_DIR: str = os.path.join(os.path.dirname(__file__), "index")

    # ── Data directory (raw .txt textbook files) ─────────
    DATA_DIR: str = os.path.join(
        os.path.dirname(__file__), "..", "data"
    )

    # ── Flask ─────────────────────────────────────────────
    DEBUG: bool = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "ai-tutor-secret-key-change-in-prod")
