#!/usr/bin/env python3
"""
MCM/ICM problem intake generator.

Inputs:
  --problem-pdf: problem statement PDF
  --data-dir: folder with provided datasets (may be missing)
  --out-dir: project root folder to write into

Outputs:
  inputs/problem.txt
  plan/problem_tasks.md
  plan/intake.md
  data/data_map.md
  paper/outline.md (template copy)
"""

from __future__ import annotations

import argparse
import csv
import re
import textwrap
from pathlib import Path


def _extract_pdf_text_pypdf(pdf_path: Path, max_pages: int | None = None) -> str:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        return ""
    reader = PdfReader(str(pdf_path))
    pages = reader.pages[: max_pages] if max_pages else reader.pages
    chunks: list[str] = []
    for i, page in enumerate(pages, start=1):
        try:
            t = page.extract_text() or ""
        except Exception:
            t = ""
        chunks.append(f"\n\n--- Page {i} ---\n\n{t}".rstrip())
    return "\n".join(chunks).strip() + "\n"


def _extract_pdf_text_ocr(pdf_path: Path, max_pages: int = 6) -> str:
    import fitz  # PyMuPDF
    import numpy as np
    from rapidocr_onnxruntime import RapidOCR

    ocr = RapidOCR()
    doc = fitz.open(str(pdf_path))
    out: list[str] = []
    for i in range(min(max_pages, doc.page_count)):
        page = doc.load_page(i)
        mat = fitz.Matrix(2, 2)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        res, _ = ocr(img)
        lines = []
        if res:
            items = []
            for box, text, score in res:
                t = (text or "").strip()
                if not t:
                    continue
                xs = [p[0] for p in box]
                ys = [p[1] for p in box]
                items.append((min(ys), min(xs), t))
            items.sort(key=lambda z: (z[0], z[1]))
            lines = [t for _, __, t in items]
        out.append(f"\n\n--- Page {i+1} ---\n\n" + "\n".join(lines))
    return "\n".join(out).strip() + "\n"


def _normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _extract_required_submission(problem_text: str) -> list[str]:
    # Extract lines under: "Your PDF solution of no more than ... should include:"
    lines = problem_text.splitlines()
    out: list[str] = []
    start = None
    for i, ln in enumerate(lines):
        if re.search(r"Your PDF solution.*should include", ln, flags=re.IGNORECASE):
            start = i
            break
    if start is None:
        return out
    for ln in lines[start : start + 40]:
        s = ln.strip(" \t•-*")
        if not s:
            continue
        if re.match(r"^Your PDF solution", s, flags=re.IGNORECASE):
            continue
        if re.match(r"^Note:", s, flags=re.IGNORECASE):
            break
        if ln.strip().startswith(("•", "-", "*")):
            out.append(_normalize_ws(s))
    return out


def _extract_task_bullets(problem_text: str) -> list[str]:
    # Extract bullets after "Specifically, use the provided data to:"
    lines = problem_text.splitlines()
    start = None
    for i, ln in enumerate(lines):
        if re.search(r"Specifically, use the provided data to", ln, flags=re.IGNORECASE):
            start = i
            break
    if start is None:
        return []
    out: list[str] = []
    for ln in lines[start : start + 200]:
        raw = ln.strip()
        if not raw:
            continue
        if re.search(r"Your PDF solution", raw, flags=re.IGNORECASE):
            break
        if raw.startswith("•"):
            out.append(_normalize_ws(raw.lstrip("•").strip()))
        # sub-bullets often begin with "o" in OCR text
        if re.match(r"^[oO]\s+", raw):
            out.append("  - " + _normalize_ws(re.sub(r"^[oO]\s+", "", raw)))
    return out


def _data_map_markdown(data_dir: Path) -> str:
    lines: list[str] = []
    lines.append("# Data Map (given datasets)")
    lines.append("")
    lines.append(f"- Data dir: `{data_dir}`")
    lines.append("")
    if not data_dir.exists():
        lines.append("> Data directory not found. If the problem provides no data, list your external data plan here.")
        return "\n".join(lines).strip() + "\n"

    files = sorted([p for p in data_dir.iterdir() if p.is_file()])
    lines.append("## Files")
    for p in files:
        lines.append(f"- `{p.name}` ({p.stat().st_size} bytes)")
    lines.append("")

    dd = data_dir / "data_dictionary.csv"
    if dd.exists():
        lines.append("## data_dictionary.csv (preview)")
        try:
            # lightweight preview: show first 40 rows
            with dd.open("r", encoding="utf-8", errors="ignore", newline="") as f:
                r = csv.reader(f)
                rows = []
                for i, row in enumerate(r):
                    rows.append(row)
                    if i >= 40:
                        break
            for row in rows:
                lines.append("- " + " | ".join([c.strip() for c in row if c is not None][:6]))
        except Exception as e:
            lines.append(f"- [failed to read data_dictionary.csv] {e}")
        lines.append("")

    # Note about encoding for programs.csv (common gotcha)
    if (data_dir / "summerOly_programs.csv").exists():
        lines.append("## Encoding note")
        lines.append("- `summerOly_programs.csv` may not be UTF-8; if pandas throws UnicodeDecodeError, try `encoding=\"latin-1\"`.")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def _write_outline_template(skill_dir: Path, out_dir: Path) -> None:
    tpl = skill_dir / "templates" / "outline.md"
    if not tpl.exists():
        return
    paper_dir = out_dir / "paper"
    paper_dir.mkdir(parents=True, exist_ok=True)
    target = paper_dir / "outline.md"
    if target.exists():
        return
    target.write_text(tpl.read_text(encoding="utf-8"), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an MCM/ICM problem intake package")
    parser.add_argument("--problem-pdf", required=True, help="Path to problem PDF")
    parser.add_argument("--data-dir", default=None, help="Optional: data directory path")
    parser.add_argument("--out-dir", required=True, help="Project root to write outputs into")
    parser.add_argument("--ocr-fallback", action="store_true", help="Force OCR even if PDF text exists")
    args = parser.parse_args()

    problem_pdf = Path(args.problem_pdf).expanduser().resolve()
    if not problem_pdf.exists():
        raise SystemExit(f"Problem PDF not found: {problem_pdf}")

    out_dir = Path(args.out_dir).expanduser().resolve()
    inputs_dir = out_dir / "inputs"
    plan_dir = out_dir / "plan"
    data_out_dir = out_dir / "data"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    plan_dir.mkdir(parents=True, exist_ok=True)
    data_out_dir.mkdir(parents=True, exist_ok=True)

    # Extract problem text
    text = ""
    if not args.ocr_fallback:
        text = _extract_pdf_text_pypdf(problem_pdf, max_pages=8)
    if args.ocr_fallback or len(_normalize_ws(text)) < 400:
        text = _extract_pdf_text_ocr(problem_pdf, max_pages=6)

    (inputs_dir / "problem.pdf").write_bytes(problem_pdf.read_bytes())
    (inputs_dir / "problem.txt").write_text(text, encoding="utf-8")

    # Parse tasks and requirements
    tasks = _extract_task_bullets(text)
    reqs = _extract_required_submission(text)

    tasks_md = ["# Problem Tasks (from PDF)",""]
    if tasks:
        for t in tasks:
            if t.startswith("  - "):
                tasks_md.append(t)
            else:
                tasks_md.append(f"- {t}")
    else:
        tasks_md.append("> [TODO] Failed to auto-extract bullet tasks. Open inputs/problem.txt and copy them here manually.")
    tasks_md.append("")
    (plan_dir / "problem_tasks.md").write_text("\n".join(tasks_md).strip() + "\n", encoding="utf-8")

    intake = []
    intake.append("# Intake")
    intake.append("")
    intake.append("## Inputs")
    intake.append(f"- Problem PDF: `{inputs_dir / 'problem.pdf'}`")
    intake.append(f"- Problem text: `{inputs_dir / 'problem.txt'}`")
    if args.data_dir:
        intake.append(f"- Data dir: `{Path(args.data_dir).expanduser().resolve()}`")
    else:
        intake.append("- Data dir: <not provided>")
    intake.append("")
    intake.append("## Hard constraints (auto-extracted if possible)")
    if reqs:
        for r in reqs:
            intake.append(f"- {r}")
    else:
        intake.append("- [TODO] Find the official page limit, required sections, and AI policy lines in inputs/problem.txt.")
    intake.append("")
    intake.append("## Task breakdown (edit to team language)")
    intake.append(f"- See: `{plan_dir / 'problem_tasks.md'}`")
    intake.append("")
    intake.append("## Team decisions needed (fill now, not later)")
    intake.append("1) Target modeling route A (interpretable) vs route B (performance) and why")
    intake.append("2) Uncertainty plan (bootstrap / Bayesian / Monte Carlo) and what intervals to report")
    intake.append("3) Validation plan (backtesting by Olympiad; metrics)")
    intake.append("4) How to operationalize any 'coach effect' (proxy variable, identification strategy)")
    intake.append("")
    intake.append("## Risks / TODOs")
    intake.append("- [TODO] Data anomalies & cleaning decisions (NOC/Team naming, encoding, missing years, etc.)")
    intake.append("- [TODO] Page budget & outline freeze")
    intake.append("- [TODO] Citation plan (official rules + data dictionary + method sources)")
    intake.append("")
    (plan_dir / "intake.md").write_text("\n".join(intake).strip() + "\n", encoding="utf-8")

    # Data map
    data_dir = Path(args.data_dir).expanduser().resolve() if args.data_dir else None
    if data_dir:
        (data_out_dir / "data_map.md").write_text(_data_map_markdown(data_dir), encoding="utf-8")
    else:
        (data_out_dir / "data_map.md").write_text(_data_map_markdown(Path("<missing>")), encoding="utf-8")

    # Outline template
    skill_dir = Path(__file__).expanduser().resolve().parents[1]
    _write_outline_template(skill_dir, out_dir)

    print(f"Wrote: {out_dir}")
    print(f"- {inputs_dir / 'problem.txt'}")
    print(f"- {plan_dir / 'problem_tasks.md'}")
    print(f"- {plan_dir / 'intake.md'}")
    print(f"- {data_out_dir / 'data_map.md'}")
    print(f"- {out_dir / 'paper' / 'outline.md'}")


if __name__ == "__main__":
    main()

