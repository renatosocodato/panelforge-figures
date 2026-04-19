"""Fixed vs random vs residual variance partition (Nakagawa-Schielzeth).

Decomposes total outcome variance into three strata — fixed-effect
share (marginal R²), random-effect share (conditional R² − marginal R²),
and residual — as a single stacked bar per model. Inside the fixed
stripe, per-term subcontributions are shown as a secondary hatch strip.

Distinct from `icc_variance_decomposition`: that recipe partitions the
random-effect side only (level-2 / level-3 / residual), while this
partitions the fixed-vs-random split at the top level.
"""

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


class ModelPartition(RecipeContract):
    name: str
    r2_marginal: float
    r2_conditional: float
    fixed_terms: dict[str, float] = Field(default_factory=dict)


class VariancePartitionInput(RecipeContract):
    models: list[ModelPartition] = Field(..., min_length=1)
    title: str = "Fixed vs random vs residual variance"


def _demo() -> VariancePartitionInput:
    return VariancePartitionInput(
        models=[
            ModelPartition(
                name="Y ~ X + (1|animal)",
                r2_marginal=0.28,
                r2_conditional=0.62,
                fixed_terms={"X": 0.18, "sex": 0.04, "age_z": 0.06},
            ),
            ModelPartition(
                name="Y ~ X + (X|animal)",
                r2_marginal=0.31,
                r2_conditional=0.71,
                fixed_terms={"X": 0.20, "sex": 0.05, "age_z": 0.06},
            ),
            ModelPartition(
                name="Y ~ X + sex*genotype + (X|animal)",
                r2_marginal=0.42,
                r2_conditional=0.78,
                fixed_terms={"X": 0.18, "sex": 0.04, "genotype": 0.10,
                             "sex:genotype": 0.08, "age_z": 0.02},
            ),
        ],
    )


_META = RecipeMetadata(
    name="fixed_vs_random_effect_partition",
    modality="mixed_effects_models",
    family=RecipeFamily.matrix,
    answers_question=(
        "How is the total outcome variance split into fixed-effect vs "
        "random-effect vs residual variance?"
    ),
    required_fields=("models",),
    optional_fields=("title",),
    file_format_hints=("csv", "yaml", "rds"),
    alternatives_in_modality=(
        "icc_variance_decomposition",
        "model_comparison_aic_bic_ladder",
    ),
)


@register_recipe(
    metadata=_META,
    contract=VariancePartitionInput,
    demo_contract=_demo,
)
def render(contract: VariancePartitionInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    models = contract.models
    y = np.arange(len(models))[::-1]
    bar_h = 0.55

    fixed_color = palette.pick("F_WT") if "F_WT" in palette.semantic else palette[0]
    random_color = palette.pick("M_WT") if "M_WT" in palette.semantic else palette[1]
    residual_color = "#888888"

    # Distinct hatches for the per-term stripe inside the fixed segment.
    hatches = ["", "////", "....", "xxxx", "||||", "\\\\\\\\"]

    for yi, m in zip(y, models):
        r2_m = float(np.clip(m.r2_marginal, 0.0, 1.0))
        r2_c = float(np.clip(m.r2_conditional, r2_m, 1.0))
        random_share = r2_c - r2_m
        residual = 1.0 - r2_c

        # Top-level partition (three rectangles, patches counted for matrix rule).
        left = 0.0
        for frac, color, label in [
            (r2_m, fixed_color, "fixed"),
            (random_share, random_color, "random"),
            (residual, residual_color, "residual"),
        ]:
            import matplotlib.patches as mpatches
            ax.add_patch(mpatches.Rectangle(
                (left, yi - bar_h / 2), frac, bar_h,
                facecolor=color, edgecolor="white", linewidth=0.8,
                alpha=0.88, zorder=2,
            ))
            if frac > 0.06:
                ax.text(left + frac / 2, yi,
                        f"{label}\n{smart_fmt(frac * 100)}%",
                        ha="center", va="center",
                        color="white", fontsize=6.4, zorder=4)
            left += frac

        # Per-term secondary stripe inside the fixed segment.
        total_fix = sum(m.fixed_terms.values())
        if m.fixed_terms and total_fix > 0:
            sub_y = yi - bar_h / 2 - 0.14
            sub_h = 0.10
            sub_left = 0.0
            for i, (term, share) in enumerate(m.fixed_terms.items()):
                frac = r2_m * (share / total_fix)
                import matplotlib.patches as mpatches
                ax.add_patch(mpatches.Rectangle(
                    (sub_left, sub_y), frac, sub_h,
                    facecolor=fixed_color, edgecolor="white",
                    linewidth=0.4, alpha=0.55,
                    hatch=hatches[i % len(hatches)], zorder=2,
                ))
                if frac > 0.04:
                    ax.text(sub_left + frac / 2, sub_y + sub_h / 2,
                            term, ha="center", va="center",
                            fontsize=5.8, color="#111111", zorder=3)
                sub_left += frac

        # Right-of-bar numeric callout.
        ax.text(
            1.02, yi,
            f"R²m={smart_fmt(r2_m)}   R²c={smart_fmt(r2_c)}",
            ha="left", va="center", fontsize=6.4, color="#222222",
            transform=ax.get_yaxis_transform(),
        )

    ax.set_xlim(0, 1)
    ax.set_ylim(-0.8, len(models) - 0.3)
    ax.set_yticks(y)
    ax.set_yticklabels([m.name for m in models], fontsize=7.0)
    ax.set_xticks(np.linspace(0, 1, 6))
    ax.set_xticklabels([f"{int(p)}%" for p in np.linspace(0, 100, 6)],
                       fontsize=7.0)
    ax.set_xlabel("share of total variance")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    for s in ("left",):
        ax.spines[s].set_visible(False)

    # Legend proxies (top-level only; term-level uses hatches inline).
    from matplotlib.patches import Patch
    proxies = [
        Patch(facecolor=fixed_color, edgecolor="white", label="fixed (R²m)"),
        Patch(facecolor=random_color, edgecolor="white", label="random"),
        Patch(facecolor=residual_color, edgecolor="white", label="residual"),
    ]
    ax.legend(handles=proxies, fontsize=6.6, frameon=False,
              loc="lower right", handlelength=1.4, ncols=3,
              bbox_to_anchor=(1.0, -0.18))
    return ax
