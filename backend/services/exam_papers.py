# ============================================================
# services/exam_papers.py — Past exam paper ingestion + matching
#
# Lets a teacher/student upload a PDF of a previous exam question
# paper. We extract the individual questions, embed them, and store
# them in a small FAISS index (separate from the textbook RAG index)
# tagged by subject + class. Later, when a student asks a question in
# chat, we check whether it closely matches one of these previously
# indexed questions so the frontend can flag it as "asked before".
# ============================================================

import os
import re
import json

import numpy as np
import faiss
from pypdf import PdfReader

from services.embedding import get_embeddings
from config import Config

# ── Paths ─────────────────────────────────────────────────
EXAM_INDEX_DIR = Config.INDEX_DIR
EXAM_QUESTIONS_FILE = os.path.join(EXAM_INDEX_DIR, "exam_questions.json")
EXAM_INDEX_FILE = os.path.join(EXAM_INDEX_DIR, "exam_questions.index")

# FAISS's IndexFlatL2 returns SQUARED L2 distance. Our embeddings are
# unit-normalized (see embedding.py), so squared L2 = 2 - 2*cos_sim:
# 0 = identical, 2 = unrelated, 4 = opposite. Paraphrases of the same
# question typically land under ~0.55 (cos_sim ≳ 0.72); unrelated
# questions land well above 1. Tune this if matches feel too loose/strict.
IMPORTANT_QUESTION_DISTANCE_THRESHOLD = 0.55

MIN_QUESTION_CHARS = 12
MAX_QUESTION_CHARS = 600

# Matches a leading question number like "1.", "12)", "Q3.", "Question 4 -"
# at the start of a line — how most past-paper PDFs separate questions.
_QUESTION_NUMBER_RE = re.compile(
    r"(?:^|\n)\s*(?:Q(?:uestion)?\.?\s*)?(\d{1,2})\s*[\.\)]\s+",
    re.IGNORECASE,
)


def extract_text_from_pdf(file_stream) -> str:
    """Extract raw text from an uploaded PDF file-like object."""
    reader = PdfReader(file_stream)
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def split_into_questions(raw_text: str) -> list[str]:
    """
    Heuristically split a past exam paper's raw text into individual
    questions, using leading question numbers ("1.", "Q2)", ...) as
    boundaries. Not perfect for every paper layout, but good enough to
    catch the recurring questions that matter for exam-prep flagging.
    """
    matches = list(_QUESTION_NUMBER_RE.finditer(raw_text))
    if not matches:
        return []

    questions = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw_text)
        text = " ".join(raw_text[start:end].split())  # collapse whitespace/newlines
        if len(text) >= MIN_QUESTION_CHARS:
            questions.append(text[:MAX_QUESTION_CHARS])

    return questions


# ─────────────────────────────────────────────────────────
# INDEX (cached in memory, persisted to disk)
# ─────────────────────────────────────────────────────────

_index_cache = None
_questions_cache = None


def _load_or_create_index(dim: int):
    global _index_cache, _questions_cache

    if _index_cache is not None:
        return _index_cache, _questions_cache

    if os.path.exists(EXAM_INDEX_FILE) and os.path.exists(EXAM_QUESTIONS_FILE):
        try:
            _index_cache = faiss.read_index(EXAM_INDEX_FILE)
            with open(EXAM_QUESTIONS_FILE, "r", encoding="utf-8") as f:
                _questions_cache = json.load(f)
            return _index_cache, _questions_cache
        except Exception as e:
            # A corrupted/partially-written index file shouldn't permanently
            # break uploads and important-question matching — fall through
            # and start a fresh index instead. Past exam papers will need
            # re-uploading, but that's recoverable; a crash loop isn't.
            print(f"[ExamPapers] Could not load existing exam index ({e}); starting a fresh one.")

    _index_cache = faiss.IndexFlatL2(dim)
    _questions_cache = []
    return _index_cache, _questions_cache


def _save_index():
    os.makedirs(EXAM_INDEX_DIR, exist_ok=True)
    faiss.write_index(_index_cache, EXAM_INDEX_FILE)
    with open(EXAM_QUESTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(_questions_cache, f, ensure_ascii=False, indent=2)


def _closest_same_group(vector: np.ndarray, subject: str, standard: str):
    """Return the smallest distance to an already-indexed question with the
    same subject+standard, or None if the index is empty / has no match."""
    index, meta = _index_cache, _questions_cache
    if index.ntotal == 0:
        return None

    fetch_k = min(index.ntotal, 8)
    distances, indices = index.search(vector.reshape(1, -1).astype(np.float32), fetch_k)

    best = None
    for dist, idx in zip(distances[0], indices[0]):
        if idx < 0 or idx >= len(meta):
            continue
        chunk = meta[idx]
        if chunk["subject"] == subject and chunk["standard"] == standard:
            if best is None or dist < best:
                best = float(dist)
    return best


def add_exam_questions(questions: list[str], subject: str, standard: str, source: str) -> int:
    """
    Embed and append `questions` to the past-exam-papers index, tagged with
    subject/standard/source. Near-duplicates already indexed for the same
    subject+standard (papers often repeat questions across years) are
    skipped. Returns the number of questions actually added.
    """
    if not questions:
        return 0

    vectors = get_embeddings(questions)
    _load_or_create_index(vectors.shape[1])

    added = 0
    for text, vector in zip(questions, vectors):
        best = _closest_same_group(vector, subject, standard)
        if best is not None and best < IMPORTANT_QUESTION_DISTANCE_THRESHOLD:
            continue

        _index_cache.add(vector.reshape(1, -1).astype(np.float32))
        _questions_cache.append({"text": text, "subject": subject, "standard": standard, "source": source})
        added += 1

    if added:
        _save_index()

    return added


def list_exam_papers() -> list[dict]:
    """
    Return a summary of every uploaded past exam paper, grouped by
    (source file, subject, class), with a question count per group — for
    the "Uploaded Papers" list in Settings. Reads the metadata file
    directly rather than going through the cache, so listing never needs
    to load the embedding model or FAISS index.
    """
    if not os.path.exists(EXAM_QUESTIONS_FILE):
        return []

    try:
        with open(EXAM_QUESTIONS_FILE, "r", encoding="utf-8") as f:
            meta = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"[ExamPapers] Could not read exam questions metadata ({e}); reporting no papers.")
        return []

    groups = {}
    for entry in meta:
        key = (entry.get("source"), entry.get("subject"), entry.get("standard"))
        groups[key] = groups.get(key, 0) + 1

    papers = [
        {
            "source": source,
            "subject": subject,
            "standard": standard,
            "class": (standard or "").replace("standard_", ""),
            "question_count": count,
        }
        for (source, subject, standard), count in groups.items()
    ]
    papers.sort(key=lambda p: (p["subject"] or "", p["class"] or "", p["source"] or ""))
    return papers


def is_important_question(question: str, subject: str, standard: str) -> bool:
    """
    Return True if `question` closely matches a question from a previously
    uploaded past exam paper for the same subject + class.
    """
    if not question or not os.path.exists(EXAM_INDEX_FILE):
        return False

    vector = get_embeddings([question])[0]
    _load_or_create_index(vector.shape[0])

    best = _closest_same_group(vector, subject, standard)
    return best is not None and best < IMPORTANT_QUESTION_DISTANCE_THRESHOLD
