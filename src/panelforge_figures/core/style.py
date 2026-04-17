"""Base typography, spine, tick, and export rcParams — applied once per session."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any

import matplotlib as mpl
import matplotlib.pyplot as plt

log = logging.getLogger(__name__)

# Helvetica → Helvetica Neue → Arial → Liberation Sans → DejaVu Sans fallback.
PF_FONT_STACK: tuple[str, ...] = (
    "Helvetica",
    "Helvetica Neue",
    "Arial",
    "Liberation Sans",
    "DejaVu Sans",
)

PF_SPINE_COLOR = "#333333"
PF_TEXT_COLOR = "#111111"
PF_MUTED_COLOR = "#666666"
PF_GRID_ALPHA = 0.0  # no grid by default

_CURRENT_THEME: str = "default"


def _rc_defaults() -> dict[str, Any]:
    """Return the shared matplotlib rcParams baseline.

    Size conventions (pt):
      - base font               8.5
      - panel title             9.5 bold
      - suptitle               12.0 bold
      - suptitle subtitle       9.0 (muted)
      - legend                  7.5
      - tick labels             7.5
    """
    return {
        "font.family": "sans-serif",
        "font.sans-serif": list(PF_FONT_STACK),
        "font.size": 8.5,
        "text.color": PF_TEXT_COLOR,
        "axes.edgecolor": PF_SPINE_COLOR,
        "axes.linewidth": 0.7,
        "axes.labelcolor": PF_TEXT_COLOR,
        "axes.labelsize": 8.5,
        "axes.titlesize": 9.5,
        "axes.titleweight": "bold",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": False,
        "xtick.color": PF_SPINE_COLOR,
        "ytick.color": PF_SPINE_COLOR,
        "xtick.major.width": 0.7,
        "ytick.major.width": 0.7,
        "xtick.major.size": 3.0,
        "ytick.major.size": 3.0,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.labelsize": 7.5,
        "ytick.labelsize": 7.5,
        "legend.fontsize": 7.5,
        "legend.frameon": False,
        "figure.titlesize": 12.0,
        "figure.titleweight": "bold",
        "figure.facecolor": "white",
        "figure.dpi": 120,
        "savefig.dpi": 600,
        "savefig.bbox": "tight",
        "savefig.facecolor": "white",
        # Preserve text as text in vector outputs — critical for editors.
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "pdf.use14corefonts": False,
    }


def apply_base_style(theme: str = "default", overrides: dict[str, Any] | None = None) -> None:
    """Apply the shared baseline rcParams, then optionally layer per-theme rcParams."""
    global _CURRENT_THEME
    for k, v in _rc_defaults().items():
        mpl.rcParams[k] = v
    if overrides:
        for k, v in overrides.items():
            mpl.rcParams[k] = v
    _CURRENT_THEME = theme
    log.debug("applied base style; theme=%s", theme)


def current_theme() -> str:
    return _CURRENT_THEME


@contextmanager
def temporary_style(overrides: dict[str, Any]):
    """Context manager for one-off rc overrides (used mainly in tests)."""
    saved = {k: mpl.rcParams[k] for k in overrides}
    try:
        for k, v in overrides.items():
            mpl.rcParams[k] = v
        yield
    finally:
        for k, v in saved.items():
            mpl.rcParams[k] = v


def close_all_figures() -> None:
    plt.close("all")
