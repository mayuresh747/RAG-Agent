"""
FastAPI Chat Server — SSE streaming RAG chat with settings management.
"""

import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.core.config import DEFAULT_SYSTEM_PROMPT, LLM_TEMPERATURE
from src.core.rag_chain import chat_stream


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
    top_k: Optional[int] = 10


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

    def event_generator():
        for event in chat_stream(
            user_message=request.message,
            conversation_history=_state["conversation_history"],
            system_prompt=_state["system_prompt"],
            top_k=request.top_k or 10,
            temperature=_state["temperature"],
        ):
            if event["type"] == "token":
                full_tokens.append(event["data"])
            elif event["type"] == "done":
                # Save to conversation history
                _state["conversation_history"].append(
                    {"role": "user", "content": request.message}
                )
                _state["conversation_history"].append(
                    {"role": "assistant", "content": "".join(full_tokens)}
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
