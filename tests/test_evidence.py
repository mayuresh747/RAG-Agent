"""Tests for two-pass evidence selection."""
import pytest
from tests.conftest import make_chunk
from src.core.analyzer import AnalysisResult
from src.core.evidence import select_evidence, _guaranteed_slots


class TestGuaranteedSlots:
    def test_mode_A_always_zero(self):
        assert _guaranteed_slots("RCW", relevance=3, mode="A") == 0
        assert _guaranteed_slots("COURT", relevance=3, mode="A") == 0

    def test_court_always_2_in_conflict_modes(self):
        for mode in ("B", "C", "D"):
            assert _guaranteed_slots("COURT", relevance=1, mode=mode) == 2

    def test_relevance_3_gives_2_slots(self):
        assert _guaranteed_slots("RCW", relevance=3, mode="C") == 2

    def test_relevance_2_gives_1_slot(self):
        assert _guaranteed_slots("WAC", relevance=2, mode="C") == 1

    def test_relevance_1_gives_0_slots(self):
        assert _guaranteed_slots("SMC", relevance=1, mode="C") == 0


class TestSelectEvidence:
    def test_guaranteed_slots_filled_first(self, sample_chunks, conflict_analysis):
        """Pass 1: RCW (rel=3) gets 2 guaranteed slots, WAC and SMC (rel=2) get 1 each."""
        result = select_evidence(sample_chunks, conflict_analysis, top_k=6)
        texts = [c.text for c in result]
        # RCW top 2 must be present (guaranteed)
        assert "RCW top" in texts
        assert "RCW second" in texts
        # WAC top must be present (1 guaranteed slot)
        assert "WAC top" in texts
        # SMC top must be present (1 guaranteed slot)
        assert "SMC top" in texts

    def test_total_count_respects_top_k(self, sample_chunks, conflict_analysis):
        """Result never exceeds top_k."""
        result = select_evidence(sample_chunks, conflict_analysis, top_k=4)
        assert len(result) <= 4

    def test_pair_coverage_check_force_inserts_missing_agency(self):
        """If an agency in scope has no chunks in the pool, force-insert its best."""
        analysis = AnalysisResult(
            mode="C",
            agencies_in_scope=["RCW", "SMC"],
            agency_relevance={"RCW": 3, "SMC": 2},
            top_k=4,
            requires_numerical_comparison=False,
        )
        # Only provide RCW chunks — SMC is missing
        chunks = [
            make_chunk(text="RCW 1", library="rcw_chapters", rerank_score=8.0),
            make_chunk(text="RCW 2", library="rcw_chapters", rerank_score=7.0),
            make_chunk(text="RCW 3", library="rcw_chapters", rerank_score=6.0),
            make_chunk(text="RCW 4", library="rcw_chapters", rerank_score=5.0),
            make_chunk(text="SMC 1", library="smc_chapters", rerank_score=1.0),
        ]
        result = select_evidence(chunks, analysis, top_k=4)
        libraries = {c.library for c in result}
        # SMC must be represented despite low rerank score
        assert "smc_chapters" in libraries

    def test_court_excluded_from_coverage_check(self):
        """COURT is not force-inserted by the coverage check (handled by guaranteed slots)."""
        # COURT is in scope but not in the chunk pool
        analysis = AnalysisResult(
            mode="C",
            agencies_in_scope=["RCW", "COURT"],
            agency_relevance={"RCW": 3, "COURT": 3},
            top_k=4,
            requires_numerical_comparison=False,
        )
        chunks = [
            make_chunk(text="RCW 1", library="rcw_chapters", rerank_score=8.0),
            make_chunk(text="RCW 2", library="rcw_chapters", rerank_score=7.0),
            make_chunk(text="RCW 3", library="rcw_chapters", rerank_score=6.0),
        ]
        # Should not raise, and should NOT force-insert COURT since COURT is not
        # subject to the pair coverage check (it's in guaranteed slots from pass 1)
        result = select_evidence(chunks, analysis, top_k=4)
        assert all(c.library == "rcw_chapters" for c in result)

    def test_mode_A_no_guaranteed_slots_pure_reranker(self, factual_analysis):
        """Mode A: all slots filled by global best, no guaranteed allocation."""
        chunks = [
            make_chunk(text="high", library="rcw_chapters", rerank_score=9.0),
            make_chunk(text="med",  library="rcw_chapters", rerank_score=5.0),
            make_chunk(text="low",  library="rcw_chapters", rerank_score=1.0),
        ]
        result = select_evidence(chunks, factual_analysis, top_k=2)
        assert result[0].text == "high"
        assert result[1].text == "med"
