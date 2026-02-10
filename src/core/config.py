"""
Central configuration for the RAG Agent.
Loads settings from .env and provides library mappings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# ── App ──────────────────────────────────────────────────────────────────
APP_ENV = os.getenv("APP_ENV", "development")
APP_PORT = int(os.getenv("APP_PORT", "8000"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")

# ── OpenAI ───────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# ── Embedding ────────────────────────────────────────────────────────────
EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIMENSIONS = 3072  # text-embedding-3-large native dimension
EMBEDDING_BATCH_SIZE = 500   # chunks per API call

# ── Chunking ─────────────────────────────────────────────────────────────
CHUNK_SIZE = 1000       # characters
CHUNK_OVERLAP = 200     # characters

# ── Vector Store ─────────────────────────────────────────────────────────
VECTOR_DB_PATH = str(PROJECT_ROOT / os.getenv("VECTOR_DB_PATH", "./data/chromadb"))

# ── LLM ──────────────────────────────────────────────────────────────────
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))

# ── Document Libraries ──────────────────────────────────────────────────
ALL_DOCUMENTS_DIR = PROJECT_ROOT / "All Documents"

LIBRARIES = {
    "ibc_wa_docs": {
        "name": "IBC WA Docs",
        "path": ALL_DOCUMENTS_DIR / "IBC WA Docs",
        "description": "International Building, Fire, Mechanical, Residential, and Energy Codes (WA amendments)",
    },
    "rcw_chapters": {
        "name": "RCW Chapters",
        "path": ALL_DOCUMENTS_DIR / "RCW_Chapters",
        "description": "Revised Code of Washington — state statutes organized by Title",
    },
    "smc_chapters": {
        "name": "SMC Chapters",
        "path": ALL_DOCUMENTS_DIR / "SMC_Chapters",
        "description": "Seattle Municipal Code — city ordinances organized by Title",
    },
    "spu_design_standards": {
        "name": "SPU Design Standards",
        "path": ALL_DOCUMENTS_DIR / "SPU Design Standards",
        "description": "Seattle Public Utilities engineering and design standards",
    },
    "seattle_dir_rules": {
        "name": "Seattle DIR Rules",
        "path": ALL_DOCUMENTS_DIR / "Seattle_Active_DIR_Rules",
        "description": "Seattle Director's Rules — building, zoning, and land use interpretations",
    },
    "wac_chapters": {
        "name": "WAC Chapters",
        "path": ALL_DOCUMENTS_DIR / "WAC_Chapters",
        "description": "Washington Administrative Code — state agency regulations by Title",
    },
    "wa_governor_orders": {
        "name": "WA Governor Orders",
        "path": ALL_DOCUMENTS_DIR / "WA_Governor_Active_Orders",
        "description": "Active executive orders from the Washington State Governor (2025)",
    },
    "washington_court_opinions": {
        "name": "Washington Court Opinions",
        "path": ALL_DOCUMENTS_DIR / "washington_court_opinions",
        "description": "Washington Supreme Court and Court of Appeals opinions",
    },
}

# Ordered list for sequential ingestion
LIBRARY_ORDER = [
    "wa_governor_orders",          # 12 files  — smallest, fastest to test
    "ibc_wa_docs",                 # 7 files
    "spu_design_standards",        # 14 files
    "smc_chapters",                # 22 files
    "seattle_dir_rules",           # 179 files
    "washington_court_opinions",   # 200 files
    "rcw_chapters",                # ~1,100 files
    "wac_chapters",                # ~4,300 files — largest, last
]
