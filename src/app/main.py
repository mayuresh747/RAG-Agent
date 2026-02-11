"""
FastAPI Chat Server — SSE streaming RAG chat with settings management.
"""

import json
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.core.config import DEFAULT_SYSTEM_PROMPT, LLM_TEMPERATURE
from src.core.rag_chain import chat_stream
from src.core.session_logger import log_session
from src.core.retrieval_logger import log_retrieval


# ── App setup ────────────────────────────────────────────────────────────
app = FastAPI(title="RAG Agent — WA Legal Research", version="1.0.0")

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── In-memory state ──────────────────────────────────────────────────────
_state = {
    "system_prompt": DEFAULT_SYSTEM_PROMPT,
    "conversation_history": [],
    "temperature": LLM_TEMPERATURE,
}


# ── Request / Response models ────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    top_k: Optional[int] = 25


class SettingsRequest(BaseModel):
    system_prompt: str
    temperature: Optional[float] = None


# ── Routes ───────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serve the chat UI."""
    index_path = STATIC_DIR / "index.html"
    return HTMLResponse(content=index_path.read_text(), status_code=200)


@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """Stream a RAG-augmented chat response via SSE."""
    full_tokens = []
    usage_info = {"input_tokens": 0, "output_tokens": 0}
    sources_data = []  # Store full source objects for logging
    start_time = time.time()

    def event_generator():
        nonlocal sources_data
        for event in chat_stream(
            user_message=request.message,
            conversation_history=_state["conversation_history"],
            system_prompt=_state["system_prompt"],
            top_k=request.top_k or 10,
            temperature=_state["temperature"],
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
                _state["conversation_history"].append(
                    {"role": "user", "content": request.message}
                )
                _state["conversation_history"].append(
                    {"role": "assistant", "content": answer_text}
                )
                # Log session
                duration_ms = int((time.time() - start_time) * 1000)
                log_session(
                    question=request.message,
                    answer=answer_text,
                    input_tokens=usage_info["input_tokens"],
                    output_tokens=usage_info["output_tokens"],
                    sources_count=len(sources_data),
                    temperature=_state["temperature"],
                    duration_ms=duration_ms,
                )
                # Log detailed retrieval
                log_retrieval(
                    question=request.message,
                    sources=sources_data,
                    temperature=_state["temperature"],
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


@app.get("/api/settings")
async def get_settings():
    """Get current system instruction and temperature."""
    return {
        "system_prompt": _state["system_prompt"],
        "temperature": _state["temperature"],
    }


@app.put("/api/settings")
async def update_settings(request: SettingsRequest):
    """Update the system instruction and/or temperature."""
    _state["system_prompt"] = request.system_prompt
    if request.temperature is not None:
        _state["temperature"] = max(0.0, min(1.0, request.temperature))
    return {
        "status": "ok",
        "system_prompt": _state["system_prompt"],
        "temperature": _state["temperature"],
    }


@app.delete("/api/chat/history")
async def clear_history():
    """Clear conversation history."""
    _state["conversation_history"] = []
    return {"status": "ok", "message": "Conversation cleared"}
