"""
FastAPI Chat Server — SSE streaming RAG chat with settings management.
"""

import json
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status, Security
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from typing import Dict, List

from src.core.config import (
    DEFAULT_SYSTEM_PROMPT, 
    LLM_TEMPERATURE, 
    API_ACCESS_KEY
)
from src.core.rag_chain import chat_stream
from src.core.session_logger import log_session
from src.core.retrieval_logger import log_retrieval


# ── App setup ────────────────────────────────────────────────────────────
app = FastAPI(title="RAG Agent — WA Legal Research", version="1.0.0")

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


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
        
    if not api_key or api_key != API_ACCESS_KEY:
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
    message: str
    session_id: str
    top_k: Optional[int] = 25


class SettingsRequest(BaseModel):
    session_id: str
    system_prompt: str
    temperature: Optional[float] = None


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
        for event in chat_stream(
            user_message=request.message,
            conversation_history=state["conversation_history"],
            system_prompt=state["system_prompt"],
            top_k=request.top_k or 10,
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
                # Log session
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
                # Log detailed retrieval
                log_retrieval(
                    session_id=request.session_id,
                    question=request.message,
                    sources=sources_data,
                    temperature=state["temperature"],
                )
            yield f"data: {json.dumps(event)}\n\n"

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
