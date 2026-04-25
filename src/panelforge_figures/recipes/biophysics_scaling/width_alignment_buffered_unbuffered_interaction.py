"""Width x alignment interaction — does alignment alpha scale with
protrusion width differently per genotype? Per-cell scatter coloured
by group, per-group fitted curves with 95 % CI ribbons, and shaded
'buffered' / 'unbuffered' regions.

The descriptor 'buffered / unbuffered' is operational, not molecular:
the buffered region is the width range over which alpha is
genotype-invariant; the unbuffered region is where group fits diverge.

Timecourse-hierarchical-CI family: >=1 filled CI band + >=1 mean
line. Satisfied by per-group LOESS curves + bootstrap CI ribbons.
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


class WidthAlignmentInput(RecipeContract):
    width_um_by_cell: dict[str, float] = Field(...)
    alpha_by_cell: dict[str, float] = Field(...)
    group_by_cell: dict[str, str] = Field(...)
    fit: str = Field("loess", description="'loess' | 'linear'")
    buffered_min_w_um: float = 1.5
    buffered_max_w_um: float = 4.0
    unbuffered_min_w_um: float = 0.4
    unbuffered_max_w_um: float = 1.0
    title: str = "Width × alignment — buffered vs unbuffered"


def _demo() -> WidthAlignmentInput:
    rng = np.random.default_rng(2231)
    n = 60
    cells = [f"C{i:03d}" for i in range(n)]
    groups = ["WT"] * (n // 2) + ["LI"] * (n - n // 2)
    width = np.concatenate([
        rng.lognormal(mean=np.log(1.8), sigma=0.5, size=n // 2),
        rng.lognormal(mean=np.log(1.4), sigma=0.55, size=n - n // 2),
    ])
    # alpha increases with width; LI rises more steeply at small w.
    alpha = []
    for w, g in zip(width, groups):
        base = 0.30 + 0.20 * np.tanh((w - 1.0) / 1.0)
        if g == "LI":
            base += 0.18 * np.exp(-((w - 0.7) / 0.45) ** 2)
        alpha.append(float(np.clip(base + rng.normal(0, 0.05), 0, 1)))
    return WidthAlignmentInput(
        width_um_by_cell={c: float(v) for c, v in zip(cells, width)},
        alpha_by_cell={c: a for c, a in zip(cells, alpha)},
        group_by_cell={c: g for c, g in zip(cells, groups)},
    )


_META = RecipeMetadata(
    name="width_alignment_buffered_unbuffered_interaction",
    modality="biophysics_scaling",
    family=RecipeFamily.timecourse_hierarchical_ci,
    answers_question=(
        "Does the protrusion alignment alpha scale with width "
        "differently per genotype, and where is the relationship "
        "buffered vs unbuffered?"
    ),
    required_fields=("width_um_by_cell", "alpha_by_cell", "group_by_cell"),
    optional_fields=(
        "fit", "buffered_min_w_um", "buffered_max_w_um",
        "unbuffered_min_w_um", "unbuffered_max_w_um", "title",
    ),
    file_format_hints=("csv",),
    alternatives_in_modality=("shared_manifold_scatter_with_residuals",),
)


def _loess(x: np.ndarray, y: np.ndarray, xg: np.ndarray, frac: float = 0.55) -> np.ndarray:
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
    contract=WidthAlignmentInput,
    demo_contract=_demo,
)
def render(contract: WidthAlignmentInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 4.0))
    AESTHETIC.apply_to_ax(ax)

    cells = list(contract.width_um_by_cell.keys())
    width = np.array([contract.width_um_by_cell[c] for c in cells], float)
    alpha = np.array([contract.alpha_by_cell[c] for c in cells], float)
    groups = np.array([contract.group_by_cell[c] for c in cells])
    unique_groups = list(dict.fromkeys(groups.tolist()))

    # Buffered / unbuffered region shading.
    ax.axvspan(contract.buffered_min_w_um, contract.buffered_max_w_um,
               color="#2E7D32", alpha=0.06, linewidth=0, zorder=1)
    ax.axvspan(contract.unbuffered_min_w_um, contract.unbuffered_max_w_um,
               color="#C62828", alpha=0.06, linewidth=0, zorder=1)
    ax.text(
        (contract.buffered_min_w_um + contract.buffered_max_w_um) / 2,
        0.97, "buffered", transform=ax.get_xaxis_transform(),
        ha="center", va="top", fontsize=6.6, color="#2E7D32",
        fontweight="bold", zorder=6,
    )
    ax.text(
        (contract.unbuffered_min_w_um + contract.unbuffered_max_w_um) / 2,
        0.97, "unbuffered", transform=ax.get_xaxis_transform(),
        ha="center", va="top", fontsize=6.6, color="#C62828",
        fontweight="bold", zorder=6,
    )

    # Per-group scatter + LOESS fit + bootstrap CI ribbon.
    xg = np.linspace(max(width.min(), 0.3), width.max(), 60)
    rng = np.random.default_rng(13)
    interaction_term: float | None = None
    fits_at_xg: dict[str, np.ndarray] = {}
    for g in unique_groups:
        mask = groups == g
        x = width[mask]
        y = alpha[mask]
        order = np.argsort(x)
        x_sorted = x[order]
        y_sorted = y[order]
        colour = _GROUP_COLOURS.get(g, "#333333")
        ax.scatter(x, y, s=28, color=colour, edgecolor="white",
                   linewidth=0.5, alpha=0.85, zorder=4, label=g)
        # LOESS fit + 200 bootstrap resamples for CI ribbon.
        yg = _loess(x_sorted, y_sorted, xg)
        fits_at_xg[g] = yg
        boot_curves = []
        for _ in range(200):
            idx = rng.integers(0, x.size, size=x.size)
            xb = x[idx]
            yb = y[idx]
            o = np.argsort(xb)
            boot_curves.append(_loess(xb[o], yb[o], xg))
        boot = np.asarray(boot_curves)
        lo = np.quantile(boot, 0.025, axis=0)
        hi = np.quantile(boot, 0.975, axis=0)
        ax.plot(xg, yg, color=colour, lw=1.2, zorder=5)
        ax.fill_between(xg, lo, hi, color=colour, alpha=0.18,
                        linewidth=0, zorder=2)

    # Approximate group x width interaction term: ratio of (Δfit at
    # unbuffered midpoint) / (Δfit at buffered midpoint).
    if len(fits_at_xg) == 2:
        g0, g1 = list(fits_at_xg.keys())
        unbuf_mid = (contract.unbuffered_min_w_um
                     + contract.unbuffered_max_w_um) / 2
        buf_mid = (contract.buffered_min_w_um
                   + contract.buffered_max_w_um) / 2
        d_unbuf = float(
            np.interp(unbuf_mid, xg, fits_at_xg[g1])
            - np.interp(unbuf_mid, xg, fits_at_xg[g0])
        )
        d_buf = float(
            np.interp(buf_mid, xg, fits_at_xg[g1])
            - np.interp(buf_mid, xg, fits_at_xg[g0])
        )
        interaction_term = d_unbuf - d_buf

    ax.set_xlabel("protrusion width w (um)")
    ax.set_ylabel("alignment alpha")
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(fontsize=6.8, frameon=False, loc="lower right",
              handlelength=1.2)

    title_bits = [contract.title]
    if interaction_term is not None:
        title_bits.append(
            f"group × width interaction = {smart_fmt(interaction_term)}"
        )
    ax.set_title("  ·  ".join(title_bits), fontsize=8.2, pad=4)
    return ax
