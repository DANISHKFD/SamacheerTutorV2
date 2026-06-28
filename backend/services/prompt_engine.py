# ============================================================
# services/prompt_engine.py — Subject-aware prompt builder
#
# Constructs a Gemini prompt that tells the model:
#   • WHO it is (Tamil Nadu tutor)
#   • WHAT context to use (RAG chunks)
#   • HOW to format the answer (per subject + mode)
# ============================================================


# ── Per-subject instruction blocks ────────────────────────

SUBJECT_INSTRUCTIONS = {
    "maths": """
You are helping a Class 8–10 Tamil Nadu State Board student with Mathematics.
Follow these rules STRICTLY:
1. Read the context carefully before answering.
2. Show the FORMULA or rule being used.
3. Solve STEP BY STEP — number every step clearly.
4. Write the FINAL ANSWER at the end in bold or on its own line.
5. Use simple English words. Avoid jargon.
6. If the question cannot be answered from context, say so politely and give a brief general explanation.
7. Since it is maths, avoid long explaination of programs. give a brief explaination if needed then proceed with the calculations.
""",

    "science": """
You are helping a Class 8–10 Tamil Nadu State Board student with Science.
Follow these rules STRICTLY:
1. First, EXPLAIN the concept in 1–2 simple sentences.
2. Explain WHY it happens (the reason or cause).
3. Give ONE real-life example that a student in Tamil Nadu can relate to.
4. Keep sentences short. Use simple English.
5. If the question cannot be answered from context, say so politely and give a brief general explanation.
""",

    "social": """
You are helping a Class 8–10 Tamil Nadu State Board student with Social Science (History, Geography, Civics, Economics).
Follow these rules STRICTLY:
1. Tell the answer like a SHORT, engaging story or narrative.
2. Use simple language — imagine you are talking to a 13-year-old.
3. At the end, add a "Key Points:" section with 3–5 bullet points summarising the main facts.
4. Avoid difficult words. If you must use one, explain it in brackets.
5. If the question cannot be answered from context, say so politely and give a brief general explanation.
"""
}

# ── Mode modifiers ─────────────────────────────────────────

MODE_MODIFIERS = {
    "easy": (
        "Use the SIMPLEST possible language. Very short sentences. "
        "Imagine your reader is hearing this topic for the first time."
    ),
    "detailed": (
        "Give a complete and thorough answer. Include additional details, "
        "diagrams described in words, and deeper explanations where helpful."
    )
}


# ─────────────────────────────────────────────────────────
# PUBLIC FUNCTION
# ─────────────────────────────────────────────────────────

def _build_history_block(history: list[dict] | None) -> str:
    """Render prior turns as a transcript so the model has conversational memory."""
    if not history:
        return ""

    lines = []
    for turn in history:
        speaker = "Student" if turn.get("role") == "user" else "Vidya"
        text = (turn.get("text") or "").strip()
        if text:
            lines.append(f"{speaker}: {text}")

    if not lines:
        return ""

    return (
        "\n=== CONVERSATION SO FAR (for context — do not repeat the greeting) ===\n"
        + "\n".join(lines)
        + "\n"
    )


EXERCISE_LOOKUP_INSTRUCTIONS = """
The TEXTBOOK CONTEXT below was looked up directly by exercise/question number,
not by topic search — it contains the exact textbook question(s) the student
asked about.
1. Briefly quote/restate the exact question text first, so the student can
   confirm you found the right one (this is different from repeating their
   conversational phrasing — here it confirms which textbook problem you're
   solving).
2. Then solve it step by step following the subject instructions above.
3. If the context contains multiple questions (the exact one wasn't found),
   politely point out which questions ARE available in that exercise instead
   of guessing.
"""


def build_prompt(
    question: str,
    chunks: list[str],
    subject: str = "science",
    mode: str = "easy",
    history: list[dict] | None = None,
    is_exercise_lookup: bool = False,
) -> str:
    """
    Assemble the full prompt for Gemini.

    Args:
        question           : the student's question
        chunks              : list of retrieved textbook passage strings
        subject             : "maths" | "science" | "social"
        mode                : "easy" | "detailed"
        history             : prior turns in this conversation, e.g.
                              [{"role": "user", "text": "..."}, {"role": "ai", "text": "..."}]
        is_exercise_lookup  : True when `chunks` came from a direct
                              "Exercise X.Y, Question N" metadata lookup
                              rather than semantic search

    Returns:
        A single formatted prompt string.
    """
    # Fallback if subject key not found
    subject_instr = SUBJECT_INSTRUCTIONS.get(subject, SUBJECT_INSTRUCTIONS["science"])
    mode_modifier = MODE_MODIFIERS.get(mode, MODE_MODIFIERS["easy"])
    exercise_instr = EXERCISE_LOOKUP_INSTRUCTIONS.strip() if is_exercise_lookup else ""

    # Join retrieved context chunks with separator
    context_block = "\n\n---\n\n".join(
        [f"[Passage {i+1}]\n{chunk.strip()}" for i, chunk in enumerate(chunks)]
    ) if chunks else "No specific textbook passage found."

    history_block = _build_history_block(history)

    prompt = f"""=== ROLE ===
You are "GemTutor", a warm and patient AI tutor for Tamil Nadu State Board students (Classes 8–10).
Your goal is to make learning easy, fun, and clear.
This is an ONGOING conversation — only greet the student once at the very start, and use the conversation
history below to understand follow-up questions (e.g. "explain that more", "why?", "give another example").
NEVER restate, paraphrase, or summarise the student's question back to them before answering
(e.g. do NOT start with "You're asking about...", "You are asking why...", "Great question about...").
Jump straight into the answer, the way a teacher naturally would mid-conversation.

=== SUBJECT-SPECIFIC INSTRUCTIONS ===
{subject_instr.strip()}
{("\n=== EXERCISE LOOKUP INSTRUCTIONS ===\n" + exercise_instr + "\n") if exercise_instr else ""}
=== LANGUAGE MODE ===
{mode_modifier}

=== TEXTBOOK CONTEXT (use this to answer) ===
{context_block}
{history_block}
=== STUDENT'S QUESTION ===
{question.strip()}

=== YOUR ANSWER ===
(Answer below — follow the subject instructions exactly)
"""

    return prompt
