"""Shared pytest fixtures for multi-agent retrieval tests."""
import pytest
from src.core.retriever import RetrievedChunk
from src.core.analyzer import AnalysisResult


def make_chunk(
    text="Sample legal text.",
    score=0.75,
    library="rcw_chapters",
    source_file="RCW_59.18.200.pdf",
    page_number=3,
    rerank_score=0.0,
) -> RetrievedChunk:
    c = RetrievedChunk(
        text=text,
        score=score,
        library=library,
        source_file=source_file,
        page_number=page_number,
    )
    c.rerank_score = rerank_score
    return c


@pytest.fixture
def conflict_analysis():
    """Mode C analysis with 3 agencies, varying relevance."""
    return AnalysisResult(
        mode="C",
        agencies_in_scope=["RCW", "WAC", "SMC"],
        agency_relevance={"RCW": 3, "WAC": 2, "SMC": 2},
        top_k=24,
        requires_numerical_comparison=False,
    )


@pytest.fixture
def factual_analysis():
    """Mode A analysis, single agency."""
    return AnalysisResult(
        mode="A",
        agencies_in_scope=["RCW"],
        agency_relevance={"RCW": 3},
        top_k=12,
        requires_numerical_comparison=False,
    )


@pytest.fixture
def sample_chunks():
    """Six chunks across three agencies with rerank scores."""
    return [
        make_chunk(text="RCW top",    score=0.9, library="rcw_chapters",  source_file="RCW_59.18.200.pdf",  rerank_score=8.0),
        make_chunk(text="RCW second", score=0.8, library="rcw_chapters",  source_file="RCW_59.18.060.pdf",  rerank_score=5.0),
        make_chunk(text="WAC top",    score=0.7, library="wac_chapters",   source_file="WAC_365.196.pdf",    rerank_score=7.0),
        make_chunk(text="WAC second", score=0.6, library="wac_chapters",   source_file="WAC_365.100.pdf",    rerank_score=3.0),
        make_chunk(text="SMC top",    score=0.5, library="smc_chapters",   source_file="SMC_23.45.502.pdf",  rerank_score=6.0),
        make_chunk(text="SMC second", score=0.4, library="smc_chapters",   source_file="SMC_23.76.004.pdf",  rerank_score=2.0),
    ]
