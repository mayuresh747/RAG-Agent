"""
Legal-text-aware chunking.
Uses LangChain's RecursiveCharacterTextSplitter with custom separators
tuned for statutes, codes, and court opinions.
"""

from typing import Optional

from langchain.text_splitter import RecursiveCharacterTextSplitter

from src.core.config import CHUNK_SIZE, CHUNK_OVERLAP
from src.core.pdf_loader import PageContent


# Separators ordered from most to least preferred.
# Legal text often uses these structural markers.
LEGAL_SEPARATORS = [
    "\n\n",           # double newline (paragraph break)
    "\nChapter ",     # chapter heading
    "\nSection ",     # section heading
    "\nRCW ",         # RCW section reference
    "\nWAC ",         # WAC section reference
    "\nSMC ",         # SMC section reference
    "\n§ ",           # section symbol
    "\nArt. ",        # article
    "\n(",            # numbered subsection e.g. (1), (a)
    "\n",             # single newline
    ". ",             # sentence boundary
    " ",              # word boundary
]


def build_splitter(
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> RecursiveCharacterTextSplitter:
    """Create a text splitter with legal-aware separators."""
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=LEGAL_SEPARATORS,
        length_function=len,
        is_separator_regex=False,
    )


def chunk_pages(
    pages: list,
    splitter: Optional[RecursiveCharacterTextSplitter] = None,
) -> list[dict]:
    """
    Split a list of PageContent into chunks, preserving metadata.

    Returns a list of dicts with keys:
        text, metadata (library, source_file, title, page_number, chunk_index)
    """
    if splitter is None:
        splitter = build_splitter()

    chunks: list[dict] = []
    chunk_index = 0

    for page in pages:
        splits = splitter.split_text(page.text)
        for split_text in splits:
            if not split_text.strip():
                continue
            chunks.append(
                {
                    "text": split_text,
                    "metadata": {
                        **page.metadata,
                        "chunk_index": chunk_index,
                    },
                }
            )
            chunk_index += 1

    return chunks
