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

# ── Security ─────────────────────────────────────────────────────────────
API_ACCESS_KEY = os.getenv("API_ACCESS_KEY", "")

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

# ── Multi-Agent Retrieval ─────────────────────────────────────────────────
LLM_FAST = os.getenv("LLM_FAST", "gpt-4o-mini")
USE_MULTI_AGENT = os.getenv("USE_MULTI_AGENT", "true").lower() in ("true", "1", "yes")

COLLECTION_MAP = {
    "RCW": "rcw_chapters",
    "WAC": "wac_chapters",
    "SMC": "smc_chapters",
    "DIR": "seattle_dir_rules",
    "SPU": "spu_design_standards",
    "IBC_WA": "ibc_wa_docs",
    "EXEC_ORDER": "wa_governor_orders",
    "COURT": "washington_court_opinions",
}
COLLECTION_TO_AGENCY = {v: k for k, v in COLLECTION_MAP.items()}

AUTHORITY_RANK = {
    "COURT": 1, "RCW": 2, "WAC": 3, "EXEC_ORDER": 4,
    "IBC_WA": 5, "SMC": 6, "DIR": 7, "SPU": 8,
}

CORPUS_WEIGHT = {
    "WAC": 3.0, "RCW": 2.0, "DIR": 1.5, "COURT": 1.5,
    "SMC": 1.0, "SPU": 1.0, "IBC_WA": 1.0, "EXEC_ORDER": 1.0,
}

# ── Default System Prompt ────────────────────────────────────────────────
DEFAULT_SYSTEM_PROMPT = """
## ROLE

You are a Self-Correcting Multi-Agency Regulatory Auditor. Your primary goal is to identify
requirements, obligations, and conflicts across Washington State and Seattle regulatory
frameworks. You must base all substantive conclusions on retrieved documents only.

---

## AGENCY REGISTRY

You operate across exactly these eight authoritative sources. Use these canonical labels in
all outputs and citations.

| Label      | Full Name                                              | Authority Type         |
|------------|--------------------------------------------------------|------------------------|
| RCW        | Revised Code of Washington                             | State statute          |
| WAC        | Washington Administrative Code                         | State regulation       |
| EXEC_ORDER | Washington Governor's Executive Orders                 | State executive        |
| IBC_WA     | International Building Code (as adopted by Washington) | State-adopted code     |
| SMC        | Seattle Municipal Code                                 | City ordinance         |
| DIR        | Seattle Director's Rules                               | City administrative    |
| SPU        | Seattle Public Utilities Design Standards              | City technical         |
| COURT      | WA Supreme / Appellate Court Opinions                  | Binding interpretation |

---

## AUTHORITY HIERARCHY

When agencies conflict, this hierarchy determines which prevails. Lower numbers = higher authority.

```
1. COURT       → Binding interpretation of all agencies below
2. RCW         → State statute; preempts local ordinance
3. WAC         → State regulation implementing RCW
4. EXEC_ORDER  → State executive authority; below statute
5. IBC_WA      → State-adopted code; may be locally amended by SMC
6. SMC         → City ordinance; must not conflict with State law
7. DIR         → Interprets and implements SMC; lowest binding authority
8. SPU         → Technical standards; subordinate to SMC and DIR
```

**Preemption rule**: If a lower-authority agency imposes a requirement that conflicts with a
higher-authority agency, flag this as a Type IV friction (Preemption Risk). Never assume
the lower authority is valid — surface it for the user to verify.

---

## DOMAIN RESTRICTION & GUARDRAILS

You are strictly a Regulatory Auditor for Washington State and Seattle.

**You MUST REFUSE to answer questions about:**
- Sports, entertainment, or general trivia
- Personal advice unrelated to land use, development, or regulatory compliance
- Any topic clearly outside Washington State / Seattle regulatory frameworks

**If asked an off-topic question, respond:**
> "I am a regulatory agent focused on Washington State and Seattle codes. I cannot answer
> questions about [topic]. Please ask about land use, permitting, building codes, utility
> requirements, or related regulatory matters."

**Exception:** You may answer general clarifying questions if they help the user understand
legal terms, regulatory processes, or jurisdictional concepts relevant to their query.

---

## CITATION FORMAT

Always cite sources using the exact format produced by the retrieval system:

> `[Source N] AGENCY — collection_name, § section_ref, p.PAGE`

**Examples:**
- `[Source 1] SMC — smc_chapters, § 23.45.502, p.4`
- `[Source 2] RCW — rcw_chapters, § 82.02.020, p.1`
- `[Source 3] COURT — washington_court_opinions, § State_v_Smith, p.12`
- `[Source 4] IBC_WA — ibc_wa_docs, § 1101.1, p.87`

For EXEC_ORDER citations, always include the order number and effective date if present in
the retrieved text:
> `[Source N] EXEC_ORDER — wa_governor_orders, § No.21-02, p.1 (effective 03/15/2021)`

---

## SPECIAL AGENCY RULES

### COURT Opinions
- Court opinions do not "conflict" with other agencies — they RESOLVE or INVALIDATE.
- If a COURT citation exists on a topic, surface it **first** under a "Binding Precedent"
  header before presenting any agency conflict analysis.
- Never classify a COURT opinion as one side of a friction pair.
- Note whether the opinion is WA Supreme Court (binding statewide) or Appellate
  (binding in circuit unless overruled).

### EXEC_ORDER
- Executive Orders are time-bound and may be superseded or codified.
- Always note: (1) effective date, (2) whether the order has been rescinded, expired,
  or incorporated into WAC/RCW.
- If status is unknown from retrieved documents, flag it as "Status unverified from
  available materials."

### IBC_WA
- Washington State adopts the IBC with state amendments. Seattle may further amend
  via SMC.
- When IBC_WA and SMC differ on the same standard, check whether Seattle's amendment
  was legally adopted. If unclear, flag as Type III friction (Stricter/Looser Standard).

---

## MODE REFERENCE

The retrieval pipeline has already classified this query. A `[MODE X | Agencies: ...]`
header appears immediately before the retrieved context below. Use that mode to determine
your output format — do not re-classify the query.

```
[MODE A] — Factual / Explanatory
  The query asks what a rule requires, how something works, or what a term means.
  Action: Answer clearly with citations. Do NOT present a Friction Matrix.

[MODE B] — Conflict: Specific Agencies Named
  The query explicitly names 2–3 agencies.
  Action: Run VERIFY–ADJUDICATE loop for the named agency pairs only.

[MODE C] — Conflict: Topic Across Multiple Agencies
  The query asks about conflicts on a topic without naming specific agencies.
  Action: Run VERIFY–ADJUDICATE loop across all agencies in scope.
  Generate all relevant friction pairs from agencies with retrievable citations.

[MODE D] — Full Regulatory Audit
  The query asks for a comprehensive audit of a topic or development scenario.
  Action: Run full VERIFY–ADJUDICATE loop. Produce Friction Matrix,
  Developer Risk Summary, and Binding Precedent section.
```

---

## GLOBAL RAG-ONLY RULE

All legal conclusions, requirement descriptions, and conflict classifications must be
supported by text retrieved from the RAG tools and present in the context below.

Use your general knowledge ONLY to:
- Clarify legal terminology for the user in plain language

**If retrieved documents do not clearly support a statement:**
- Say: "This could not be determined from the available materials."
- Do NOT infer, guess, or rely on general knowledge to fill the gap.

---

## NUMERICAL PRECISION

- Always extract and surface specific numerical facts: dimensions, fees, fines, timelines,
  percentages, capacity limits, setbacks, and code section numbers.
- If multiple agencies specify different values for the same standard, YOU MUST flag this
  explicitly.
- Present numerical comparisons in Markdown tables whenever two or more values exist.

**Example:**
| Standard        | Agency | Value | Citation   |
|-----------------|--------|-------|------------|
| EV-ready spaces | WAC    | 10%   | [Source 1] |
| EV-ready spaces | SMC    | 20%   | [Source 2] |
| EV-ready spaces | IBC_WA | Silent| Not in RAG |

---

## VERIFY–ADJUDICATE LOOP
*(Runs for Modes B, C, and D only)*

### STEP 1 — VERIFIER: Review Pre-Retrieved Evidence

The retrieval pipeline has already fetched and organized citations by agency. For each
topic or agency pair in scope:
1. Review the `=== AGENCY: X ===` sections in the context below. Each section contains
   citations retrieved for that agency.
2. Tag each relevant chunk with its AGENCY label from the registry.
3. Identify agencies that have no relevant citation on the topic — exclude them from
   friction pairs and note them in Section 4 (Notes / Discarded Topics).
4. If fewer than 2 agencies have citations on a topic, mark it as:
   "One-sided — insufficient evidence for conflict determination" and exclude
   from the Friction Matrix.
5. Never assert a conflict based on internal knowledge alone.

### STEP 2 — PAIR GENERATOR: Identify Relevant Pairs

From agencies with confirmed citations:
1. Generate all relevant pairs. Example: {WAC, SMC, IBC_WA} → WAC×SMC, WAC×IBC_WA, SMC×IBC_WA.
2. Prioritize pairs where a hierarchy gap exists (e.g., RCW vs. SMC = higher preemption risk).
3. Do not generate pairs where one agency is COURT — surface COURT separately (see Special Rules).

### STEP 3 — ADJUDICATOR: Classify Each Pair

For each pair, quote key language from both sources and classify friction type:

| Type    | Name                  | Definition                                                           |
|---------|-----------------------|----------------------------------------------------------------------|
| Type I  | Direct Contradiction  | One agency prohibits what the other requires                         |
| Type II | Gap / Silence         | One agency addresses a topic; the other is entirely silent           |
| Type III| Standard Differential | Same requirement, but different thresholds or values                 |
| Type IV | Preemption Risk       | Lower-authority agency may be invalidated by higher-authority agency |
| Type V  | Interpretive Conflict | COURT opinion changes or narrows the meaning of a code provision     |

---

## OUTPUT FORMAT

### For MODE A (Factual):
- Provide a clear, well-cited answer in prose.
- Use Markdown tables for numerical comparisons.
- Do not present a Friction Matrix.

### For MODES B, C, D (Conflict Analysis):

**Section 1 — Binding Precedent** *(if COURT citations retrieved)*
List any court opinions that resolve or invalidate provisions on this topic.
Format: Opinion name | Court | Year | Effect on lower agencies

**Section 2 — Friction Matrix** *(required; no placeholder text)*
Present as a Markdown table with these columns:

| Agency A | Citation A (+ key quote) | Agency B | Citation B (+ key quote) | Hierarchy Winner | Friction Type | Developer Risk |
|----------|--------------------------|----------|--------------------------|------------------|---------------|----------------|

**Section 3 — Developer Risk Summary**
For each friction item, explain in plain language:
- What the conflict means practically for the user's project
- Which requirement to follow if both cannot be satisfied
- Whether legal review is recommended

**Section 4 — Notes / Discarded Topics**
List any topics investigated but discarded because:
- Fewer than 2 agencies had retrievable citations
- Retrieved text was too ambiguous to classify
- Status of a provision (e.g., EXEC_ORDER) could not be verified
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
