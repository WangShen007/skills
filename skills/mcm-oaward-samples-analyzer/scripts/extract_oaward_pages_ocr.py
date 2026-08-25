#!/usr/bin/env python3
"""
Extract OCR text from selected pages of the 2025 Problem C O-award PDFs:
- page 1 (Summary Sheet)
- pages 2-4 (TOC / early structure)
- last 6 pages (References / AI report)

Outputs per-paper text files to help manual review.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _lazy_imports():
    import fitz  # PyMuPDF
    import numpy as np
    from rapidocr_onnxruntime import RapidOCR

    return fitz, np, RapidOCR


def _render_page_numpy(fitz, np, page, scale: float = 2.0):
    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    return img


def _ocr_text_items(ocr, img):
    res, _ = ocr(img)
    if not res:
        return []
    items = []
    for box, text, score in res:
        t = (text or "").strip()
        if not t:
            continue
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        items.append((min(ys), min(xs), t))
    items.sort(key=lambda z: (z[0], z[1]))
    return items


def _join(items) -> str:
    return "\n".join(t for _, __, t in items).strip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="OCR extract key pages from O-award PDFs")
    parser.add_argument("--pdf-dir", required=True, help="Directory containing PDFs")
    parser.add_argument("--out-dir", required=True, help="Output directory")
    args = parser.parse_args()

    pdf_dir = Path(args.pdf_dir).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    fitz, np, RapidOCR = _lazy_imports()
    ocr = RapidOCR()

    pdfs = sorted([p for p in pdf_dir.glob("*.pdf") if p.is_file()])
    if not pdfs:
        raise SystemExit(f"No PDFs in: {pdf_dir}")

    for i, pdf in enumerate(pdfs, start=1):
        print(f"[{i}/{len(pdfs)}] {pdf.name}", file=sys.stderr)
        doc = fitz.open(str(pdf))
        base = pdf.stem

        # Summary page
        p0 = doc.load_page(0)
        img0 = _render_page_numpy(fitz, np, p0, scale=2.0)
        s0 = _join(_ocr_text_items(ocr, img0))
        (out_dir / "summary").mkdir(parents=True, exist_ok=True)
        (out_dir / "summary" / f"{base}.txt").write_text(s0, encoding="utf-8")

        # TOC / early
        (out_dir / "toc").mkdir(parents=True, exist_ok=True)
        early = []
        for j in range(1, min(4, doc.page_count)):
            pj = doc.load_page(j)
            img = _render_page_numpy(fitz, np, pj, scale=1.7)
            early.append(f"\n--- Page {j+1} ---\n" + _join(_ocr_text_items(ocr, img)))
        (out_dir / "toc" / f"{base}.txt").write_text("".join(early).lstrip(), encoding="utf-8")

        # Last pages
        (out_dir / "tail").mkdir(parents=True, exist_ok=True)
        tail = []
        start = max(0, doc.page_count - 6)
        for j in range(start, doc.page_count):
            pj = doc.load_page(j)
            img = _render_page_numpy(fitz, np, pj, scale=1.5)
            tail.append(f"\n--- Page {j+1} ---\n" + _join(_ocr_text_items(ocr, img)))
        (out_dir / "tail" / f"{base}.txt").write_text("".join(tail).lstrip(), encoding="utf-8")

    print(f"Wrote: {out_dir}")


if __name__ == "__main__":
    main()

