"""
Context builder — groups retrieved chunks by authority rank and formats
them into a structured string for the LLM system prompt.
"""

import re
from collections import defaultdict
from pathlib import Path

from src.core.config import AUTHORITY_RANK, COLLECTION_TO_AGENCY
from src.core.retriever import RetrievedChunk


def _section_ref(source_file: str) -> str:
    """
    Derive a section reference from a PDF filename.

    Examples:
        RCW_59.18.200.pdf          →  § 59.18.200   (RCW uses periods)
        WAC_365-04_Description.pdf →  § 365-04      (WAC uses hyphens)
        SMC_23.76.004.pdf          →  § 23.76.004
        State_v_Smith.pdf          →  § State_v_Smith
    """
    stem = Path(source_file).stem
    # Capture digits, periods, and hyphens — WAC uses hyphens (e.g. WAC_365-04_...),
    # RCW uses periods (e.g. RCW_59.18_...). Stop at the first underscore after the number.
    m = re.match(r"^[A-Z_]+_([\d.\-]+)", stem)
    if m:
        return f"§ {m.group(1)}"
    return f"§ {stem}"


def build_context(chunks: list) -> str:
    """
    Build an authority-grouped context block for the LLM.

    Groups chunks by agency label, orders groups by AUTHORITY_RANK,
    and formats each chunk as a numbered [Source N] entry.
    """
    if not chunks:
        return "(No relevant documents found.)"

    by_agency: dict = defaultdict(list)
    for c in chunks:
        agency = COLLECTION_TO_AGENCY.get(c.library, c.library)
        by_agency[agency].append(c)

    agencies_sorted = sorted(
        by_agency.keys(),
        key=lambda a: AUTHORITY_RANK.get(a, 99),
    )

    blocks = []
    source_idx = 1
    for agency in agencies_sorted:
        rank = AUTHORITY_RANK.get(agency, 99)
        blocks.append(f"=== AGENCY: {agency} (Authority Level {rank}) ===\n")
        for c in by_agency[agency]:
            section = _section_ref(c.source_file)
            blocks.append(
                f"[Source {source_idx}] {agency} — {c.library}, {section}, p.{c.page_number}\n"
                f'"{c.text}"'
            )
            source_idx += 1

    blocks.append("\n=== END OF RETRIEVED CONTEXT ===")
    return "\n\n".join(blocks)


def build_sources_metadata(chunks: list) -> list:
    """
    Build the sources list sent to the frontend via SSE.

    Schema is identical to the legacy path so the frontend needs no changes.
    """
    return [
        {
            "source_file": c.source_file,
            "library": c.library,
            "page_number": c.page_number,
            "score": round(c.score, 3),
            "text": c.text,
        }
        for c in chunks
    ]
