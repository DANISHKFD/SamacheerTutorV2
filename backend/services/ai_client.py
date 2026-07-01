# ============================================================
# services/ai_client.py — Gemini API wrapper
#
# Reads GEMINI_API_KEY from environment (.env loaded by config.py)
# Uses google-generativeai library with gemini-1.5-flash model.
# ============================================================

import os
import time

import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable
from config import Config

# ── Retry/backoff for transient errors (429 RPM bursts, 503 server hiccups) ──
# Does NOT help once the daily free-tier quota is exhausted — Gemini's
# retry_delay for that case is short (~seconds) but the request will keep
# failing until the quota resets, so we still give up after MAX_RETRIES.
MAX_RETRIES = 3
BACKOFF_BASE_SECONDS = 2
RETRYABLE_EXCEPTIONS = (ResourceExhausted, ServiceUnavailable)


def _retry_delay_seconds(exc: Exception, attempt: int) -> float:
    """Use the server-suggested retry_delay if present, else exponential backoff."""
    for detail in exc.details:
        retry_delay = getattr(detail, "retry_delay", None)
        if retry_delay is not None:
            return retry_delay.seconds + retry_delay.nanos / 1e9
    return BACKOFF_BASE_SECONDS ** attempt


# ── Model setup (lazy) ─────────────────────────────────────
# Configuring the SDK / creating the model at import time means a missing
# API key crashes the entire Flask app before it can even start. Instead we
# build the model lazily on first use so the app boots and surfaces a clean
# per-request error if the key is missing.
_model = None


def _get_model():
    global _model
    if _model is not None:
        return _model

    api_key = Config.GEMINI_API_KEY
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY is not set. "
            "Copy .env.example → .env and add your key."
        )

    genai.configure(api_key=api_key)
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
    return _model


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
    model = _get_model()

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = model.generate_content(prompt)

            # Extract text safely
            if response.parts:
                return response.text.strip()

            # If model was blocked by safety filters
            finish_reason = response.candidates[0].finish_reason if response.candidates else "UNKNOWN"
            raise RuntimeError(
                f"Gemini returned no content. finish_reason={finish_reason}. "
                "The question may have been blocked by safety filters."
            )

        except RETRYABLE_EXCEPTIONS as exc:
            if attempt == MAX_RETRIES:
                raise RuntimeError(f"Gemini API call failed: {exc}") from exc
            time.sleep(_retry_delay_seconds(exc, attempt))

        except Exception as exc:
            # Re-raise with a clean message so the route can surface it to the user
            raise RuntimeError(f"Gemini API call failed: {exc}") from exc
