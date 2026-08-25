#!/usr/bin/env python3
"""
Analyze local MCM/ICM O-award PDFs (image-based) via OCR to extract:
- Summary sheet key methods/keywords
- Table-of-contents / section structure (heuristic)
- Figure/Table counts (heuristic via caption OCR)
- References hints (URLs/DOIs/official sources)
- Whether AI Use Report is present

This script is designed for the user's local dataset:
  $MCM_WORKSPACE/C/*.pdf

Outputs:
  - 2025_oaward_c_report.md
  - 2025_oaward_c_papers.csv
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable


def _lazy_imports():
    import fitz  # PyMuPDF
    import numpy as np
    from rapidocr_onnxruntime import RapidOCR

    return fitz, np, RapidOCR


@dataclass
class PaperStats:
    file: str
    pages: int
    title_guess: str
    toc_present: bool
    sections_guess: str  # pipe-separated
    fig_count: int
    table_count: int
    refs_count_guess: int
    refs_hints: str  # pipe-separated short hints
    ai_report_present: bool
    methods_keywords: str  # pipe-separated


KEYWORDS = [
    # time series / forecasting
    "ARIMA",
    "SARIMA",
    "LSTM",
    "GRU",
    "Prophet",
    "Kalman",
    "state-space",
    "Markov",
    "HMM",
    # ML
    "XGBoost",
    "LightGBM",
    "CatBoost",
    "Random Forest",
    "SVM",
    "Neural",
    "CNN",
    # stats / inference
    "Bayesian",
    "bootstrap",
    "Monte Carlo",
    "Poisson",
    "negative binomial",
    "zero-inflated",
    "hierarchical",
    "mixed effects",
    # dimensionality / explainability
    "PCA",
    "SVD",
    "SHAP",
    "attention",
    # optimization
    "linear programming",
    "integer programming",
    "genetic algorithm",
    "simulated annealing",
]


SECTION_CANON = [
    "Abstract",
    "Summary",
    "Table of Contents",
    "Introduction",
    "Problem Restatement",
    "Assumptions",
    "Notation",
    "Data",
    "Model",
    "Method",
    "Results",
    "Validation",
    "Sensitivity",
    "Discussion",
    "Strengths",
    "Weaknesses",
    "Conclusion",
    "Recommendations",
    "References",
    "Appendix",
    "Report on Use of AI",
]


def _render_page_numpy(fitz, np, page, scale: float = 2.0):
    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    return img


def _ocr_text_lines(ocr, img):
    # Returns list of (y, x, text) sorted roughly in reading order.
    res, _ = ocr(img)
    if not res:
        return []
    items = []
    for box, text, score in res:
        t = (text or "").strip()
        if not t:
            continue
        # box: 4 points [[x,y],...]
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        items.append((min(ys), min(xs), t))
    items.sort(key=lambda z: (z[0], z[1]))
    return items


def _join_lines(items) -> str:
    # Basic join; keep newline between boxes. For our use (keyword/heading detection) it is enough.
    return "\n".join(t for _, __, t in items)


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def _find_keywords(text: str) -> list[str]:
    t = _normalize(text)
    found = []
    for kw in KEYWORDS:
        if _normalize(kw) in t:
            found.append(kw)
    return found


def _guess_title_from_summary(lines: list[str]) -> str:
    # Heuristic: line after "Summary Sheet" or the longest title-like line near top.
    joined = "\n".join(lines)
    # Common pattern: Summary Sheet then Title
    m = re.search(r"Summary Sheet\s*\n(.{6,120})", joined, flags=re.IGNORECASE)
    if m:
        return m.group(1).strip()
    # Fallback: pick first non-trivial, non-metadata line.
    for s in lines:
        s2 = s.strip()
        if not s2:
            continue
        if re.fullmatch(r"\d{4}", s2):
            continue
        if re.search(r"Team\s*Control\s*Number", s2, flags=re.IGNORECASE):
            continue
        if re.search(r"Problem\s*Chosen", s2, flags=re.IGNORECASE):
            continue
        if re.search(r"MCM/ICM", s2, flags=re.IGNORECASE):
            continue
        if len(s2) >= 12:
            return s2
    return ""


def _detect_sections(text: str) -> list[str]:
    t = _normalize(text)
    present = []
    for sec in SECTION_CANON:
        if _normalize(sec) in t:
            present.append(sec)
    return present


def _extract_section_order_from_toc(toc_text: str) -> list[str]:
    # Try to parse numbered TOC items like "1 Introduction" etc.
    lines = [ln.strip() for ln in toc_text.splitlines() if ln.strip()]
    out: list[str] = []
    for ln in lines:
        # typical: "1 Introduction" or "1. Introduction" or "2.1 Data"
        m = re.match(r"^(\d+(\.\d+)*)\s*[\.\-]?\s+(.{3,80})$", ln)
        if not m:
            continue
        title = m.group(3).strip()
        # remove trailing page numbers
        title = re.sub(r"\s+\d{1,2}$", "", title).strip()
        # ignore if it is just dots
        title = re.sub(r"\.{2,}.*$", "", title).strip()
        if not title:
            continue
        # canonicalize to known keywords if possible
        out.append(title)
    # de-duplicate while preserving order
    seen = set()
    dedup = []
    for x in out:
        k = _normalize(x)
        if k in seen:
            continue
        seen.add(k)
        dedup.append(x)
    return dedup[:40]


def _unique_numbers(pattern: str, text: str) -> set[int]:
    nums = set()
    for m in re.finditer(pattern, text, flags=re.IGNORECASE):
        try:
            nums.add(int(m.group(1)))
        except Exception:
            pass
    return nums


def _scan_fig_table_counts(fitz, np, ocr, doc) -> tuple[int, int]:
    # Fast-ish heuristic: OCR bottom 35% of each page and count unique Figure/Table numbers.
    fig_nums: set[int] = set()
    tbl_nums: set[int] = set()

    for i in range(doc.page_count):
        page = doc.load_page(i)
        img = _render_page_numpy(fitz, np, page, scale=1.1)
        h, w = img.shape[0], img.shape[1]
        crop = img[int(h * 0.62) : h, 0:w]  # bottom region
        items = _ocr_text_lines(ocr, crop)
        txt = _join_lines(items)
        fig_nums |= _unique_numbers(r"\bFigure\s+(\d+)\b", txt)
        tbl_nums |= _unique_numbers(r"\bTable\s+(\d+)\b", txt)
    return len(fig_nums), len(tbl_nums)


def _scan_refs_hints_and_count(fitz, np, ocr, doc) -> tuple[int, list[str]]:
    # OCR last pages and look for reference-like patterns / URLs / DOIs.
    last_n = min(10, doc.page_count)
    refs_entries = 0
    hints: list[str] = []
    for i in range(doc.page_count - last_n, doc.page_count):
        page = doc.load_page(i)
        img = _render_page_numpy(fitz, np, page, scale=1.5)
        items = _ocr_text_lines(ocr, img)
        txt = _join_lines(items)

        # Count lines like [1] ... or 1. ...
        for ln in txt.splitlines():
            s = ln.strip()
            if re.match(r"^\[\d+\]\s+", s):
                refs_entries += 1
            elif re.match(r"^\d+\.\s+", s) and ("http" in s.lower() or "doi" in s.lower()):
                refs_entries += 1

        # Hints: urls, doi, olympics/IOC, comap
        for token in re.findall(r"(https?://\\S+)", txt):
            short = token.strip().rstrip(").,;")
            hints.append(short[:120])
        if re.search(r"\bdoi\b", txt, flags=re.IGNORECASE):
            hints.append("DOI present")
        if re.search(r"\bOlympic|IOC|olympics\\.com\b", txt, flags=re.IGNORECASE):
            hints.append("Olympics/IOC source")
        if re.search(r"\bCOMAP\b", txt, flags=re.IGNORECASE):
            hints.append("COMAP official/policy")

    # Dedup hints
    dedup = []
    seen = set()
    for h in hints:
        k = _normalize(h)
        if k in seen:
            continue
        seen.add(k)
        dedup.append(h)
    return refs_entries, dedup[:20]


def _detect_ai_report(text: str) -> bool:
    t = _normalize(text)
    return ("report on use of ai" in t) or ("ai use report" in t) or ("reportaiuse" in t) or ("aimatter" in t)


def analyze_pdf(fitz, np, ocr, pdf_path: Path, *, scan_fig_table: bool) -> PaperStats:
    doc = fitz.open(str(pdf_path))

    # Summary page OCR
    page0 = doc.load_page(0)
    img0 = _render_page_numpy(fitz, np, page0, scale=2.0)
    items0 = _ocr_text_lines(ocr, img0)
    text0 = _join_lines(items0)
    lines0 = [t for _, __, t in items0]

    title_guess = _guess_title_from_summary(lines0)
    methods = _find_keywords(text0)

    # TOC / early pages
    toc_text = ""
    toc_present = False
    section_order: list[str] = []
    early_combined = []
    for i in range(min(4, doc.page_count)):
        page = doc.load_page(i)
        img = _render_page_numpy(fitz, np, page, scale=1.8)
        items = _ocr_text_lines(ocr, img)
        t = _join_lines(items)
        early_combined.append(t)
        if re.search(r"Table of Contents|Contents", t, flags=re.IGNORECASE):
            toc_present = True
            toc_text += "\n" + t
    if toc_present:
        section_order = _extract_section_order_from_toc(toc_text)

    # Figures/tables (heuristic)
    if scan_fig_table:
        fig_count, table_count = _scan_fig_table_counts(fitz, np, ocr, doc)
    else:
        fig_count, table_count = (0, 0)

    # References hints
    refs_count_guess, refs_hints = _scan_refs_hints_and_count(fitz, np, ocr, doc)

    # AI report present?
    # Scan last pages quickly
    ai_present = False
    last_scan = []
    for i in range(max(0, doc.page_count - 6), doc.page_count):
        page = doc.load_page(i)
        img = _render_page_numpy(fitz, np, page, scale=1.4)
        items = _ocr_text_lines(ocr, img)
        last_scan.append(_join_lines(items))
    ai_present = _detect_ai_report("\n".join(last_scan))

    # Section keywords present (from early pages + toc)
    sec_present = _detect_sections("\n".join(early_combined) + "\n" + toc_text)
    sections_guess = "|".join(section_order) if section_order else "|".join(sec_present)

    return PaperStats(
        file=pdf_path.name,
        pages=int(doc.page_count),
        title_guess=title_guess,
        toc_present=bool(toc_present),
        sections_guess=sections_guess,
        fig_count=int(fig_count),
        table_count=int(table_count),
        refs_count_guess=int(refs_count_guess),
        refs_hints="|".join(refs_hints),
        ai_report_present=bool(ai_present),
        methods_keywords="|".join(methods),
    )


def write_csv(rows: list[PaperStats], out_csv: Path) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(asdict(rows[0]).keys()))
        w.writeheader()
        for r in rows:
            w.writerow(asdict(r))


def _freq(items: Iterable[str]) -> list[tuple[str, int]]:
    m: dict[str, int] = {}
    for x in items:
        if not x:
            continue
        m[x] = m.get(x, 0) + 1
    return sorted(m.items(), key=lambda kv: (-kv[1], kv[0]))


def write_report(rows: list[PaperStats], out_md: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)

    # Aggregate section tokens (use SECTION_CANON presence from sections_guess)
    method_tokens: list[str] = []
    ai_count = 0
    toc_count = 0
    figs = []
    tbls = []
    pages = []
    titles = []
    for r in rows:
        pages.append(r.pages)
        figs.append(r.fig_count)
        tbls.append(r.table_count)
        titles.append(r.title_guess)
        if r.ai_report_present:
            ai_count += 1
        if r.toc_present:
            toc_count += 1
        method_tokens.extend([t for t in r.methods_keywords.split("|") if t])

    method_freq = _freq(method_tokens)[:20]

    def _median(nums: list[int]) -> int:
        s = sorted(nums)
        if not s:
            return 0
        mid = len(s) // 2
        return s[mid] if len(s) % 2 == 1 else int(round((s[mid - 1] + s[mid]) / 2))

    md_lines = []
    md_lines.append("# 2025 MCM Problem C — O-award Papers Meta Analysis (OCR-based)")
    md_lines.append("")
    md_lines.append("> This report is generated via OCR. For image-based PDFs, OCR may introduce errors; treat numbers as approximations.")
    md_lines.append("")
    md_lines.append("## Corpus")
    md_lines.append(f"- Papers: **{len(rows)}**")
    md_lines.append(f"- Total PDF pages (median): **{_median(pages)}** (min {min(pages)}, max {max(pages)})")
    md_lines.append(f"- Figures referenced (median): **{_median(figs)}**")
    md_lines.append(f"- Tables referenced (median): **{_median(tbls)}**")
    md_lines.append(f"- TOC present: **{toc_count}/{len(rows)}**")
    md_lines.append(f"- AI Use Report detected: **{ai_count}/{len(rows)}**")
    md_lines.append("")
    md_lines.append("## High-frequency methods/keywords (from Summary Sheet only)")
    md_lines.append("")
    md_lines.append("| Keyword | Count |")
    md_lines.append("|---|---:|")
    for k, c in method_freq:
        md_lines.append(f"| {k} | {c} |")
    md_lines.append("")
    md_lines.append("## Per-paper quick inventory")
    md_lines.append("")
    md_lines.append("| File | Pages | Title (guess) | TOC | Fig | Tbl | Refs* | AI report | Methods (summary keywords) |")
    md_lines.append("|---|---:|---|:--:|---:|---:|---:|:--:|---|")
    for r in rows:
        md_lines.append(
            f"| {r.file} | {r.pages} | {r.title_guess[:60]} | {'Y' if r.toc_present else 'N'} | {r.fig_count} | {r.table_count} | {r.refs_count_guess} | {'Y' if r.ai_report_present else 'N'} | {r.methods_keywords} |"
        )
    md_lines.append("")
    md_lines.append("\\* Refs are estimated by counting reference-like lines on the last pages; not exact.")
    md_lines.append("")
    md_lines.append("## Notes to guide manual reading (what to look for)")
    md_lines.append("- Summary Sheet: 1-page, dense, has **framework + methods + quantitative results + uncertainty**.")
    md_lines.append("- Body: look for a clear **model ladder** (baseline → improved → final) and **validation/sensitivity**.")
    md_lines.append("- References: check for a mix of **official IOC/Olympics/COMAP** + **methods papers** + **data dictionary citations**.")
    md_lines.append("- AI Use Report: if present, it should be appended after the main solution (not counted in 25 pages).")
    md_lines.append("")

    out_md.write_text("\n".join(md_lines).strip() + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf-dir", required=True, help="Directory containing PDFs (e.g., $MCM_WORKSPACE/C)")
    parser.add_argument("--out-dir", required=True, help="Output directory for report/csv")
    parser.add_argument("--fast", action="store_true", help="Skip full figure/table scan (much faster, less accurate)")
    parser.add_argument("--resume", action="store_true", help="Resume from an existing CSV in out-dir (if present)")
    args = parser.parse_args()

    pdf_dir = Path(args.pdf_dir).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    pdfs = sorted([p for p in pdf_dir.glob("*.pdf") if p.is_file()])
    if not pdfs:
        raise SystemExit(f"No PDFs found in: {pdf_dir}")

    fitz, np, RapidOCR = _lazy_imports()
    # Create OCR engine ONCE (model load is expensive).
    ocr = RapidOCR()

    out_csv = out_dir / "2025_oaward_c_papers.csv"
    out_md = out_dir / "2025_oaward_c_report.md"

    existing: dict[str, PaperStats] = {}
    if args.resume and out_csv.exists():
        with out_csv.open("r", encoding="utf-8", newline="") as f:
            r = csv.DictReader(f)
            for row in r:
                try:
                    existing[row["file"]] = PaperStats(
                        file=row["file"],
                        pages=int(row["pages"]),
                        title_guess=row.get("title_guess", ""),
                        toc_present=str(row.get("toc_present", "")).lower() in {"1", "true", "y", "yes"},
                        sections_guess=row.get("sections_guess", ""),
                        fig_count=int(row.get("fig_count", "0") or 0),
                        table_count=int(row.get("table_count", "0") or 0),
                        refs_count_guess=int(row.get("refs_count_guess", "0") or 0),
                        refs_hints=row.get("refs_hints", ""),
                        ai_report_present=str(row.get("ai_report_present", "")).lower() in {"1", "true", "y", "yes"},
                        methods_keywords=row.get("methods_keywords", ""),
                    )
                except Exception:
                    continue

    rows: list[PaperStats] = list(existing.values())

    for i, p in enumerate(pdfs, start=1):
        if p.name in existing:
            print(f"[{i}/{len(pdfs)}] Skipping (resume): {p.name}", file=sys.stderr)
            continue
        print(f"[{i}/{len(pdfs)}] OCR analyzing: {p.name}", file=sys.stderr)
        stat = analyze_pdf(fitz, np, ocr, p, scan_fig_table=not args.fast)
        rows.append(stat)

        # Persist progress after each file to allow resume.
        write_csv(rows, out_csv)

    if rows:
        write_csv(rows, out_csv)
        write_report(rows, out_md)
        print(f"Wrote: {out_csv}")
        print(f"Wrote: {out_md}")


if __name__ == "__main__":
    main()
