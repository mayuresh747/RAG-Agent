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
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-5.1")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "8192"))
CONVERSATION_MEMORY_SIZE = int(os.getenv("CONVERSATION_MEMORY_SIZE", "20"))

# ── Default System Prompt ────────────────────────────────────────────────
DEFAULT_SYSTEM_PROMPT = """ROLE
You are a Self-Correcting Regulatory Auditor. Your primary goal, when asked,
is to identify conflicts between State (WAC/RCW) and City (SMC/SPU/Director's Rules)
codes. You must base all substantive conclusions on retrieved documents.

MODE SWITCH
If the user explicitly asks for conflicts, inconsistencies, differences,
preemption, or friction between State and City rules, run the VERIFY–ADJUDICATE loop.

If the user asks a normal factual or explanatory question and does NOT
ask for conflicts, then:
- Skip the Verify–Adjudicate loop.
- Perform RAG lookup(s) in the most relevant library.
- Answer the question clearly with citations.
- Do NOT search for or present conflicts unless requested.

GLOBAL RAG-ONLY RULE
All legal conclusions, descriptions of requirements, and conflict classifications
must be supported by text retrieved from the RAG tools.
Use your general knowledge ONLY to:
- choose which documents/sections to inspect next
- clarify legal terminology for the user
If the documents do not clearly support a statement, say it is not found
or cannot be determined from the provided materials. Do NOT guess.

VERIFY–ADJUDICATE LOOP (for conflict questions only)

STEP 1: VERIFIER (Evidence Collection)
For each topic raised by the user:
- Perform RAG lookup(s) to find:
  - At least one relevant State citation (RCW/WAC/etc.), and
  - At least one relevant City citation (SMC/SPU/Director's Rule).
- If you cannot find BOTH sides in the RAG documents, DISCARD the topic
  OR mark it as "one-sided / no conflict determined" and keep it out of the
  final conflict table.
- Never rely on internal knowledge alone to assert a conflict.

STEP 2: ADJUDICATOR (Final Matrix)
For each verified conflict candidate:
- Quote the key language from both State and City sources, with section numbers.
- Compare the texts and classify the friction (Type I, II, or III).
- Ensure the classification is supported by the quoted language.

CRITICAL OUTPUT RULES
1. Transparency:
   - In a short "Notes" section, mention any investigated topics that were
     discarded because no clear supporting text was found.
2. Final Table:
   - Only include items where BOTH State and City citations were retrieved
     and support a real difference or tension.
   - For each row, include:
     - State citation + quote
     - City citation + quote
     - Friction type (I/II/III)
     - Brief justification tied directly to the quoted text.

OUTPUT FORMAT
[Provide the Friction Matrix Table here, followed by a short Notes section]
"""

# ── Document Libraries ──────────────────────────────────────────────────
ALL_DOCUMENTS_DIR = PROJECT_ROOT / "All Documents"

LIBRARIES = {
    "ibc_wa_docs": {
        "name": "IBC WA Docs",
        "path": ALL_DOCUMENTS_DIR / "IBC WA Docs",
        "description": (
            "International Building Codes, Fire Codes, Energy Codes, Residential Codes, "
            "and other construction-related codes adopted by Washington. "
            "Use when the user asks about building standards, construction requirements, "
            "fire safety regulations, energy efficiency codes, structural design, "
            "IBC, IRC, IFC, IMC, IECC, or WA amendments to international codes."
        ),
    },
    "rcw_chapters": {
        "name": "RCW Chapters",
        "path": ALL_DOCUMENTS_DIR / "RCW_Chapters",
        "description": (
            "Statutes and laws of the State of Washington, organized by Title and Chapter. "
            "Use when the user asks about state laws, statutes, acts, or legal definitions "
            "applicable to the entire state. Covers criminal law, family law, landlord-tenant, "
            "business regulations, real property, and all other RCW titles."
        ),
    },
    "smc_chapters": {
        "name": "SMC Chapters",
        "path": ALL_DOCUMENTS_DIR / "SMC_Chapters",
        "description": (
            "Laws, ordinances, and regulations specific to the City of Seattle. "
            "Use when the user asks about local city laws, zoning ordinances, land use "
            "regulations, noise control, building permits, or other municipal codes "
            "specific to Seattle."
        ),
    },
    "spu_design_standards": {
        "name": "SPU Design Standards",
        "path": ALL_DOCUMENTS_DIR / "SPU Design Standards",
        "description": (
            "Technical design standards and requirements for Seattle's public utilities "
            "(Water, Drainage, Wastewater). Use when the user asks about technical "
            "engineering standards, utility infrastructure design, drainage requirements, "
            "water system specifications, pump stations, SCADA, or physical security "
            "for utility facilities."
        ),
    },
    "seattle_dir_rules": {
        "name": "Seattle DIR Rules",
        "path": ALL_DOCUMENTS_DIR / "Seattle_Active_DIR_Rules",
        "description": (
            "Administrative rules, interpretations, and procedural guidelines issued by "
            "Seattle department directors (SDCI, SDOT). Use when the user asks about "
            "specific administrative interpretations, procedural rules, implementation "
            "guidelines, Director's Rules, RRIO, green factor, tree protection, or how "
            "city codes are applied or enforced by specific departments."
        ),
    },
    "wac_chapters": {
        "name": "WAC Chapters",
        "path": ALL_DOCUMENTS_DIR / "WAC_Chapters",
        "description": (
            "Regulations of executive branch agencies in Washington State. "
            "Use when the user asks about agency regulations, administrative rules, "
            "procedures, or requirements set by state agencies (Dept of Ecology, L&I, "
            "DSHS, DOH, etc). Covers environmental regs, licensing, health and safety, "
            "education, and all other WAC titles."
        ),
    },
    "wa_governor_orders": {
        "name": "WA Governor Orders",
        "path": ALL_DOCUMENTS_DIR / "WA_Governor_Active_Orders",
        "description": (
            "Proclamations, emergency orders, and executive directives from the Governor "
            "of Washington. Use when the user asks about executive orders, state of "
            "emergency declarations, gubernatorial proclamations, or temporary mandates "
            "issued by the Governor."
        ),
    },
    "washington_court_opinions": {
        "name": "Washington Court Opinions",
        "path": ALL_DOCUMENTS_DIR / "washington_court_opinions",
        "description": (
            "Written opinions and rulings from Washington State courts. Use when the user "
            "asks about legal precedents, case law, court rulings, judicial interpretations, "
            "or specific case names (e.g., 'State v. Smith'). Provides how laws have been "
            "interpreted in court and legal authority from past cases."
        ),
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
