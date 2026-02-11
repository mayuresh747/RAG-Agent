
import sys
import os
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from src.core.retriever import retrieve

def debug_query(query: str, top_k: int = 20):
    print(f"\n Query: {query}")
    print(f"🔍 Top-k: {top_k}")
    
    try:
        result = retrieve(query=query, top_k=top_k, auto_route=True)
        
        print(f"\nFound {len(result.chunks)} chunks.")
        
        for i, chunk in enumerate(result.chunks, 1):
            source_file = Path(chunk.source_file).name
            print(f"\n[{i}] Score: {chunk.score:.4f} | Lib: {chunk.library} | File: {source_file}")
            # Print first 200 chars to identify content
            formatted_text = chunk.text.replace("\n", " ")[:200]
            print(f"    Content: {formatted_text}...")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    queries = [
        "Does Seattle's minimum wage ordinance conflict with state RCW?",
        "Conflict between IBC egress width and ADA requirements?",
        "What are the requirements for ADUs in Seattle under SMC?"
    ]
    
    for q in queries:
        debug_query(q)
