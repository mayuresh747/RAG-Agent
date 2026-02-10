#!/usr/bin/env python3
"""
CLI entry point for document ingestion.

Usage:
    python scripts/run_ingest.py --library wa_governor_orders
    python scripts/run_ingest.py --all
"""

import argparse
import logging
import sys
from pathlib import Path

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.config import LIBRARIES, LIBRARY_ORDER
from src.core.ingest import ingest_library
from src.core.vector_store import collection_stats


def main():
    parser = argparse.ArgumentParser(description="Ingest PDFs into ChromaDB")
    parser.add_argument(
        "--library", "-l",
        type=str,
        choices=list(LIBRARIES.keys()),
        help="Ingest a single library by key",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Ingest all libraries in order",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Print collection stats and exit",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s  %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.stats:
        for key in LIBRARY_ORDER:
            s = collection_stats(key)
            print(f"  {key:35s}  {s['count']:>8,} chunks")
        return

    if args.library:
        summary = ingest_library(args.library)
        print(f"\n{'='*60}")
        print(f"Library:   {summary.get('library_name', summary['library'])}")
        print(f"Files:     {summary['total_files']}")
        print(f"Chunks:    {summary['total_chunks']}")
        print(f"Stored:    {summary.get('collection_count', 'N/A')}")
        print(f"Time:      {summary['elapsed_seconds']}s")
        if summary['errors']:
            print(f"Errors:    {len(summary['errors'])}")
            for e in summary['errors'][:10]:
                print(f"  - {e}")
        print(f"{'='*60}")

    elif args.all:
        for key in LIBRARY_ORDER:
            summary = ingest_library(key)
            print(f"  ✓ {key}: {summary['total_chunks']} chunks in {summary['elapsed_seconds']}s")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
