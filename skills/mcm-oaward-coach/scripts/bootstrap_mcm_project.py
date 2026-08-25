#!/usr/bin/env python3
"""
Bootstrap a reproducible local project structure for an MCM/ICM run:
- Copy/download problem PDF and extract its text
- Copy data (file/dir) when provided
- Create a LaTeX skeleton based on the user's local mcmthesis template

This is a helper script for the mcm-oaward-coach skill.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import re
import shutil
import subprocess
import sys
import textwrap
import urllib.parse
import urllib.request
from pathlib import Path


def _is_url(s: str) -> bool:
    try:
        u = urllib.parse.urlparse(s)
    except Exception:
        return False
    return u.scheme in {"http", "https"}


def _download(url: str, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Avoid partial file if download fails.
    tmp_path = out_path.with_suffix(out_path.suffix + ".partial")
    if tmp_path.exists():
        tmp_path.unlink()
    try:
        urllib.request.urlretrieve(url, tmp_path)  # nosec - user-provided URL
        tmp_path.replace(out_path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)  # type: ignore[arg-type]


def _slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "mcm-project"


def _guess_year_from_name(name: str) -> str | None:
    m = re.search(r"(19|20)\d{2}", name)
    return m.group(0) if m else None


def _copy_data(src: Path, dest_dir: Path) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dest_dir / src.name, dirs_exist_ok=True)
    else:
        shutil.copy2(src, dest_dir / src.name)


def _ensure_symlink_or_dir(target: Path, link_path: Path) -> None:
    if link_path.exists() or link_path.is_symlink():
        return
    try:
        link_path.symlink_to(target)
    except Exception:
        link_path.mkdir(parents=True, exist_ok=True)


def _latex_main_tex(problem_letter: str, tcn: str) -> str:
    # Keep this skeleton short; user will fill in content.
    return textwrap.dedent(
        rf"""
        \documentclass{{mcmthesis}}
        % If you use a CTeX distribution and need Chinese, uncomment:
        % \documentclass[CTeX = true]{{mcmthesis}}

        \mcmsetup{{tcn = {tcn}, problem = {problem_letter},
          sheet = true, titleinsheet = true, keywordsinsheet = true,
          titlepage = false, abstract = true}}

        \usepackage{{caption}}
        \captionsetup[figure]{{font=small}}
        \captionsetup[table]{{font=small}}
        \captionsetup[table]{{skip=2pt}}
        \usepackage{{indentfirst}}
        \usepackage{{subcaption}}
        \usepackage{{xcolor}}
        % References (BibTeX, minimal dependencies)
        % If you prefer biblatex/biber, switch later.

        % Fix fancyhdr warning (optional)
        \setlength{{\headheight}}{{14pt}}
        \addtolength{{\topmargin}}{{-1.6pt}}

        \setcounter{{tocdepth}}{{2}} % keep TOC compact

        \title{{<Your Paper Title Here>}}
        \date{{\today}}

        \begin{{document}}

        \begin{{abstract}}
        % Summary (1 page max in the final PDF, per contest rules).
        % Write AFTER results are ready; place it here as the first page.
        %
        % Template:
        % - Problem in 1 sentence
        % - Overall framework (1–2 sentences)
        % - Key assumptions (1–3)
        % - Key quantitative results (2–4 bullets with numbers + units)
        % - Recommendations / conclusions
        % - Validation / sensitivity (1 sentence)

        <Write your summary here.>

        \begin{{keywords}}
        <keyword1>, <keyword2>, <keyword3>
        \end{{keywords}}
        \end{{abstract}}

        % Optional TOC (many teams include it; remove if it costs pages).
        % \tableofcontents

        \section{{Introduction and Problem Restatement}}
        <...>

        \section{{Assumptions and Notation}}
        <...>

        \section{{Data}}
        <...>

        \section{{Model Formulation}}
        <...>

        \section{{Results}}
        <...>

        \section{{Analysis and Discussion}}
        <...>

        \section{{Sensitivity / Robustness / Validation}}
        <...>

        \section{{Strengths and Weaknesses}}
        <...>

        \section{{Conclusion and Recommendations}}
        <...>

        \bibliographystyle{{plain}}
        \bibliography{{references}}

        % Mark the end of the main (counted) solution for page-limit checks.
        % The COMAP AI policy allows appending an AI Use Report after the 25-page solution.
        \label{{MainLastPage}}

        % --- Report on Use of AI Tools (append after the 25-page solution) ---
        % If you did NOT use AI tools, remove this block and delete ai_use_report.tex.
        \clearpage
        \input{{ai_use_report}}

        % For "Page X of Y" header in mcmthesis.cls (total pages of the whole PDF)
        \label{{LastPage}}

        \end{{document}}
        """
    ).lstrip()


def _copy_template(template_path: Path, dest_path: Path) -> None:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_text(template_path.read_text(encoding="utf-8"), encoding="utf-8")


def _run_script(script_path: Path, argv: list[str]) -> None:
    cmd = [sys.executable, str(script_path), *argv]
    subprocess.run(cmd, check=True)  # nosec - local trusted scripts


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap an MCM/ICM project folder")
    parser.add_argument("--problem-pdf", required=True, help="Path or URL to the problem PDF")
    parser.add_argument("--data-path", default=None, help="Optional: path or URL to dataset (file or directory)")
    parser.add_argument("--oaward-samples", default=None, help="Optional: local path to O-award sample PDFs folder")
    parser.add_argument("--mcm-notes", default=None, help="Optional: local path to your MCM notes folder")
    parser.add_argument("--latex-template", default="$MCM_WORKSPACE/MCM_Latex2026", help="Path to mcmthesis template folder")
    parser.add_argument("--problem-letter", default="C", help="Problem letter, e.g. A/B/C/D/E/F")
    parser.add_argument("--tcn", default="<TCN>", help="Team Control Number (placeholder is ok)")
    parser.add_argument("--out-dir", default=".", help="Where to create the project folder")
    parser.add_argument("--project-name", default=None, help="Optional: override project directory name")
    args = parser.parse_args()

    timestamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    problem_letter = str(args.problem_letter).strip().upper() or "C"
    tcn = str(args.tcn).strip() or "<TCN>"

    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Resolve problem pdf: local path or download URL.
    problem_pdf_in = args.problem_pdf
    problem_pdf_name = Path(urllib.parse.urlparse(problem_pdf_in).path).name if _is_url(problem_pdf_in) else Path(problem_pdf_in).name
    year = _guess_year_from_name(problem_pdf_name) or _dt.datetime.now().strftime("%Y")

    project_name = args.project_name or _slugify(f"{year}_mcm_{problem_letter}_{timestamp}")
    project_dir = out_dir / project_name
    project_dir.mkdir(parents=True, exist_ok=False)

    # Standard structure.
    inputs_dir = project_dir / "inputs"
    data_dir = project_dir / "data"
    analysis_dir = project_dir / "analysis"
    figures_dir = project_dir / "figures"
    plan_dir = project_dir / "plan"
    results_dir = project_dir / "results"
    paper_dir = project_dir / "paper"
    for d in (inputs_dir, data_dir, analysis_dir, figures_dir, plan_dir, results_dir, paper_dir):
        d.mkdir(parents=True, exist_ok=True)

    skill_dir = Path(__file__).expanduser().resolve().parents[1]
    templates_dir = skill_dir / "templates"
    scripts_dir = skill_dir / "scripts"

    # Put a short README.
    (project_dir / "README.md").write_text(
        textwrap.dedent(
            f"""\
            # MCM/ICM Project

            - Problem: {problem_letter}
            - Year (guessed): {year}
            - Created: {timestamp}

            ## Key folders
            - inputs/: problem PDF and extracted text
            - data/: datasets and `README.md` for sources
            - analysis/: notebooks/scripts for EDA and models
            - figures/: publication-ready figures (pdf/png 300dpi)
            - paper/: LaTeX source (mcmthesis)

            ## Compile LaTeX
            ```bash
            cd paper
            latexmk -xelatex -interaction=nonstopmode main.tex
            ```
            """
        ),
        encoding="utf-8",
    )

    # Copy/download problem PDF.
    problem_pdf_out = inputs_dir / "problem.pdf"
    if _is_url(problem_pdf_in):
        _download(problem_pdf_in, problem_pdf_out)
    else:
        src = Path(problem_pdf_in).expanduser().resolve()
        if not src.exists():
            raise SystemExit(f"Problem PDF not found: {src}")
        shutil.copy2(src, problem_pdf_out)

    # Extract text.
    extracted_txt = inputs_dir / "problem.txt"
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(str(problem_pdf_out))
        chunks = []
        for i, page in enumerate(reader.pages, start=1):
            txt = ""
            try:
                txt = page.extract_text() or ""
            except Exception:
                txt = ""
            chunks.append(f"\n\n--- Page {i} ---\n\n{txt}".rstrip())
        extracted_txt.write_text("\n".join(chunks).strip() + "\n", encoding="utf-8")
    except Exception as e:
        extracted_txt.write_text(f"[extract failed] {e}\n", encoding="utf-8")

    # Copy data if provided.
    if args.data_path:
        if _is_url(args.data_path):
            # Download into data/ (best-effort; filename inferred from URL path)
            url_name = Path(urllib.parse.urlparse(args.data_path).path).name or "dataset"
            _download(args.data_path, data_dir / url_name)
        else:
            data_src = Path(args.data_path).expanduser().resolve()
            if not data_src.exists():
                raise SystemExit(f"Data path not found: {data_src}")
            _copy_data(data_src, data_dir)

    # Data sources README placeholder.
    (data_dir / "README.md").write_text(
        textwrap.dedent(
            """\
            # Data sources (fill this)

            For every dataset you use (given or external), record:
            - name:
            - source (URL / organization):
            - download date:
            - time coverage:
            - fields/units notes:
            - how it's used in the paper:
            """
        ),
        encoding="utf-8",
    )

    # Plan/intake placeholder (link local resources; do not copy large PDFs).
    (plan_dir / "intake.md").write_text(
        textwrap.dedent(
            f"""\
            # Intake

            ## Inputs
            - Problem PDF: {problem_pdf_out}
            - Problem text: {extracted_txt}
            - Data: {data_dir}

            ## Local reference resources (optional)
            - O-award samples: {args.oaward_samples or "<not provided>"}
            - MCM notes: {args.mcm_notes or "<not provided>"}

            ## Hard constraints (verify against official docs for the target year)
            - Page limit: <= N pages for the *main solution* (often 25; check official instructions).
            - Page limit counts: Summary Sheet, Solution, References, TOC, Notes, Appendices, Code, and any problem-specific requirements.
            - PDF in English, readable font >= 12pt.
            - Anonymity: no student/advisor/school names; only TCN.
            - If AI tools used: append "Report on Use of AI Tools" after the main solution (typically not counted; check policy).

            ## Questions to answer (edit this list)
            1. What are the sub-questions/tasks in the problem statement?
            2. What are the evaluation metrics and constraints?
            3. What data is given vs. missing (data gap list)?
            4. What modeling approaches are plausible (2+ routes)?
            5. What is the validation / sensitivity plan?
            """
        ),
        encoding="utf-8",
    )

    # Planning / QA artifacts (best-effort; bootstrap should not fail if a helper fails).
    try:
        _run_script(
            scripts_dir / "create_page_budget.py",
            ["--out", str(plan_dir / "page_budget.md"), "--page-limit", "25", "--include-toc"],
        )
    except Exception:
        pass

    try:
        _run_script(
            scripts_dir / "create_issues_csv.py",
            ["--out", str(plan_dir / "issues.csv"), "--problem-letter", problem_letter],
        )
    except Exception:
        pass

    try:
        _copy_template(templates_dir / "ai_use_log.md", plan_dir / "ai_use_log.md")
    except Exception:
        pass
    try:
        _copy_template(templates_dir / "results_summary.md", results_dir / "summary.md")
    except Exception:
        pass

    # Optional: extract official constraints from cached docs under mcm-notes/来源.
    if args.mcm_notes:
        notes_dir = Path(args.mcm_notes).expanduser().resolve()
        instr_html = notes_dir / "来源" / "mcm_instructions.html"
        ai_pdf = notes_dir / "来源" / "Contest_AI_Policy.pdf"
        if instr_html.exists() or ai_pdf.exists():
            try:
                _run_script(
                    scripts_dir / "extract_official_constraints.py",
                    [
                        "--out",
                        str(plan_dir / "constraints.md"),
                        "--instructions-html",
                        str(instr_html),
                        "--ai-policy-pdf",
                        str(ai_pdf),
                    ],
                )
            except Exception:
                pass

    # Optional: index local O-award samples (inventory only).
    if args.oaward_samples:
        samples_dir = Path(args.oaward_samples).expanduser().resolve()
        if samples_dir.exists():
            try:
                _run_script(
                    scripts_dir / "index_oaward_samples.py",
                    ["--samples-dir", str(samples_dir), "--out", str(plan_dir / "oaward_samples_index.md")],
                )
            except Exception:
                pass

    # LaTeX skeleton (copy cls + bib; create main.tex).
    latex_template = Path(args.latex_template).expanduser().resolve()
    cls_src = latex_template / "mcmthesis.cls"
    bib_src = latex_template / "references.bib"
    if not cls_src.exists():
        raise SystemExit(f"mcmthesis.cls not found under: {latex_template}")
    shutil.copy2(cls_src, paper_dir / "mcmthesis.cls")
    if bib_src.exists():
        shutil.copy2(bib_src, paper_dir / "references.bib")
    else:
        (paper_dir / "references.bib").write_text("% Add BibTeX entries here\n", encoding="utf-8")

    # AI Use Report template (append after main solution; not counted in page limit per policy).
    try:
        _copy_template(templates_dir / "ai_use_report.tex", paper_dir / "ai_use_report.tex")
    except Exception:
        (paper_dir / "ai_use_report.tex").write_text("% AI Use Report (fill if applicable)\n", encoding="utf-8")

    (paper_dir / "main.tex").write_text(_latex_main_tex(problem_letter=problem_letter, tcn=tcn), encoding="utf-8")

    # Link figures for convenience.
    _ensure_symlink_or_dir(figures_dir, paper_dir / "figures")

    (paper_dir / "README.md").write_text(
        textwrap.dedent(
            """\
            # LaTeX (mcmthesis) paper

            Compile:
            ```bash
            latexmk -xelatex -interaction=nonstopmode main.tex
            ```

            Notes:
            - This skeleton uses BibTeX (`references.bib`) for minimal dependencies.
            - Put figures under ../figures (or paper/figures).
            - Page-limit check (recommended):
              ```bash
              python3 ~/.codex/skills/mcm-oaward-coach/scripts/check_page_limit.py \
                --pdf main.pdf --aux main.aux --limit 25
              ```
            """
        ),
        encoding="utf-8",
    )

    print(f"Project: {project_dir}")
    print(f"Problem PDF: {problem_pdf_out}")
    print(f"Problem text: {extracted_txt}")
    print(f"Paper: {paper_dir / 'main.tex'}")


if __name__ == "__main__":
    main()
