"""MA plot — log2FC vs log mean expression with lowess overlay."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    bootstrap_ci,
    density_alpha,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class MAPlotInput(RecipeContract):
    mean_expr: list[float] = Field(..., description="mean normalized expression (log scale)")
    log2fc: list[float] = Field(...)
    padj: list[float] = Field(default_factory=list)
    log2fc_threshold: float = 1.0
    padj_threshold: float = 0.05
    title: str = "MA plot"


def _demo() -> MAPlotInput:
    rng = np.random.default_rng(257)
    n = 2000
    m = rng.uniform(-1, 6, n)          # log mean expression
    # Central bulk fc ≈ 0; hits at higher expression.
    fc = rng.normal(0, 0.4, n)
    p = rng.uniform(0.1, 1.0, n)
    hit_idx = rng.choice(n, size=60, replace=False)
    fc[hit_idx] = rng.choice([-1, 1], 60) * rng.uniform(1.2, 3.2, 60)
    p[hit_idx] = rng.uniform(1e-6, 1e-3, 60)
    return MAPlotInput(
        mean_expr=m.tolist(),
        log2fc=fc.tolist(),
        padj=p.tolist(),
    )


_META = RecipeMetadata(
    name="ma_plot_with_lowess",
    modality="omics_differential",
    family=RecipeFamily.volcano,
    answers_question="Does effect-size depend on mean expression (bias), and where do the significant hits fall across expression range?",
    required_fields=("mean_expr", "log2fc"),
    optional_fields=("padj", "log2fc_threshold", "padj_threshold", "title"),
    file_format_hints=("csv", "parquet", "tsv"),
    alternatives_in_modality=("volcano_labeled_repelled",),
)


@register_recipe(metadata=_META, contract=MAPlotInput, demo_contract=_demo)
def render(contract: MAPlotInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    m = np.array(contract.mean_expr, dtype=float)
    fc = np.array(contract.log2fc, dtype=float)
    p = (np.array(contract.padj, dtype=float)
         if contract.padj else np.ones_like(fc))

    sig = (p < contract.padj_threshold) & (np.abs(fc) > contract.log2fc_threshold)
    ns = ~sig
    up = sig & (fc > 0)
    dn = sig & (fc < 0)

    alpha_ns = density_alpha(m[ns], fc[ns]) if ns.any() else np.array([])
    ax.scatter(m[ns], fc[ns], s=8, c="#BBBBBB", alpha=alpha_ns,
               edgecolor="none", zorder=2, label=f"n.s. ({ns.sum()})")
    ax.scatter(m[up], fc[up], s=16, c=palette[1], alpha=0.85,
               edgecolor="white", linewidth=0.3, zorder=3,
               label=f"up ({up.sum()})")
    ax.scatter(m[dn], fc[dn], s=16, c=palette[0], alpha=0.85,
               edgecolor="white", linewidth=0.3, zorder=3,
               label=f"down ({dn.sum()})")

    # lowess-lite via bootstrap_ci (uses tricube-weighted local mean).
    xg, mean, lo, hi = bootstrap_ci(m, fc, n_resamples=100, fit="lowess", frac=0.35)
    ax.fill_between(xg, lo, hi, color="#333333", alpha=0.15,
                    linewidth=0, zorder=4)
    ax.plot(xg, mean, color="#111111", lw=1.2, zorder=5, label="lowess")

    # Zero reference.
    ax.axhline(0, color="#888888", lw=0.5, ls=":", zorder=1)
    # FC threshold lines.
    ax.axhline(contract.log2fc_threshold, color="#888888", lw=0.5, ls="--", zorder=1)
    ax.axhline(-contract.log2fc_threshold, color="#888888", lw=0.5, ls="--", zorder=1)

    ax.set_xlabel(r"$\log_{10}$ mean expression")
    ax.set_ylabel(r"$\log_2$ fold-change")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.6, frameon=False, loc="upper right",
              handlelength=1.4)

    # Summary.
    med_lowess = float(np.nanmedian(mean))
    ax.text(0.01, 0.03,
            f"median lowess = {smart_fmt(med_lowess)}   "
            f"(ideal = 0 for unbiased)",
            transform=ax.transAxes, ha="left", va="bottom",
            fontsize=6.4, color="#333333",
            bbox=dict(boxstyle="round,pad=0.18", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=6)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
