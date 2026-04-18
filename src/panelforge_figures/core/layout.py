"""Figure-size presets and panel-grid helpers."""

from __future__ import annotations

from collections.abc import Sequence

import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

# Size presets in inches (width, height).
FIGSIZE_PRESETS: dict[str, tuple[float, float]] = {
    "single": (3.5, 2.6),
    "single_sq": (3.5, 3.5),
    "1p5": (5.2, 3.6),
    "double": (7.2, 3.6),
    "double_sq": (7.2, 7.2),
    "tall": (3.5, 5.5),
    "a4_portrait": (7.2, 9.7),
    "a4_landscape": (9.7, 7.2),
}


def make_figure(size: str | tuple[float, float] = "single", dpi: int = 120):
    """Create a figure at a registered preset, or pass an explicit (w, h) tuple."""
    wh = FIGSIZE_PRESETS[size] if isinstance(size, str) else tuple(size)
    return plt.figure(figsize=wh, dpi=dpi)


def make_panel_grid(
    fig,
    nrows: int,
    ncols: int,
    *,
    hspace: float = 0.35,
    wspace: float = 0.30,
    left: float = 0.08,
    right: float = 0.97,
    top: float = 0.90,
    bottom: float = 0.10,
    height_ratios: Sequence[float] | None = None,
    width_ratios: Sequence[float] | None = None,
) -> GridSpec:
    """Shared gridspec with conservative margins — panels show breathing room."""
    return fig.add_gridspec(
        nrows=nrows,
        ncols=ncols,
        hspace=hspace,
        wspace=wspace,
        left=left,
        right=right,
        top=top,
        bottom=bottom,
        height_ratios=height_ratios,
        width_ratios=width_ratios,
    )


def panel_tag(ax, tag: str, *, pad_left: float = -0.14, pad_top: float = 1.08,
              fontsize: float = 11.0, fontweight: str = "bold"):
    """Draw the A/B/C panel tag at the upper-left."""
    ax.text(
        pad_left,
        pad_top,
        tag,
        transform=ax.transAxes,
        fontsize=fontsize,
        fontweight=fontweight,
        ha="left",
        va="top",
    )


def suptitle_with_subtitle(
    fig, title: str, subtitle: str | None = None, *, y_title: float = 0.985, y_sub: float = 0.952
):
    """Suptitle bold; optional 9pt muted subtitle below."""
    fig.suptitle(title, fontsize=12, fontweight="bold", y=y_title)
    if subtitle:
        fig.text(0.5, y_sub, subtitle, ha="center", va="top", fontsize=9, color="#555555")
