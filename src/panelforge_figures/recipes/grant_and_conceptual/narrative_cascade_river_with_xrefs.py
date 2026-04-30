"""Narrative cascade river with cross-references — multi-stage
causal river integrating manuscript-level findings with figure
cross-references and inline statistics.

Conceptual family — pure matplotlib annotation; no strict family
quality rule. Synthesis-figure primitive.
"""

from __future__ import annotations

import matplotlib.patches as mpatches
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC
from ._shared import CascadeStage, CascadeTransition


class NarrativeCascadeInput(RecipeContract):
    stages: list[CascadeStage] = Field(..., min_length=2)
    transitions: list[CascadeTransition] = Field(default_factory=list)
    title: str = "Narrative cascade with cross-references"


def _demo() -> NarrativeCascadeInput:
    stages = [
        CascadeStage(
            label="DISC1-linked perturbation",
            figure_xref="Fig 1C",
            p_value=0.001,
            summary="genotype enters multivariate state space",
        ),
        CascadeStage(
            label="territory reorganization",
            figure_xref="Fig 2A-B",
            p_value=0.002,
            summary="contact patches densify; desert shrinks",
        ),
        CascadeStage(
            label="protrusion narrowing",
            figure_xref="Fig 2E",
            p_value=0.005,
            summary="width compressed; erosion deepens",
        ),
        CascadeStage(
            label="checkpoint crossing",
            figure_xref="Fig 5C",
            p_value=0.0001,
            summary="bifurcation at Actin Drive Index ~ 0.6",
        ),
        CascadeStage(
            label="confinement-driven buckling",
            figure_xref="Fig 4D-E",
            p_value=6e-5,
            summary="z-span > Euler L_crit; coordinated curvature",
        ),
        CascadeStage(
            label="forward-validated regime split",
            figure_xref="Fig 6D",
            p_value=None,
            summary="empirical medians inside simulated 95% CI",
        ),
    ]
    transitions = [
        CascadeTransition(from_stage=stages[i].label,
                          to_stage=stages[i + 1].label,
                          weight=1.0)
        for i in range(len(stages) - 1)
    ]
    return NarrativeCascadeInput(
        stages=stages, transitions=transitions,
    )


_META = RecipeMetadata(
    name="narrative_cascade_river_with_xrefs",
    modality="grant_and_conceptual",
    family=RecipeFamily.conceptual,
    answers_question=(
        "Across multi-stage manuscript narrative, how does each "
        "step connect to the next, with figure cross-references "
        "and inline statistics?"
    ),
    required_fields=("stages",),
    optional_fields=("transitions", "title"),
    file_format_hints=("yaml",),
    alternatives_in_modality=("methods_pipeline_flow",),
)


@register_recipe(
    metadata=_META,
    contract=NarrativeCascadeInput,
    demo_contract=_demo,
)
def render(contract: NarrativeCascadeInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.4, 4.8))
    AESTHETIC.apply_to_ax(ax)

    n = len(contract.stages)
    # Vertical layout: row i is stage i; cascade flows top-to-bottom.
    box_h = 0.62
    box_w = 0.74
    box_x = 0.18
    y_top = -0.5
    y_bot = n - 0.3
    ax.set_xlim(0, 1)
    ax.set_ylim(y_bot, y_top)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])

    # Stage boxes with summary + xref + p-value.
    palette = ["#37474F", "#26A69A", "#EF5350", "#AB47BC",
               "#FFA726", "#5E35B1"]
    box_centres_y = list(range(n))
    for i, stg in enumerate(contract.stages):
        cy = box_centres_y[i]
        colour = palette[i % len(palette)]
        ax.add_patch(mpatches.FancyBboxPatch(
            (box_x, cy - box_h / 2), box_w, box_h,
            boxstyle="round,pad=0.02",
            facecolor=colour, edgecolor="white",
            linewidth=0.7, alpha=0.85, zorder=4,
        ))
        # 3-row interior layout to keep summary and p-value on
        # separate lines (avoids horizontal collisions in narrow boxes):
        #   Row 1 (cy - 0.14): label (left)              [Fig X] (right)
        #   Row 2 (cy + 0.04): summary (left, italic)
        #   Row 3 (cy + 0.18):                            p = ... (right)
        # Stage label (bold, row 1 left).
        ax.text(box_x + 0.02, cy - 0.14, stg.label,
                ha="left", va="center", fontsize=7.6,
                color="white", fontweight="bold", zorder=5)
        # Figure cross-reference (row 1 right).
        if stg.figure_xref:
            ax.text(box_x + box_w - 0.02, cy - 0.14,
                    f"[{stg.figure_xref}]",
                    ha="right", va="center", fontsize=6.4,
                    color="white", zorder=5)
        # Summary on its own line (row 2, italic), truncated to fit box_w.
        if stg.summary:
            # Coarse character budget tuned to box_w = 0.74 at fontsize 6.4.
            max_chars = 52
            summary_text = (stg.summary if len(stg.summary) <= max_chars
                            else stg.summary[:max_chars - 1].rstrip() + "…")
            ax.text(box_x + 0.02, cy + 0.04, summary_text,
                    ha="left", va="center", fontsize=6.4,
                    color="white", style="italic", zorder=5)
        # P-value on its own line below xref (row 3 right).
        if stg.p_value is not None:
            p_str = (f"p = {smart_fmt(stg.p_value)}"
                     if stg.p_value >= 1e-4
                     else "p < 1e-4")
            ax.text(box_x + box_w - 0.02, cy + 0.18, p_str,
                    ha="right", va="center", fontsize=6.4,
                    color="white", zorder=5)

    # Transition arrows (between consecutive boxes).
    stage_index = {s.label: i for i, s in enumerate(contract.stages)}
    for tr in contract.transitions:
        if tr.from_stage not in stage_index \
                or tr.to_stage not in stage_index:
            continue
        i_from = stage_index[tr.from_stage]
        i_to = stage_index[tr.to_stage]
        cx = box_x + box_w / 2
        y_from = i_from + box_h / 2
        y_to = i_to - box_h / 2
        arrow = mpatches.FancyArrowPatch(
            (cx, y_from), (cx, y_to),
            arrowstyle="->",
            mutation_scale=14,
            color="#888888",
            linewidth=1.1, zorder=2,
        )
        ax.add_patch(arrow)
        if tr.label:
            ax.text(cx + 0.02, (y_from + y_to) / 2, tr.label,
                    ha="left", va="center", fontsize=6.0,
                    color="#666666", style="italic", zorder=4)

    # Numbered side stage indices on the left.
    for i, stg in enumerate(contract.stages):
        ax.text(box_x - 0.04, i, f"{i + 1}.",
                ha="right", va="center", fontsize=7.6,
                color="#444444", fontweight="bold", zorder=4)

    ax.set_title(
        f"{contract.title}  ·  {n} stage"
        f"{'s' if n != 1 else ''}",
        fontsize=8.6, pad=8,
    )
    return ax
