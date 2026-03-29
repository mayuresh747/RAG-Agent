"""
Two-pass evidence selection — guarantees balanced agency representation
in the final chunk set passed to the LLM.
"""

import logging
from collections import defaultdict

from src.core.config import COLLECTION_TO_AGENCY
from src.core.retriever import RetrievedChunk
from src.core.analyzer import AnalysisResult

logger = logging.getLogger(__name__)


def _guaranteed_slots(agency: str, relevance: int, mode: str) -> int:
    """
    Pass 1 slot allocation:
    - Mode A: 0 (pure reranker)
    - COURT in conflict modes: always 2
    - relevance=3: 2 slots
    - relevance=2: 1 slot
    - relevance=1: 0 slots
    """
    if mode == "A":
        return 0
    if agency == "COURT":
        return 2
    if relevance >= 3:
        return 2
    if relevance == 2:
        return 1
    return 0


def select_evidence(chunks: list, analysis: AnalysisResult, top_k: int) -> list:
    """
    Select final evidence set using two-pass strategy.

    Pass 1: Reserve guaranteed slots per agency (by highest rerank_score).
    Pass 2: Fill remaining slots with globally best unreserved chunks.
    Coverage check: every non-COURT agency in scope must have ≥1 chunk;
                    if not, force-insert its best-scoring chunk with a warning.

    Args:
        chunks: Reranked list (sorted descending by rerank_score).
        analysis: Output from analyze_query().
        top_k: Target result size.

    Returns:
        List of selected chunks (may slightly exceed top_k if coverage check fires).
    """
    # Group by agency label (not collection name)
    by_agency: dict = defaultdict(list)
    for c in chunks:
        agency = COLLECTION_TO_AGENCY.get(c.library, c.library)
        by_agency[agency].append(c)

    selected = []
    selected_ids: set = set()

    # Pass 1 — guaranteed slots
    for agency in analysis.agencies_in_scope:
        slots = _guaranteed_slots(
            agency,
            analysis.agency_relevance.get(agency, 1),
            analysis.mode,
        )
        for c in by_agency.get(agency, [])[:slots]:
            if id(c) not in selected_ids:
                selected.append(c)
                selected_ids.add(id(c))

    # Pass 2 — global fill
    remaining = top_k - len(selected)
    if remaining > 0:
        unreserved = sorted(
            [c for c in chunks if id(c) not in selected_ids],
            key=lambda c: c.rerank_score,
            reverse=True,
        )
        for c in unreserved[:remaining]:
            selected.append(c)
            selected_ids.add(id(c))

    # Coverage check — every non-COURT agency must appear
    for agency in analysis.agencies_in_scope:
        if agency == "COURT":
            continue
        present = any(
            COLLECTION_TO_AGENCY.get(c.library, c.library) == agency
            for c in selected
        )
        if not present:
            candidates = by_agency.get(agency, [])
            if candidates:
                logger.warning(
                    "Coverage check: force-inserting chunk for %s (zero representation)", agency
                )
                selected.append(candidates[0])

    return selected
