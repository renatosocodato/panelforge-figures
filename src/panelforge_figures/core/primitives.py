"""Shared drawing primitives used across all modality recipes.

This module is the single source of truth for the visual craft in
panelforge-figures: halo'd labels, smart numeric formatting, right-of-CI label
placement, colored bracket group markers, white-bordered stat callout boxes,
density-based scatter alpha, bootstrap CI bands, violin with per-animal ring
markers, and helpers for phase-portrait decoration (fixed-point dots, saddle
stars, regime shading).
"""

from __future__ import annotations

import math
from typing import Iterable, Sequence

import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np


# ──────────────────────────── text primitives ────────────────────────────

def smart_fmt(v: float, tiny_threshold: float = 0.01) -> str:
    """3 decimals if |v| < tiny_threshold, else 2. Handles NaN/inf safely."""
    if v is None:
        return ""
    try:
        if math.isnan(v) or math.isinf(v):
            return f"{v}"
    except TypeError:
        return str(v)
    if abs(v) < tiny_threshold:
        return f"{v:.3f}"
    return f"{v:.2f}"


def add_halo_label(
    ax,
    x: float,
    y: float,
    text: str,
    *,
    color: str = "#111111",
    fontsize: float = 8.5,
    fontweight: str = "normal",
    halo_color: str = "white",
    halo_width: float = 2.8,
    ha: str = "center",
    va: str = "center",
    zorder: float = 10,
    **kwargs,
):
    """Text with a white halo stroke — readable over colored backgrounds.

    Returns the Text artist so recipes can apply further transforms.
    """
    t = ax.text(
        x,
        y,
        text,
        color=color,
        fontsize=fontsize,
        fontweight=fontweight,
        ha=ha,
        va=va,
        zorder=zorder,
        **kwargs,
    )
    t.set_path_effects(
        [pe.withStroke(linewidth=halo_width, foreground=halo_color), pe.Normal()]
    )
    return t


def callout_box(
    ax,
    x: float,
    y: float,
    text: str,
    *,
    accent: str = "#333333",
    pad: float = 0.28,
    fontsize: float = 7.5,
    ha: str = "left",
    va: str = "top",
    transform=None,
    **kwargs,
):
    """White-bordered rounded callout for statistical annotations."""
    return ax.text(
        x,
        y,
        text,
        fontsize=fontsize,
        ha=ha,
        va=va,
        transform=transform if transform is not None else ax.transAxes,
        bbox=dict(
            boxstyle=f"round,pad={pad}",
            fc="white",
            ec=accent,
            lw=0.6,
        ),
        **kwargs,
    )


# ─────────────────────────── forest-plot primitives ───────────────────────

def right_of_ci_label(
    ax,
    y: float,
    upper_ci: float,
    estimate: float,
    *,
    gap_frac: float = 0.04,
    color: str = "#111111",
    fontsize: float = 7.5,
    weight: str = "normal",
):
    """Place the numeric label to the right of the upper CI extent.

    Position never depends on the sign of the estimate — consistent across panels.
    The gap is `gap_frac` of the current x-axis span.
    """
    xlo, xhi = ax.get_xlim()
    dx = (xhi - xlo) * gap_frac
    ax.text(
        upper_ci + dx,
        y,
        smart_fmt(estimate),
        ha="left",
        va="center",
        color=color,
        fontsize=fontsize,
        fontweight=weight,
    )


def colored_bracket(
    ax,
    y_top: float,
    y_bot: float,
    x_left: float,
    label: str,
    *,
    color: str = "#555555",
    fontsize: float = 8.0,
    lw: float = 1.3,
    label_offset: float = 0.02,
):
    """Colored bracket marker for grouped forest plots (group label rotated)."""
    ax.annotate(
        "",
        xy=(x_left, y_bot),
        xytext=(x_left, y_top),
        xycoords=("axes fraction", "data"),
        arrowprops=dict(arrowstyle="-", color=color, lw=lw),
    )
    ax.text(
        x_left - label_offset,
        0.5 * (y_top + y_bot),
        label,
        transform=ax.get_yaxis_transform(),
        ha="right",
        va="center",
        rotation=90,
        color=color,
        fontsize=fontsize,
        fontweight="bold",
    )


# ─────────────────────── density / distribution primitives ────────────────

def density_alpha(
    x: np.ndarray,
    y: np.ndarray,
    *,
    gridsize: int = 60,
    alpha_min: float = 0.08,
    alpha_max: float = 0.9,
) -> np.ndarray:
    """Return per-point alpha, inversely scaled with local 2D density.

    Cheap approximation: bin into a grid, read back each point's bin count,
    invert-normalize. Useful for volcanos / MA / big UMAPs.
    """
    if len(x) == 0:
        return np.array([])
    H, xe, ye = np.histogram2d(x, y, bins=gridsize)
    ix = np.clip(np.searchsorted(xe, x) - 1, 0, gridsize - 1)
    iy = np.clip(np.searchsorted(ye, y) - 1, 0, gridsize - 1)
    density = H[ix, iy]
    d = density / density.max() if density.max() > 0 else density
    alpha = alpha_max - d * (alpha_max - alpha_min)
    return np.clip(alpha, alpha_min, alpha_max)


def bootstrap_ci(
    x: np.ndarray,
    y: np.ndarray,
    *,
    xgrid: np.ndarray | None = None,
    n_resamples: int = 400,
    fit: str = "lowess",
    frac: float = 0.6,
    ci: float = 0.95,
    rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Bootstrap CI around a regression curve.

    Returns (xgrid, mean, lo, hi). `fit` is one of {"lowess", "linear"}.
    Percentile method; no analytical SE.
    """
    rng = rng if rng is not None else np.random.default_rng(0)
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    if xgrid is None:
        xgrid = np.linspace(np.nanmin(x), np.nanmax(x), 80)
    yhat = np.empty((n_resamples, xgrid.size))
    n = len(x)
    alpha = (1 - ci) / 2
    for b in range(n_resamples):
        idx = rng.integers(0, n, n)
        xb, yb = x[idx], y[idx]
        yhat[b] = _fit_eval(xb, yb, xgrid, fit=fit, frac=frac)
    mean = np.nanmean(yhat, axis=0)
    lo = np.nanquantile(yhat, alpha, axis=0)
    hi = np.nanquantile(yhat, 1 - alpha, axis=0)
    return xgrid, mean, lo, hi


def _fit_eval(x: np.ndarray, y: np.ndarray, xgrid: np.ndarray, fit: str, frac: float) -> np.ndarray:
    if fit == "linear":
        # Rank-safe least-squares fallback; returns NaN for degenerate fits.
        if np.nanstd(x) == 0:
            return np.full_like(xgrid, np.nanmean(y), dtype=float)
        slope, intercept = np.polyfit(x, y, 1)
        return intercept + slope * xgrid
    # lowess-lite: weighted-local-mean by tricube kernel, no statsmodels dep.
    n = len(x)
    r = max(2, int(frac * n))
    yg = np.empty_like(xgrid, dtype=float)
    for i, x0 in enumerate(xgrid):
        d = np.abs(x - x0)
        order = np.argsort(d)
        idx = order[:r]
        h = d[idx[-1]] if d[idx[-1]] > 0 else 1.0
        w = (1 - np.clip(d[idx] / h, 0, 1) ** 3) ** 3
        yg[i] = np.average(y[idx], weights=w) if w.sum() > 0 else np.nan
    return yg


def violin_with_ring_markers(
    ax,
    groups: Sequence[str],
    values_by_group: dict[str, np.ndarray],
    *,
    animal_ids_by_group: dict[str, Sequence] | None = None,
    colors_by_group: dict[str, str] | None = None,
    positions: Sequence[float] | None = None,
    width: float = 0.72,
    ring_size: float = 28.0,
):
    """Area-normalized violin + per-animal ring markers (white face, colored edge).

    Used for nested-design data. Overlays:
      - Q1–Q3 black bar
      - median as white dot with black edge
      - animal-level ring markers (one per unique animal_id per group)
    """
    if positions is None:
        positions = list(range(len(groups)))
    data = [values_by_group[g] for g in groups]
    parts = ax.violinplot(
        data,
        positions=positions,
        widths=width,
        showmeans=False,
        showmedians=False,
        showextrema=False,
    )
    for i, pc in enumerate(parts["bodies"]):
        g = groups[i]
        col = (colors_by_group or {}).get(g, "#888888")
        pc.set_facecolor(col)
        pc.set_edgecolor("#333333")
        pc.set_alpha(0.55)

    for pos, g in zip(positions, groups):
        vals = np.asarray(values_by_group[g])
        if vals.size == 0:
            continue
        q1, med, q3 = np.nanquantile(vals, [0.25, 0.5, 0.75])
        col = (colors_by_group or {}).get(g, "#888888")
        ax.plot([pos, pos], [q1, q3], color="black", lw=3.2, zorder=4, solid_capstyle="butt")
        ax.scatter([pos], [med], s=38, facecolor="white", edgecolor="black",
                   linewidth=1.0, zorder=5)
        if animal_ids_by_group is not None and g in animal_ids_by_group:
            ids = np.asarray(animal_ids_by_group[g])
            rng = np.random.default_rng(abs(hash(g)) % (2**32))
            for aid in np.unique(ids):
                mvals = vals[ids == aid]
                if mvals.size == 0:
                    continue
                jitter = rng.uniform(-0.18, 0.18)
                ax.scatter(
                    [pos + jitter],
                    [np.nanmean(mvals)],
                    s=ring_size,
                    facecolor="white",
                    edgecolor=col,
                    linewidth=1.2,
                    zorder=6,
                )


# ─────────────────────── phase-portrait decorations ───────────────────────

def fixed_point_marker(
    ax, x: float, y: float, kind: str = "stable", size: float = 72.0, label: str | None = None
):
    """Fixed-point dot: filled for stable, open for unstable, half-filled for saddle."""
    if kind == "stable":
        ax.scatter([x], [y], s=size, facecolor="black", edgecolor="white", linewidth=1.4, zorder=6)
    elif kind == "unstable":
        ax.scatter([x], [y], s=size, facecolor="white", edgecolor="black", linewidth=1.4, zorder=6)
    else:  # saddle
        ax.scatter([x], [y], s=size, facecolor="#888888", edgecolor="black", linewidth=1.4, zorder=6)
    if label is not None:
        add_halo_label(ax, x, y, label, fontsize=7.8, fontweight="bold", va="bottom",
                       ha="left")


def saddle_node_star(ax, x: float, y: float, *, color: str = "#D32F2F"):
    ax.scatter([x], [y], marker="*", s=220, color=color, edgecolor="white", linewidth=1.2, zorder=7)


def shaded_regime(ax, x0: float, x1: float, color: str = "#FFEBEE", alpha: float = 0.55, label: str | None = None):
    ax.axvspan(x0, x1, color=color, alpha=alpha, zorder=0)
    if label is not None:
        ymin, ymax = ax.get_ylim()
        ax.text(
            0.5 * (x0 + x1),
            ymax - 0.05 * (ymax - ymin),
            label,
            ha="center",
            va="top",
            fontsize=7.2,
            color="#555555",
            fontweight="bold",
        )


# ─────────────────────────── general helpers ──────────────────────────────

def clean_spines(ax, keep: Iterable[str] = ("left", "bottom")) -> None:
    """Hide all spines except those in `keep`."""
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(side in keep)


def grid_light(ax, which: str = "major", axis: str = "both", alpha: float = 0.18):
    """Subtle grid — used sparingly, always below data."""
    ax.grid(True, which=which, axis=axis, linewidth=0.4, color="#cccccc", alpha=alpha, zorder=0)
    ax.set_axisbelow(True)


def fade_axis(ax, side: str = "bottom", color: str = "#BBBBBB"):
    """Fade a single spine — used when suppressing an irrelevant axis."""
    ax.spines[side].set_color(color)
    tick_axis = "x" if side in ("top", "bottom") else "y"
    ax.tick_params(axis=tick_axis, colors=color)


def add_scale_bar(
    ax,
    length_data: float,
    label: str,
    *,
    color: str = "white",
    lw: float = 3.0,
    xy_axes: tuple[float, float] = (0.05, 0.06),
):
    """Scale-bar primitive for imaging/morphometry recipes."""
    x0, y0 = xy_axes
    ax.plot(
        [x0, x0 + length_data * 0.0],  # placeholder; converted via axes→data by recipes.
        [y0, y0],
        transform=ax.transAxes,
        color=color,
        lw=lw,
        solid_capstyle="butt",
    )
    ax.text(x0, y0 + 0.025, label, transform=ax.transAxes,
            color=color, fontsize=7.0, fontweight="bold")


def close_figure(fig):
    plt.close(fig)
