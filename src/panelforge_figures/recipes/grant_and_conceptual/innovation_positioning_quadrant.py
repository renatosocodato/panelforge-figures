"""Innovation-positioning quadrant — 2D quadrant showing our-proposal
vs state-of-the-art competitors on novelty × feasibility axes.

Matrix family: ≥4 quadrant patches. Helps reviewers place a proposal
relative to existing work.
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


class Competitor(RecipeContract):
    name: str
    novelty: float = Field(..., ge=0.0, le=1.0)
    feasibility: float = Field(..., ge=0.0, le=1.0)


class InnovationPositioningInput(RecipeContract):
    competitors: list[Competitor] = Field(..., min_length=3)
    our_name: str = "our proposal"
    our_novelty: float = Field(..., ge=0.0, le=1.0)
    our_feasibility: float = Field(..., ge=0.0, le=1.0)
    title: str = "Innovation positioning"


def _demo() -> InnovationPositioningInput:
    return InnovationPositioningInput(
        competitors=[
            Competitor(name="Group A 2023", novelty=0.35, feasibility=0.85),
            Competitor(name="Group B 2024", novelty=0.55, feasibility=0.70),
            Competitor(name="Group C 2022", novelty=0.75, feasibility=0.35),
            Competitor(name="Group D 2024", novelty=0.45, feasibility=0.55),
            Competitor(name="Group E 2021", novelty=0.25, feasibility=0.60),
            Competitor(name="Group F 2024", novelty=0.65, feasibility=0.45),
        ],
        our_name="ATHENA",
        our_novelty=0.82,
        our_feasibility=0.72,
    )


_META = RecipeMetadata(
    name="innovation_positioning_quadrant",
    modality="grant_and_conceptual",
    family=RecipeFamily.matrix,
    answers_question=(
        "Where does our proposal sit on a novelty × feasibility "
        "quadrant relative to state-of-the-art competitors?"
    ),
    required_fields=(
        "competitors", "our_name", "our_novelty", "our_feasibility",
    ),
    optional_fields=("title",),
    file_format_hints=("yaml", "csv"),
    alternatives_in_modality=("milestone_vs_risk_matrix",),
)


@register_recipe(
    metadata=_META,
    contract=InnovationPositioningInput,
    demo_contract=_demo,
)
def render(contract: InnovationPositioningInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 4.2))
    AESTHETIC.apply_to_ax(ax)

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    # 2 x 2 quadrant backgrounds. Place labels in the *outer* corners
    # of each quadrant so they never collide with the central dashed
    # axis lines or with competitor markers clustering near the mid.
    quadrants = [
        # (lo_x, lo_y, color, label, label_x, label_y, ha, va)
        (0.0, 0.0, "#ECEFF1", "incremental",    0.02, 0.02, "left",  "bottom"),
        (0.5, 0.0, "#FFF3E0", "risky-risky",    0.98, 0.02, "right", "bottom"),
        (0.0, 0.5, "#E8F5E9", "safe-safe",      0.02, 0.98, "left",  "top"),
        (0.5, 0.5, "#E3F2FD", "sweet spot",     0.98, 0.98, "right", "top"),
    ]
    for (lo_x, lo_y, color, lab, lx, ly, ha, va) in quadrants:
        ax.add_patch(mpatches.Rectangle(
            (lo_x, lo_y), 0.5, 0.5,
            facecolor=color, edgecolor="none", alpha=0.85, zorder=1,
        ))
        ax.text(lx, ly, lab,
                ha=ha, va=va, fontsize=6.2,
                color="#555555", style="italic", zorder=2)

    # Axis reference lines.
    ax.axhline(0.5, color="#888888", lw=0.6, ls="--", zorder=2)
    ax.axvline(0.5, color="#888888", lw=0.6, ls="--", zorder=2)

    # Competitors.
    for c in contract.competitors:
        ax.scatter([c.novelty], [c.feasibility],
                   s=56, color="#78909C", edgecolor="white",
                   linewidth=0.6, alpha=0.85, zorder=4)
        ax.text(c.novelty + 0.02, c.feasibility + 0.01, c.name,
                ha="left", va="bottom", fontsize=6.4,
                color="#455A64", zorder=5)

    # Our proposal — distinct star marker (label is drawn by hand
    # above the marker; no legend needed since it would duplicate
    # that label and clutter a corner).
    ax.scatter([contract.our_novelty], [contract.our_feasibility],
               s=260, marker="*", color="#C62828",
               edgecolor="white", linewidth=1.0,
               alpha=0.95, zorder=6)
    ax.text(contract.our_novelty, contract.our_feasibility + 0.035,
            contract.our_name,
            ha="center", va="bottom", fontsize=7.4,
            color="#C62828", fontweight="bold", zorder=7)

    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticklabels(["0.0", "0.25", "0.50", "0.75", "1.0"],
                       fontsize=6.8)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0.0", "0.25", "0.50", "0.75", "1.0"],
                       fontsize=6.8)
    ax.set_xlabel("novelty")
    ax.set_ylabel("feasibility")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    return ax
