
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

# Log file path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / "retrievals.jsonl"

def log_retrieval(
    session_id: int,
    question: str,
    sources: List[Dict[str, Any]],
    temperature: float = 0.1,
) -> None:
    """
    Log retrieval details to a JSONL file.
    
    Args:
        session_id: The sequential session number.
        question: The user's query.
        sources: List of source dictionaries (file, library, text, score, etc).
        temperature: LLM temperature used.
    """
    # Ensure log directory exists
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "question": question,
        "temperature": temperature,
        "chunks_accessed": []
    }
    
    for s in sources:
        record["chunks_accessed"].append({
            "file": s.get("source_file"),
            "page": s.get("page_number"),
            "library": s.get("library"),
            "score": s.get("score"),
            "text_preview": (s.get("text") or "")[:100] + "..."  # Preview only to save space
        })
        
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
