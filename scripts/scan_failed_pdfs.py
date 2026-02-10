#!/usr/bin/env python3
"""
Scan all libraries and identify PDFs with no extractable text.
Outputs a structured report.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.config import LIBRARIES, LIBRARY_ORDER
from src.core.pdf_loader import extract_pdf, find_pdfs


def main():
    total_failed = 0
    total_scanned = 0

    for key in LIBRARY_ORDER:
        lib = LIBRARIES[key]
        pdfs = find_pdfs(lib["path"])
        failed = []

        for pdf_path in pdfs:
            total_scanned += 1
            try:
                pages = extract_pdf(pdf_path, key)
                if not pages:
                    failed.append(pdf_path)
            except Exception as e:
                failed.append(pdf_path)

        if failed:
            print(f"\n### {lib['name']} ({len(failed)} of {len(pdfs)} failed)")
            for f in sorted(failed):
                # Check file size
                size_kb = f.stat().st_size / 1024
                print(f"| `{f.name}` | {size_kb:.0f} KB |")
            total_failed += len(failed)

    print(f"\n---")
    print(f"**Total:** {total_failed} failed out of {total_scanned} scanned")


if __name__ == "__main__":
    main()
