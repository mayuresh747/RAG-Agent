"""
Multi-agent retrieval orchestrator.

Pipeline (7 steps):
    1. analyze_query()     — classify intent, select agencies
    2. plan_retrieval()    — compute per-agency fetch budgets
    3. embed_query()       — single embedding shared across all agencies
    4. ThreadPoolExecutor  — parallel vector_search() per agency
    5. rerank()            — cross-encoder scoring
    6. select_evidence()   — two-pass selection + pair coverage
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.core.analyzer import analyze_query
from src.core.planner import plan_retrieval, AgencyTask
from src.core.embedder import embed_query
from src.core.reranker import rerank
from src.core.evidence import select_evidence
from src.core.retriever import RetrievedChunk, RetrievalResult
from src.core.vector_store import search as vector_search

logger = logging.getLogger(__name__)


def _fetch_agency_chunks(task: AgencyTask, query_vector: list, min_score: float) -> list:
    """
    Fetch chunks for one agency from ChromaDB and apply cosine min_score filter.

    min_score is a cosine similarity threshold (0-1). Applied BEFORE the cross-encoder.
    ChromaDB returns distances; cosine similarity = 1 - distance.
    """
    result = vector_search(task.collection, query_vector, n_results=task.budget)
    ids = result.get("ids", [[]])[0]
    docs = result.get("documents", [[]])[0]
    metas = result.get("metadatas", [[]])[0]
    dists = result.get("distances", [[]])[0]

    chunks = []
    for doc_text, meta, dist in zip(docs, metas, dists):
        score = 1.0 - float(dist)
        if score < min_score:
            continue
        chunks.append(RetrievedChunk(
            text=doc_text,
            score=score,
            library=task.collection,
            source_file=meta.get("source_file", ""),
            page_number=int(meta.get("page_number", 0)),
            title=meta.get("title", ""),
            chunk_index=int(meta.get("chunk_index", 0)),
        ))
    return chunks


def multi_agent_retrieve(query: str, min_score: float = 0.1) -> RetrievalResult:
    """
    Run the full multi-agent retrieval pipeline.

    Args:
        query:     User message.
        min_score: Cosine similarity threshold applied during parallel retrieval
                   (before cross-encoder). Default 0.1 — lower than legacy 0.25
                   to give the cross-encoder more material to work with.

    Returns:
        RetrievalResult with chunks sorted by evidence selection priority.
    """
    # Step 1: classify query intent
    analysis = analyze_query(query)
    logger.info("Query mode=%s agencies=%s top_k=%d", analysis.mode, analysis.agencies_in_scope, analysis.top_k)

    # Step 2: compute per-agency budgets
    tasks = plan_retrieval(analysis)

    # Step 3: single embedding shared across all agencies
    query_vector = embed_query(query)

    # Step 4: parallel vector search
    # Guard: LLM could hallucinate an empty agencies_in_scope; min(0, 8)=0 → ValueError
    if not tasks:
        return RetrievalResult(query=query, chunks=[], libraries_searched=[], total_candidates=0)

    all_chunks: list = []
    max_workers = min(len(tasks), 8)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_task = {
            executor.submit(_fetch_agency_chunks, task, query_vector, min_score): task
            for task in tasks
        }
        for future in as_completed(future_to_task):
            try:
                all_chunks.extend(future.result())
            except Exception as exc:
                task = future_to_task[future]
                logger.error("Retrieval failed for %s: %s", task.agency, exc)

    logger.info("Fetched %d candidates across %d agencies", len(all_chunks), len(tasks))

    # Step 5: cross-encoder reranking (wider window for evidence selector)
    reranked = rerank(query, all_chunks, top_k=analysis.top_k * 2)

    # Step 6: two-pass evidence selection
    final_chunks = select_evidence(reranked, analysis, top_k=analysis.top_k)

    return RetrievalResult(
        query=query,
        chunks=final_chunks,
        libraries_searched=[t.collection for t in tasks],
        total_candidates=len(all_chunks),
    )
