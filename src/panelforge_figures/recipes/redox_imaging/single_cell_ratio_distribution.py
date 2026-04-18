"""Single-cell redox-ratio distribution — histogram + KDE with bimodality highlight."""

from __future__ import annotations

import numpy as np
from pydantic import Field
from scipy.stats import gaussian_kde

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class RatioDistributionInput(RecipeContract):
    ratios: list[float] = Field(..., description="per-cell redox ratio")
    condition: str = "baseline"
    title: str = "Single-cell redox ratio"


def _demo() -> RatioDistributionInput:
    rng = np.random.default_rng(137)
    # Bimodal mixture around 0.6 (reduced) and 1.4 (oxidized).
    a = rng.normal(0.6, 0.12, 700)
    b = rng.normal(1.4, 0.15, 500)
    return RatioDistributionInput(
        ratios=np.concatenate([a, b]).tolist(),
        condition="LPS 100 ng/mL",
    )


def _bimodality_coefficient(x: np.ndarray) -> float:
    """Pearson's bimodality coefficient; > 5/9 ≈ 0.555 suggests bimodality."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if x.size < 4:
        return 0.0
    s = (x - x.mean()) / max(x.std(), 1e-9)
    skew = float(np.mean(s ** 3))
    kurt = float(np.mean(s ** 4) - 3)
    return (skew ** 2 + 1) / (kurt + 3 * (x.size - 1) ** 2 / ((x.size - 2) * (x.size - 3)))


_META = RecipeMetadata(
    name="single_cell_ratio_distribution",
    modality="redox_imaging",
    family=RecipeFamily.ridge_by_group,
    answers_question="What is the distribution of redox ratios across single cells, and is it bimodal?",
    required_fields=("ratios",),
    optional_fields=("condition", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("bimodality_coefficient_grid",),
)


@register_recipe(metadata=_META, contract=RatioDistributionInput, demo_contract=_demo)
def render(contract: RatioDistributionInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    x = np.array(contract.ratios, dtype=float)
    x = x[np.isfinite(x)]

    # Histogram.
    hist, edges = np.histogram(x, bins=40, density=True)
    centers = 0.5 * (edges[:-1] + edges[1:])
    ax.bar(centers, hist, width=(edges[1] - edges[0]),
           color=palette.pick("intermediate"), alpha=0.35,
           edgecolor="none", zorder=2)

    # KDE overlay — fill both sides of ratio=1 with different colors.
    xg = np.linspace(x.min(), x.max(), 300)
    kde = gaussian_kde(x)
    dens = kde(xg)
    mask_red = xg <= 1.0
    ax.fill_between(xg[mask_red], dens[mask_red], 0,
                    color=palette.pick("reduced"), alpha=0.35,
                    linewidth=0, zorder=3)
    ax.fill_between(xg[~mask_red], dens[~mask_red], 0,
                    color=palette.pick("oxidized"), alpha=0.35,
                    linewidth=0, zorder=3)
    ax.plot(xg, dens, color="#222222", lw=1.0, zorder=4, label="KDE")

    # Ratio-neutral reference.
    ax.axvline(1.0, color="#888888", lw=0.6, ls="--", zorder=1,
               label="ratio = 1")

    # Bimodality callout.
    bc = _bimodality_coefficient(x)
    is_bim = bc > 5 / 9
    ax.text(0.01, 0.99,
            f"N cells = {x.size}   condition: {contract.condition}\n"
            f"bimodality coef = {smart_fmt(bc)} "
            f"({'bimodal' if is_bim else 'unimodal'})",
            transform=ax.transAxes, ha="left", va="top",
            fontsize=6.6, color="#333333",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=5)

    ax.set_xlabel("redox ratio")
    ax.set_ylabel("density")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="upper right",
              handlelength=1.6)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
