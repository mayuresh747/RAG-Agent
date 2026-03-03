# Changelog

All notable changes to the RAG Agent project are documented here.

## [1.0.0] — 2026-03-02

### Added
- 10 validated security and bug fixes (XSS, input validation, etc.)
- Upload scripts for AWS deployment (`upload_chunks_robust.sh`, `upload_paramiko.py`)
- AWS Lightsail deployment with Docker Compose + Caddy
- Domain: `seattlepolicyagent.duckdns.org`

### Changed
- `.gitignore` updated to exclude `.agent/` directory

---

## [0.9.0] — 2026-02-13

### Changed
- Renamed project and simplified README
- Optimized Docker build by excluding `data/` and `logs/` from context
- Excluded local log files from AWS deployment artifacts
- Docker volume mount for persistent log storage
- Stopped tracking `deploy_aws.sh`

---

## [0.8.0] — 2026-02-12

### Fixed
- XSS vulnerability — sanitized chat output

### Changed
- `.gitignore` updated for sensitive files (Caddyfile, `.ai`, logs)

---

## [0.7.0] — 2026-02-11

### Added
- Structured JSONL session & retrieval logging (`logs/sessions.jsonl`, `logs/retrievals.jsonl`)

### Fixed
- Source count inconsistency — consistently returns 25 sources per query

---

## [0.6.0] — 2026-02-10

### Added
- Full RAG pipeline: PDF extraction → chunking → embedding → ChromaDB storage
- 8 document libraries (6,021 PDFs, 399,380 chunks)
- Multi-collection retrieval engine with keyword auto-routing (~180 patterns)
- Cross-collection re-ranking and deduplication
- GPT-5.1 RAG chain with SSE streaming and conversation memory
- FastAPI backend with REST API endpoints
- Dark glassmorphism chat UI with editable system instructions
- Temperature slider and max tokens configuration
