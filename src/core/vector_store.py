"""
ChromaDB vector store — persistent, one collection per library.
"""

import logging
from pathlib import Path
from typing import Optional

import chromadb

from src.core.config import VECTOR_DB_PATH

logger = logging.getLogger(__name__)

_client: Optional[chromadb.PersistentClient] = None


def _get_client() -> chromadb.PersistentClient:
    """Lazily create a persistent ChromaDB client."""
    global _client
    if _client is None:
        Path(VECTOR_DB_PATH).mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=VECTOR_DB_PATH)
        logger.info("ChromaDB client initialized at %s", VECTOR_DB_PATH)
    return _client


def get_or_create_collection(name: str) -> chromadb.Collection:
    """Get or create a collection by name."""
    client = _get_client()
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


def add_chunks(
    collection_name: str,
    ids: list,
    embeddings: list,
    documents: list,
    metadatas: list,
) -> None:
    """
    Add embedded chunks to a ChromaDB collection.
    Upserts to avoid duplicates on re-run.
    """
    collection = get_or_create_collection(collection_name)
    # ChromaDB has an internal batch limit; upsert in groups of 5000
    batch_size = 5000
    for i in range(0, len(ids), batch_size):
        collection.upsert(
            ids=ids[i : i + batch_size],
            embeddings=embeddings[i : i + batch_size],
            documents=documents[i : i + batch_size],
            metadatas=metadatas[i : i + batch_size],
        )
    logger.info(
        "Upserted %d chunks into collection '%s'", len(ids), collection_name
    )


def search(
    collection_name: str,
    query_embedding: list,
    n_results: int = 10,
    where: Optional[dict] = None,
) -> dict:
    """
    Search a collection by query embedding.
    Returns dict with keys: ids, documents, metadatas, distances.
    """
    collection = get_or_create_collection(collection_name)
    kwargs = {
        "query_embeddings": [query_embedding],
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        kwargs["where"] = where
    return collection.query(**kwargs)


def collection_stats(collection_name: str) -> dict:
    """Return count and name for a collection."""
    collection = get_or_create_collection(collection_name)
    return {
        "name": collection_name,
        "count": collection.count(),
    }


def list_all_collections() -> list[dict]:
    """Return stats for every collection in the DB."""
    client = _get_client()
    collections = client.list_collections()
    return [
        {"name": c.name, "count": c.count()}
        for c in collections
    ]
