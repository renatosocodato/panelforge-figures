"""Shared-manifold scatter with per-group marginal residual histograms.

Tests whether two groups share the same (x, y) relationship: fit a
LOESS curve to the pooled data, and show per-group residual
distributions on the top and right margins. If residuals overlap and
an ANCOVA group term is non-significant given x, the manifold is
shared across groups.

Scatter-collapse family: >=1 scatter + >=1 fit line. Satisfied by
the central group-coloured scatter + the shared LOESS fit.
"""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC

_GROUP_COLOURS = {"WT": "#1565C0", "LI": "#C62828",
                  "control": "#1565C0", "treated": "#C62828"}


class SharedManifoldInput(RecipeContract):
    x_by_cell: dict[str, float] = Field(..., min_length=10)
    y_by_cell: dict[str, float] = Field(..., min_length=10)
    group_by_cell: dict[str, str] = Field(..., min_length=10)
    x_label: str
    y_label: str
    fit: str = Field(
        "loess",
        description="'loess' | 'gam' | 'linear'",
    )
    show_residual_histograms: bool = True
    title: str = "Shared-manifold scatter"


def _demo() -> SharedManifoldInput:
    rng = np.random.default_rng(4711)
    n = 60
    # Cell area (x) vs standoff distance (y). Two groups with different
    # x distributions but shared y|x manifold.
    cells = [f"C{i:03d}" for i in range(n)]
    groups = ["WT"] * (n // 2) + ["LI"] * (n - n // 2)
    x_wt = rng.lognormal(mean=np.log(180), sigma=0.25, size=n // 2)
    x_li = rng.lognormal(mean=np.log(240), sigma=0.28, size=n - n // 2)
    x_all = np.concatenate([x_wt, x_li])
    # y = 0.02 * x + 2 + noise — shared manifold.
    y_all = 0.018 * x_all + 2.0 + rng.normal(0, 0.6, n)
    return SharedManifoldInput(
        x_by_cell={c: float(v) for c, v in zip(cells, x_all)},
        y_by_cell={c: float(v) for c, v in zip(cells, y_all)},
        group_by_cell={c: g for c, g in zip(cells, groups)},
        x_label="cell area (um^2)",
        y_label="standoff (um)",
    )


_META = RecipeMetadata(
    name="shared_manifold_scatter_with_residuals",
    modality="biophysics_scaling",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "Do two groups share the same (x, y) manifold after accounting "
        "for x, or does a residual group effect remain?"
    ),
    required_fields=(
        "x_by_cell", "y_by_cell", "group_by_cell", "x_label", "y_label",
    ),
    optional_fields=("fit", "show_residual_histograms", "title"),
    file_format_hints=("csv",),
    alternatives_in_modality=("geometric_mediation_path_diagram",),
)


def _loess(x: np.ndarray, y: np.ndarray, xg: np.ndarray, frac: float = 0.55) -> np.ndarray:
    """Lightweight tricube LOESS; returns smoothed y at grid points."""
    n = len(x)
    k = max(3, int(np.ceil(frac * n)))
    out = np.zeros_like(xg)
    for i, x0 in enumerate(xg):
        d = np.abs(x - x0)
        idx = np.argsort(d)[:k]
        dw = d[idx] / max(d[idx].max(), 1e-9)
        w = (1 - dw ** 3) ** 3
        xi = x[idx]
        yi = y[idx]
        wx = np.sum(w * xi)
        wy = np.sum(w * yi)
        wxx = np.sum(w * xi * xi)
        wxy = np.sum(w * xi * yi)
        sw = np.sum(w)
        denom = sw * wxx - wx * wx
        if abs(denom) < 1e-12:
            out[i] = wy / max(sw, 1e-9)
        else:
            b = (sw * wxy - wx * wy) / denom
            a = (wy - b * wx) / sw
            out[i] = a + b * x0
    return out


@register_recipe(
    metadata=_META,
    contract=SharedManifoldInput,
    demo_contract=_demo,
)
def render(contract: SharedManifoldInput, ax=None, **_):
    from mpl_toolkits.axes_grid1 import make_axes_locatable
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 4.8))
    AESTHETIC.apply_to_ax(ax)

    # Arrange data.
    cells = list(contract.x_by_cell.keys())
    x = np.array([contract.x_by_cell[c] for c in cells], float)
    y = np.array([contract.y_by_cell[c] for c in cells], float)
    groups = np.array([contract.group_by_cell[c] for c in cells])
    unique_groups = list(dict.fromkeys(groups.tolist()))

    # Fit shared LOESS curve on pooled data.
    order = np.argsort(x)
    x_sorted = x[order]
    y_sorted = y[order]
    xg = np.linspace(x.min(), x.max(), 80)
    yg = _loess(x_sorted, y_sorted, xg)
    # Residuals per cell (relative to the pooled fit).
    y_pred = np.interp(x, xg, yg)
    resid = y - y_pred

    # Central scatter.
    for g in unique_groups:
        mask = groups == g
        ax.scatter(x[mask], y[mask], s=34,
                   color=_GROUP_COLOURS.get(g, "#555555"),
                   edgecolor="white", linewidth=0.5,
                   alpha=0.85, zorder=5, label=g)
    # Shared LOESS fit line.
    ax.plot(xg, yg, color="#333333", lw=1.2, zorder=4,
            label=f"shared {contract.fit}")

    ax.set_xlabel(contract.x_label)
    ax.set_ylabel(contract.y_label)
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(fontsize=6.6, frameon=False, loc="lower right",
              handlelength=1.2)

    # Marginal residual histograms.
    if contract.show_residual_histograms:
        divider = make_axes_locatable(ax)
        top = divider.append_axes("top", size=0.8, pad=0.12,
                                  sharex=ax)
        right = divider.append_axes("right", size=0.8, pad=0.12,
                                    sharey=ax)
        # Top strip: per-group histogram of x (shows coverage).
        bins_x = np.linspace(x.min(), x.max(), 18)
        for g in unique_groups:
            mask = groups == g
            top.hist(x[mask], bins=bins_x, alpha=0.55,
                     color=_GROUP_COLOURS.get(g, "#555555"),
                     edgecolor="white", linewidth=0.4)
        top.set_ylabel("count", fontsize=6.4)
        top.tick_params(axis="x", labelbottom=False)
        top.tick_params(axis="y", labelsize=6.0)
        for side in ("top", "right"):
            top.spines[side].set_visible(False)

        # Right strip: per-group residual distribution (y_actual -
        # y_predicted by shared fit).
        bins_r = np.linspace(resid.min() - 0.1, resid.max() + 0.1, 18)
        for g in unique_groups:
            mask = groups == g
            # Orient horizontally (binned residuals on y).
            right.hist(resid[mask], bins=bins_r, alpha=0.55,
                       color=_GROUP_COLOURS.get(g, "#555555"),
                       edgecolor="white", linewidth=0.4,
                       orientation="horizontal")
        right.axhline(0, color="#888888", lw=0.5, ls="--", zorder=1)
        right.set_xlabel("residual count", fontsize=6.4)
        right.tick_params(axis="y", labelleft=False)
        right.tick_params(axis="x", labelsize=6.0)
        for side in ("top", "right"):
            right.spines[side].set_visible(False)
    else:
        top = None

    # Simple ANCOVA-style group-term F test given x.
    # Compare pooled-fit residual variance vs per-group-centered variance.
    ss_pool = float(np.sum(resid ** 2))
    ss_group = 0.0
    for g in unique_groups:
        mask = groups == g
        r_g = resid[mask]
        ss_group += float(np.sum((r_g - r_g.mean()) ** 2))
    n = len(x)
    k = len(unique_groups)
    f_stat = ((ss_pool - ss_group) / max(k - 1, 1)) / max(
        ss_group / max(n - k, 1), 1e-9)
    # Approximate one-sided p via F distribution.
    try:
        from scipy.stats import f as f_dist
        p_val = float(1 - f_dist.cdf(f_stat, k - 1, n - k))
    except Exception:
        p_val = float("nan")

    # ANCOVA pill (upper-left, doesn't collide with the scatter body or
    # marginal histograms).
    callout_ax = top if top is not None else ax
    callout_ax.text(
        0.02, 0.96,
        f"ANCOVA group | x : F = {smart_fmt(float(f_stat))}  "
        f"p = {smart_fmt(p_val)}",
        transform=callout_ax.transAxes,
        ha="left", va="top", fontsize=6.4, color="#333333",
        bbox=dict(boxstyle="round,pad=0.22", fc="white",
                  ec="#BBBBBB", lw=0.4, alpha=0.90),
        zorder=8,
    )
    # Title goes on the top marginal strip when present (the main
    # axis's title gets hidden underneath the top-strip axes).
    if top is not None:
        top.set_title(contract.title, fontsize=8.4, pad=4)
    else:
        ax.set_title(contract.title, fontsize=8.4, pad=4)
    return ax
