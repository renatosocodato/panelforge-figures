"""Random-effects caterpillar — per-cluster BLUPs sorted with 95% CIs."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
)
from ._aesthetic import AESTHETIC


class CaterpillarInput(RecipeContract):
    cluster_ids: list[str] = Field(..., min_length=3)
    blups: list[float] = Field(..., description="best linear unbiased predictors")
    se: list[float] = Field(..., description="standard errors")
    grouping: str = "animal"
    title: str = "Random-effect BLUPs"


def _demo() -> CaterpillarInput:
    rng = np.random.default_rng(47)
    n = 36
    ids = [f"A{i+1:02d}" for i in range(n)]
    blups = rng.normal(0, 0.35, n)
    se = rng.uniform(0.08, 0.22, n)
    return CaterpillarInput(
        cluster_ids=ids,
        blups=blups.tolist(),
        se=se.tolist(),
        grouping="animal",
    )


_META = RecipeMetadata(
    name="random_effects_caterpillar",
    modality="mixed_effects_models",
    family=RecipeFamily.coef_forest,
    answers_question="How much does each cluster (animal, batch) deviate from the population mean, and how confident are we?",
    required_fields=("cluster_ids", "blups", "se"),
    optional_fields=("grouping", "title"),
    file_format_hints=("csv", "rds"),
    alternatives_in_modality=("random_slopes_per_cluster",),
)


@register_recipe(metadata=_META, contract=CaterpillarInput, demo_contract=_demo)
def render(contract: CaterpillarInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 3.2))
    AESTHETIC.apply_to_ax(ax)

    palette = get_palette(AESTHETIC.primary_palette)
    blups = np.array(contract.blups, dtype=float)
    se = np.array(contract.se, dtype=float)
    order = np.argsort(blups)
    blups = blups[order]
    se = se[order]
    ids = [contract.cluster_ids[i] for i in order]

    xs = np.arange(len(blups))

    # Population zero reference.
    ax.axhline(0, color="#888888", lw=0.7, ls="--", zorder=1)

    # Color by sign: above zero vs below.
    pos_color = palette.pick("F_WT") if "F_WT" in palette.semantic else palette[0]
    neg_color = palette.pick("M_WT") if "M_WT" in palette.semantic else palette[1]

    # Vertical CI bars.
    for x, b, s in zip(xs, blups, se):
        color = pos_color if b >= 0 else neg_color
        lo = b - 1.96 * s
        hi = b + 1.96 * s
        ax.plot([x, x], [lo, hi], color=color, lw=0.8, alpha=0.8, zorder=2)
    # Estimate markers.
    colors = [pos_color if b >= 0 else neg_color for b in blups]
    ax.scatter(xs, blups, c=colors, s=14, edgecolor="white",
               linewidth=0.6, zorder=3)

    # Axis decoration.
    n_ticks = min(len(ids), 8)
    tick_idx = np.linspace(0, len(ids) - 1, n_ticks, dtype=int)
    ax.set_xticks(tick_idx)
    ax.set_xticklabels([ids[i] for i in tick_idx], rotation=35,
                       ha="right", fontsize=6.6)
    ax.set_xlabel(f"{contract.grouping} (sorted)")
    ax.set_ylabel("BLUP")
    ax.set_title(contract.title, fontsize=9.0, pad=4)

    # Above-average vs below-average counts.
    n_pos = int((blups >= 0).sum())
    n_neg = int((blups < 0).sum())
    ax.text(0.01, 0.99,
            f"above 0: {n_pos}   below 0: {n_neg}",
            transform=ax.transAxes, ha="left", va="top",
            fontsize=6.8, color="#333333",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=5)
    ax.grid(axis="y", color="#DDDDDD", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
