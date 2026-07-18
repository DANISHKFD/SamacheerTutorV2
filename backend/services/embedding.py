# ============================================================
# services/embedding.py — Local free embeddings via sentence-transformers
#
# Uses the "all-MiniLM-L6-v2" model (≈80 MB, 384-dim vectors).
# This model is completely FREE and works offline after first download.
# ============================================================

import numpy as np
from sentence_transformers import SentenceTransformer

# ── Model selection ───────────────────────────────────────
# all-MiniLM-L6-v2: fast, 384-dim, great for semantic similarity
MODEL_NAME = "all-MiniLM-L6-v2"

# Lazy-load: the model is large, so load it once and reuse
_model = None


def _get_model() -> SentenceTransformer:
    """Return a cached SentenceTransformer model instance."""
    global _model
    if _model is None:
        print(f"[Embedding] Loading model '{MODEL_NAME}' … (first run may take a moment)")
        try:
            _model = SentenceTransformer(MODEL_NAME)
        except Exception as e:
            # Most common cause: no internet on first run, when the model
            # still needs to be downloaded from Hugging Face. Re-raise with
            # a message that actually points at the fix, since the raw
            # exception from deep inside the download stack usually doesn't.
            raise RuntimeError(
                f"Could not load the embedding model '{MODEL_NAME}'. This is usually "
                "caused by no internet connection on first run (the model needs to "
                f"download once, ~80MB). Original error: {e}"
            ) from e
        print(f"[Embedding] Model loaded. Embedding dim: {_model.get_sentence_embedding_dimension()}")
    return _model


def get_embeddings(texts: list[str]) -> np.ndarray:
    """
    Convert a list of strings into a 2-D numpy array of float32 embeddings.

    Args:
        texts : list of strings to embed

    Returns:
        np.ndarray of shape (len(texts), 384)
    """
    if not texts:
        raise ValueError("texts list must not be empty")

    model = _get_model()

    # encode() returns a numpy array automatically
    vectors = model.encode(
        texts,
        batch_size=64,       # process in batches to avoid OOM on small machines
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True   # unit-length → cosine ≈ dot product ≈ L2
    )

    return vectors.astype(np.float32)
