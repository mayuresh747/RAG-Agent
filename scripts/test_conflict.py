
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.rag_chain import chat_sync
from src.core.config import DEFAULT_SYSTEM_PROMPT

query = "Audit the friction between State and City codes regarding wetland buffer widths for high-impact land use."

print(f"QUERY: {query}\n")
print("-" * 60)

response = chat_sync(
    user_message=query,
    conversation_history=[],
    system_prompt=DEFAULT_SYSTEM_PROMPT,
    top_k=8
)

print(response["response"])
print("-" * 60)
