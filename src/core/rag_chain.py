"""
RAG Chain — GPT 5.1 integration with retriever context injection and streaming.
"""

from typing import Optional, Generator
from openai import OpenAI

from src.core.config import (
    OPENAI_API_KEY,
    LLM_MODEL,
    LLM_FAST,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
    CONVERSATION_MEMORY_SIZE,
    DEFAULT_SYSTEM_PROMPT,
    USE_MULTI_AGENT,
)
from src.core.retriever import retrieve, RetrievalResult
from src.core.multi_agent import multi_agent_retrieve
from src.core.context_builder import build_context, build_sources_metadata


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

def _is_complex_query(query: str, client: OpenAI) -> bool:
    """Determine if a query is asking for conflicts/comparisons using a fast LLM."""
    try:
        response = client.chat.completions.create(
            model=LLM_FAST,
            messages=[
                {"role": "system", "content": "You are a query classifier. Return 'COMPLEX' if the user is asking for a comparison, conflict, difference, preemption, or inconsistency between rules, agencies, or locations. Otherwise, return 'SIMPLE'."},
                {"role": "user", "content": query}
            ],
            temperature=0.0,
            max_tokens=10,
        )
        return "COMPLEX" in (response.choices[0].message.content or "").upper()
    except Exception:
        # Fallback to simple keyword logic if API fails
        complex_keywords = ["conflict", "inconsistenc", "difference", "preemption", "friction", "contradict", "at odds"]
        return any(kw in query.lower() for kw in complex_keywords)

def chat_stream(
    user_message: str,
    conversation_history: list,
    system_prompt: Optional[str] = None,
    top_k: Optional[int] = None,
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

    # Retrieve relevant context (multi-agent or legacy path)
    try:
        if USE_MULTI_AGENT:
            retrieval_result = multi_agent_retrieve(user_message, min_score=0.1)
            context_block = build_context(retrieval_result.chunks)
            sources = build_sources_metadata(retrieval_result.chunks)
            if retrieval_result.audit_trace:
                yield {"type": "audit", "data": retrieval_result.audit_trace}
        else:
            if top_k is None:
                client = _get_client()
                is_complex = _is_complex_query(user_message, client)
                top_k = 24 if is_complex else 12
            retrieval_result = retrieve(
                query=user_message,
                top_k=top_k,
                auto_route=True,
                min_score=0.25,
            )
            context_block = _build_context_block(retrieval_result)
            sources = [
                {
                    "source_file": c.source_file,
                    "library": c.library,
                    "page_number": c.page_number,
                    "score": round(c.score, 3),
                    "text": c.text,
                }
                for c in retrieval_result.chunks
            ]
    except Exception as e:
        yield {"type": "error", "data": f"Retrieval error: {e}"}
        return

    yield {"type": "sources", "data": sources}

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
            stream_options={"include_usage": True},
        )

        usage_data = None
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield {"type": "token", "data": chunk.choices[0].delta.content}
            # Capture usage from the final chunk
            if hasattr(chunk, "usage") and chunk.usage is not None:
                usage_data = {
                    "input_tokens": chunk.usage.prompt_tokens or 0,
                    "output_tokens": chunk.usage.completion_tokens or 0,
                }

        if usage_data:
            yield {"type": "usage", "data": usage_data}
        yield {"type": "done"}

    except Exception as e:
        yield {"type": "error", "data": f"LLM error: {e}"}


def chat_sync(
    user_message: str,
    conversation_history: list,
    system_prompt: Optional[str] = None,
    top_k: Optional[int] = None,
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
