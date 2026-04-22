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

    import textwrap

    # Column layout: n_aims equal-width columns covering 0.04..0.96.
    aims = contract.aim_titles
    n_aims = len(aims)
    avail = 0.92
    col_gap = 0.02
    col_w = (avail - col_gap * (n_aims - 1)) / n_aims
    col_x = [0.04 + i * (col_w + col_gap) for i in range(n_aims)]

    # Top: objective banner spans full width with the OBJECTIVE label
    # fully above the objective sentence (no overlap).
    obj_h = 0.20
    obj_y = 0.76
    ax.add_patch(mpatches.FancyBboxPatch(
        (0.04, obj_y), avail, obj_h,
        boxstyle="round,pad=0.008,rounding_size=0.018",
        facecolor="#263238", edgecolor="none", alpha=0.92,
        zorder=3,
    ))
    ax.text(0.06, obj_y + obj_h - 0.025, "OBJECTIVE",
            ha="left", va="top", fontsize=7.0,
            color="#B0BEC5", fontweight="bold", zorder=4)
    wrapped = "\n".join(textwrap.wrap(contract.objective, width=58))
    ax.text(0.5, obj_y + 0.055, wrapped,
            ha="center", va="center", fontsize=7.0,
            color="white", zorder=4)

    # Middle: aim bands, one per column.
    aim_y = 0.54
    aim_h = 0.16
    color_keys = ["signaling", "metabolic", "cytoskeletal", "other"]
    for i, title in enumerate(aims):
        x = col_x[i]
        ck = color_keys[i % len(color_keys)]
        color = palette.pick(ck) if ck in palette.semantic else palette[i]
        ax.add_patch(mpatches.FancyBboxPatch(
            (x, aim_y), col_w, aim_h,
            boxstyle="round,pad=0.006,rounding_size=0.014",
            facecolor=color, edgecolor="white", linewidth=0.7,
            alpha=0.90, zorder=3,
        ))
        # Normalise em-dash to ASCII + wrap narrowly.
        title_ascii = title.replace("—", "-").replace("–", "-")
        title_wrap = "\n".join(textwrap.wrap(title_ascii, width=13))
        ax.text(x + col_w / 2, aim_y + aim_h / 2, title_wrap,
                ha="center", va="center", fontsize=7.2,
                color="white", fontweight="bold", zorder=4)
        # Connector from objective down to aim.
        ax.plot([x + col_w / 2, x + col_w / 2],
                [obj_y, aim_y + aim_h],
                color="#888888", lw=0.8, zorder=1)

    # Base: per-aim sub-question cards stacked beneath each aim.
    for i, subs in enumerate(contract.aim_subquestions):
        x = col_x[i]
        n_sub = min(len(subs), 3)
        if n_sub == 0:
            continue
        # Allocate vertical space 0.04..0.48 for this column's subs.
        top_y = 0.48
        bot_y = 0.04
        sub_h = (top_y - bot_y - 0.015 * (n_sub - 1)) / n_sub
        for j, q in enumerate(subs[:3]):
            sub_y = top_y - (j + 1) * sub_h - j * 0.015
            ax.add_patch(mpatches.FancyBboxPatch(
                (x, sub_y), col_w, sub_h,
                boxstyle="round,pad=0.004,rounding_size=0.010",
                facecolor="white", edgecolor="#BBBBBB", linewidth=0.5,
                alpha=0.98, zorder=3,
            ))
            q_wrap = "\n".join(textwrap.wrap(q, width=20))
            ax.text(x + col_w / 2, sub_y + sub_h / 2, q_wrap,
                    ha="center", va="center", fontsize=6.4,
                    color="#333333", zorder=4)

    ax.set_title(contract.title, fontsize=9.0, pad=4)
    return ax
