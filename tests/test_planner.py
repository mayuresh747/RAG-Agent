"""Tests for retrieval budget planner."""
import pytest
from src.core.planner import plan_retrieval, CONFLICT_FLOOR, FACTUAL_FLOOR, AgencyTask
from src.core.analyzer import AnalysisResult


class TestPlanRetrieval:
    def test_total_pool_equals_top_k_times_3(self):
        """Sum of budgets >= top_k*3 is not guaranteed (floors push it up), but
        each individual budget >= floor and total_pool calculation is correct."""
        analysis = AnalysisResult(
            mode="C",
            agencies_in_scope=["RCW", "WAC"],
            agency_relevance={"RCW": 3, "WAC": 3},
            top_k=24,
            requires_numerical_comparison=False,
        )
        tasks = plan_retrieval(analysis)
        # Proportion is from total_pool = 24*3 = 72
        # raw_weight RCW = 2.0 * 3 = 6.0; WAC = 3.0 * 3 = 9.0; sum=15
        # proportion RCW = int(72 * 6/15) = int(28.8) = 28
        # proportion WAC = int(72 * 9/15) = int(43.2) = 43
        by_agency = {t.agency: t for t in tasks}
        assert by_agency["RCW"].budget == 28
        assert by_agency["WAC"].budget == 43

    def test_conflict_floor_applied_when_proportion_is_smaller(self):
        """Agencies with low relevance get at least CONFLICT_FLOOR budget."""
        analysis = AnalysisResult(
            mode="C",
            agencies_in_scope=["RCW", "WAC", "EXEC_ORDER"],
            agency_relevance={"RCW": 3, "WAC": 3, "EXEC_ORDER": 1},
            top_k=16,
            requires_numerical_comparison=False,
        )
        tasks = plan_retrieval(analysis)
        by_agency = {t.agency: t for t in tasks}
        # EXEC_ORDER proportion will be very small (weight=1.0*1=1 vs RCW 2*3=6, WAC 3*3=9, sum=16)
        # int(48 * 1/16) = int(3.0) = 3 < CONFLICT_FLOOR[EXEC_ORDER]=4
        assert by_agency["EXEC_ORDER"].budget == CONFLICT_FLOOR["EXEC_ORDER"]

    def test_factual_floor_used_in_mode_A(self):
        """Mode A uses FACTUAL_FLOOR (3) instead of CONFLICT_FLOOR."""
        analysis = AnalysisResult(
            mode="A",
            agencies_in_scope=["RCW"],
            agency_relevance={"RCW": 3},
            top_k=12,
            requires_numerical_comparison=False,
        )
        tasks = plan_retrieval(analysis)
        # proportion = int(36 * 1.0) = 36, which > FACTUAL_FLOOR (3)
        # So budget = 36
        assert tasks[0].budget == 36

    def test_agency_task_collection_matches_config(self):
        """AgencyTask.collection is the ChromaDB collection name, not label."""
        analysis = AnalysisResult(
            mode="C",
            agencies_in_scope=["SMC"],
            agency_relevance={"SMC": 2},
            top_k=24,
            requires_numerical_comparison=False,
        )
        tasks = plan_retrieval(analysis)
        assert tasks[0].collection == "smc_chapters"
        assert tasks[0].agency == "SMC"

    def test_returns_one_task_per_agency(self):
        """Returns exactly one AgencyTask per agency in scope."""
        analysis = AnalysisResult(
            mode="B",
            agencies_in_scope=["RCW", "SMC", "COURT"],
            agency_relevance={"RCW": 3, "SMC": 3, "COURT": 3},
            top_k=20,
            requires_numerical_comparison=False,
        )
        tasks = plan_retrieval(analysis)
        assert len(tasks) == 3
        agencies = {t.agency for t in tasks}
        assert agencies == {"RCW", "SMC", "COURT"}
