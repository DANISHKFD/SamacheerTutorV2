# ============================================================
# routes/chat.py — /api/chat POST endpoint
# Orchestrates RAG + Gemini to answer student questions
# ============================================================

import re

from flask import Blueprint, request, jsonify
from services.rag import search_index, find_exercise_chunks
from services.prompt_engine import build_prompt, get_language_instruction
from services.ai_client import ask_gemini

chat_bp = Blueprint("chat", __name__)

# How many prior turns (user+ai messages) to feed back to the model as
# conversational memory. Capped to keep prompt size/cost bounded.
MAX_HISTORY_TURNS = 12
MAX_HISTORY_TEXT_LEN = 2000

# Same idea, but for snippets pulled from the student's OTHER saved chats
# (cross-chat memory) — kept smaller since it's background, not the live turn.
MAX_CROSS_CHAT_ENTRIES = 12
MAX_CHAT_TITLE_LEN = 80

# Recognise "Exercise 5.8" / "exercise no. 5.8" and "question 3" / "Q3" /
# "problem 3" so we can look the question up directly instead of relying
# on semantic search over noisy, PDF-extracted maths text.
_EXERCISE_REF_RE = re.compile(r"exercise\s*(?:no\.?|number)?\s*(\d+\.\d+)", re.I)
_QUESTION_REF_RE = re.compile(r"(?:question|problem|q)\.?\s*(?:no\.?|number)?\s*#?\s*(\d{1,2})\b", re.I)


def _extract_exercise_reference(question: str):
    """Return (exercise, question_no) parsed from the student's text, or (None, None)."""
    ex_match = _EXERCISE_REF_RE.search(question)
    if not ex_match:
        return None, None
    q_match = _QUESTION_REF_RE.search(question)
    return ex_match.group(1), (q_match.group(1) if q_match else None)


def _sanitize_history(raw_history) -> list[dict]:
    """Validate and trim client-supplied history into a safe, bounded list."""
    if not isinstance(raw_history, list):
        return []

    cleaned = []
    for turn in raw_history[-MAX_HISTORY_TURNS:]:
        if not isinstance(turn, dict):
            continue
        role = turn.get("role")
        text = turn.get("text")
        if role not in ("user", "ai") or not isinstance(text, str) or not text.strip():
            continue
        cleaned.append({"role": role, "text": text.strip()[:MAX_HISTORY_TEXT_LEN]})

    return cleaned


def _sanitize_cross_chat_memory(raw_memory) -> list[dict]:
    """Validate and trim client-supplied cross-chat memory into a safe, bounded list."""
    if not isinstance(raw_memory, list):
        return []

    cleaned = []
    for turn in raw_memory[-MAX_CROSS_CHAT_ENTRIES:]:
        if not isinstance(turn, dict):
            continue
        role = turn.get("role")
        text = turn.get("text")
        if role not in ("user", "ai") or not isinstance(text, str) or not text.strip():
            continue

        entry = {"role": role, "text": text.strip()[:MAX_HISTORY_TEXT_LEN]}
        title = turn.get("chatTitle")
        if isinstance(title, str) and title.strip():
            entry["chatTitle"] = title.strip()[:MAX_CHAT_TITLE_LEN]
        cleaned.append(entry)

    return cleaned


@chat_bp.route("/chat", methods=["POST"])
def chat():
    """
    POST /api/chat
    Request body:
        {
            "question": "What is photosynthesis?",
            "subject":  "science",          # maths | science | social
            "mode":     "easy",             # easy | detailed
            "language": "english",          # english | tamil — language of the answer
            "class":    "9",                # 8 | 9 | 10 (defaults to 9)
            "history":  [{"role": "user", "text": "..."}, {"role": "ai", "text": "..."}],
            "crossChatMemory": [{"role": "user", "text": "...", "chatTitle": "..."}]
        }
    Returns:
        { "answer": "...", "chunks_used": [...] }
    """
    data = request.get_json(silent=True)

    # ── 1. Validate input ──────────────────────────────────
    if not data:
        return jsonify({"error": "Request body must be JSON."}), 400

    question    = data.get("question", "").strip()
    subject     = data.get("subject", "science").lower().strip()
    mode        = data.get("mode", "easy").lower().strip()
    language    = data.get("language", "english").lower().strip()
    student_class = str(data.get("class", "9")).strip()
    history     = _sanitize_history(data.get("history"))
    cross_chat_memory = _sanitize_cross_chat_memory(data.get("crossChatMemory"))

    if not question:
        return jsonify({"error": "Field 'question' is required."}), 400

    if subject not in ("maths", "science", "social"):
        return jsonify({"error": "subject must be one of: maths, science, social"}), 400

    if mode not in ("easy", "detailed"):
        mode = "easy"

    if language not in ("english", "tamil"):
        language = "english"

    if student_class not in ("8", "9", "10"):
        student_class = "9"
    standard = f"standard_{student_class}"

    # ── 2. Retrieve relevant chunks via RAG ───────────────
    is_exercise_lookup = False
    chunks = []
    try:
        exercise, question_no = (None, None)
        if subject == "maths":
            exercise, question_no = _extract_exercise_reference(question)

        if exercise:
            chunks = find_exercise_chunks(standard=standard, exercise=exercise, question_no=question_no)
            is_exercise_lookup = bool(chunks)

        if not chunks:
            chunks = search_index(question, subject=subject, standard=standard, top_k=3)
    except FileNotFoundError as e:
        return jsonify({
            "error": str(e),
            "hint": "Run scripts/build_index.py first to generate the FAISS index."
        }), 503
    except Exception as e:
        return jsonify({"error": f"RAG retrieval failed: {str(e)}"}), 500

    # ── 3. Build subject-aware prompt (includes conversation memory) ──
    prompt = build_prompt(
        question, chunks, subject=subject, mode=mode, language=language, history=history,
        cross_chat_memory=cross_chat_memory, is_exercise_lookup=is_exercise_lookup,
    )

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
    Request body: { "text": "...", "subject": "science", "language": "english" }
    """
    data = request.get_json(silent=True)
    if not data or not data.get("text"):
        return jsonify({"error": "'text' field is required."}), 400

    original = data["text"].strip()
    subject  = data.get("subject", "science")
    language = data.get("language", "english").lower().strip()
    if language not in ("english", "tamil"):
        language = "english"

    simplify_prompt = (
        f"You are a friendly teacher for Tamil Nadu State Board class 8-10 students.\n"
        f"Re-explain the following answer in the SIMPLEST possible terms. "
        f"Use very short sentences. Avoid difficult words. "
        f"If it is a {subject} topic, keep the style appropriate.\n\n"
        f"{get_language_instruction(language)}\n\n"
        f"Original answer:\n{original}\n\n"
        f"Simplified answer:"
    )

    try:
        answer = ask_gemini(simplify_prompt)
    except Exception as e:
        return jsonify({"error": f"Gemini API error: {str(e)}"}), 502

    return jsonify({"answer": answer})
