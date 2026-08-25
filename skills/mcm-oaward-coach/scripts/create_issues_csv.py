#!/usr/bin/env python3
"""
Create a traceable task contract (plan/issues.csv) for an MCM/ICM project.

This is intentionally lightweight: a CSV you can open in Excel/Numbers/Sheets.
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
from pathlib import Path


def _rows(problem_letter: str) -> list[dict[str, str]]:
    today = _dt.date.today().isoformat()
    p = problem_letter.strip().upper() or "C"

    # status: TODO / DOING / DONE / BLOCKED
    # priority: P0 (hard-fail risk) / P1 (high value) / P2 (nice-to-have)
    return [
        {
            "id": "P0-INTAKE-01",
            "area": "Intake",
            "priority": "P0",
            "status": "TODO",
            "task": f"Read Problem {p} PDF end-to-end; extract sub-questions + constraints into plan/intake.md",
            "acceptance": "plan/intake.md has sub-questions list + evaluation metrics + hard constraints + open questions",
            "outputs": "plan/intake.md, inputs/problem.txt",
            "owner": "",
            "date": today,
        },
        {
            "id": "P0-RULES-01",
            "area": "Compliance",
            "priority": "P0",
            "status": "TODO",
            "task": "Confirm official page limit + font + anonymity + AI policy; write plan/constraints.md",
            "acceptance": "plan/constraints.md cites official instructions + AI policy and states what counts in page limit",
            "outputs": "plan/constraints.md",
            "owner": "",
            "date": today,
        },
        {
            "id": "P0-DATA-01",
            "area": "Data",
            "priority": "P0",
            "status": "TODO",
            "task": "Inventory datasets; create data dictionary; record sources in data/README.md",
            "acceptance": "data/README.md filled; columns/units documented; missing fields identified",
            "outputs": "data/README.md, results/data_inventory.md",
            "owner": "",
            "date": today,
        },
        {
            "id": "P1-EDA-01",
            "area": "Data",
            "priority": "P1",
            "status": "TODO",
            "task": "Run minimum EDA (4–6 figs + 2 tables) to support model choices",
            "acceptance": "figures/ has publication-ready plots; results/eda_summary.md states 3+ findings tied to modeling choices",
            "outputs": "analysis/01_eda.py, results/eda_summary.md, figures/*",
            "owner": "",
            "date": today,
        },
        {
            "id": "P1-PLAN-01",
            "area": "Writing",
            "priority": "P1",
            "status": "TODO",
            "task": "Freeze outline with bullets + planned visuals; create page budget",
            "acceptance": "paper/outline.md completed; plan/page_budget.md sums to page limit",
            "outputs": "paper/outline.md, plan/page_budget.md",
            "owner": "",
            "date": today,
        },
        {
            "id": "P1-MODEL-01",
            "area": "Model",
            "priority": "P1",
            "status": "TODO",
            "task": "Define baseline model (simple, explainable) and evaluation protocol",
            "acceptance": "plan/model_plan.md includes baseline definition + metrics + validation design",
            "outputs": "plan/model_plan.md",
            "owner": "",
            "date": today,
        },
        {
            "id": "P1-MODEL-02",
            "area": "Model",
            "priority": "P1",
            "status": "TODO",
            "task": "Implement baseline end-to-end; produce first quantitative results",
            "acceptance": "results/metrics.json filled; figures show baseline results; can be re-run from analysis/",
            "outputs": "analysis/02_baseline.py, results/metrics.json, figures/*",
            "owner": "",
            "date": today,
        },
        {
            "id": "P1-MODEL-03",
            "area": "Model",
            "priority": "P1",
            "status": "TODO",
            "task": "Implement improved/final model (one clear improvement over baseline)",
            "acceptance": "Improved model beats baseline on agreed metric OR provides better interpretability; results documented",
            "outputs": "analysis/03_final_model.py, results/metrics.json, figures/*",
            "owner": "",
            "date": today,
        },
        {
            "id": "P1-VALID-01",
            "area": "Model",
            "priority": "P1",
            "status": "TODO",
            "task": "Validation / robustness (at least one strong piece of evidence)",
            "acceptance": "results/validation.md + figure/table; clearly states what was validated and outcome",
            "outputs": "analysis/04_validation.py, results/validation.md, figures/*",
            "owner": "",
            "date": today,
        },
        {
            "id": "P1-SENS-01",
            "area": "Model",
            "priority": "P1",
            "status": "TODO",
            "task": "Sensitivity analysis (key parameters / scenarios)",
            "acceptance": "figures include sensitivity plot; text states whether conclusions are stable",
            "outputs": "analysis/05_sensitivity.py, results/sensitivity.md, figures/*",
            "owner": "",
            "date": today,
        },
        {
            "id": "P0-CITE-01",
            "area": "Research",
            "priority": "P0",
            "status": "TODO",
            "task": "Build references.bib from verified sources; no fake citations",
            "acceptance": "paper/references.bib contains method + domain + data + official policy refs; all cited in text",
            "outputs": "paper/references.bib, plan/citation_registry.jsonl",
            "owner": "",
            "date": today,
        },
        {
            "id": "P1-WRITE-01",
            "area": "Writing",
            "priority": "P1",
            "status": "TODO",
            "task": "Write main sections in LaTeX (intro->conclusion) following outline and page budget",
            "acceptance": "paper/main.tex compiles; sections align to sub-questions; figures referenced and captioned",
            "outputs": "paper/main.tex, paper/main.pdf",
            "owner": "",
            "date": today,
        },
        {
            "id": "P0-PAGE-01",
            "area": "QA",
            "priority": "P0",
            "status": "TODO",
            "task": "Enforce page limit for main solution; add \\label{MainLastPage} hook; run page-limit checker",
            "acceptance": "Main solution pages <= 25 (from MainLastPage); checker passes",
            "outputs": "paper/main.aux, paper/main.pdf, plan/page_budget.md",
            "owner": "",
            "date": today,
        },
        {
            "id": "P0-AI-01",
            "area": "Compliance",
            "priority": "P0",
            "status": "TODO",
            "task": "If AI tools were used, append Report on Use of AI Tools after the 25-page solution",
            "acceptance": "paper/main.pdf contains AI Use Report section after MainLastPage; report matches COMAP policy examples",
            "outputs": "paper/ai_use_report.tex (or .md), plan/ai_use_log.md",
            "owner": "",
            "date": today,
        },
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Create plan/issues.csv for an MCM/ICM project")
    parser.add_argument("--out", required=True, help="Output CSV path, e.g. plan/issues.csv")
    parser.add_argument("--problem-letter", default="C", help="Problem letter A/B/C/D/E/F")
    args = parser.parse_args()

    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows = _rows(problem_letter=str(args.problem_letter))
    fieldnames = ["id", "area", "priority", "status", "task", "acceptance", "outputs", "owner", "date"]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print(f"Wrote: {out_path}")


if __name__ == "__main__":
    main()

