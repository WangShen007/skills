#!/usr/bin/env python3
"""
Install the MCM figure style kit into a project folder.

Copies:
  - templates/plot_style.py -> <project>/analysis/plot_style.py
  - templates/figure_templates.py -> <project>/analysis/figure_templates.py
"""

from __future__ import annotations

import argparse
from pathlib import Path


def _copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Install MCM figure style kit into a project")
    parser.add_argument("--project", required=True, help="Project root (contains analysis/ folder)")
    args = parser.parse_args()

    project = Path(args.project).expanduser().resolve()
    if not project.exists():
        raise SystemExit(f"Project not found: {project}")

    skill_dir = Path(__file__).expanduser().resolve().parents[1]
    tpl_dir = skill_dir / "templates"

    _copy(tpl_dir / "plot_style.py", project / "analysis" / "plot_style.py")
    _copy(tpl_dir / "figure_templates.py", project / "analysis" / "figure_templates.py")

    print(f"Installed into: {project}")
    print(f"- {project / 'analysis' / 'plot_style.py'}")
    print(f"- {project / 'analysis' / 'figure_templates.py'}")


if __name__ == "__main__":
    main()

