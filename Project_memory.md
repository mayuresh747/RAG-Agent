# Project Memory — RAG Agent

> This file serves as the persistent memory of all decisions, strategies, and results for the RAG Agent project.
> Last updated: **2026-02-10**

---

## 1. Project Goal

Build a **local RAG (Retrieval-Augmented Generation) chatbot** that can search and answer questions from a large collection of Washington State legal documents. The system processes PDFs, creates semantic embeddings, stores them locally, and will eventually provide a chat interface with an LLM.

---

## 2. Document Corpus

### Overview
- **Total documents:** 6,021 PDFs
- **Total size:** ~2.6 GB
- **Format:** All PDF (some older files are scanned images without extractable text)

### Libraries

| # | Library | Directory | Files | Description |
|---|---|---|---|---|
| 1 | WA Governor Orders | `WA_Governor_Active_Orders/` | 12 | Active executive orders from the Governor (2025) |
| 2 | IBC WA Docs | `IBC WA Docs/` | 7 | International Building, Fire, Mechanical, Residential, and Energy Codes with WA state amendments |
| 3 | SPU Design Standards | `SPU Design Standards/` | 14 | Seattle Public Utilities engineering and design standards |
| 4 | SMC Chapters | `SMC_Chapters/` | 22 | Seattle Municipal Code — city ordinances organized by Title |
| 5 | Seattle DIR Rules | `Seattle_Active_DIR_Rules/` | 179 | Seattle Director's Rules — building, zoning, and land use interpretations |
| 6 | Washington Court Opinions | `washington_court_opinions/` | 199 | Washington Supreme Court and Court of Appeals published opinions |
| 7 | RCW Chapters | `RCW_Chapters/` | 2,762 | Revised Code of Washington — state statutes organized by Title (100 title subdirectories) |
| 8 | WAC Chapters | `WAC_Chapters/` | 2,826 | Washington Administrative Code — state agency regulations (227 title subdirectories) |

---

## 3. Embedding Strategy

### Options Evaluated

| Option | Model | Type | Dimensions | Quality | Cost (est.) |
|---|---|---|---|---|---|
| 1 | `all-MiniLM-L6-v2` | Local (sentence-transformers) | 384 | Good | Free |
| 2 | `text-embedding-3-small` | OpenAI API | 1,536 | Better | ~$0.92 |
| **3 (chosen)** | **`text-embedding-3-large`** | **OpenAI API** | **3,072** | **Best** | **~$5.85** |

### Decision Rationale
- **Quality over cost:** For legal text where precision matters, the highest quality model was chosen.
- **Cost is minimal:** ~$5.85 for the entire corpus (estimated 45 million tokens) is negligible.
- **Local storage:** Embeddings are computed via API but stored locally in ChromaDB — data never leaves the machine after embedding.
- **One-time cost:** Embeddings only need to be generated once. Subsequent queries use locally stored vectors.

---

## 4. Chunking Strategy

### Parameters
| Parameter | Value | Rationale |
|---|---|---|
| **Chunk size** | 1,000 characters | Balances context preservation with retrieval granularity for legal text |
| **Chunk overlap** | 200 characters | Ensures continuity across chunk boundaries — important for multi-section legal provisions |
| **Splitter** | `RecursiveCharacterTextSplitter` (LangChain) | Hierarchical splitting with custom separators |

### Legal-Text-Aware Separators (ordered by priority)
```
1. "\n\n"           — paragraph break
2. "\nChapter "     — chapter heading
3. "\nSection "     — section heading
4. "\nRCW "         — RCW section reference
5. "\nWAC "         — WAC section reference
6. "\nSMC "         — SMC section reference
7. "\n§ "           — section symbol
8. "\nArt. "        — article
9. "\n("            — numbered subsection e.g. (1), (a)
10. "\n"            — single newline
11. ". "            — sentence boundary
12. " "             — word boundary (last resort)
```

These custom separators ensure chunks respect the natural structure of legal documents rather than splitting mid-section.

---

## 5. PDF Extraction

- **Library used:** PyMuPDF (`fitz`) — chosen for speed and reliability over PyPDF2
- **Extraction method:** `page.get_text()` per page
- **Metadata preserved per page:**
  - `library` — which library the document belongs to
  - `source_file` — original PDF filename
  - `title` — document title (from PDF metadata or filename)
  - `page_number` — page within the document
- **Known limitation:** 37 PDFs across all libraries are scanned images with no extractable text. OCR (e.g., Tesseract) could be added later.

---

## 6. Embedding Execution

### Model Details
| Parameter | Value |
|---|---|
| Model | `text-embedding-3-large` |
| Provider | OpenAI |
| Dimensions | 3,072 |
| Batch size | 500 chunks per API call |
| API endpoint | `POST https://api.openai.com/v1/embeddings` |

### Ingestion Results (folder by folder)

| # | Library | Files | Chunks | Time | Errors | Date |
|---|---|---|---|---|---|---|
| 1 | WA Governor Orders | 12 | 146 | 4s | 1 (scanned PDF) | 2026-02-10 |
| 2 | IBC WA Docs | 7 | 3,120 | 22s | 0 | 2026-02-10 |
| 3 | SPU Design Standards | 14 | 3,962 | 23s | 0 | 2026-02-10 |
| 4 | SMC Chapters | 22 | 22,288 | 3m 20s | 0 | 2026-02-10 |
| 5 | Seattle DIR Rules | 179 | 5,606 | 53s | 36 (scanned PDFs) | 2026-02-10 |
| 6 | Washington Court Opinions | 199 | 16,281 | 1m 37s | 0 | 2026-02-10 |
| 7 | RCW Chapters | 2,762 | 147,316 | 18m | 0 | 2026-02-10 |
| 8 | WAC Chapters | 2,826 | 200,661 | 31m | 0 | 2026-02-10 |
| **TOTAL** | | **6,021** | **399,380** | **~55 min** | **37** | |

### Token & Cost Estimates
- **Estimated total tokens:** ~45 million (across all 6,021 PDFs)
- **Estimated embedding cost:** ~$5.85 (at $0.13 per 1M tokens for `text-embedding-3-large`)
- **Actual total embedding time:** ~55 minutes (primarily API rate-limited)

---

## 7. Vector Store

### Technology
- **Database:** ChromaDB (persistent mode)
- **Storage path:** `./data/chromadb/`
- **Distance metric:** Cosine similarity (`hnsw:space: cosine`)
- **Upsert batch size:** 5,000 chunks per upsert call

### Collection Strategy
Each document library has its own ChromaDB collection. This provides:
- **Isolation:** Libraries don't interfere with each other during search
- **Targeted search:** Can search a single collection (e.g., only RCW) for better precision
- **Cross-collection search:** Can search multiple or all collections and merge results
- **Independent updates:** Can re-ingest one library without affecting others

### Collections

| Collection Name | Chunks |
|---|---|
| `wa_governor_orders` | 146 |
| `ibc_wa_docs` | 3,120 |
| `spu_design_standards` | 3,962 |
| `smc_chapters` | 22,288 |
| `seattle_dir_rules` | 5,606 |
| `washington_court_opinions` | 16,281 |
| `rcw_chapters` | 147,316 |
| `wac_chapters` | 200,661 |
| **Total** | **399,380** |

---

## 8. Search Quality Verification

40 test queries were run across all 8 libraries (5 per library). Every query returned the correct source document as the top result.

### Sample Results by Library

**WA Governor Orders**
| Query | Top Result | Score |
|---|---|---|
| "immigrant protection" | `25-09 - Reaffirming Washington's Commitment...` | 0.46 |

**IBC WA Docs**
| Query | Top Result | Score |
|---|---|---|
| "maximum building height for residential buildings" | `IBC International Building Code.pdf` Table 504.3 | 0.47 |

**SPU Design Standards**
| Query | Top Result | Score |
|---|---|---|
| "cathodic protection requirements" | `6CathodicProtectionFinalRedacted.pdf` | 0.69 |
| "pump station design criteria" | `11PumpStationsFinalRedacted.pdf` | 0.68 |
| "SCADA system requirements" | `10IC-SCADA-FinalRedacted.pdf` | 0.54 |
| "water infrastructure pipe material" | `5WaterInfrastructureFinalRedacted.pdf` | 0.54 |
| "physical security fence access control" | `15PhysicalSecurityFinalRedacted.pdf` | 0.57 |

**SMC Chapters**
| Query | Top Result | Score |
|---|---|---|
| "Seattle noise regulations" | `Title 25 - Environmental Protection` | 0.69 |
| "land use zoning requirements" | `Title 23 - Land Use Code` | 0.53 |
| "criminal code theft penalties" | `Title 12A - Criminal Code` | 0.51 |
| "sidewalk cafe permit requirements" | `Title 15 - Street and Sidewalk Use` | 0.64 |
| "utility rate increases water sewer" | `Title 21 - Utilities` | 0.54 |

**Seattle DIR Rules**
| Query | Top Result | Score |
|---|---|---|
| "RRIO inspection process rental properties" | `23-2017 - RRIO checklist.pdf` | 0.63 |
| "stormwater drainage requirements" | `17-2017 - Stormwater Manual.pdf` | 0.65 |
| "design review requirements new construction" | `11-2003 - Design Guidelines Link Light Rail` | 0.52 |
| "tenant relocation assistance eviction" | `16-2020 - Tenant Relocation Assistance` | 0.59 |
| "fire sprinkler system inspection" | `24-2014 - Field Inspection Procedures` | 0.52 |

**Washington Court Opinions**
| Query | Top Result | Score |
|---|---|---|
| "State v. Bell" | `State v. Bell.pdf` | **0.76** |
| "employment discrimination wrongful termination" | `Suarez v. State.pdf` | 0.54 |
| "property tax assessment appeal" | `Hardel Mut. Plywood Corp. v. Lewis County.pdf` | 0.50 |
| "child custody dependency proceedings" | `In re Dependency of E.M..pdf` | 0.60 |
| "insurance coverage dispute liability" | `New York Life Ins. Co. v. Mitchell.pdf` | 0.51 |

**RCW Chapters**
| Query | Top Result | Score |
|---|---|---|
| "landlord tenant eviction notice requirements" | `RCW_59.18_Residential_landlord-tenant_act.pdf` | 0.59 |
| "DUI penalties blood alcohol level" | `RCW_46.61_Rules_of_the_road.pdf` | 0.53 |
| "environmental protection water quality standards" | `RCW_90.48_Water_pollution_control.pdf` | 0.60 |
| "workers compensation injury claim filing" | `RCW_51.28_Notice_and_report_of_accident.pdf` | 0.53 |
| "marijuana cannabis regulation licensing" | `RCW_66.08_Liquor_and_cannabis_board.pdf` | 0.56 |

**WAC Chapters**
| Query | Top Result | Score |
|---|---|---|
| "food safety restaurant inspection" | `WAC_16-165_Food_inspection.pdf` | 0.57 |
| "teacher certification requirements" | `WAC_181-79A_Standards_for_teacher...certification.pdf` | 0.61 |
| "unemployment benefits eligibility" | `WAC_182-12_Eligible_and_noneligible_employees.pdf` | 0.52 |
| "hazardous waste disposal regulations" | `WAC_173-303_Dangerous_waste_regulations.pdf` | 0.58 |
| "nursing home patient rights" | `WAC_388-97_Nursing_homes.pdf` | **0.71** |

### Score Interpretation
- **0.70+** — Excellent: near-exact semantic match
- **0.50–0.70** — Strong: confident, relevant retrieval
- **0.35–0.50** — Good: relevant but less specific
- **Below 0.35** — Noise / unlikely relevant

Legal text typically scores lower than conversational text due to its formal, domain-specific language. Scores of 0.50+ on legal documents indicate very strong retrieval.

---

## 9. Retrieval Engine (Phase 5)

Built in `src/core/retriever.py`. Provides multi-collection semantic search with intelligent routing.

### Features
| Feature | Description |
|---|---|
| Multi-collection search | Queries one or more of the 8 ChromaDB collections and merges results |
| Keyword auto-routing | ~180 regex patterns detect relevant libraries from query text (e.g., "DUI" → RCW only) |
| Metadata filtering | ChromaDB `where` filters by library, source file, page, etc. |
| Cross-collection re-ranking | All candidates sorted by cosine similarity regardless of source collection |
| Deduplication | Same source + page doesn't repeat in results |
| LLM context formatting | `retrieve_with_context()` produces citation-annotated text blocks for LLM prompts |

### Auto-Routing Keyword Coverage
| Library | Example Keywords |
|---|---|
| RCW Chapters (~50 patterns) | RCW, homicide, assault, DUI, divorce, child custody, landlord, eviction, foreclosure, cannabis, probate, consumer protection |
| WAC Chapters (~50 patterns) | WAC, Ecology, groundwater, DOH, immunization, DSHS, nursing home, L&I, OSHA, teacher certification, property tax, hunting, pesticide |
| SMC Chapters (~25 patterns) | SMC, seattle zoning, seattle noise, FAR, height limit, seattle tree, seattle harbor |
| IBC WA Docs (~25 patterns) | IBC, IFC, IRC, IMC, IECC, fire sprinkler, egress, seismic, HVAC, ADA, occupant load |
| SPU Design Standards (~20 patterns) | SPU, pump station, cathodic, SCADA, water main, combined sewer, CSO, switchgear |
| Seattle DIR Rules (~25 patterns) | DIR, SDCI, RRIO, streetscape, green factor, tree protection, shotcrete, Master Use Permit |
| WA Governor Orders (~15 patterns) | executive order, governor, immigrant, tribal nation, FAFSA, clean energy, project labor |
| Court Opinions (~20 patterns) | court opinion, supreme court, plaintiff, defendant, summary judgment, certiorari, remand, dissent |

### Retriever Verification (6 test queries)
| Query | Auto-Routed To | Top Result | Score |
|---|---|---|---|
| "child custody rules in divorce" | RCW only | `RCW_26.27_Child_Custody.pdf` | 0.48 |
| "nursing home patient abuse reporting" | WAC only | `WAC_388-97_Nursing_homes.pdf` | 0.63 |
| "fire sprinkler requirements high rise" | IBC only | `IBC International Fire Code.pdf` | 0.60 |
| "SCADA pump station electrical design" | WAC + SPU | `SPU 11PumpStations.pdf` | 0.66 |
| "RRIO rental tenant relocation assistance" | RCW + DIR | `DIR 16-2020 Tenant Relocation.pdf` | 0.55 |
| "State v. Bell defendant appeal" | Court Opinions only | `State v. Bell.pdf` | **0.77** |

---

## 10. Chat Interface & LLM Integration (Phase 6)

Built a full-stack RAG chat application with GPT 5.1 streaming and a custom dark-theme UI.

### RAG Chain (`src/core/rag_chain.py`)
| Feature | Detail |
|---|---|
| LLM model | OpenAI `gpt-5.1` |
| Streaming | Token-by-token via Python generator → SSE events |
| Context injection | Retriever results formatted as numbered `[Source N]` blocks |
| Conversation memory | Last 20 messages (configurable via `CONVERSATION_MEMORY_SIZE`) |
| System prompt | Customizable per session; defaults to WA legal research assistant |
| Error handling | Retrieval failures and LLM API errors yield typed error events |

### FastAPI Backend (`src/app/main.py`)
| Endpoint | Method | Purpose |
|---|---|---|
| `/api/chat` | POST | SSE streaming chat (sources + tokens + done/error events) |
| `/api/settings` | GET/PUT | Read/update system instruction |
| `/api/chat/history` | DELETE | Clear conversation memory |
| `/` | GET | Serve chat UI (static files) |

### Chat UI (`src/app/static/`)
| File | Purpose |
|---|---|
| `index.html` | Page structure — header, sidebar, chat area, input |
| `style.css` | Dark glassmorphism theme with custom CSS properties, animations, responsive layout |
| `app.js` | SSE streaming client, markdown rendering (via `marked.js`), sidebar logic, source display |

### UI Features
- Dark-mode glassmorphism design with Inter font and accent colors
- Example query buttons on welcome screen
- Auto-resizing message input
- Expandable source badges showing library, file, page, and relevance score
- Slide-out sidebar for editing/resetting the system instruction
- Clear chat button with history reset
- Typing indicator animation during streaming
- Responsive layout for mobile/desktop

### GPT 5.1 API Notes
- Uses `max_completion_tokens` (not `max_tokens`) — required by the GPT 5.1 model family
- Default temperature: 0.1 (low for factual legal responses)
- Default max tokens: 2048

---

## 11. Architecture Decisions

| Decision | Choice | Why |
|---|---|---|
| PDF extractor | PyMuPDF (`fitz`) | Fastest, most reliable for structured PDFs |
| Text splitter | `RecursiveCharacterTextSplitter` | Hierarchical splitting with custom legal separators |
| Embedding model | `text-embedding-3-large` | Best quality for legal text precision |
| Vector store | ChromaDB (persistent) | Simple, local, no external dependencies |
| Collection strategy | One per library | Isolation, targeted search, independent updates |
| Chunk ID | MD5 hash of `library::filename::chunk_index` | Deterministic — re-runs upsert, no duplicates |
| Ingestion order | Smallest → largest library | Fail fast on small data before committing to large batches |
| Retrieval routing | Keyword auto-routing (~180 patterns) | Narrows search from 400K chunks to relevant collections |
| Re-ranking | Score-based cross-collection merge | Best results float to top regardless of source library |
| LLM model | GPT 5.1 | Latest model, best quality for legal Q&A |
| Chat UI framework | Custom HTML/CSS/JS | Maximum design control for glassmorphism, sidebar, and streaming UX |
| Streaming protocol | Server-Sent Events (SSE) | Simple, native browser support, no WebSocket complexity |
| Backend framework | FastAPI | Async support, automatic OpenAPI docs, SSE-friendly |

---

## 12. Core Modules

| Module | Purpose |
|---|---|
| `src/core/config.py` | Central configuration, library mappings, model settings, default system prompt |
| `src/core/pdf_loader.py` | PDF text extraction with per-page metadata |
| `src/core/chunker.py` | Legal-text-aware recursive text chunking |
| `src/core/embedder.py` | OpenAI embedding API wrapper with batching |
| `src/core/vector_store.py` | ChromaDB collection management, upsert, search |
| `src/core/ingest.py` | Ingestion orchestrator (load → chunk → embed → store) |
| `src/core/retriever.py` | Multi-collection retrieval with auto-routing, re-ranking, dedup |
| `src/core/rag_chain.py` | GPT 5.1 RAG chain with streaming, context injection, conversation memory |
| `src/app/main.py` | FastAPI server — SSE chat, settings, history endpoints, static file serving |
| `src/app/static/` | Chat UI — HTML, CSS (glassmorphism), JavaScript (SSE client, markdown) |

| Script | Purpose |
|---|---|
| `scripts/run_ingest.py` | CLI for running ingestion per library or all |
| `scripts/run_chat.py` | CLI to start the FastAPI chat server (`python scripts/run_chat.py`) |
| `scripts/test_library.py` | CLI for testing search against a single collection |
| `scripts/test_retriever.py` | CLI for testing multi-collection retrieval with auto-routing |
| `scripts/estimate_tokens.py` | Estimate token counts and embedding costs |

---

## 13. Dependencies

```
fastapi, uvicorn, python-dotenv, langchain, langchain-community, langchain-openai,
chromadb, sentence-transformers, requests, pydantic, pytest, PyMuPDF,
tiktoken, tqdm, openai, sse-starlette
```

Frontend CDN: `marked.js` (markdown rendering), Google Fonts (Inter)

---

## 14. Known Issues & Limitations

1. **37 scanned image PDFs** have no extractable text (mostly older DIR Rules from 1980s–90s and one Governor's Order). OCR integration (e.g., Tesseract) would capture these.
2. **Python version:** The system runs on Python 3.9 (macOS default). Type hints use `Optional[X]` instead of `X | None` for compatibility.
3. **No OCR:** Current pipeline only extracts text-layer PDFs. Image-only PDFs are skipped.
4. **In-memory state:** Conversation history and system prompt changes are stored in-memory — lost on server restart.

---

## 15. What's Next

- [x] **Retrieval engine** — multi-collection search with auto-routing & re-ranking ✓
- [x] **RAG chain** — GPT 5.1 with streaming, context injection, conversation memory ✓
- [x] **FastAPI backend** — SSE streaming chat, settings, and history endpoints ✓
- [x] **Chat UI** — custom dark glassmorphism interface with editable system instructions ✓
- [ ] **OCR integration** — capture text from scanned image PDFs
- [ ] **Automated tests** — unit tests for all core modules
- [ ] **Persistent chat history** — save conversations across server restarts
- [ ] **Deployment** — containerization and hosting strategy
