# ============================================================
# services/ai_client.py — Gemini API wrapper
#
# Reads GEMINI_API_KEY from environment (.env loaded by config.py)
# Uses google-generativeai library with gemini-1.5-flash model.
# ============================================================

import os
import google.generativeai as genai
from config import Config


# ── Configure the Gemini SDK once at import time ──────────
_api_key = Config.GEMINI_API_KEY
if not _api_key:
    raise EnvironmentError(
        "GEMINI_API_KEY is not set. "
        "Copy .env.example → .env and add your key."
    )

genai.configure(api_key=_api_key)

# ── Model setup ───────────────────────────────────────────
# gemini-1.5-flash: fast + cheap, perfect for educational Q&A
_model = genai.GenerativeModel(
    model_name="gemini-2.5-flash-lite",
    generation_config={
        "temperature": 0.4,       # lower = more factual, less hallucination
        "top_p": 0.9,
        "max_output_tokens": 1024,
    },
    safety_settings=[
        # Keep the default safety settings; students use this app
        {"category": "HARM_CATEGORY_HARASSMENT",        "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH",       "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    ]
)


def ask_gemini(prompt: str) -> str:
    """
    Send a prompt to Gemini and return the plain-text response.

    Args:
        prompt : the full prompt string (built by prompt_engine.py)

    Returns:
        Stripped response text from Gemini.

    Raises:
        RuntimeError if the API call fails or returns empty content.
    """
    try:
        response = _model.generate_content(prompt)

        # Extract text safely
        if response.parts:
            return response.text.strip()

        # If model was blocked by safety filters
        finish_reason = response.candidates[0].finish_reason if response.candidates else "UNKNOWN"
        raise RuntimeError(
            f"Gemini returned no content. finish_reason={finish_reason}. "
            "The question may have been blocked by safety filters."
        )

    except Exception as exc:
        # Re-raise with a clean message so the route can surface it to the user
        raise RuntimeError(f"Gemini API call failed: {exc}") from exc
