"""
Query intent analyzer — classifies user query into mode A-D and identifies
relevant agencies using a fast LLM call.
"""

import json
import logging
import re
from dataclasses import dataclass, field

from openai import OpenAI

from src.core.config import OPENAI_API_KEY, LLM_FAST, COLLECTION_MAP, LIBRARIES

logger = logging.getLogger(__name__)


def _build_classify_prompt() -> str:
    """Build the classifier prompt with live agency descriptions from config."""
    agency_lines = "\n".join(
        f"- {label}: {LIBRARIES[collection]['description']}"
        for label, collection in COLLECTION_MAP.items()
    )
    return f"""\
You are a query intent classifier for a Washington State legal research system.

Available agencies and what their documents cover:
{agency_lines}

── MODE (pick exactly one) ───────────────────────────────────────────────────
A — Factual lookup: user wants a specific rule, definition, or requirement from
    one agency. No comparison or conflict requested. Example: "What is the RCW
    notice period for eviction?"
B — Named conflict: user explicitly names 2-3 agencies and asks how they differ
    or conflict. Example: "How does WAC conflict with SMC on stormwater?"
C — Topic conflict: user describes a scenario (building type, use, activity)
    that likely touches multiple agencies, but doesn't name them. You select
    the relevant agencies. Example: "What conflicts exist for my apartment's
    EV charging installation?"
D — Full audit: user asks for a comprehensive development scenario audit across
    all applicable agencies. Example: "Do a full code audit for a new mixed-use
    building in Seattle."

── AGENCY_RELEVANCE scale ────────────────────────────────────────────────────
3 = Core to answering this query. This agency almost certainly has directly
    applicable rules. Include in guaranteed retrieval slots.
2 = Likely relevant. Probably has related rules worth checking.
1 = Peripheral. Include only if the user's topic could indirectly touch this
    agency. Omit if truly unrelated.
Omit agencies entirely if they have no plausible connection to the query topic.

── FIELDS TO RETURN ──────────────────────────────────────────────────────────
- "mode": one of "A", "B", "C", "D" per the rules above
- "agencies_in_scope": list of agency labels (only those with relevance >= 1)
- "agency_relevance": dict mapping each agency in agencies_in_scope to 1, 2, or 3
- "top_k": integer — use 12 for A, choose 16-20 for B, choose 24-32 for C
  (higher end if many agencies or complex scenario), 40 for D
- "requires_numerical_comparison": true if query asks about specific numeric
  values (fees, setbacks, heights, timelines, capacity limits); false otherwise

Return ONLY valid JSON. No markdown fences. No explanation."""


_CLASSIFY_PROMPT = _build_classify_prompt()


@dataclass
class AnalysisResult:
    mode: str
    agencies_in_scope: list
    agency_relevance: dict
    top_k: int
    requires_numerical_comparison: bool


def analyze_query(query: str) -> AnalysisResult:
    """
    Classify query intent with a fast LLM call.
    Falls back to conservative mode-C defaults on any failure.
    """
    client = OpenAI(api_key=OPENAI_API_KEY)
    try:
        response = client.chat.completions.create(
            model=LLM_FAST,
            messages=[
                {"role": "system", "content": _CLASSIFY_PROMPT},
                {"role": "user", "content": query},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or ""
        # Strip markdown fences if the model added them anyway
        raw = re.sub(r"^```json\s*", "", raw.strip())
        raw = re.sub(r"\s*```$", "", raw)
        data = json.loads(raw)
        return AnalysisResult(
            mode=str(data["mode"]),
            agencies_in_scope=list(data["agencies_in_scope"]),
            agency_relevance=dict(data["agency_relevance"]),
            top_k=int(data["top_k"]),
            requires_numerical_comparison=bool(data.get("requires_numerical_comparison", False)),
        )
    except Exception as exc:
        logger.warning("analyze_query fallback (mode C): %s", exc)
        all_agencies = list(COLLECTION_MAP.keys())
        return AnalysisResult(
            mode="C",
            agencies_in_scope=all_agencies,
            agency_relevance={ag: 2 for ag in all_agencies},
            top_k=32,
            requires_numerical_comparison=False,
        )
