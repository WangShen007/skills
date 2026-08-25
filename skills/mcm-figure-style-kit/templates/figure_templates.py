"""
Common figure templates for MCM/ICM papers.

These are minimal helpers to quickly create publication-ready figures with consistent style.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def trend_line(x: Sequence[float], y: Sequence[float], *, xlabel: str, ylabel: str, title: str, out: str) -> None:
    from plot_style import apply_mcm_style, COLORBLIND

    apply_mcm_style()
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.6, 3.6))
    ax.plot(x, y, marker="o", color=COLORBLIND[0], linewidth=2)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    fig.tight_layout()
    _ensure_dir(Path(out))
    fig.savefig(out)
    plt.close(fig)


def distribution_hist(data: Sequence[float], *, xlabel: str, title: str, out: str) -> None:
    from plot_style import apply_mcm_style, COLORBLIND

    apply_mcm_style()
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    ax.hist(data, bins=30, color=COLORBLIND[2], alpha=0.85)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Count")
    ax.set_title(title)
    fig.tight_layout()
    _ensure_dir(Path(out))
    fig.savefig(out)
    plt.close(fig)


def tornado_plot(
    labels: Sequence[str],
    low: Sequence[float],
    high: Sequence[float],
    *,
    xlabel: str,
    title: str,
    out: str,
) -> None:
    from plot_style import apply_mcm_style, COLORBLIND

    apply_mcm_style()
    import matplotlib.pyplot as plt
    import numpy as np

    y = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.barh(y, high, color=COLORBLIND[0], alpha=0.85, label="High")
    ax.barh(y, low, color=COLORBLIND[1], alpha=0.85, label="Low")
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel(xlabel)
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    _ensure_dir(Path(out))
    fig.savefig(out)
    plt.close(fig)

