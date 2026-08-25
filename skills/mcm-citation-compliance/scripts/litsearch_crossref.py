#!/usr/bin/env python3
"""
Crossref-based literature search -> BibTeX appender.

Why this exists:
- MCM/ICM papers still need credible references (domain + methods + data + official rules).
- AI tools can hallucinate citations. This script fetches BibTeX from Crossref by DOI.

Workflow:
1) Decide keywords (plan/keywords.txt)
2) Run this script to fetch candidate papers into paper/references.bib
3) Manually verify relevance + actually cite them in paper/main.tex

This is a helper; it does not guarantee correctness of metadata.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import textwrap
import urllib.parse
import urllib.request
from pathlib import Path


def _http_get_json(url: str, timeout: int = 30) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "mcm-oaward-coach/1.0 (mailto:local)"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec - URL is controlled by script
        return json.loads(resp.read().decode("utf-8", errors="ignore"))


def _http_get_text(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "mcm-oaward-coach/1.0 (mailto:local)"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec
        return resp.read().decode("utf-8", errors="ignore")


def _crossref_search(query: str, rows: int) -> list[dict]:
    q = urllib.parse.quote(query)
    url = f"https://api.crossref.org/works?query={q}&rows={int(rows)}"
    data = _http_get_json(url)
    items = data.get("message", {}).get("items", [])
    return [it for it in items if isinstance(it, dict)]


def _bibtex_for_doi(doi: str) -> str:
    doi_q = urllib.parse.quote(doi)
    url = f"https://api.crossref.org/works/{doi_q}/transform/application/x-bibtex"
    return _http_get_text(url).strip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Search Crossref and append BibTeX entries by DOI")
    parser.add_argument("--query", required=True, help="Search query, e.g. 'CUSUM change point detection'")
    parser.add_argument("--rows", type=int, default=10, help="How many Crossref results to fetch (default: 10)")
    parser.add_argument("--out-bib", required=True, help="BibTeX file to append to, e.g. paper/references.bib")
    parser.add_argument(
        "--registry",
        default=None,
        help="Optional: write a JSONL registry of fetched DOIs, e.g. plan/citation_registry.jsonl",
    )
    args = parser.parse_args()

    out_bib = Path(args.out_bib).expanduser().resolve()
    out_bib.parent.mkdir(parents=True, exist_ok=True)

    registry_path = Path(args.registry).expanduser().resolve() if args.registry else None
    if registry_path:
        registry_path.parent.mkdir(parents=True, exist_ok=True)

    items = _crossref_search(query=str(args.query), rows=int(args.rows))
    dois: list[str] = []
    for it in items:
        doi = (it.get("DOI") or "").strip()
        if doi:
            dois.append(doi)

    if not dois:
        raise SystemExit("No DOI results found from Crossref. Try a different query.")

    # Read existing file to avoid duplicating identical DOI entries.
    existing = out_bib.read_text(encoding="utf-8", errors="ignore") if out_bib.exists() else ""

    appended = 0
    for doi in dois:
        if doi.lower() in existing.lower():
            continue
        try:
            bib = _bibtex_for_doi(doi)
        except Exception:
            continue
        header = textwrap.dedent(
            f"""\
            % --- fetched from Crossref ---
            % doi: {doi}
            % query: {args.query}
            % date: {_dt.date.today().isoformat()}
            """
        )
        out_bib.write_text(existing + header + bib + "\n", encoding="utf-8")
        existing = out_bib.read_text(encoding="utf-8", errors="ignore")
        appended += 1

        if registry_path:
            with registry_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"doi": doi, "query": args.query, "date": _dt.date.today().isoformat()}) + "\n")

    print(f"Bib file: {out_bib}")
    print(f"Found DOIs: {len(dois)}")
    print(f"Appended new entries: {appended}")


if __name__ == "__main__":
    main()

