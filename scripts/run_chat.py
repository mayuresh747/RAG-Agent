#!/usr/bin/env python3
"""
Start the RAG Agent chat server.

Usage:
    python scripts/run_chat.py              # default port 8000
    python scripts/run_chat.py --port 9000  # custom port
"""

import argparse
import sys
from pathlib import Path

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uvicorn


def main():
    parser = argparse.ArgumentParser(description="Start the RAG Agent chat server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    parser.add_argument("--reload", action="store_true", help="Auto-reload on code changes")
    args = parser.parse_args()

    print(f"\n🚀  RAG Agent starting at  http://localhost:{args.port}")
    print(f"📚  Press Ctrl+C to stop\n")

    uvicorn.run(
        "src.app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
