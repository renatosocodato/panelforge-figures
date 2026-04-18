"""ICC variance decomposition — stacked bar of variance components per model term."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class ICCInput(RecipeContract):
    levels: list[str] = Field(..., description="e.g. ['subject', 'session', 'residual']")
    variance: list[float] = Field(..., description="variance component per level")
    model_name: str = "mixed model"
    title: str = "Variance components"


def _demo() -> ICCInput:
    levels = ["animal", "session", "slice", "residual"]
    variance = [0.42, 0.11, 0.06, 0.41]
    return ICCInput(levels=levels, variance=variance, model_name="LMM (Y ~ X + (1|animal/session))")


_META = RecipeMetadata(
    name="icc_variance_decomposition",
    modality="mixed_effects_models",
    family=RecipeFamily.matrix,
    answers_question="What fraction of the outcome variance lives at each hierarchical level?",
    required_fields=("levels", "variance"),
    optional_fields=("model_name", "title"),
    file_format_hints=("csv", "rds"),
    alternatives_in_modality=("random_effects_caterpillar",),
)


@register_recipe(metadata=_META, contract=ICCInput, demo_contract=_demo)
def render(contract: ICCInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.4, 3.0))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    levels = contract.levels
    var = np.array(contract.variance, dtype=float)
    total = max(var.sum(), 1e-9)
    frac = var / total
    icc = 1 - frac[-1]          # 1 - residual share

    # Horizontal stacked bar.
    left = 0.0
    bar_y = 0.5
    bar_h = 0.36
    for i, (lvl, v, f) in enumerate(zip(levels, var, frac)):
        color = "#888888" if lvl == "residual" else palette[i]
        ax.barh(bar_y, f, height=bar_h, left=left,
                color=color, edgecolor="white", linewidth=0.8, zorder=2,
                alpha=0.92)
        # Centered label if segment is wide enough.
        if f > 0.08:
            ax.text(left + f / 2, bar_y, f"{lvl}\n{smart_fmt(f*100)}%",
                    ha="center", va="center",
                    color="white", fontsize=6.6, zorder=3)
        left += f

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_yticks([])
    ax.set_xticks(np.linspace(0, 1, 6))
    ax.set_xticklabels([f"{int(p)}%" for p in np.linspace(0, 100, 6)],
                       fontsize=7.0)
    ax.set_xlabel("share of total variance")
    ax.set_title(f"{contract.title} · ICC = {smart_fmt(icc)}",
                 fontsize=9.0, pad=4)
    for s in ("left",):
        ax.spines[s].set_visible(False)

    # Model label below the bar.
    ax.text(0.5, 0.18, contract.model_name,
            ha="center", va="top", fontsize=6.6, color="#555555",
            transform=ax.transAxes, style="italic")
    return ax
