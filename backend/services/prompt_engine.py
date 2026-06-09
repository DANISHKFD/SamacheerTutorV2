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

def build_prompt(question: str, chunks: list[str], subject: str = "science", mode: str = "easy") -> str:
    """
    Assemble the full prompt for Gemini.

    Args:
        question : the student's question
        chunks   : list of retrieved textbook passage strings
        subject  : "maths" | "science" | "social"
        mode     : "easy" | "detailed"

    Returns:
        A single formatted prompt string.
    """
    # Fallback if subject key not found
    subject_instr = SUBJECT_INSTRUCTIONS.get(subject, SUBJECT_INSTRUCTIONS["science"])
    mode_modifier = MODE_MODIFIERS.get(mode, MODE_MODIFIERS["easy"])

    # Join retrieved context chunks with separator
    context_block = "\n\n---\n\n".join(
        [f"[Passage {i+1}]\n{chunk.strip()}" for i, chunk in enumerate(chunks)]
    ) if chunks else "No specific textbook passage found."

    prompt = f"""=== ROLE ===
You are "GemTutor", a warm and patient AI tutor for Tamil Nadu State Board students (Classes 8–10).
Your goal is to make learning easy, fun, and clear.

=== SUBJECT-SPECIFIC INSTRUCTIONS ===
{subject_instr.strip()}

=== LANGUAGE MODE ===
{mode_modifier}

=== TEXTBOOK CONTEXT (use this to answer) ===
{context_block}

=== STUDENT'S QUESTION ===
{question.strip()}

=== YOUR ANSWER ===
(Answer below — follow the subject instructions exactly)
"""

    return prompt
