"""
FastAPI Chat Server — SSE streaming RAG chat with settings management.
"""

import hmac
import json
import secrets
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status, Security
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from typing import Dict, List

from src.core.config import (
    DEFAULT_SYSTEM_PROMPT,
    LLM_TEMPERATURE,
    API_ACCESS_KEY,
    LIBRARIES,
    ALL_DOCUMENTS_DIR,
)
from src.core.rag_chain import chat_stream
from src.core.session_logger import log_session
from src.core.retrieval_logger import log_retrieval


# ── App setup ────────────────────────────────────────────────────────────
app = FastAPI(title="RAG Agent — WA Legal Research", version="1.0.0")

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ── Shares DB ─────────────────────────────────────────────────────────────
SHARES_DB_PATH = Path("./data/shares.db")

def init_shares_db():
    conn = sqlite3.connect(SHARES_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS shared_conversations (
            share_id          TEXT PRIMARY KEY,
            created_at        TEXT NOT NULL,
            expires_at        TEXT,
            title             TEXT NOT NULL,
            conversation_json TEXT NOT NULL,
            message_count     INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()

@app.on_event("startup")
async def startup():
    init_shares_db()


# ── In-memory state ──────────────────────────────────────────────────────
# ── In-memory state ──────────────────────────────────────────────────────
# Map session_id (str) -> dict of state
sessions: Dict[str, Dict] = {}

# ── Auth ─────────────────────────────────────────────────────────────────
API_KEY_HEADER = APIKeyHeader(name="x-api-key", auto_error=False)

async def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    """Enforce API Key authentication if API_ACCESS_KEY is set."""
    if not API_ACCESS_KEY:
        # If no key configured, allow open access (dev mode)
        return api_key

    if not api_key or not hmac.compare_digest(api_key, API_ACCESS_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API Key"
        )
    return api_key

def get_session_state(session_id: str) -> Dict:
    """Get or create session state."""
    if session_id not in sessions:
        sessions[session_id] = {
            "system_prompt": DEFAULT_SYSTEM_PROMPT,
            "conversation_history": [],
            "temperature": LLM_TEMPERATURE,
        }
    return sessions[session_id]


# ── Request / Response models ────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    session_id: str = Field(..., min_length=1, max_length=100)
    top_k: Optional[int] = Field(None, ge=1, le=100)


class SettingsRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=100)
    system_prompt: str = Field(..., max_length=50000)
    temperature: Optional[float] = Field(None, ge=0.0, le=1.0)


class ShareRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=100)


# ── Routes ───────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serve the chat UI."""
    index_path = STATIC_DIR / "index.html"
    return HTMLResponse(content=index_path.read_text(), status_code=200)


@app.post("/api/chat", dependencies=[Depends(verify_api_key)])
async def chat_endpoint(request: ChatRequest):
    """Stream a RAG-augmented chat response via SSE."""
    state = get_session_state(request.session_id)
    
    full_tokens = []
    usage_info = {"input_tokens": 0, "output_tokens": 0}
    sources_data = []  # Store full source objects for logging
    start_time = time.time()

    def event_generator():
        nonlocal sources_data
        history_saved = False
        try:
            for event in chat_stream(
                user_message=request.message,
                conversation_history=state["conversation_history"],
                system_prompt=state["system_prompt"],
                top_k=request.top_k,
                temperature=state["temperature"],
            ):
                if event["type"] == "token":
                    full_tokens.append(event["data"])
                elif event["type"] == "sources":
                    sources_data = event.get("data", [])
                elif event["type"] == "usage":
                    usage_info.update(event.get("data", {}))
                elif event["type"] == "done":
                    # Save to conversation history
                    answer_text = "".join(full_tokens)
                    state["conversation_history"].append(
                        {"role": "user", "content": request.message}
                    )
                    state["conversation_history"].append(
                        {"role": "assistant", "content": answer_text}
                    )
                    history_saved = True
                    # Log session (isolated so failures don't break the stream)
                    try:
                        duration_ms = int((time.time() - start_time) * 1000)
                        log_session(
                            session_id=request.session_id,
                            question=request.message,
                            answer=answer_text,
                            input_tokens=usage_info["input_tokens"],
                            output_tokens=usage_info["output_tokens"],
                            sources_count=len(sources_data),
                            temperature=state["temperature"],
                            duration_ms=duration_ms,
                        )
                        log_retrieval(
                            session_id=request.session_id,
                            question=request.message,
                            sources=sources_data,
                            temperature=state["temperature"],
                        )
                    except Exception:
                        pass  # Logging failure must not affect chat or history
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            # Fallback: save history even if streaming was interrupted early
            if not history_saved and full_tokens:
                answer_text = "".join(full_tokens)
                state["conversation_history"].append(
                    {"role": "user", "content": request.message}
                )
                state["conversation_history"].append(
                    {"role": "assistant", "content": answer_text}
                )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/settings", dependencies=[Depends(verify_api_key)])
async def get_settings(session_id: str):
    """Get current system instruction and temperature."""
    state = get_session_state(session_id)
    return {
        "system_prompt": state["system_prompt"],
        "temperature": state["temperature"],
    }


@app.put("/api/settings", dependencies=[Depends(verify_api_key)])
async def update_settings(request: SettingsRequest):
    """Update the system instruction and/or temperature."""
    state = get_session_state(request.session_id)
    state["system_prompt"] = request.system_prompt
    if request.temperature is not None:
        state["temperature"] = max(0.0, min(1.0, request.temperature))
    return {
        "status": "ok",
        "system_prompt": state["system_prompt"],
        "temperature": state["temperature"],
    }


@app.delete("/api/chat/history", dependencies=[Depends(verify_api_key)])
async def clear_history(session_id: str):
    """Clear conversation history for a specific session."""
    if session_id in sessions:
        sessions[session_id]["conversation_history"] = []
    return {
        "status": "ok",
        "message": "Conversation cleared",
        "session_id": session_id
    }


# ── Share endpoints ───────────────────────────────────────────────────────

@app.post("/api/share", dependencies=[Depends(verify_api_key)])
async def create_share(req: ShareRequest):
    """Save a conversation to disk and return a shareable link."""
    session = sessions.get(req.session_id)
    if not session or not session.get("conversation_history"):
        raise HTTPException(status_code=404, detail="Session not found or empty")

    history = session["conversation_history"]
    title = next(
        (m["content"][:80] for m in history if m["role"] == "user"), "Untitled"
    )
    now = datetime.now(timezone.utc)
    share_id = secrets.token_urlsafe(12)  # 16-char URL-safe random token

    conn = sqlite3.connect(SHARES_DB_PATH)
    conn.execute(
        "INSERT INTO shared_conversations VALUES (?, ?, ?, ?, ?, ?)",
        (share_id, now.isoformat(), None,
         title, json.dumps(history), len(history)),
    )
    conn.commit()
    conn.close()

    return {"share_id": share_id, "share_url": f"/share/{share_id}"}


@app.get("/api/share/{share_id}")
async def get_share(share_id: str):
    """Retrieve a shared conversation by its ID."""
    conn = sqlite3.connect(SHARES_DB_PATH)
    row = conn.execute(
        "SELECT title, conversation_json, created_at, expires_at "
        "FROM shared_conversations WHERE share_id = ?",
        (share_id,),
    ).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Share not found")

    # Check expiry only if expires_at was set (legacy rows)
    if row[3]:
        expires_at = datetime.fromisoformat(row[3])
        if datetime.now(timezone.utc) > expires_at:
            raise HTTPException(status_code=410, detail="This link has expired")

    return {
        "title": row[0],
        "conversation": json.loads(row[1]),
        "created_at": row[2],
    }


@app.get("/share/{share_id}")
async def share_page(share_id: str):
    """Serve the read-only shared conversation view."""
    return FileResponse(str(STATIC_DIR / "share.html"))


# ── Document serving ────────────────────────────────────────────────────

def _resolve_document_path(library_key: str, filename: str):
    """Locate a PDF on disk, validating against directory traversal."""
    if library_key not in LIBRARIES:
        return None
    if "/" in filename or "\\" in filename or ".." in filename:
        return None
    if not filename.lower().endswith(".pdf"):
        return None

    lib_path = LIBRARIES[library_key]["path"]
    it = lib_path.rglob(filename)
    first_match = next(it, None)
    if first_match is None:
        return None
    second_match = next(it, None)
    if second_match is not None:
        return None

    resolved = first_match.resolve()
    base_dir = ALL_DOCUMENTS_DIR.resolve()
    try:
        resolved.relative_to(base_dir)
    except ValueError:
        return None

    return resolved


@app.get("/api/documents/{library_key}/{filename}")
async def serve_document(library_key: str, filename: str):
    """Stream a PDF from disk for the document viewer."""
    path = _resolve_document_path(library_key, filename)
    if path is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return FileResponse(
        str(path),
        media_type="application/pdf",
        headers={"Content-Disposition": "inline"},
    )
