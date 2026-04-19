"""Model-comparison ladder — competing models ranked by AIC, paired with BIC.

Rows are candidate model specifications, ordered by AIC. Each row shows
the ΔAIC (horizontal bar) from the best-fit model, with a paired BIC dot
and the usual Δ = 2 / 4 / 7 significance strip. The best-fit row is
highlighted with a subtle band.
"""

from __future__ import annotations

import matplotlib.patches as mpatches
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


class ModelRow(RecipeContract):
    name: str
    aic: float
    bic: float
    n_params: int = 0


class ModelComparisonInput(RecipeContract):
    models: list[ModelRow] = Field(..., min_length=3)
    title: str = "Model comparison (ΔAIC)"


def _demo() -> ModelComparisonInput:
    return ModelComparisonInput(
        models=[
            ModelRow(name="Y ~ X + (1|animal)",                      aic=842.1, bic=868.4, n_params=7),
            ModelRow(name="Y ~ X + (1|animal/session)",              aic=836.5, bic=870.2, n_params=9),
            ModelRow(name="Y ~ X + (X|animal)",                      aic=833.8, bic=871.6, n_params=10),
            ModelRow(name="Y ~ X + (X|animal/session)",              aic=829.2, bic=877.1, n_params=13),
            ModelRow(name="Y ~ X * sex + (X|animal)",                aic=847.6, bic=891.7, n_params=12),
            ModelRow(name="Y ~ X + (1|animal) + (1|batch)",          aic=840.0, bic=871.1, n_params=8),
            ModelRow(name="Y ~ X + sex + (1|animal)",                aic=839.2, bic=870.3, n_params=8),
        ],
    )


_META = RecipeMetadata(
    name="model_comparison_aic_bic_ladder",
    modality="mixed_effects_models",
    family=RecipeFamily.ladder,
    answers_question=(
        "Among competing mixed-model specifications, which has the lowest "
        "AIC / BIC, and by how much?"
    ),
    required_fields=("models",),
    optional_fields=("title",),
    file_format_hints=("csv", "rds", "yaml"),
    alternatives_in_modality=(
        "icc_variance_decomposition",
        "mixed_model_residual_diagnostic",
    ),
)


@register_recipe(
    metadata=_META,
    contract=ModelComparisonInput,
    demo_contract=_demo,
)
def render(contract: ModelComparisonInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.0, 3.4))
    AESTHETIC.apply_to_ax(ax)

    rows = sorted(contract.models, key=lambda r: r.aic)
    aic = np.array([r.aic for r in rows], dtype=float)
    bic = np.array([r.bic for r in rows], dtype=float)
    best = aic.min()
    d_aic = aic - best
    best_bic = bic.min()
    d_bic = bic - best_bic

    y = np.arange(len(rows))[::-1]
    xmax = float(max(d_aic.max(), d_bic.max())) * 1.22 + 2.0

    # Evidence strip colours (Burnham & Anderson-style):
    # Δ < 2 substantial, 2-4 some, 4-7 considerably less, >7 none.
    def tier_color(delta: float) -> str:
        if delta < 2.0:
            return "#2E7D32"
        if delta < 4.0:
            return "#558B2F"
        if delta < 7.0:
            return "#F9A825"
        return "#C62828"

    # Background tier bands.
    for lo, hi, fc in [(0, 2, "#E8F5E9"), (2, 4, "#F1F8E9"),
                       (4, 7, "#FFF8E1"), (7, xmax, "#FFEBEE")]:
        ax.add_patch(mpatches.Rectangle(
            (lo, -0.5), hi - lo, len(rows),
            facecolor=fc, alpha=0.55, edgecolor="none", zorder=0,
        ))

    for yi, r, da, db in zip(y, rows, d_aic, d_bic):
        color = tier_color(float(da))
        ax.barh(yi, da, height=0.52, color=color, alpha=0.85,
                edgecolor="white", linewidth=0.8, zorder=2)
        # BIC paired dot (offset slightly on y).
        ax.scatter([db], [yi], s=26, marker="D", color="#111111",
                   edgecolor="white", linewidth=0.6, zorder=4,
                   label="ΔBIC" if yi == y[0] else None)
        # Right-of-bar label.
        ax.text(max(da, db) + xmax * 0.015, yi,
                f"ΔAIC={smart_fmt(da)}  ΔBIC={smart_fmt(db)}",
                va="center", ha="left", fontsize=6.6, color="#222222")

    # Highlight best-fit row.
    ax.axhspan(y[0] - 0.42, y[0] + 0.42, facecolor="#2E7D32",
               alpha=0.08, zorder=1)

    # Tier strip reference lines.
    for x_tier, label in [(2, "Δ=2"), (4, "Δ=4"), (7, "Δ=7")]:
        ax.axvline(x_tier, color="#666666", lw=0.5, ls=":", zorder=1)
        ax.text(x_tier, len(rows) - 0.45, label,
                ha="center", va="bottom", fontsize=6.2, color="#666666")

    ax.set_yticks(y)
    ax.set_yticklabels([r.name for r in rows], fontsize=7.0)
    ax.set_xlabel("ΔAIC from best fit")
    ax.set_xlim(0, xmax)
    ax.set_ylim(-0.8, len(rows) - 0.4)
    ax.set_title(
        f"{contract.title}  ·  best: {rows[0].name.split('~')[0].strip() or 'M1'} "
        f"(AIC={smart_fmt(best)})",
        fontsize=9.0, pad=4,
    )
    ax.legend(fontsize=6.6, frameon=False, loc="lower right",
              handlelength=1.2)
    ax.grid(axis="x", color="#DDDDDD", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
