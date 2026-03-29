# Multi-Agent Retrieval Layer — Design Spec

**Date:** 2026-03-29
**Branch:** `multi-agent-upgrade`
**Status:** Approved

---

## Context

The existing RAG system retrieves up to 25 candidates per library using cosine similarity, then selects the global top-k by similarity score. For conflict queries (e.g., "what are all the EV charging conflicts for my apartment building?"), this produces lopsided evidence: WAC has 4,300 files and dominates the candidate pool, while COURT and SMC — essential for conflict analysis — get squeezed out.

The multi-agent retrieval layer adds:
1. A structured query intent classification (mode A-D) replacing the binary SIMPLE/COMPLEX classifier
2. Per-agency candidate budgets weighted by corpus size and query relevance
3. Parallel retrieval across all agency collections
4. Cross-encoder reranking for semantic relevance (not just vector proximity)
5. Two-pass evidence selection guaranteeing balanced representation across conflict pairs
6. Authority-ordered structured context replacing the flat source list

Nothing in ChromaDB, ingestion, or the frontend changes.

---

## Agency Labels

| Label | ChromaDB Collection | Authority Rank | Corpus Weight |
|-------|-------------------|---------------|--------------|
| COURT | washington_court_opinions | 1 | 1.5 |
| RCW | rcw_chapters | 2 | 2.0 |
| WAC | wac_chapters | 3 | 3.0 |
| EXEC_ORDER | wa_governor_orders | 4 | 1.0 |
| IBC_WA | ibc_wa_docs | 5 | 1.0 |
| SMC | smc_chapters | 6 | 1.0 |
| DIR | seattle_dir_rules | 7 | 1.5 |
| SPU | spu_design_standards | 8 | 1.0 |

---

## Query Modes

| Mode | Trigger | top_k |
|------|---------|-------|
| A — Factual | Single-agency lookup, no conflict analysis | 12 |
| B — Named conflict | User explicitly names 2-3 agencies | 16-20 |
| C — Topic conflict | LLM selects 3-6 relevant agencies | 24-32 |
| D — Full audit | Development scenario audit, all relevant agencies | 40 |

---

## Files Changed

### Modified

| File | Change |
|------|--------|
| `src/core/config.py` | Add: `LLM_FAST`, `USE_MULTI_AGENT`, `COLLECTION_MAP`, `COLLECTION_TO_AGENCY`, `AUTHORITY_RANK`, `CORPUS_WEIGHT` |
| `src/core/retriever.py` | Add: `rerank_score: float = 0.0` field to `RetrievedChunk` dataclass |
| `src/core/rag_chain.py` | Feature flag routing at lines 92-123; import `LLM_FAST` from config (replace hardcoded `"gpt-4o-mini"` on line 59) |

### New

| File | Purpose |
|------|---------|
| `src/core/analyzer.py` | `analyze_query(query) → AnalysisResult`; single gpt-4o-mini JSON call; returns mode, agencies, relevance scores, top_k, requires_numerical_comparison |
| `src/core/planner.py` | `plan_retrieval(analysis) → list[AgencyTask]`; budget = top_k×3 × (corpus_weight×relevance / Σweights), with agency floors |
| `src/core/reranker.py` | `rerank(query, chunks, top_k) → list[RetrievedChunk]`; cross-encoder/ms-marco-MiniLM-L-6-v2, lazy-loaded |
| `src/core/evidence.py` | `select_evidence(chunks, analysis, top_k) → list[RetrievedChunk]`; two-pass selection + pair coverage check |
| `src/core/context_builder.py` | `build_context(chunks) → str`; authority-grouped context; `build_sources_metadata(chunks) → list[dict]` for SSE |
| `src/core/multi_agent.py` | `multi_agent_retrieve(query, min_score) → RetrievalResult`; orchestrates all 6 steps; uses ThreadPoolExecutor for parallel searches |

---

## Pipeline Data Flow

```
chat_stream(user_message)
  │
  ├─[USE_MULTI_AGENT=true]
  │   multi_agent_retrieve(user_message)
  │     ├── analyze_query()           → AnalysisResult (gpt-4o-mini, temp=0, JSON mode)
  │     ├── plan_retrieval()          → [AgencyTask(collection, budget, relevance)]
  │     ├── embed_query()             → vector (single call, shared across all agencies)
  │     ├── ThreadPoolExecutor        → parallel vector_search() per AgencyTask
  │     ├── rerank()                  → sorted RetrievedChunks (cross-encoder)
  │     └── select_evidence()         → final top_k RetrievedChunks
  │   build_context()                 → structured context string
  │   build_sources_metadata()        → sources list for SSE
  │
  └─[USE_MULTI_AGENT=false]
      _is_complex_query() + retrieve() + _build_context_block()  ← unchanged
  │
  yield {"type": "sources", ...}      ← same schema either path
  augmented_system = system + context
  LLM stream (GPT-5.1)               ← unchanged
```

---

## Budget Calculation (Planner)

```
total_pool = top_k × 3
raw_weight[agency] = CORPUS_WEIGHT[agency] × agency_relevance[agency]
proportion[agency] = int(total_pool × raw_weight[agency] / Σ(raw_weights))
budget[agency] = max(CONFLICT_FLOOR[agency], proportion[agency])
```

**Conflict floors:** COURT=8, RCW=6, WAC=6, SMC=6, DIR=4, IBC_WA=4, SPU=4, EXEC_ORDER=4
**Factual floor (Mode A):** 3

---

## Two-Pass Evidence Selection (Evidence Collector)

**Pass 1 — Guaranteed slots** (picked by highest rerank_score within each agency):
- COURT in conflict modes: always 2 slots
- relevance=3: 2 slots
- relevance=2: 1 slot
- relevance=1 or Mode A: 0 slots (pure reranker)

**Pass 2 — Global fill:**
Remaining `top_k − guaranteed` slots filled by globally best unreserved chunks.

**Pair coverage check:**
For every non-COURT agency pair in scope, both sides must have ≥1 chunk. If missing, force-insert the top-scoring chunk from the missing agency (with a log warning).

---

## Context Block Format (Context Builder)

```
=== AGENCY: COURT (Authority Level 1) ===

[Source 1] COURT — washington_court_opinions, § State_v_Smith, p.7
"The city argued that the nexus test was satisfied..."

=== AGENCY: RCW (Authority Level 2) ===

[Source 2] RCW — rcw_chapters, § 59.18.200, p.3
"No condition shall be imposed on a development permit..."

=== END OF RETRIEVED CONTEXT ===
```

Section reference is derived from `source_file` filename:
- `RCW_59.18.200.pdf` → `§ 59.18.200`
- `SMC_23.76.004.pdf` → `§ 23.76.004`
- Unstructured filenames: `§ <stem>`

---

## Integration in rag_chain.py

```python
# Replace lines 92-123 in chat_stream():
if USE_MULTI_AGENT:
    retrieval_result = multi_agent_retrieve(user_message, min_score=0.25)
    context_block = build_context(retrieval_result.chunks)
    sources = build_sources_metadata(retrieval_result.chunks)
else:
    if top_k is None:
        is_complex = _is_complex_query(user_message, _get_client())
        top_k = 24 if is_complex else 12
    retrieval_result = retrieve(user_message, top_k=top_k, auto_route=True, min_score=0.25)
    context_block = _build_context_block(retrieval_result)
    sources = [{"source_file": c.source_file, "library": c.library,
                "page_number": c.page_number, "score": round(c.score, 3),
                "text": c.text} for c in retrieval_result.chunks]

yield {"type": "sources", "data": sources}
# context_block used below in augmented_system (unchanged)
```

The `_build_context_block()` function stays in `rag_chain.py` for the legacy path.

---

## Compatibility Contract

Both paths return `RetrievalResult` with `list[RetrievedChunk]`. New path populates `rerank_score`; old path leaves it at `0.0`. No existing code reads `rerank_score`. The `sources` SSE event schema (`source_file`, `library`, `page_number`, `score`, `text`) is identical.

---

## New config.py Constants

```python
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
```

---

## Analyzer Fallback

If gpt-4o-mini returns malformed JSON (e.g., markdown fences, partial output):
- Strip ` ```json ` fences before parsing
- On `json.JSONDecodeError`: log the raw response, return conservative default:
  ```python
  AnalysisResult(mode="B", agencies_in_scope=list(COLLECTION_MAP.keys()),
                 agency_relevance={ag: 2 for ag in COLLECTION_MAP},
                 top_k=20, requires_numerical_comparison=False)
  ```

---

## Deployment

### Model pre-bake (Dockerfile)

Add after `pip install` step:
```dockerfile
RUN python -c "from sentence_transformers import CrossEncoder; CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"
```

This downloads the ~85MB model into the image so AWS Lightsail doesn't need HuggingFace egress at runtime.

### FastAPI startup warmup

When `USE_MULTI_AGENT=true`, trigger reranker initialization in the `startup` event to avoid cold-start delay on the first real query.

### .env addition

```
USE_MULTI_AGENT=true
# LLM_FAST=gpt-4o-mini  # uncomment to override
```

---

## Testing

New `tests/` directory with:

| File | Coverage |
|------|---------|
| `tests/test_planner.py` | Budget math: floors, weights, total pool = top_k×3 |
| `tests/test_evidence.py` | Two-pass: guaranteed slots, global fill, pair coverage check |
| `tests/test_context_builder.py` | Agency grouping, COURT before RCW, section derivation from filename |
| `tests/test_analyzer.py` | JSON parsing, fallback on malformed LLM output |
| `tests/test_multi_agent.py` | Integration test (mocked OpenAI + ChromaDB) → RetrievalResult |

---

## Implementation Order

Dependencies flow bottom-up:

1. `config.py` — Add constants
2. `retriever.py` — Add `rerank_score` field
3. `analyzer.py` — Uses config (can be tested with mocked LLM)
4. `planner.py` — Uses config + AnalysisResult type
5. `reranker.py` — Uses RetrievedChunk only
6. `evidence.py` — Uses RetrievedChunk + AnalysisResult
7. `context_builder.py` — Uses config + RetrievedChunk
8. `multi_agent.py` — Orchestrates all above; parallel retrieval
9. `rag_chain.py` — Feature flag integration, last to touch

Steps 3-5 are independent and can proceed in parallel.

---

## Risks

| Risk | Mitigation |
|------|-----------|
| Analyzer returns malformed JSON | JSON fence stripping + fallback defaults |
| Cross-encoder model not downloaded on AWS | Pre-bake in Dockerfile |
| Cross-encoder cold start (~3-5s) | FastAPI startup warmup |
| Mode D latency (~5-10s) | Accepted; document for users |
| ThreadPoolExecutor + ChromaDB contention | Max 8 workers; ChromaDB reads are thread-safe |
| Feature flag evaluated at import time | Requires server restart to change; documented |
