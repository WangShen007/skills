#!/usr/bin/env python3
"""
Create a page/figure/table budget for an MCM/ICM paper (25-page solution by default).

This generates a *planning* document to help keep the main solution within the
official page limit while maintaining O-award-style information density.

Notes:
- The 25-page limit applies to the ENTIRE submission (Summary Sheet, solution,
  references, TOC, appendices, code, etc.) per COMAP instructions.
- The "Report on Use of AI Tools" is appended after the 25-page solution and is
  not counted toward the 25-page limit (per COMAP AI policy).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import textwrap
from pathlib import Path


def _default_budget(include_toc: bool) -> list[dict]:
    # Budget sums to 25 pages (main solution only). AI report excluded.
    budget = [
        {"section": "Summary Sheet (Abstract in mcmthesis)", "pages": 1, "fig": 0, "tbl": 0, "must": "2–4 quantitative results + framework + validation sentence"},
    ]
    if include_toc:
        budget.append({"section": "Table of Contents (optional but common)", "pages": 1, "fig": 0, "tbl": 0, "must": "Keep tocdepth=2; counts toward page limit"})
    budget += [
        {"section": "1. Introduction / Problem Restatement", "pages": 1, "fig": 1, "tbl": 0, "must": "Restate tasks + objectives + evaluation metrics"},
        {"section": "2. Assumptions & Notation", "pages": 1, "fig": 0, "tbl": 1, "must": "Notation table with units; assumptions defendable"},
        {"section": "3. Data", "pages": 2, "fig": 3, "tbl": 1, "must": "Data dictionary + preprocessing + 2–3 EDA findings"},
        {"section": "4. Model Formulation (Baseline -> Final)", "pages": 5, "fig": 2, "tbl": 1, "must": "Model ladder + key equations/algorithms + complexity"},
        {"section": "5. Results", "pages": 4, "fig": 6, "tbl": 1, "must": "Quantitative results for each sub-task; baseline vs final"},
        {"section": "6. Analysis & Discussion", "pages": 2, "fig": 2, "tbl": 0, "must": "Interpretation + trade-offs + boundary conditions"},
        {"section": "7. Sensitivity / Robustness / Validation", "pages": 3, "fig": 3, "tbl": 1, "must": "At least one of: sensitivity / validation; ideally both"},
        {"section": "8. Strengths & Weaknesses", "pages": 1, "fig": 0, "tbl": 1, "must": "Actionable weaknesses; not generic"},
        {"section": "9. Conclusion & Recommendations", "pages": 1, "fig": 0, "tbl": 0, "must": "Answer each sub-question explicitly; actionable recommendations"},
        {"section": "References", "pages": 2, "fig": 0, "tbl": 0, "must": "No fake citations; include data sources + AI tool citations if used"},
        {"section": "Appendix (derivations / extra figs / code)", "pages": 2, "fig": 1, "tbl": 1, "must": "Only include what strengthens credibility; still counts in 25 pages"},
    ]
    return budget


def _sum(budget: list[dict], key: str) -> int:
    return int(sum(int(x.get(key, 0)) for x in budget))


def render_markdown(page_limit: int, include_toc: bool) -> str:
    budget = _default_budget(include_toc=include_toc)
    total_pages = _sum(budget, "pages")
    total_fig = _sum(budget, "fig")
    total_tbl = _sum(budget, "tbl")

    # If user changes page_limit away from 25, keep the template but warn.
    warn = ""
    if total_pages != page_limit:
        warn = (
            f"\n> ⚠️ Warning: template sums to {total_pages} pages, but --page-limit={page_limit}. "
            "Adjust section budgets below so the SUM equals the official page limit.\n"
        )

    today = _dt.date.today().isoformat()
    md = f"""\
    # Page Budget (Main Solution) — Target ≤ {page_limit} pages

    Date: {today}

    This file is a *budget*, not the final paper. It exists to prevent the #1 hard-fail: exceeding the page limit.

    - Target page limit (main solution): **≤ {page_limit} pages**
    - IMPORTANT: the page limit counts **Summary Sheet + Solution + References + TOC + Notes + Appendices + Code + problem-specific requirements**.
    - If you used AI tools: append **Report on Use of AI Tools** after the main solution (no page limit; not counted toward the {page_limit} pages).

    Planned density (O-award tendency, adjust to your topic):
    - Figures: ~**18** (median reported in your notes), target in this plan: **{total_fig}**
    - Tables: ~**7** (median reported in your notes), target in this plan: **{total_tbl}**
    {warn}
    ## Section-by-section budget

    | Section | Target pages | Fig | Table | Must-have (acceptance criteria) |
    |---|---:|---:|---:|---|
    """

    lines = [textwrap.dedent(md).rstrip()]
    for row in budget:
        lines.append(
            f"| {row['section']} | {row['pages']} | {row['fig']} | {row['tbl']} | {row['must']} |"
        )

    lines.append("")
    lines.append("## How to use this budget")
    lines.append("- First freeze `paper/outline.md` (2–4 bullets per section + planned visuals).")
    lines.append("- Then write section-by-section; if a section exceeds its budget, cut or move details to Appendix.")
    lines.append("- Every figure/table must be referenced in text and have a conclusion-style caption (\"so what\").")
    lines.append("")
    lines.append("## Page-limit check hook (recommended)")
    lines.append("- Ensure `paper/main.tex` defines `\\label{MainLastPage}` right before the AI Use Report section.")
    lines.append("- After compilation, run:")
    lines.append("")
    lines.append("```bash")
    lines.append("python3 ~/.codex/skills/mcm-oaward-coach/scripts/check_page_limit.py \\")
    lines.append("  --pdf paper/main.pdf --aux paper/main.aux --limit 25")
    lines.append("```")
    lines.append("")

    return "\n".join(lines).strip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Create plan/page_budget.md for an MCM/ICM project")
    parser.add_argument("--out", required=True, help="Output markdown path, e.g. plan/page_budget.md")
    parser.add_argument("--page-limit", type=int, default=25, help="Main-solution page limit (default: 25)")
    parser.add_argument("--include-toc", action="store_true", help="Include 1 page TOC in the budget (recommended)")
    args = parser.parse_args()

    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        render_markdown(page_limit=int(args.page_limit), include_toc=bool(args.include_toc)),
        encoding="utf-8",
    )
    print(f"Wrote: {out_path}")


if __name__ == "__main__":
    main()

