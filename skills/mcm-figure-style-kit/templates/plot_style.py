"""
Reusable plotting style for MCM/ICM papers (clean 2D, colorblind-friendly).

Usage:
  from plot_style import apply_mcm_style, COLORBLIND
  apply_mcm_style()
"""

from __future__ import annotations


COLORBLIND = [
    "#0072B2",  # blue
    "#D55E00",  # vermillion
    "#009E73",  # green
    "#CC79A7",  # reddish purple
    "#F0E442",  # yellow
    "#56B4E9",  # sky blue
    "#000000",  # black
]


def apply_mcm_style() -> None:
    import matplotlib as mpl

    try:
        import seaborn as sns  # type: ignore

        sns.set_theme(style="whitegrid", context="talk")
    except Exception:
        pass

    mpl.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "DejaVu Serif", "STIXGeneral"],
            "axes.unicode_minus": False,
            "figure.dpi": 120,
            "savefig.dpi": 300,
            "axes.titleweight": "bold",
            "axes.labelsize": 12,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "legend.frameon": False,
            "grid.alpha": 0.2,
        }
    )

