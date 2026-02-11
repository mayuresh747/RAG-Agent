"""
RAG Chain — GPT 5.1 integration with retriever context injection and streaming.
"""

from typing import Optional, Generator
from openai import OpenAI

from src.core.config import (
    OPENAI_API_KEY,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
    CONVERSATION_MEMORY_SIZE,
    DEFAULT_SYSTEM_PROMPT,
)
from src.core.retriever import retrieve, RetrievalResult


# ── Lazy client ──────────────────────────────────────────────────────────
_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


# ── Context builder ──────────────────────────────────────────────────────

def _build_context_block(result: RetrievalResult) -> str:
    """Format retriever results into a context block for the LLM."""
    if not result.chunks:
        return "(No relevant documents found.)"

    blocks = []
    for i, chunk in enumerate(result.chunks, 1):
        source = chunk.source_file
        library = chunk.library
        page = chunk.page_number
        score = chunk.score
        text = chunk.text

        blocks.append(
            f"[Source {i}] {source} (Library: {library}, Page: {page}, "
            f"Relevance: {score:.2f})\n{text}"
        )

    return "\n\n---\n\n".join(blocks)


# ── Main chat function ───────────────────────────────────────────────────

def chat_stream(
    user_message: str,
    conversation_history: list,
    system_prompt: Optional[str] = None,
    top_k: int = 10,
    temperature: Optional[float] = None,
    max_context_chars: int = 10000,
) -> Generator[dict, None, None]:
    """
    Stream a RAG-augmented chat response.

    Yields dicts with keys:
        - {"type": "sources", "data": [...]}     — retrieved source metadata
        - {"type": "token", "data": "..."}       — streamed token
        - {"type": "done"}                       — stream finished
        - {"type": "error", "data": "..."}       — error message
    """
    system = system_prompt or DEFAULT_SYSTEM_PROMPT

    # 1) Retrieve relevant context
    try:
        retrieval_result = retrieve(
            query=user_message,
            top_k=top_k,
            auto_route=True,
            min_score=0.25,
        )
    except Exception as e:
        yield {"type": "error", "data": f"Retrieval error: {e}"}
        return

    # 2) Yield source metadata to the UI (include text for expansion)
    sources = []
    for chunk in retrieval_result.chunks:
        sources.append({
            "source_file": chunk.source_file,
            "library": chunk.library,
            "page_number": chunk.page_number,
            "score": round(chunk.score, 3),
            "text": chunk.text,
        })
    yield {"type": "sources", "data": sources}

    # 3) Build the augmented prompt
    context_block = _build_context_block(retrieval_result)

    augmented_system = (
        f"{system}\n\n"
        f"─── RETRIEVED CONTEXT ───\n\n"
        f"{context_block}\n\n"
        f"─── END CONTEXT ───\n\n"
        f"Use the above context to answer the user's question. "
        f"Cite sources by their [Source N] reference."
    )

    # 4) Build messages list with conversation memory
    messages = [{"role": "system", "content": augmented_system}]

    # Trim conversation history to memory size
    recent_history = conversation_history[-(CONVERSATION_MEMORY_SIZE * 2):]
    messages.extend(recent_history)

    messages.append({"role": "user", "content": user_message})

    # 5) Stream from GPT 5.1
    try:
        client = _get_client()
        temp = temperature if temperature is not None else LLM_TEMPERATURE
        stream = client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            temperature=temp,
            max_completion_tokens=LLM_MAX_TOKENS,
            stream=True,
        )

        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield {"type": "token", "data": chunk.choices[0].delta.content}

        yield {"type": "done"}

    except Exception as e:
        yield {"type": "error", "data": f"LLM error: {e}"}


def chat_sync(
    user_message: str,
    conversation_history: list,
    system_prompt: Optional[str] = None,
    top_k: int = 10,
    temperature: Optional[float] = None,
) -> dict:
    """Non-streaming version — returns full response at once."""
    tokens = []
    sources = []
    error = None

    for event in chat_stream(user_message, conversation_history, system_prompt, top_k, temperature):
        if event["type"] == "token":
            tokens.append(event["data"])
        elif event["type"] == "sources":
            sources = event["data"]
        elif event["type"] == "error":
            error = event["data"]

    return {
        "response": "".join(tokens),
        "sources": sources,
        "error": error,
    }
