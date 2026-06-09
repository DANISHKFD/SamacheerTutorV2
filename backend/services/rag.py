# ============================================================
# services/rag.py — FAISS-based Retrieval-Augmented Generation
#
# Two public functions:
#   build_faiss_index(chunks)  → saves index + metadata to disk
#   search_index(query, ...)   → returns top-k relevant text chunks
# ============================================================

import os
import json
import numpy as np
import faiss

from services.embedding import get_embeddings
from config import Config


# ── Paths ─────────────────────────────────────────────────
INDEX_DIR = Config.INDEX_DIR            # e.g. backend/index/
CHUNK_FILE = os.path.join(INDEX_DIR, "chunks.json")
INDEX_FILE = os.path.join(INDEX_DIR, "faiss.index")


# ─────────────────────────────────────────────────────────
# BUILD
# ─────────────────────────────────────────────────────────

def build_faiss_index(chunks: list[dict]):
    """
    Given a list of chunk dicts like:
        [{"text": "...", "subject": "maths", "source": "ch1"}, ...]
    Compute embeddings and store a FAISS flat-L2 index on disk.
    """
    os.makedirs(INDEX_DIR, exist_ok=True)

    texts = [c["text"] for c in chunks]
    print(f"[RAG] Embedding {len(texts)} chunks …")
    vectors = get_embeddings(texts)          # shape: (N, dim)

    dim = vectors.shape[1]
    print(f"[RAG] Embedding dimension: {dim}")

    # Flat L2 index — exact nearest-neighbour, great for < 100k chunks
    index = faiss.IndexFlatL2(dim)
    index.add(vectors.astype(np.float32))

    # Persist index
    faiss.write_index(index, INDEX_FILE)

    # Persist chunk metadata (text + subject) alongside
    with open(CHUNK_FILE, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    print(f"[RAG] ✅ Index saved to {INDEX_FILE}  ({index.ntotal} vectors)")
    return index


# ─────────────────────────────────────────────────────────
# SEARCH
# ─────────────────────────────────────────────────────────

# Cache loaded index & chunks in memory so repeated calls are fast
_index_cache = None
_chunks_cache = None


def _load_index():
    """Load FAISS index and chunk metadata from disk (cached)."""
    global _index_cache, _chunks_cache

    if _index_cache is not None:
        return _index_cache, _chunks_cache

    if not os.path.exists(INDEX_FILE):
        raise FileNotFoundError(
            f"FAISS index not found at '{INDEX_FILE}'. "
            "Please run scripts/build_index.py first."
        )

    _index_cache = faiss.read_index(INDEX_FILE)
    with open(CHUNK_FILE, "r", encoding="utf-8") as f:
        _chunks_cache = json.load(f)

    print(f"[RAG] Index loaded — {_index_cache.ntotal} vectors")
    return _index_cache, _chunks_cache


def search_index(query: str, subject: str = None, top_k: int = 3) -> list[str]:
    """
    Embed the query, search FAISS, and return the top-k text chunks.

    Args:
        query   : the student's question
        subject : optional filter — only return chunks from this subject
        top_k   : number of chunks to return

    Returns:
        List of chunk text strings (most relevant first)
    """
    index, chunks = _load_index()

    # Embed the query (must match the dimension used at index-build time)
    q_vector = get_embeddings([query]).astype(np.float32)   # (1, dim)

    # Fetch more candidates if we plan to filter by subject
    fetch_k = top_k * 5 if subject else top_k
    distances, indices = index.search(q_vector, fetch_k)

    results = []
    for idx in indices[0]:
        if idx < 0 or idx >= len(chunks):
            continue
        chunk = chunks[idx]
        # Optional subject filter
        if subject and chunk.get("subject", "").lower() != subject.lower():
            continue
        results.append(chunk["text"])
        if len(results) >= top_k:
            break

    # Fall back to unfiltered if subject filter returns nothing
    if not results:
        for idx in indices[0]:
            if 0 <= idx < len(chunks):
                results.append(chunks[idx]["text"])
            if len(results) >= top_k:
                break

    return results
