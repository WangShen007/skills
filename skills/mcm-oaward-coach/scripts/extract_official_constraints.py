#!/usr/bin/env python3
"""
Extract a small set of 'hard constraints' from:
- COMAP MCM/ICM contest instructions HTML (cached locally), and/or
- COMAP "Use of AI Tools" policy PDF

Output is a short markdown file (plan/constraints.md) for fail-fast compliance.

This is best-effort text extraction; always manually verify against the official
documents for the specific contest year you are submitting to.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import re
from pathlib import Path


def _read_text_from_pdf(pdf_path: Path) -> str:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception as e:  # pragma: no cover
        raise SystemExit("Missing dependency 'pypdf'. Install with: python3 -m pip install pypdf") from e
    reader = PdfReader(str(pdf_path))
    chunks: list[str] = []
    for page in reader.pages:
        try:
            chunks.append(page.extract_text() or "")
        except Exception:
            chunks.append("")
    return "\n".join(chunks)


def _find_sentences(text: str, patterns: list[str]) -> list[str]:
    found: list[str] = []
    # Rough sentence split; we avoid heavy NLP deps.
    sentences = re.split(r"(?<=[.!?])\\s+", re.sub(r"\\s+", " ", text))
    for pat in patterns:
        rx = re.compile(pat, re.IGNORECASE)
        for s in sentences:
            if rx.search(s):
                s2 = s.strip()
                if s2 and s2 not in found:
                    found.append(s2)
    return found


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract official MCM/ICM constraints into markdown")
    parser.add_argument("--out", required=True, help="Output markdown path, e.g. plan/constraints.md")
    parser.add_argument("--instructions-html", default=None, help="Optional: cached mcm_instructions.html path")
    parser.add_argument("--ai-policy-pdf", default=None, help="Optional: Contest_AI_Policy.pdf path")
    args = parser.parse_args()

    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    today = _dt.date.today().isoformat()
    lines: list[str] = []
    lines.append("# Official Constraints (Fail-Fast)")
    lines.append("")
    lines.append(f"Date: {today}")
    lines.append("")
    lines.append("> NOTE: This file is generated. Always manually verify against the official docs for your contest year.")
    lines.append("")

    if args.instructions_html:
        html_path = Path(args.instructions_html).expanduser().resolve()
        if html_path.exists():
            html = html_path.read_text(encoding="utf-8", errors="ignore")
            key = _find_sentences(
                html,
                patterns=[
                    r"25\\s+page\\s+limit",
                    r"12-?point",
                    r"typed\\s+in\\s+English",
                    r"must\\s+not\\s+appear\\s+on\\s+any\\s+page",
                ],
            )
            lines.append("## From COMAP contest instructions (local cache)")
            lines.append(f"- Source: `{html_path}`")
            if key:
                for s in key[:8]:
                    lines.append(f"- {s}")
            else:
                lines.append("- [no matches found automatically] Please open the HTML and copy the key constraints manually.")
            lines.append("")
        else:
            lines.append("## From COMAP contest instructions (local cache)")
            lines.append(f"- Source: `{html_path}` (missing)")
            lines.append("")

    if args.ai_policy_pdf:
        pdf_path = Path(args.ai_policy_pdf).expanduser().resolve()
        if pdf_path.exists():
            txt = _read_text_from_pdf(pdf_path)
            key = _find_sentences(
                txt,
                patterns=[
                    r"Report on Use of AI",
                    r"no page limit",
                    r"will not be counted",
                    r"main solution.*25 pages",
                    r"inline citations",
                ],
            )
            lines.append("## From COMAP AI policy (local cache)")
            lines.append(f"- Source: `{pdf_path}`")
            if key:
                for s in key[:10]:
                    lines.append(f"- {s}")
            else:
                lines.append("- [no matches found automatically] Please open the PDF and copy the key constraints manually.")
            lines.append("")
        else:
            lines.append("## From COMAP AI policy (local cache)")
            lines.append(f"- Source: `{pdf_path}` (missing)")
            lines.append("")

    out_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    print(f"Wrote: {out_path}")


if __name__ == "__main__":
    main()

