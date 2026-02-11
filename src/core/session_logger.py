"""
Session Logger — writes chat session records to JSONL for audit trail.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from src.core.config import PROJECT_ROOT

LOGS_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOGS_DIR / "sessions.jsonl"


def log_session(
    question: str,
    answer: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    sources_count: int = 0,
    temperature: float = 0.1,
    duration_ms: int = 0,
) -> None:
    """Append a session record to the JSONL log file."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "question": question,
        "answer": answer,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "sources_count": sources_count,
        "temperature": temperature,
        "duration_ms": duration_ms,
    }

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
