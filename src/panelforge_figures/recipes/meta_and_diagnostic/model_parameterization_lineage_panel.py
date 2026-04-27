"""Model parameterization lineage panel — two-column box-and-arrow
diagram linking each modeled input on the left to the empirical
measurement that constrains it on the right; per-edge transformation
note above each arrow.

Conceptual family — pure matplotlib annotation; no strict family
quality rule.
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
from ._shared import ParameterLineageEdge


class ParameterLineageInput(RecipeContract):
    edges: list[ParameterLineageEdge] = Field(..., min_length=2)
    left_header: str = "modeled input"
    right_header: str = "measured readout"
    title: str = "Model parameterization lineage"


def _demo() -> ParameterLineageInput:
    edges = [
        ParameterLineageEdge(
            modeled_input="protrusion width w",
            measurement="manual cross-section",
            transformation_note="median over 30 frames",
            units="um",
        ),
        ParameterLineageEdge(
            modeled_input="actin persistence Lp_actin",
            measurement="curvature autocorrelation fit",
            transformation_note="Bayesian posterior mode",
            units="um",
        ),
        ParameterLineageEdge(
            modeled_input="microtubule persistence Lp_mt",
            measurement="curvature autocorrelation fit",
            transformation_note="Bayesian posterior mode",
            units="um",
        ),
        ParameterLineageEdge(
            modeled_input="cell area A",
            measurement="thresholded actin extent",
            transformation_note="largest connected blob",
            units="um^2",
        ),
        ParameterLineageEdge(
            modeled_input="MT segment length",
            measurement="3D filament tracing",
            transformation_note="connected-arc length",
            units="um",
        ),
        ParameterLineageEdge(
            modeled_input="alpha (buffering)",
            measurement="width-vs-coherency slope",
            transformation_note="hierarchical OLS by genotype",
            units="dimensionless",
        ),
    ]
    return ParameterLineageInput(edges=edges)


_META = RecipeMetadata(
    name="model_parameterization_lineage_panel",
    modality="meta_and_diagnostic",
    family=RecipeFamily.conceptual,
    answers_question=(
        "For each modeled input, what empirical measurement "
        "constrains it, and how is the measurement transformed "
        "into the model parameter?"
    ),
    required_fields=("edges",),
    optional_fields=("left_header", "right_header", "title"),
    file_format_hints=("yaml",),
    alternatives_in_modality=("prisma_flow_diagram",),
)


@register_recipe(
    metadata=_META,
    contract=ParameterLineageInput,
    demo_contract=_demo,
)
def render(contract: ParameterLineageInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.4, 4.4))
    AESTHETIC.apply_to_ax(ax)

    n = len(contract.edges)
    # Vertical layout: row i spans y in [i, i+0.85], top = 0, bottom = n.
    y_top = -0.5
    y_bot = n - 0.5
    box_h = 0.7
    left_x = 0.05
    right_x = 0.65
    box_w = 0.30

    ax.set_xlim(0, 1)
    ax.set_ylim(y_bot, y_top)
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)

    # Headers.
    ax.text(left_x + box_w / 2, y_top - 0.18,
            contract.left_header,
            ha="center", va="bottom", fontsize=7.6,
            color="#222222", fontweight="bold")
    ax.text(right_x + box_w / 2, y_top - 0.18,
            contract.right_header,
            ha="center", va="bottom", fontsize=7.6,
            color="#222222", fontweight="bold")

    # Per-edge boxes + arrow.
    for i, edge in enumerate(contract.edges):
        cy = i
        # Left box (modeled input).
        left_box = mpatches.FancyBboxPatch(
            (left_x, cy - box_h / 2), box_w, box_h,
            boxstyle="round,pad=0.02",
            facecolor="#37474F", edgecolor="white",
            linewidth=0.6, zorder=3,
        )
        ax.add_patch(left_box)
        label_left = edge.modeled_input
        if edge.units:
            label_left += f"\n({edge.units})"
        ax.text(left_x + box_w / 2, cy, label_left,
                ha="center", va="center", fontsize=6.8,
                color="white", zorder=4)

        # Right box (measurement).
        right_box = mpatches.FancyBboxPatch(
            (right_x, cy - box_h / 2), box_w, box_h,
            boxstyle="round,pad=0.02",
            facecolor="#26A69A", edgecolor="white",
            linewidth=0.6, zorder=3,
        )
        ax.add_patch(right_box)
        ax.text(right_x + box_w / 2, cy, edge.measurement,
                ha="center", va="center", fontsize=6.8,
                color="white", zorder=4)

        # Arrow from left to right.
        arrow = mpatches.FancyArrowPatch(
            (left_x + box_w + 0.005, cy),
            (right_x - 0.005, cy),
            arrowstyle="->", mutation_scale=12,
            color="#888888", linewidth=1.1, zorder=2,
        )
        ax.add_patch(arrow)

        # Transformation note above arrow.
        if edge.transformation_note:
            mid_x = (left_x + box_w + right_x) / 2
            ax.text(mid_x, cy - 0.22,
                    edge.transformation_note,
                    ha="center", va="bottom", fontsize=6.0,
                    color="#666666", style="italic", zorder=4)

    # Title.
    ax.set_title(
        f"{contract.title}  ·  {n} parameterization edge"
        f"{'s' if n != 1 else ''}",
        fontsize=8.4, pad=8,
    )
    return ax
