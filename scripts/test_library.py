#!/usr/bin/env python3
"""
Quick test: embed a query and search a ChromaDB collection.

Usage:
    python scripts/test_library.py --library wa_governor_orders --query "immigrant protection"
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.embedder import embed_query
from src.core.vector_store import search, collection_stats


def main():
    parser = argparse.ArgumentParser(description="Test search against a library")
    parser.add_argument("--library", "-l", required=True, help="Collection name")
    parser.add_argument("--query", "-q", required=True, help="Search query")
    parser.add_argument("--top-k", "-k", type=int, default=5, help="Number of results")
    args = parser.parse_args()

    stats = collection_stats(args.library)
    print(f"\nCollection: {args.library}  ({stats['count']} chunks)")
    print(f"Query:      \"{args.query}\"")
    print(f"Top-K:      {args.top_k}")
    print("─" * 70)

    query_vec = embed_query(args.query)
    results = search(args.library, query_vec, n_results=args.top_k)

    for i, (doc, meta, dist) in enumerate(
        zip(results["documents"][0], results["metadatas"][0], results["distances"][0]),
        start=1,
    ):
        score = 1 - dist  # cosine distance → similarity
        print(f"\n  [{i}]  score={score:.4f}  | {meta.get('source_file', '?')}  p.{meta.get('page_number', '?')}")
        # Show first 300 chars of the chunk
        snippet = doc[:300].replace("\n", " ")
        print(f"       {snippet}...")

    print("\n" + "─" * 70)
    print("✓ Search complete\n")


if __name__ == "__main__":
    main()
