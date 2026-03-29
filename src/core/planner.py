"""
Retrieval budget planner — computes per-agency ChromaDB fetch budgets
based on corpus weight, query relevance, and query mode floors.
"""

from dataclasses import dataclass

from src.core.config import COLLECTION_MAP, CORPUS_WEIGHT
from src.core.analyzer import AnalysisResult

CONFLICT_FLOOR = {
    "COURT": 8, "RCW": 6, "WAC": 6, "SMC": 6,
    "DIR": 4, "IBC_WA": 4, "SPU": 4, "EXEC_ORDER": 4,
}
FACTUAL_FLOOR = 3


@dataclass
class AgencyTask:
    """A single agency retrieval task with its collection name and budget."""
    agency: str
    collection: str
    budget: int
    relevance: int


def plan_retrieval(analysis: AnalysisResult) -> list:
    """
    Compute per-agency fetch budgets.

    Budget formula:
        total_pool = top_k * 3
        raw_weight[ag] = CORPUS_WEIGHT[ag] * agency_relevance[ag]
        proportion[ag] = int(total_pool * raw_weight[ag] / sum(raw_weights))
        budget[ag] = max(floor, proportion[ag])

    Floor is FACTUAL_FLOOR (3) for mode A, CONFLICT_FLOOR[agency] for all other modes.
    """
    total_pool = analysis.top_k * 3
    agencies = analysis.agencies_in_scope
    relevance = analysis.agency_relevance

    raw_weights = {
        ag: CORPUS_WEIGHT[ag] * relevance[ag]
        for ag in agencies
    }
    total_raw = sum(raw_weights.values())

    tasks = []
    for ag in agencies:
        proportion = int(total_pool * raw_weights[ag] / total_raw)
        floor = FACTUAL_FLOOR if analysis.mode == "A" else CONFLICT_FLOOR[ag]
        budget = max(floor, proportion)
        tasks.append(AgencyTask(
            agency=ag,
            collection=COLLECTION_MAP[ag],
            budget=budget,
            relevance=relevance[ag],
        ))
    return tasks
