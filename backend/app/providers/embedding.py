"""EmbeddingProvider implementations (Subsystem 9).

Default: HashingTfidfEmbedder — a deterministic hashing vectorizer (no model
download, fully offline). Optional: SentenceTransformerEmbedder for real
semantic embeddings when the package + weights are available.
"""

from __future__ import annotations

import hashlib
import math
import re

from .base import EmbeddingProvider

_TOKEN_RE = re.compile(r"[a-z0-9_]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _stable_hash(token: str) -> int:
    """Process-independent hash (Python's builtin hash() is randomized)."""
    digest = hashlib.md5(token.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


class HashingTfidfEmbedder(EmbeddingProvider):
    """Hashing bag-of-words with sublinear TF and L2 normalization."""

    name = "hashing"

    def __init__(self, dim: int = 256):
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        counts: dict[int, float] = {}
        for tok in _tokenize(text):
            idx = _stable_hash(tok) % self.dim
            counts[idx] = counts.get(idx, 0.0) + 1.0
        for idx, c in counts.items():
            vec[idx] = 1.0 + math.log(c)  # sublinear TF
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


class SentenceTransformerEmbedder(EmbeddingProvider):
    """Optional real semantic embeddings (drop-in)."""

    name = "sentence_transformer"

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer  # noqa: F401

        self._model = SentenceTransformer(model_name)
        self.dim = int(self._model.get_sentence_embedding_dimension())

    def embed(self, text: str) -> list[float]:
        v = self._model.encode([text], normalize_embeddings=True)[0]
        return [float(x) for x in v]
