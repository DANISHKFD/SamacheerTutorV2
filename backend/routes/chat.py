# ============================================================
# routes/chat.py — /api/chat POST endpoint
# Orchestrates RAG + Gemini to answer student questions
# ============================================================

from flask import Blueprint, request, jsonify
from services.rag import search_index
from services.prompt_engine import build_prompt
from services.ai_client import ask_gemini

chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/chat", methods=["POST"])
def chat():
    """
    POST /api/chat
    Request body:
        {
            "question": "What is photosynthesis?",
            "subject":  "science",          # maths | science | social
            "mode":     "easy"              # easy | detailed
        }
    Returns:
        { "answer": "...", "chunks_used": [...] }
    """
    data = request.get_json(silent=True)

    # ── 1. Validate input ──────────────────────────────────
    if not data:
        return jsonify({"error": "Request body must be JSON."}), 400

    question = data.get("question", "").strip()
    subject  = data.get("subject", "science").lower().strip()
    mode     = data.get("mode", "easy").lower().strip()

    if not question:
        return jsonify({"error": "Field 'question' is required."}), 400

    if subject not in ("maths", "science", "social"):
        return jsonify({"error": "subject must be one of: maths, science, social"}), 400

    if mode not in ("easy", "detailed"):
        mode = "easy"

    # ── 2. Retrieve relevant chunks via RAG ───────────────
    try:
        chunks = search_index(question, subject=subject, top_k=3)
    except FileNotFoundError as e:
        return jsonify({
            "error": str(e),
            "hint": "Run scripts/build_index.py first to generate the FAISS index."
        }), 503
    except Exception as e:
        return jsonify({"error": f"RAG retrieval failed: {str(e)}"}), 500

    # ── 3. Build subject-aware prompt ─────────────────────
    prompt = build_prompt(question, chunks, subject=subject, mode=mode)

    # ── 4. Call Gemini ────────────────────────────────────
    try:
        answer = ask_gemini(prompt)
    except Exception as e:
        return jsonify({"error": f"Gemini API error: {str(e)}"}), 502

    return jsonify({
        "answer": answer,
        "chunks_used": chunks          # handy for debugging / transparency
    })


@chat_bp.route("/simplify", methods=["POST"])
def simplify():
    """
    POST /api/simplify
    Takes an existing AI answer and makes it even simpler.
    Request body: { "text": "...", "subject": "science" }
    """
    data = request.get_json(silent=True)
    if not data or not data.get("text"):
        return jsonify({"error": "'text' field is required."}), 400

    original = data["text"].strip()
    subject  = data.get("subject", "science")

    simplify_prompt = (
        f"You are a friendly teacher for Tamil Nadu State Board class 8-10 students.\n"
        f"Re-explain the following answer in the SIMPLEST possible English. "
        f"Use very short sentences. Avoid difficult words. "
        f"If it is a {subject} topic, keep the style appropriate.\n\n"
        f"Original answer:\n{original}\n\n"
        f"Simplified answer:"
    )

    try:
        answer = ask_gemini(simplify_prompt)
    except Exception as e:
        return jsonify({"error": f"Gemini API error: {str(e)}"}), 502

    return jsonify({"answer": answer})
