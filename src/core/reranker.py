"""
Cross-encoder reranker — lazy-loads ms-marco-MiniLM-L-6-v2 on first use.
Accepts RetrievedChunk list, returns same list sorted by rerank_score,
truncated to top_k.
"""

import logging
from typing import Optional

from src.core.retriever import RetrievedChunk

logger = logging.getLogger(__name__)

_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class _LegalReranker:
    """Wraps CrossEncoder with lazy initialization."""

    def __init__(self):
        self._model = None

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder
            logger.info("Loading cross-encoder model: %s", _MODEL_NAME)
            self._model = CrossEncoder(_MODEL_NAME)
        return self._model

    def rerank(self, query: str, chunks: list, top_k: int) -> list:
        """
        Score and rank chunks by cross-encoder relevance.

        Scores are raw logits (~-10 to +10). They are NOT cosine similarities
        and must not be filtered by min_score thresholds.
        """
        if not chunks:
            return []
        model = self._get_model()
        pairs = [(query, c.text) for c in chunks]
        scores = model.predict(pairs)
        for chunk, score in zip(chunks, scores):
            chunk.rerank_score = float(score)
        ranked = sorted(chunks, key=lambda c: c.rerank_score, reverse=True)
        return ranked[:top_k]

    def warmup(self):
        """Pre-load model to avoid cold-start on first request."""
        self._get_model()
        logger.info("Reranker warmed up.")


_reranker = _LegalReranker()


def rerank(query: str, chunks: list, top_k: int) -> list:
    """Public interface — delegates to module-level singleton."""
    return _reranker.rerank(query, chunks, top_k)


def warmup():
    """Call from FastAPI startup to pre-load the cross-encoder."""
    _reranker.warmup()
