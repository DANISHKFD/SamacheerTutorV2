#!/usr/bin/env python3
# ============================================================
# scripts/prepare_data.py
#
# PURPOSE: Load raw textbook .txt files → clean → chunk → save JSON
#
# USAGE:
#   python scripts/prepare_data.py
#
# INPUT:  data/maths.txt, data/science.txt, data/social.txt
# OUTPUT: data/chunks.json
#
# Add your own textbook content to the .txt files before running.
# ============================================================

import sys
import os
import json

# Make sure backend/ modules are importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from utils.text_cleaner import clean_text
from utils.chunker import chunk_by_paragraph, chunk_maths_exercises
from config import Config

# ── Settings ──────────────────────────────────────────────
DATA_DIR   = Config.DATA_DIR
OUTPUT_FILE = os.path.join(DATA_DIR, "chunks.json")

# Map filename → subject label used for filtering in RAG
# Map standard -> subject -> filename
BOOKS = {
    "standard_10": {
        "maths":   "tenmath.txt",
        "science": "tenscience.txt",
        "social":  "tensst.txt",
    },
    "standard_9": {
        "maths":   "ninemath.txt",
        "science": "ninescience.txt",
        "social":  "ninesst.txt",
    },
    "standard_8": {
        "maths":   "eightmaths.txt",
        "science": "eightscience.txt",
        "social":  "eightsst.txt",
    }
}


def prepare(chunk_size: int = 400, overlap: int = 50):
    """Run the full prepare pipeline and save chunks.json."""
    os.makedirs(DATA_DIR, exist_ok=True)
    all_chunks = []

    # Loop through standards first, then subjects
    for standard, subjects in BOOKS.items():
        for subject, filename in subjects.items():
            filepath = os.path.join(DATA_DIR, filename)

            # Create empty placeholder files if they don't exist yet
            if not os.path.exists(filepath):
                print(f"[prepare] ⚠️  '{filepath}' not found — creating empty placeholder.")
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(f"# {standard.title()} {subject.title()} textbook content goes here.\n")
                continue

            print(f"[prepare] Reading '{filepath}' …")
            with open(filepath, "r", encoding="utf-8") as f:
                raw_text = f.read()

            # Clean the raw text
            cleaned = clean_text(raw_text)
            print(f"[prepare]   → Cleaned: {len(cleaned.split())} words")

            # Maths chapters get exercise/question-aware chunking so a
            # question like "Exercise 5.8, Q3" can be looked up directly.
            # Other subjects use the plain paragraph chunker.
            if subject == "maths":
                chunks = chunk_maths_exercises(cleaned)
                n_exercise = sum(1 for c in chunks if c["exercise"])
                print(f"[prepare]   → Created {len(chunks)} chunks ({n_exercise} exercise questions)")
            else:
                chunks = [
                    {"text": t, "exercise": None, "question_no": None}
                    for t in chunk_by_paragraph(cleaned, max_words=chunk_size)
                ]
                print(f"[prepare]   → Created {len(chunks)} chunks")

            # Build chunk metadata dicts
            for i, chunk in enumerate(chunks):
                all_chunks.append({
                    "text":        chunk["text"],
                    "standard":    standard,  # Added standard to metadata
                    "subject":     subject,
                    "source":      filename,
                    "exercise":    chunk["exercise"],
                    "question_no": chunk["question_no"],
                    # Updated chunk_id to prevent duplicates across standards
                    "chunk_id": f"{standard}_{subject}_{i:04d}"
                })

    # Save to JSON
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    print(f"\n[prepare] ✅ Saved {len(all_chunks)} total chunks to '{OUTPUT_FILE}'")
    return all_chunks

if __name__ == "__main__":
    prepare()
