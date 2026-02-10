"""
OpenAI embedding wrapper.
Uses text-embedding-3-large via the OpenAI API.
"""

import logging
from typing import Optional
from openai import OpenAI

from src.core.config import OPENAI_API_KEY, EMBEDDING_MODEL, EMBEDDING_BATCH_SIZE

logger = logging.getLogger(__name__)

_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


def embed_texts(texts: list[str], batch_size: int = EMBEDDING_BATCH_SIZE) -> list[list[float]]:
    """
    Embed a list of texts using OpenAI's embedding API.

    Processes in batches to stay within API limits.
    Returns a list of embedding vectors (list of floats).
    """
    client = _get_client()
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        try:
            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=batch,
            )
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)
            logger.info(
                "Embedded batch %d-%d / %d",
                i + 1,
                min(i + batch_size, len(texts)),
                len(texts),
            )
        except Exception as e:
            logger.error("Embedding failed for batch %d: %s", i, e)
            raise

    return all_embeddings


def embed_query(text: str) -> list[float]:
    """Embed a single query string."""
    client = _get_client()
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=[text],
    )
    return response.data[0].embedding
