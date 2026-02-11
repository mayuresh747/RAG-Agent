#!/usr/bin/env python3
"""
Test the multi-collection retrieval engine.

Usage:
    python scripts/test_retriever.py --query "building height limits"
    python scripts/test_retriever.py --query "RCW landlord tenant eviction" --top-k 10
    python scripts/test_retriever.py --query "stormwater drainage" --libraries seattle_dir_rules smc_chapters
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.retriever import retrieve, format_results_table, detect_relevant_libraries


def main():
    parser = argparse.ArgumentParser(description="Test multi-collection retrieval")
    parser.add_argument("--query", "-q", required=True, help="Search query")
    parser.add_argument("--top-k", "-k", type=int, default=5, help="Number of results")
    parser.add_argument("--libraries", "-l", nargs="+", help="Specific libraries to search")
    parser.add_argument("--all", action="store_true", help="Search all libraries (disable auto-routing)")
    parser.add_argument("--min-score", type=float, default=0.0, help="Minimum similarity score")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s  %(message)s",
        datefmt="%H:%M:%S",
    )

    # Show which libraries would be auto-selected
    if not args.libraries and not args.all:
        detected = detect_relevant_libraries(args.query)
        print(f"\n🔍 Auto-detected libraries: {', '.join(detected)}")

    result = retrieve(
        query=args.query,
        libraries=args.libraries,
        top_k=args.top_k,
        auto_route=not args.all,
        min_score=args.min_score,
    )

    print(f"\n{format_results_table(result)}")


if __name__ == "__main__":
    main()
