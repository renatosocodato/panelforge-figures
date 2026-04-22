"""Methods pipeline flow — strictly linear step-by-step pipeline with
rounded boxes and arrow connectors.

Distinct from `work_package_flow` (WP dependency DAG): this is a
single-track left-to-right pipeline with one input and one output,
the standard "Methods" figure for an A4 portrait proposal.
"""

from __future__ import annotations

import matplotlib.patches as mpatches
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
)
from ._aesthetic import AESTHETIC


class PipelineStep(RecipeContract):
    title: str
    description: str = ""
    color_key: str = "signaling"


class MethodsPipelineInput(RecipeContract):
    input_label: str = Field("input", description="label for the input data")
    output_label: str = Field("output", description="label for the output")
    steps: list[PipelineStep] = Field(..., min_length=2, max_length=6)
    title: str = "Methods pipeline"


def _demo() -> MethodsPipelineInput:
    return MethodsPipelineInput(
        input_label="raw 2P + FRET\nacquisitions",
        output_label="model-ready\ntrajectories",
        steps=[
            PipelineStep(title="Segment",
                         description="StarDist + tracking",
                         color_key="signaling"),
            PipelineStep(title="Normalise",
                         description="bleach / background",
                         color_key="metabolic"),
            PipelineStep(title="Quantify",
                         description="FRET ratios, kinematics",
                         color_key="cytoskeletal"),
            PipelineStep(title="Classify",
                         description="HMM state assignment",
                         color_key="other"),
        ],
        title="Methods pipeline (A4)",
    )


_META = RecipeMetadata(
    name="methods_pipeline_flow",
    modality="grant_and_conceptual",
    family=RecipeFamily.flow,
    answers_question=(
        "What are the sequential data-generation and analysis steps, "
        "from input to output?"
    ),
    required_fields=("input_label", "output_label", "steps"),
    optional_fields=("title",),
    file_format_hints=("yaml", "toml"),
    alternatives_in_modality=("work_package_flow",),
)


@register_recipe(
    metadata=_META,
    contract=MethodsPipelineInput,
    demo_contract=_demo,
)
def render(contract: MethodsPipelineInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.4, 2.6))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ("top", "right", "left", "bottom"):
        ax.spines[s].set_visible(False)

    steps = contract.steps
    n = len(steps)
    # Total slots = input + n steps + output = n + 2.
    slots = n + 2
    slot_w = 0.88 / slots
    gap = (1.0 - slot_w * slots) / max(slots + 1, 1)
    y_mid = 0.50
    box_h = 0.46

    # Input box (pill).
    x_in = gap
    ax.add_patch(mpatches.FancyBboxPatch(
        (x_in, y_mid - box_h / 2), slot_w, box_h,
        boxstyle="round,pad=0.006,rounding_size=0.10",
        facecolor="#F5F5F5", edgecolor="#888888", linewidth=0.8,
        zorder=3,
    ))
    ax.text(x_in + slot_w / 2, y_mid, contract.input_label,
            ha="center", va="center", fontsize=7.0,
            color="#333333", zorder=4)

    # Step boxes.
    for i, step in enumerate(steps):
        x = gap + (i + 1) * (slot_w + gap)
        ck = step.color_key
        color = palette.pick(ck) if ck in palette.semantic else palette[i]
        ax.add_patch(mpatches.FancyBboxPatch(
            (x, y_mid - box_h / 2), slot_w, box_h,
            boxstyle="round,pad=0.006,rounding_size=0.018",
            facecolor=color, edgecolor="white", linewidth=0.8,
            alpha=0.92, zorder=3,
        ))
        ax.text(x + slot_w / 2, y_mid + 0.06, step.title,
                ha="center", va="center", fontsize=7.6,
                color="white", fontweight="bold", zorder=4)
        if step.description:
            ax.text(x + slot_w / 2, y_mid - 0.10, step.description,
                    ha="center", va="center", fontsize=6.4,
                    color="white", zorder=4)

    # Output box (pill).
    x_out = gap + (n + 1) * (slot_w + gap)
    ax.add_patch(mpatches.FancyBboxPatch(
        (x_out, y_mid - box_h / 2), slot_w, box_h,
        boxstyle="round,pad=0.006,rounding_size=0.10",
        facecolor="#263238", edgecolor="white", linewidth=0.8,
        zorder=3,
    ))
    ax.text(x_out + slot_w / 2, y_mid, contract.output_label,
            ha="center", va="center", fontsize=7.0,
            color="white", zorder=4)

    # Arrows between adjacent boxes.
    for i in range(slots - 1):
        x_from = gap + i * (slot_w + gap) + slot_w
        x_to = gap + (i + 1) * (slot_w + gap)
        ax.annotate(
            "",
            xy=(x_to, y_mid), xytext=(x_from, y_mid),
            arrowprops=dict(arrowstyle="->", color="#555555",
                            lw=1.1, shrinkA=1, shrinkB=1),
            zorder=2,
        )

    ax.set_title(contract.title, fontsize=9.0, pad=4)
    return ax
