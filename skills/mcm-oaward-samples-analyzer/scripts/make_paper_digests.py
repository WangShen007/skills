#!/usr/bin/env python3
"""
Create per-paper digests from OCR'd Summary Sheet texts.

Input:
  out/pages/summary/*.txt
Output:
  out/2025_oaward_c_paper_digests.md
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


KEYS = {
    "forecast": ["ARIMA", "SARIMA", "LSTM", "GRU", "Prophet", "Kalman", "state-space"],
    "ml": ["XGBoost", "Random Forest", "LightGBM", "CatBoost", "SVM", "Neural", "CNN", "Stacking", "Ensemble"],
    "bayes": ["Bayesian", "MCMC", "Dirichlet", "Multinomial", "hierarchical", "prior", "posterior", "credible"],
    "count": ["Poisson", "negative binomial", "zero-inflated", "ZINB"],
    "uncertainty": ["bootstrap", "Monte Carlo", "prediction interval", "credible interval", "confidence interval"],
    "interpret": ["SHAP", "Spearman", "correlation", "feature importance"],
    "coach": ["DID", "PSM", "difference-in-differences", "causal", "GAN"],
    "first_medal": ["first medal", "zero", "breakthrough", "ice-breaking", "non-medal"],
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def _contains(text: str, phrase: str) -> bool:
    return _norm(phrase) in _norm(text)


def _pick_keywords(text: str, candidates: list[str]) -> list[str]:
    t = _norm(text)
    out = []
    for c in candidates:
        if _norm(c) in t:
            out.append(c)
    return out


def _guess_title(lines: list[str]) -> str:
    joined = "\n".join(lines)
    m = re.search(r"Summary Sheet\s*\n(.{6,140})", joined, flags=re.IGNORECASE)
    if m:
        return m.group(1).strip()
    # fallback: find first long line after team number block
    for ln in lines:
        s = ln.strip()
        if len(s) >= 12 and not re.fullmatch(r"\d{4}", s):
            if "team" in s.lower() and "control" in s.lower():
                continue
            if "summary" == s.lower() or "summarysheet" == s.lower():
                continue
            return s
    return ""


def digest_one(path: Path) -> dict:
    txt = path.read_text(encoding="utf-8", errors="ignore")
    lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
    title = _guess_title(lines)

    parts = {
        "forecast": _pick_keywords(txt, KEYS["forecast"]),
        "ml": _pick_keywords(txt, KEYS["ml"]),
        "bayes": _pick_keywords(txt, KEYS["bayes"]),
        "count": _pick_keywords(txt, KEYS["count"]),
        "uncertainty": _pick_keywords(txt, KEYS["uncertainty"]),
        "interpret": _pick_keywords(txt, KEYS["interpret"]),
        "coach": _pick_keywords(txt, KEYS["coach"]),
        "first_medal": _pick_keywords(txt, KEYS["first_medal"]),
    }

    # build concise tags
    tags = []
    for k in ["bayes", "count", "forecast", "ml", "uncertainty", "interpret", "coach", "first_medal"]:
        if parts[k]:
            tags.append(f"{k}:" + ",".join(parts[k][:3]))

    # one-line note: try to capture a strong "novelty" phrase
    note = ""
    m = re.search(r"(we (propose|present|develop|build).{0,120})", _norm(txt))
    if m:
        note = m.group(1)
    return {"file": path.stem + ".pdf", "title": title, "tags": " | ".join(tags), "note": note[:160]}


def main() -> None:
    parser = argparse.ArgumentParser(description="Make per-paper digests from OCR summary texts")
    parser.add_argument("--summary-dir", required=True, help="Directory with OCR summary .txt files")
    parser.add_argument("--out", required=True, help="Output markdown path")
    args = parser.parse_args()

    summary_dir = Path(args.summary_dir).expanduser().resolve()
    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    files = sorted(summary_dir.glob("*.txt"))
    if not files:
        raise SystemExit(f"No *.txt found in: {summary_dir}")

    rows = [digest_one(p) for p in files]

    md = []
    md.append("# 2025 C题 O奖论文 — Summary Sheet 摘要要点（OCR 摘要自动提取）")
    md.append("")
    md.append("> 用法：每篇先看 Summary Sheet 的方法标签与关键词，快速分类；再去对应 PDF 看正文怎么把链条讲完整。")
    md.append("")
    md.append("| Paper | Title (guess) | Method tags (from summary) | One-line note (auto) |")
    md.append("|---|---|---|---|")
    for r in rows:
        md.append(
            f"| {r['file']} | {r['title'][:60]} | {r['tags']} | {r['note']} |"
        )
    md.append("")
    out_path.write_text("\n".join(md).strip() + "\n", encoding="utf-8")
    print(f"Wrote: {out_path}")


if __name__ == "__main__":
    main()

