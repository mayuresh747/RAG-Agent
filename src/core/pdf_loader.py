"""
PDF text extraction with metadata.
Uses PyMuPDF (fitz) as primary extractor.
"""

import logging
from pathlib import Path
from dataclasses import dataclass, field

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


@dataclass
class PageContent:
    """One page of extracted text with metadata."""
    text: str
    metadata: dict = field(default_factory=dict)


def extract_pdf(file_path: Path, library_key: str) -> list[PageContent]:
    """
    Extract text page-by-page from a PDF.

    Returns a list of PageContent, one per page, each carrying metadata:
        library, source_file, title, page_number
    """
    pages: list[PageContent] = []
    title = file_path.stem  # filename without extension

    try:
        doc = fitz.open(str(file_path))
    except Exception as e:
        logger.error("Failed to open %s: %s", file_path.name, e)
        return pages

    for page_num, page in enumerate(doc, start=1):
        text = page.get_text()
        if not text or not text.strip():
            continue

        pages.append(
            PageContent(
                text=text,
                metadata={
                    "library": library_key,
                    "source_file": file_path.name,
                    "title": title,
                    "page_number": page_num,
                },
            )
        )

    doc.close()
    logger.debug("Extracted %d pages from %s", len(pages), file_path.name)
    return pages


def find_pdfs(directory: Path) -> list[Path]:
    """Recursively find all .pdf files under a directory."""
    return sorted(directory.rglob("*.pdf"))
