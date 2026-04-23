"""PRISMA flow diagram — systematic-review record flow with stage
counts and exclusion reasons.

Flow family: ≥2 rounded boxes AND ≥1 annotation arrow.
"""

from __future__ import annotations

import matplotlib.patches as mpatches
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
)
from ._aesthetic import AESTHETIC


class PRISMAStage(RecipeContract):
    name: str
    count: int
    excluded: int = 0
    exclusion_reason: str = ""


class PRISMAInput(RecipeContract):
    stages: list[PRISMAStage] = Field(..., min_length=3, max_length=6)
    title: str = "PRISMA flow diagram"


def _demo() -> PRISMAInput:
    return PRISMAInput(
        stages=[
            PRISMAStage(name="Records identified",
                        count=1248, excluded=0, exclusion_reason=""),
            PRISMAStage(name="Records screened",
                        count=1040, excluded=208,
                        exclusion_reason="duplicates"),
            PRISMAStage(name="Full-text assessed",
                        count=186, excluded=854,
                        exclusion_reason="off-topic / wrong design"),
            PRISMAStage(name="Studies eligible",
                        count=48, excluded=138,
                        exclusion_reason="insufficient data / quality"),
            PRISMAStage(name="Studies in synthesis",
                        count=32, excluded=16,
                        exclusion_reason="duplicate cohorts"),
        ],
        title="PRISMA 2020 — review flow",
    )


_META = RecipeMetadata(
    name="prisma_flow_diagram",
    modality="meta_and_diagnostic",
    family=RecipeFamily.flow,
    answers_question=(
        "How many records survive each stage of the systematic-review "
        "screening funnel?"
    ),
    required_fields=("stages",),
    optional_fields=("title",),
    file_format_hints=("yaml", "csv"),
    alternatives_in_modality=("retention_vs_attrition_sankey",),
)


@register_recipe(
    metadata=_META,
    contract=PRISMAInput,
    demo_contract=_demo,
)
def render(contract: PRISMAInput, ax=None, **_):
    import textwrap

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.8, 4.8))
    AESTHETIC.apply_to_ax(ax)

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ("top", "right", "left", "bottom"):
        ax.spines[s].set_visible(False)

    stages = contract.stages
    n = len(stages)

    # Main column: left side. Excluded column: right side.
    main_x = 0.08
    main_w = 0.52
    excl_x = 0.66
    excl_w = 0.30

    # Vertical stack.
    y_top = 0.92
    y_bot = 0.08
    box_h = (y_top - y_bot - 0.03 * (n - 1)) / n

    for i, stage in enumerate(stages):
        y = y_top - (i + 1) * box_h - i * 0.03
        # Main box.
        ax.add_patch(mpatches.FancyBboxPatch(
            (main_x, y), main_w, box_h,
            boxstyle="round,pad=0.004,rounding_size=0.012",
            facecolor="#ECEFF1", edgecolor="#455A64", linewidth=0.9,
            zorder=3,
        ))
        ax.text(main_x + 0.015, y + box_h - 0.018, stage.name,
                ha="left", va="top", fontsize=7.6,
                color="#263238", fontweight="bold", zorder=4)
        ax.text(main_x + 0.015, y + 0.020,
                f"n = {stage.count:,}",
                ha="left", va="bottom", fontsize=7.6,
                color="#1565C0", zorder=4)

        # Excluded box + exclusion reason (skip for first stage).
        if i > 0 and stage.excluded > 0:
            ax.add_patch(mpatches.FancyBboxPatch(
                (excl_x, y), excl_w, box_h,
                boxstyle="round,pad=0.004,rounding_size=0.012",
                facecolor="#FFF3E0", edgecolor="#E65100", linewidth=0.7,
                zorder=3,
            ))
            # Top line: 'Excluded  n = N'
            ax.text(excl_x + 0.015, y + box_h - 0.018,
                    f"Excluded  n = {stage.excluded:,}",
                    ha="left", va="top", fontsize=6.8,
                    color="#E65100", fontweight="bold", zorder=4)
            # Reason wrapped below with ample clearance.
            reason = textwrap.fill(stage.exclusion_reason, width=28)
            ax.text(excl_x + 0.015, y + box_h * 0.42, reason,
                    ha="left", va="top", fontsize=6.2,
                    color="#8E4500", zorder=4)
            # Side-arrow from main box to excluded box.
            ax.annotate(
                "",
                xy=(excl_x, y + box_h / 2),
                xytext=(main_x + main_w, y + box_h / 2),
                arrowprops=dict(arrowstyle="-|>", color="#E65100",
                                lw=1.0, mutation_scale=14),
                zorder=2,
            )

        # Down-arrow from this stage to next (skip last).
        if i < n - 1:
            y_next_top = y_top - (i + 2) * box_h - (i + 1) * 0.03 + box_h
            ax.annotate(
                "",
                xy=(main_x + main_w / 2, y_next_top),
                xytext=(main_x + main_w / 2, y),
                arrowprops=dict(arrowstyle="-|>", color="#455A64",
                                lw=1.2, mutation_scale=16),
                zorder=2,
            )

    ax.set_title(contract.title, fontsize=9.0, pad=4)
    return ax
