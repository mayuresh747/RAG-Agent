"""Tests for authority-grouped context builder."""
import pytest
from tests.conftest import make_chunk
from src.core.context_builder import build_context, build_sources_metadata, _section_ref


class TestSectionRef:
    def test_rcw_filename(self):
        assert _section_ref("RCW_59.18.200.pdf") == "§ 59.18.200"

    def test_smc_filename(self):
        assert _section_ref("SMC_23.76.004.pdf") == "§ 23.76.004"

    def test_wac_filename_hyphens(self):
        """WAC uses hyphens: WAC_365-04_Description.pdf → § 365-04"""
        assert _section_ref("WAC_365-04_General_procedures..pdf") == "§ 365-04"
        assert _section_ref("WAC_365-196-010_Some_title.pdf") == "§ 365-196-010"

    def test_unstructured_filename(self):
        """Falls back to § <stem> for non-standard filenames."""
        assert _section_ref("State_v_Smith.pdf") == "§ State_v_Smith"


class TestBuildContext:
    def test_court_appears_before_rcw(self):
        """Authority rank 1 (COURT) comes before rank 2 (RCW)."""
        chunks = [
            make_chunk(text="RCW text",   library="rcw_chapters",            source_file="RCW_59.18.200.pdf"),
            make_chunk(text="COURT text", library="washington_court_opinions", source_file="State_v_Smith.pdf"),
        ]
        context = build_context(chunks)
        assert context.index("AGENCY: COURT") < context.index("AGENCY: RCW")

    def test_contains_source_numbered_references(self):
        """Each chunk gets a [Source N] label."""
        chunks = [
            make_chunk(text="text A", library="rcw_chapters", source_file="RCW_59.18.200.pdf"),
            make_chunk(text="text B", library="wac_chapters",  source_file="WAC_365.196.pdf"),
        ]
        context = build_context(chunks)
        assert "[Source 1]" in context
        assert "[Source 2]" in context

    def test_ends_with_end_marker(self):
        chunks = [make_chunk(text="x", library="rcw_chapters", source_file="RCW_59.18.pdf")]
        context = build_context(chunks)
        assert "=== END OF RETRIEVED CONTEXT ===" in context

    def test_section_ref_in_output(self):
        chunks = [make_chunk(text="landlord notice", library="rcw_chapters", source_file="RCW_59.18.200.pdf")]
        context = build_context(chunks)
        assert "§ 59.18.200" in context

    def test_empty_chunks_returns_no_documents(self):
        context = build_context([])
        assert "No relevant documents" in context


class TestBuildSourcesMetadata:
    def test_returns_correct_schema(self):
        chunk = make_chunk(
            text="sample",
            score=0.82,
            library="rcw_chapters",
            source_file="RCW_59.18.200.pdf",
            page_number=5,
        )
        sources = build_sources_metadata([chunk])
        assert len(sources) == 1
        s = sources[0]
        assert s["source_file"] == "RCW_59.18.200.pdf"
        assert s["library"] == "rcw_chapters"
        assert s["page_number"] == 5
        assert s["score"] == 0.82
        assert s["text"] == "sample"
