#!/usr/bin/env python3
"""
Check MCM/ICM page limits.

We report:
- Total pages in the built PDF
- (Recommended) Main-solution pages from LaTeX aux label `MainLastPage`

This supports the common requirement: the main solution is limited to 25 pages,
while the AI Use Report (if any) is appended after and not counted.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def _pdf_total_pages(pdf_path: Path) -> int:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception as e:  # pragma: no cover
        raise SystemExit("Missing dependency 'pypdf'. Install with: python3 -m pip install pypdf") from e
    reader = PdfReader(str(pdf_path))
    return len(reader.pages)


def _aux_label_page(aux_path: Path, label: str) -> int | None:
    """
    Parse LaTeX .aux label page numbers.

    We look for:
      \\newlabel{MainLastPage}{{...}{<page>}...}
    """
    if not aux_path.exists():
        return None
    txt = aux_path.read_text(encoding="utf-8", errors="ignore")
    # LaTeX aux can contain multiple \\newlabel; keep last match.
    # In LaTeX aux, a label line typically looks like:
    #   \newlabel{MainLastPage}{{<reftext>}{<page>}...}
    # Note: braces are not preceded by backslashes in the aux content.
    pat = re.compile(r"\\newlabel\{" + re.escape(label) + r"\}\{\{.*?\}\{(\d+)\}.*?\}")
    matches = list(pat.finditer(txt))
    if not matches:
        return None
    return int(matches[-1].group(1))


def main() -> None:
    parser = argparse.ArgumentParser(description="Check MCM/ICM PDF page limits")
    parser.add_argument("--pdf", required=True, help="Path to compiled PDF (paper/main.pdf)")
    parser.add_argument("--aux", default=None, help="Optional: LaTeX aux file (paper/main.aux) to read MainLastPage")
    parser.add_argument("--limit", type=int, default=25, help="Main-solution page limit (default: 25)")
    parser.add_argument("--label", default="MainLastPage", help="Aux label marking end of main solution")
    args = parser.parse_args()

    pdf_path = Path(args.pdf).expanduser().resolve()
    if not pdf_path.exists():
        raise SystemExit(f"PDF not found: {pdf_path}")

    total = _pdf_total_pages(pdf_path)
    print(f"PDF: {pdf_path}")
    print(f"Total PDF pages: {total}")

    if args.aux:
        aux_path = Path(args.aux).expanduser().resolve()
        page = _aux_label_page(aux_path, label=str(args.label))
        if page is None:
            print(f"Main-solution pages: [unknown] (label '{args.label}' not found in {aux_path.name})")
            print("Hint: add \\label{MainLastPage} right before the AI Use Report section, then recompile.")
        else:
            ok = page <= int(args.limit)
            print(f"Main-solution pages (from {args.label}): {page} (limit {int(args.limit)}) -> {'OK' if ok else 'FAIL'}")
    else:
        print("Main-solution pages: [not checked] (no --aux provided)")


if __name__ == "__main__":
    main()
