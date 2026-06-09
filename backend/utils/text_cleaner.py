# ============================================================
# utils/text_cleaner.py — Clean raw textbook text
#
# Removes headers/footers, page numbers, extra whitespace,
# and other artefacts common in PDF-extracted text.
# ============================================================

import re
import unicodedata


def clean_text(text: str) -> str:
    """
    Full pipeline: normalise → remove artefacts → clean whitespace.

    Args:
        text : raw string from a text file or PDF extraction

    Returns:
        Cleaned string suitable for chunking and embedding.
    """
    text = _normalise_unicode(text)
    text = _remove_page_numbers(text)
    text = _remove_headers_footers(text)
    text = _remove_special_chars(text)
    text = _fix_whitespace(text)
    return text


# ── Helper functions ──────────────────────────────────────

def _normalise_unicode(text: str) -> str:
    """Convert Unicode characters to their closest ASCII equivalents."""
    # NFC normalisation handles combining characters
    text = unicodedata.normalize("NFC", text)
    # Replace common Unicode quotes / dashes with ASCII equivalents
    replacements = {
        "\u2018": "'", "\u2019": "'",   # curly single quotes
        "\u201c": '"', "\u201d": '"',   # curly double quotes
        "\u2013": "-", "\u2014": "-",   # en-dash, em-dash
        "\u00a0": " ",                   # non-breaking space
        "\u2022": "*",                   # bullet point
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text


def _remove_page_numbers(text: str) -> str:
    """Remove isolated page numbers like '42', 'Page 42', '— 42 —'."""
    # Match lines that are purely a number or "Page N"
    text = re.sub(r"(?m)^[\s\-]*[Pp]age\s+\d+[\s\-]*$", "", text)
    text = re.sub(r"(?m)^\s*\d{1,4}\s*$", "", text)
    return text


def _remove_headers_footers(text: str) -> str:
    """
    Remove repeating header/footer patterns common in Samacheer books,
    e.g. chapter titles repeated on every page, 'Samacheer Kalvi' watermarks.
    """
    patterns = [
        r"Samacheer Kalvi.*?\n",
        r"Class\s+\d+\s+[-–]\s+\w+.*?\n",
        r"Tamil Nadu\s+State Board.*?\n",
        r"NCERT.*?\n",
        r"www\.\S+",                   # any URL
        r"©.*?\n",                     # copyright line
    ]
    for pattern in patterns:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)
    return text


def _remove_special_chars(text: str) -> str:
    """Remove non-printable control characters but keep newlines."""
    # Keep printable ASCII + common punctuation; strip control chars
    text = re.sub(r"[^\x20-\x7E\n\t]", " ", text)
    return text


def _fix_whitespace(text: str) -> str:
    """Collapse multiple spaces/tabs; normalise multiple newlines."""
    text = re.sub(r"[ \t]+", " ", text)           # multiple spaces → one
    text = re.sub(r"\n{3,}", "\n\n", text)         # 3+ newlines → two
    text = re.sub(r"[ \t]*\n[ \t]*", "\n", text)  # trailing spaces on lines
    return text.strip()
