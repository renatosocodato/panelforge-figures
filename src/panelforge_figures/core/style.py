"""Base typography, spine, tick, and export rcParams — applied once per session.

This module is the single source of truth for the cross-modality visual
contract: the Helvetica-first font stack, the approved font-size and
line-width scales that every recipe should honor, and the rcParams that
enforce them globally.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass
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


@dataclass(frozen=True)
class _FontSizes:
    """Discrete font-size scale in points. Recipes should pull from here
    rather than sprinkling free-form floats.

    The scale is intentionally small: 7 named tiers span the range used
    by every gallery panel, from tick labels up to figure-level titles.
    """

    tiny: float = 5.8          # inline tags, per-group N labels
    callout: float = 6.4       # in-axes stat callouts, significance pills
    tick: float = 7.5          # matches rcParams x/ytick.labelsize
    legend: float = 7.5        # matches rcParams legend.fontsize
    axis_label: float = 8.5    # matches rcParams axes.labelsize
    panel_title: float = 9.5   # matches rcParams axes.titlesize
    fig_title: float = 12.0    # matches rcParams figure.titlesize


@dataclass(frozen=True)
class _LineWidths:
    """Line-width scale used across every plotted element."""

    hairline: float = 0.4      # grid, faint reference markers
    thin: float = 0.7          # spines, tick marks, threshold lines
    regular: float = 1.1       # data curves, fits, CI outlines
    heavy: float = 1.6         # emphasis curves (population means, fits)


PF_FONT_SIZES = _FontSizes()
PF_LINE_WIDTHS = _LineWidths()

# Range used by the QA checker to flag recipes whose text is too tiny to read
# or absurdly large (usually a units bug where points got confused with px).
# The upper bound is generous because grant-summary tiles and section
# headlines intentionally run up to ~30 pt.
PF_MIN_FONTSIZE_PT: float = 5.0
PF_MAX_FONTSIZE_PT: float = 32.0

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
        # Math text — use the sans-serif STIX set so $S_T$, $\\Pi_3$, Greek
        # letters, etc. visually match the Helvetica body text. `regular`
        # makes plain math characters inherit the regular font family
        # (Helvetica) rather than switching to an italic math font.
        "mathtext.fontset": "stixsans",
        "mathtext.default": "regular",
        "mathtext.rm": "sans",
        "mathtext.it": "sans:italic",
        "mathtext.bf": "sans:bold",
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


def is_approved_font_family(family: str | list[str] | tuple[str, ...]) -> bool:
    """True if the matplotlib font spec resolves to the panelforge stack.

    Accepts the string ``'sans-serif'`` (which defers to rcParams and
    therefore picks up the stack), or any explicit name that is a member
    of :data:`PF_FONT_STACK`. Tuples/lists are OK if their first element
    passes the same test — matplotlib uses the first item as the primary
    family.
    """
    if isinstance(family, str):
        if family == "sans-serif":
            return True
        return family in PF_FONT_STACK
    if isinstance(family, (list, tuple)) and family:
        return is_approved_font_family(family[0])
    return False
