#!/usr/bin/env python3
"""
Index local O-award sample PDFs into a markdown file.

This is *not* for copying; it's a quick inventory to:
- see what years/problems you have locally
- open a few to learn structure/figure styles (no plagiarism)
"""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Index O-award sample PDFs to markdown")
    parser.add_argument("--samples-dir", required=True, help="Folder containing PDFs (may have subfolders)")
    parser.add_argument("--out", required=True, help="Output markdown path, e.g. plan/oaward_samples_index.md")
    args = parser.parse_args()

    root = Path(args.samples_dir).expanduser().resolve()
    if not root.exists():
        raise SystemExit(f"Samples dir not found: {root}")

    pdfs = sorted([p for p in root.rglob("*.pdf") if p.is_file()])
    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append("# Local O-award samples index")
    lines.append("")
    lines.append(f"- Root: `{root}`")
    lines.append(f"- PDFs: **{len(pdfs)}**")
    lines.append("")
    lines.append("## Files")
    for p in pdfs:
        rel = p.relative_to(root)
        lines.append(f"- `{rel}`")
    lines.append("")
    lines.append("## Use rules (anti-plagiarism)")
    lines.append("- Learn structure, section order, figure types, caption style.")
    lines.append("- Do NOT copy text, figures, tables, or unique expressions.")
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote: {out_path}")


if __name__ == "__main__":
    main()

