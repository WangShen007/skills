#!/usr/bin/env python3
"""
Extract text from a PDF into a UTF-8 .txt file using pypdf.

This is intentionally minimal and dependency-light; PDF text extraction quality
depends on the PDF itself.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def extract_pdf_text(pdf_path: Path, max_pages: int | None = None) -> str:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception as e:  # pragma: no cover
        raise SystemExit(
            "Missing dependency 'pypdf'. Install with: python3 -m pip install pypdf"
        ) from e

    reader = PdfReader(str(pdf_path))
    pages = reader.pages
    if max_pages is not None:
        pages = pages[: max_pages]

    chunks: list[str] = []
    for i, page in enumerate(pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        chunks.append(f"\n\n--- Page {i} ---\n\n{text}".rstrip())
    return "\n".join(chunks).strip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract PDF text to a .txt file")
    parser.add_argument("--pdf", required=True, help="Path to input PDF")
    parser.add_argument("--out", required=True, help="Path to output .txt")
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Optional: limit number of pages to extract",
    )
    args = parser.parse_args()

    pdf_path = Path(args.pdf).expanduser().resolve()
    out_path = Path(args.out).expanduser().resolve()

    if not pdf_path.exists():
        raise SystemExit(f"PDF not found: {pdf_path}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    text = extract_pdf_text(pdf_path, max_pages=args.max_pages)
    out_path.write_text(text, encoding="utf-8")
    print(f"Wrote: {out_path}")


if __name__ == "__main__":
    main()

