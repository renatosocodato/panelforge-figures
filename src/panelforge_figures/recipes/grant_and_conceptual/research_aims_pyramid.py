"""Research-aims pyramid — hierarchical objective → aims → sub-questions.

Conceptual family. Distinct from `conceptual_triptych` (linear 3-panel
narrative) and `hypothesis_diagram` (single claim + evidence): here
the topology is a **hierarchy** with one top-level objective, a middle
row of aims, and a base row of sub-questions.
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


class AimsPyramidInput(RecipeContract):
    objective: str = Field(..., description="overarching objective, one short sentence")
    aim_titles: list[str] = Field(..., min_length=2, max_length=4)
    aim_subquestions: list[list[str]] = Field(
        ...,
        description=(
            "for each aim, 1-3 sub-questions; outer length = len(aim_titles)"
        ),
    )
    title: str = "Research aims pyramid"


def _demo() -> AimsPyramidInput:
    return AimsPyramidInput(
        objective=(
            "Resolve when microglial protrusion dynamics become a "
            "treatable driver of chronic inflammation."
        ),
        aim_titles=[
            "Aim 1 — Dynamics",
            "Aim 2 — Mechanism",
            "Aim 3 — Translation",
        ],
        aim_subquestions=[
            ["Which states exist?",
             "How fast do they switch?",
             "Is switching sex-dimorphic?"],
            ["What molecular gates control switching?",
             "Which cascades collapse the GATE well?"],
            ["Do PK-plausible doses collapse the GATE in vivo?",
             "Are there diagnostic biomarkers?"],
        ],
        title="ATHENA — research aims pyramid",
    )


_META = RecipeMetadata(
    name="research_aims_pyramid",
    modality="grant_and_conceptual",
    family=RecipeFamily.conceptual,
    answers_question=(
        "How do specific aims nest under an overarching objective, and "
        "what sub-questions does each aim address?"
    ),
    required_fields=("objective", "aim_titles", "aim_subquestions"),
    optional_fields=("title",),
    file_format_hints=("yaml", "toml", "dict"),
    alternatives_in_modality=("conceptual_triptych", "hypothesis_diagram"),
)


@register_recipe(
    metadata=_META,
    contract=AimsPyramidInput,
    demo_contract=_demo,
)
def render(contract: AimsPyramidInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.0, 3.8))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ("top", "right", "left", "bottom"):
        ax.spines[s].set_visible(False)

    # Top: objective banner.
    obj_h = 0.20
    obj_y = 0.78
    ax.add_patch(mpatches.FancyBboxPatch(
        (0.08, obj_y), 0.84, obj_h,
        boxstyle="round,pad=0.008,rounding_size=0.02",
        facecolor="#263238", edgecolor="none", alpha=0.92,
        zorder=3,
    ))
    ax.text(0.10, obj_y + obj_h * 0.68, "OBJECTIVE",
            ha="left", va="center", fontsize=7.0,
            color="#B0BEC5", fontweight="bold", zorder=4)
    # Wrap objective text.
    import textwrap
    wrapped = "\n".join(textwrap.wrap(contract.objective, width=72))
    ax.text(0.10, obj_y + obj_h * 0.32, wrapped,
            ha="left", va="center", fontsize=8.2,
            color="white", zorder=4)

    # Middle: aims row.
    aims = contract.aim_titles
    n_aims = len(aims)
    aim_w = 0.76 / n_aims
    aim_gap = 0.08 / max(n_aims - 1, 1)
    aim_y = 0.46
    aim_h = 0.20
    color_keys = ["signaling", "metabolic", "cytoskeletal", "other"]
    for i, title in enumerate(aims):
        x = 0.12 + i * (aim_w + aim_gap * (n_aims - 1) / n_aims)
        ck = color_keys[i % len(color_keys)]
        color = palette.pick(ck) if ck in palette.semantic else palette[i]
        ax.add_patch(mpatches.FancyBboxPatch(
            (x, aim_y), aim_w, aim_h,
            boxstyle="round,pad=0.006,rounding_size=0.016",
            facecolor=color, edgecolor="white", linewidth=0.7,
            alpha=0.90, zorder=3,
        ))
        ax.text(x + aim_w / 2, aim_y + aim_h / 2, title,
                ha="center", va="center", fontsize=8.2,
                color="white", fontweight="bold", zorder=4)
        # Connector from objective down to aim.
        ax.plot([x + aim_w / 2, x + aim_w / 2],
                [obj_y, aim_y + aim_h],
                color="#888888", lw=0.8, zorder=1)

    # Base: per-aim sub-question cards stacked beneath each aim.
    sub_y_top = aim_y - 0.04
    for i, subs in enumerate(contract.aim_subquestions):
        x = 0.12 + i * (aim_w + aim_gap * (n_aims - 1) / n_aims)
        for j, q in enumerate(subs[:3]):
            sub_y = sub_y_top - j * 0.10
            ax.add_patch(mpatches.FancyBboxPatch(
                (x + aim_w * 0.06, sub_y - 0.07),
                aim_w * 0.88, 0.07,
                boxstyle="round,pad=0.004,rounding_size=0.010",
                facecolor="white", edgecolor="#BBBBBB", linewidth=0.5,
                alpha=0.98, zorder=3,
            ))
            # Wrap to fit.
            q_wrap = "\n".join(textwrap.wrap(q, width=40))
            ax.text(x + aim_w / 2, sub_y - 0.035, q_wrap,
                    ha="center", va="center", fontsize=6.8,
                    color="#333333", zorder=4)

    ax.set_title(contract.title, fontsize=9.0, pad=4)
    return ax
