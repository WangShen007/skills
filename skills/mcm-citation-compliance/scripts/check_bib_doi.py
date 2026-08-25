#!/usr/bin/env python3
"""
Verify DOI entries in a BibTeX file via Crossref.

Why:
- AI tools often hallucinate citations/DOIs.
- MCM/ICM requires truthful citations; fake references are a hard credibility killer.

Output:
- A markdown report listing OK/FAIL for each DOI.
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path


def _extract_dois(bib_text: str) -> list[str]:
    dois: list[str] = []
    # Patterns seen in the wild:
    # - doi = {...} / DOI = {...}
    # - doi={...}  / DOI={...}  (Crossref "application/x-bibtex" compact format)
    patterns = [
        r"(?i)\bdoi\s*=\s*[{\"]\s*([^}\"]+)\s*[}\"]",
        r"(?i)\bdoi\s*[{\"]\s*([^}\"]+)\s*[}\"]",
    ]
    for pat in patterns:
        for m in re.finditer(pat, bib_text):
            doi = m.group(1).strip()
            doi = doi.replace("\\_", "_")
            if doi and doi not in dois:
                dois.append(doi)
    return dois


def _crossref_ok(doi: str, timeout: int = 20) -> tuple[bool, str]:
    doi_q = urllib.parse.quote(doi)
    url = f"https://api.crossref.org/works/{doi_q}"
    req = urllib.request.Request(url, headers={"User-Agent": "mcm-citation-compliance/1.0 (mailto:local)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec - fixed URL
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
            title = ""
            msg = data.get("message", {})
            if isinstance(msg, dict):
                t = msg.get("title")
                if isinstance(t, list) and t:
                    title = str(t[0])
            return True, title
    except Exception as e:
        return False, str(e)


def main() -> None:
    parser = argparse.ArgumentParser(description="Check DOIs in a BibTeX file via Crossref")
    parser.add_argument("--bib", required=True, help="Path to .bib file")
    parser.add_argument("--out", required=True, help="Output markdown report path")
    args = parser.parse_args()

    bib_path = Path(args.bib).expanduser().resolve()
    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not bib_path.exists():
        raise SystemExit(f"Bib file not found: {bib_path}")

    bib_text = bib_path.read_text(encoding="utf-8", errors="ignore")
    dois = _extract_dois(bib_text)

    lines: list[str] = []
    lines.append("# Citation DOI Check (Crossref)")
    lines.append("")
    lines.append(f"- Bib: `{bib_path}`")
    lines.append(f"- DOIs found: **{len(dois)}**")
    lines.append("")

    if not dois:
        lines.append("> No DOI fields found. Consider using DOI-based BibTeX to reduce fake-citation risk.")
        out_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
        print(f"Wrote: {out_path}")
        return

    ok_list: list[tuple[str, str]] = []
    bad_list: list[tuple[str, str]] = []
    for doi in dois:
        ok, info = _crossref_ok(doi)
        if ok:
            ok_list.append((doi, info))
        else:
            bad_list.append((doi, info))

    lines.append("## OK")
    for doi, title in ok_list:
        title_s = title.strip().replace("|", " ")[:120]
        lines.append(f"- `{doi}` — {title_s}")
    lines.append("")

    lines.append("## FAIL (needs manual verification / fix)")
    for doi, err in bad_list:
        lines.append(f"- `{doi}` — {str(err)[:160]}")
    lines.append("")

    lines.append("## Guidance")
    lines.append("- If a DOI fails, either:")
    lines.append("  1) replace it with a verified DOI, or")
    lines.append("  2) cite a URL/official report instead, with access date, or")
    lines.append("  3) remove the reference.")
    lines.append("- Never keep unverifiable references in a contest submission.")
    lines.append("")

    out_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    print(f"Wrote: {out_path}")


if __name__ == "__main__":
    main()
