# ============================================================
# utils/chunker.py — Split long text into overlapping chunks
#
# Produces chunks of 300–500 words with a small overlap so
# that context is not lost at chunk boundaries.
# ============================================================

import re


def split_into_chunks(
    text: str,
    chunk_size: int = 400,      # target words per chunk
    overlap: int = 50,          # words shared between consecutive chunks
    min_chunk: int = 50         # discard chunks shorter than this
) -> list[str]:
    """
    Split text into overlapping word-based chunks.

    Args:
        text       : the raw (cleaned) text to split
        chunk_size : target number of words per chunk
        overlap    : number of words to repeat at start of next chunk
        min_chunk  : minimum words; shorter chunks are discarded

    Returns:
        List of chunk strings.
    """
    # Collapse multiple whitespace / newlines into single space
    text = re.sub(r"\s+", " ", text).strip()

    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0

    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_words = words[start:end]

        if len(chunk_words) >= min_chunk:
            chunks.append(" ".join(chunk_words))

        # Move forward by (chunk_size - overlap) so chunks overlap
        step = max(chunk_size - overlap, 1)
        start += step

    return chunks


def chunk_by_paragraph(
    text: str,
    max_words: int = 450,
    min_words: int = 50
) -> list[str]:
    """
    Alternative strategy: split on paragraph breaks first, then
    merge short paragraphs and split oversized ones.
    Better for well-formatted textbook PDFs.

    Args:
        text      : cleaned text with newlines preserved
        max_words : split paragraphs larger than this
        min_words : merge paragraphs smaller than this

    Returns:
        List of chunk strings.
    """
    # Split on blank lines (paragraph boundaries)
    paragraphs = re.split(r"\n{2,}", text.strip())
    paragraphs = [p.strip().replace("\n", " ") for p in paragraphs if p.strip()]

    chunks = []
    buffer = []
    buffer_words = 0

    for para in paragraphs:
        para_words = para.split()

        # If a single paragraph is too large, split it with the word-based splitter
        if len(para_words) > max_words:
            # Flush buffer first
            if buffer_words >= min_words:
                chunks.append(" ".join(buffer))
            buffer, buffer_words = [], 0
            # Recursively chunk the large paragraph
            chunks.extend(split_into_chunks(para, chunk_size=max_words))
            continue

        # Check if adding this paragraph overflows the buffer
        if buffer_words + len(para_words) > max_words and buffer_words >= min_words:
            chunks.append(" ".join(buffer))
            buffer, buffer_words = [], 0

        buffer.append(para)
        buffer_words += len(para_words)

    # Don't forget the last buffer
    if buffer_words >= min_words:
        chunks.append(" ".join(buffer))

    return chunks


# ── Maths-exercise-aware chunking ──────────────────────────

_EXERCISE_HEADER_RE = re.compile(r"(?im)^\s*Exercise\s+(\d+\.\d+)\s*$")
_QUESTION_START_RE = re.compile(r"(?m)^\s*(\d{1,2})\.\s*(.*)$")

# A question buffer that grows past this many words is almost certainly
# narrative text that drifted in after the exercise's last real question
# (PDF extraction has no clean "end of exercise" marker), so we cut it
# loose and fall back to narrative mode instead of swallowing a whole chapter.
_MAX_QUESTION_WORDS = 150


def chunk_maths_exercises(text: str) -> list[dict]:
    """
    Split a maths chapter into narrative chunks plus one chunk per
    exercise question, tagged with which "Exercise X.Y" and question
    number it belongs to — so a question like "Exercise 5.8, Q3" can be
    looked up directly instead of relying on semantic search alone.

    Args:
        text : cleaned text with line breaks preserved (i.e. output of
               clean_text(), NOT the whitespace-collapsed form)

    Returns:
        List of {"text", "exercise", "question_no"} dicts. "exercise" and
        "question_no" are None for narrative (non-exercise) chunks.
    """
    narrative_buffer: list[str] = []
    narrative_chunks: list[str] = []
    exercise_chunks: list[dict] = []

    current_exercise = None
    current_question_no = None
    current_question_lines: list[str] = []

    def flush_question():
        nonlocal current_question_lines, current_question_no
        if current_exercise and current_question_no and current_question_lines:
            qtext = re.sub(r"\s+", " ", " ".join(current_question_lines)).strip()
            if qtext:
                exercise_chunks.append({
                    "text": f"[Exercise {current_exercise}, Question {current_question_no}] {qtext}",
                    "exercise": current_exercise,
                    "question_no": current_question_no,
                })
        current_question_lines = []
        current_question_no = None

    def flush_narrative():
        nonlocal narrative_buffer
        chunk_text = "\n\n".join(narrative_buffer).strip()
        if chunk_text:
            narrative_chunks.extend(chunk_by_paragraph(chunk_text))
        narrative_buffer = []

    for line in text.split("\n"):
        header_match = _EXERCISE_HEADER_RE.match(line)
        if header_match:
            flush_question()
            flush_narrative()
            current_exercise = header_match.group(1)
            continue

        if current_exercise:
            q_match = _QUESTION_START_RE.match(line)
            if q_match:
                flush_question()
                current_question_no = q_match.group(1)
                rest = q_match.group(2)
                if rest.strip():
                    current_question_lines.append(rest)
            elif current_question_no is not None:
                current_question_lines.append(line)
                word_count = sum(len(l.split()) for l in current_question_lines)
                if word_count > _MAX_QUESTION_WORDS:
                    # Likely narrative that leaked past the exercise's end.
                    flush_question()
                    current_exercise = None
                    narrative_buffer.append(line)
            # else: stray text between the "Exercise X.Y" header and its
            # first numbered question (e.g. instructions) — not useful
            # for direct lookup, so it's dropped.
        else:
            narrative_buffer.append(line)

    flush_question()
    flush_narrative()

    result = [{"text": t, "exercise": None, "question_no": None} for t in narrative_chunks]
    result.extend(exercise_chunks)
    return result
