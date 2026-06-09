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
