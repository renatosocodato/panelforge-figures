"""CONSORT-style flow diagram — enrollment → randomization → analysis boxes."""

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


class ConsortStage(RecipeContract):
    label: str
    n: int
    excluded_reason: str | None = None
    excluded_n: int | None = None


class ConsortInput(RecipeContract):
    stages: list[ConsortStage] = Field(..., min_length=3)
    title: str = "CONSORT flow"


def _demo() -> ConsortInput:
    return ConsortInput(
        stages=[
            ConsortStage(label="Assessed for eligibility", n=682),
            ConsortStage(label="Enrolled", n=540,
                         excluded_reason="Declined / ineligible", excluded_n=142),
            ConsortStage(label="Randomized", n=520,
                         excluded_reason="Withdrew consent", excluded_n=20),
            ConsortStage(label="Received intervention", n=498,
                         excluded_reason="Protocol deviation", excluded_n=22),
            ConsortStage(label="Analyzed (ITT)", n=498),
        ],
    )


_META = RecipeMetadata(
    name="consort_flow_diagram",
    modality="clinical_cohort",
    family=RecipeFamily.flow,
    answers_question="How did participants flow from screening through enrollment, randomization, and analysis, with attrition reasons?",
    required_fields=("stages",),
    optional_fields=("title",),
    file_format_hints=("yaml", "csv"),
    alternatives_in_modality=("baseline_table_visualization",),
)


@register_recipe(metadata=_META, contract=ConsortInput, demo_contract=_demo)
def render(contract: ConsortInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.6, 4.0))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    stages = contract.stages
    n = len(stages)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)

    box_w, box_h = 48, 11
    cx = 35
    ys = [95 - i * (100 / (n + 0.5)) for i in range(n)]

    for i, (s, cy) in enumerate(zip(stages, ys)):
        color = palette[0] if i == 0 else palette[3]
        ax.add_patch(mpatches.FancyBboxPatch(
            (cx - box_w / 2, cy - box_h / 2), box_w, box_h,
            boxstyle="round,pad=0.02,rounding_size=0.05",
            facecolor=color, edgecolor="white", linewidth=1.3, alpha=0.92,
        ))
        ax.text(cx, cy + 1.8, s.label, ha="center", va="center",
                color="white", fontsize=7.6, fontweight="bold")
        ax.text(cx, cy - 2.4, f"n = {s.n}", ha="center", va="center",
                color="white", fontsize=7.0)

        if i < n - 1:
            y_next = ys[i + 1]
            ax.annotate(
                "", xy=(cx, y_next + box_h / 2 + 1),
                xytext=(cx, cy - box_h / 2 - 1),
                arrowprops=dict(arrowstyle="-|>", color="#444444",
                                lw=0.9, shrinkA=0, shrinkB=0),
            )

        if s.excluded_reason is not None and s.excluded_n is not None:
            # Exclusion side-box.
            ex_x = cx + box_w / 2 + 8
            ax.annotate(
                "", xy=(ex_x - 8, cy),
                xytext=(cx + box_w / 2, cy),
                arrowprops=dict(arrowstyle="-|>", color="#888888",
                                lw=0.8, shrinkA=0, shrinkB=0),
            )
            ax.text(ex_x, cy,
                    f"{s.excluded_reason}\n(n = {s.excluded_n})",
                    ha="left", va="center", fontsize=6.4, color="#444444",
                    bbox=dict(boxstyle="round,pad=0.18", fc="#F5F5F5",
                              ec="#BBBBBB", lw=0.4))

    ax.set_title(contract.title, fontsize=9.0, pad=4)
    return ax
