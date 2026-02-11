# RAG Agent — Washington State Legal Document Search

A local Retrieval-Augmented Generation (RAG) chatbot that processes and answers questions from **6,021 PDFs** (~2.6 GB) of Washington State legal documents. All embeddings are stored locally in ChromaDB for privacy and speed.

## What's Inside

- **399,380 embedded chunks** across 8 document libraries
- **OpenAI `text-embedding-3-large`** for high-quality semantic search (3,072 dimensions)
- **ChromaDB** persistent local vector store with cosine similarity
- **Legal-text-aware chunking** with custom separators for RCW, WAC, SMC, and IBC sections
- **Per-library collections** — each library is searchable independently or across all

## Document Libraries

| Library | Files | Chunks | Description |
|---|---|---|---|
| WA Governor Orders | 12 | 146 | Active executive orders (2025) |
| IBC WA Docs | 7 | 3,120 | International Building/Fire/Mechanical/Energy Codes (WA) |
| SPU Design Standards | 14 | 3,962 | Seattle Public Utilities engineering standards |
| SMC Chapters | 22 | 22,288 | Seattle Municipal Code — city ordinances |
| Seattle DIR Rules | 179 | 5,606 | Director's Rules — building/zoning interpretations |
| Court Opinions | 199 | 16,281 | WA Supreme Court & Court of Appeals opinions |
| RCW Chapters | 2,762 | 147,316 | Revised Code of Washington — state statutes |
| WAC Chapters | 2,826 | 200,661 | WA Administrative Code — state agency regulations |
| **Total** | **6,021** | **399,380** | |

## Getting Started

### Prerequisites

- Python 3.9+
- OpenAI API key (for embeddings)

### Installation

```bash
git clone <repository-url>
cd "RAG Agent"

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
python3 -m pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env — add your OPENAI_API_KEY
```

### Ingest Documents

Documents are ingested folder by folder. The order goes from smallest to largest library:

```bash
# Ingest a single library
python3 scripts/run_ingest.py --library wa_governor_orders

# Ingest all libraries sequentially
python3 scripts/run_ingest.py --all

# Check collection stats
python3 scripts/run_ingest.py --stats
```

### Search / Test

```bash
# Test search against a specific library
python3 scripts/test_library.py --library rcw_chapters --query "landlord tenant eviction notice"

# Test with custom top-K
python3 scripts/test_library.py -l wac_chapters -q "food safety inspection" -k 10
```

## Project Structure

```
RAG Agent/
├── All Documents/          # Source PDFs (8 library folders)
├── data/
│   └── chromadb/           # Persistent vector store (local)
├── scripts/
│   ├── run_ingest.py       # CLI for document ingestion
│   ├── test_library.py     # CLI for search testing
│   └── estimate_tokens.py  # Token count estimator
├── src/
│   ├── core/
│   │   ├── config.py       # Central configuration & library mappings
│   │   ├── pdf_loader.py   # PDF text extraction (PyMuPDF)
│   │   ├── chunker.py      # Legal-text-aware text chunking
│   │   ├── embedder.py     # OpenAI embedding wrapper
│   │   ├── vector_store.py # ChromaDB operations
│   │   ├── ingest.py       # Ingestion orchestrator
│   └── app/
│       ├── main.py         # FastAPI server
│       └── static/         # Frontend assets (HTML, CSS, JS)
├── tests/                  # Unit & integration tests
├── .env.example            # Environment variable template
├── requirements.txt        # Python dependencies
└── Project_memory.md       # Detailed project history & decisions
```

## Key Configuration

| Parameter | Value |
|---|---|
| Embedding Model | `text-embedding-3-large` (OpenAI) |
| Embedding Dimensions | 3,072 |
| Chunk Size | 1,000 characters |
| Chunk Overlap | 200 characters |
| Embedding Batch Size | 500 chunks/request |
| Vector Store | ChromaDB (cosine similarity) |
| LLM | `gpt-5.1` |

## Next Steps

- [x] Multi-collection retrieval engine with re-ranking
- [x] RAG chain with GPT-5.1 + conversation memory
- [x] FastAPI REST API endpoints
- [x] Web Chat Interface (Glassmorphism UI)
- [ ] OCR for scanned image PDFs (37 files skipped)

## Logging

The application logs key events to JSONL files in the `logs/` directory:
- `logs/sessions.jsonl`: Tracks chat sessions, including tokens usage, duration, and user queries.
- `logs/retrievals.jsonl`: Detailed breakdown of retrieved documents for each query.
