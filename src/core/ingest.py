"""
Document ingestion orchestrator.
Loads PDFs from a library, chunks, embeds (OpenAI), and stores in ChromaDB.
"""

import hashlib
import logging
import time
from pathlib import Path
from tqdm import tqdm

from src.core.config import LIBRARIES, EMBEDDING_BATCH_SIZE
from src.core.pdf_loader import extract_pdf, find_pdfs
from src.core.chunker import chunk_pages, build_splitter
from src.core.embedder import embed_texts
from src.core.vector_store import add_chunks, collection_stats

logger = logging.getLogger(__name__)


def _make_chunk_id(library_key: str, source_file: str, chunk_index: int) -> str:
    """Deterministic ID so re-runs upsert instead of duplicating."""
    raw = f"{library_key}::{source_file}::chunk_{chunk_index}"
    return hashlib.md5(raw.encode()).hexdigest()


def ingest_library(library_key: str) -> dict:
    """
    Ingest all PDFs for a single library.

    Returns a summary dict:
        library, total_files, total_chunks, errors, elapsed_seconds
    """
    lib = LIBRARIES[library_key]
    lib_path: Path = lib["path"]
    logger.info("═══ Ingesting library: %s (%s) ═══", lib["name"], lib_path)

    pdf_files = find_pdfs(lib_path)
    if not pdf_files:
        logger.warning("No PDFs found in %s", lib_path)
        return {"library": library_key, "total_files": 0, "total_chunks": 0, "errors": [], "elapsed_seconds": 0}

    splitter = build_splitter()
    all_chunks: list[dict] = []
    errors: list[str] = []
    start_time = time.time()

    for pdf_path in tqdm(pdf_files, desc=f"  Loading {lib['name']}", unit="file"):
        try:
            pages = extract_pdf(pdf_path, library_key)
            if not pages:
                errors.append(f"No text: {pdf_path.name}")
                continue
            chunks = chunk_pages(pages, splitter)
            all_chunks.extend(chunks)
        except Exception as e:
            errors.append(f"Error {pdf_path.name}: {e}")
            logger.error("Failed to process %s: %s", pdf_path.name, e)

    if not all_chunks:
        logger.warning("No chunks produced for %s", library_key)
        return {"library": library_key, "total_files": len(pdf_files), "total_chunks": 0, "errors": errors, "elapsed_seconds": time.time() - start_time}

    # Build IDs, texts, metadatas
    ids = [_make_chunk_id(library_key, c["metadata"]["source_file"], c["metadata"]["chunk_index"]) for c in all_chunks]
    texts = [c["text"] for c in all_chunks]
    metadatas = [c["metadata"] for c in all_chunks]

    # Embed in batches
    logger.info("  Embedding %d chunks via OpenAI ...", len(texts))
    embeddings = embed_texts(texts, batch_size=EMBEDDING_BATCH_SIZE)

    # Store
    logger.info("  Storing in ChromaDB collection '%s' ...", library_key)
    add_chunks(library_key, ids, embeddings, texts, metadatas)

    elapsed = time.time() - start_time
    stats = collection_stats(library_key)

    summary = {
        "library": library_key,
        "library_name": lib["name"],
        "total_files": len(pdf_files),
        "total_chunks": len(all_chunks),
        "collection_count": stats["count"],
        "errors": errors,
        "elapsed_seconds": round(elapsed, 1),
    }

    logger.info(
        "  ✓ Done: %d files → %d chunks in %.1fs  (collection has %d total)",
        summary["total_files"],
        summary["total_chunks"],
        summary["elapsed_seconds"],
        summary["collection_count"],
    )
    if errors:
        logger.warning("  ⚠ %d errors: %s", len(errors), errors[:5])

    return summary
