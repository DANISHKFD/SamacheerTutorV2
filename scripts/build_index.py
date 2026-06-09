#!/usr/bin/env python3
# ============================================================
# scripts/build_index.py
#
# PURPOSE: Convert chunks.json → embeddings → FAISS index on disk
#
# USAGE:
#   python scripts/build_index.py
#
# Run this AFTER prepare_data.py.
# Re-run whenever you update the textbook .txt files.
# ============================================================

import sys
import os
import json

# Make backend/ importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from services.rag import build_faiss_index
from config import Config

CHUNKS_FILE = os.path.join(Config.DATA_DIR, "chunks.json")


def build():
    """Load chunks.json and build the FAISS index."""

    if not os.path.exists(CHUNKS_FILE):
        print(f"[build_index] ❌ chunks.json not found at '{CHUNKS_FILE}'")
        print("  → Run 'python scripts/prepare_data.py' first.")
        sys.exit(1)

    print(f"[build_index] Loading chunks from '{CHUNKS_FILE}' …")
    with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    if not chunks:
        print("[build_index] ❌ chunks.json is empty. Add textbook content to data/*.txt first.")
        sys.exit(1)

    print(f"[build_index] Found {len(chunks)} chunks. Building FAISS index …")
    index = build_faiss_index(chunks)

    print(f"\n[build_index] ✅ Done! Index contains {index.ntotal} vectors.")
    print(f"   Files saved in: {Config.INDEX_DIR}")
    print("   You can now start the Flask backend with:  python backend/app.py")


if __name__ == "__main__":
    build()
