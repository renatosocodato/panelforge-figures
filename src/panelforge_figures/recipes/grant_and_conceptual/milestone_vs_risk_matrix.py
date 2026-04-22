"""Milestone × risk matrix — 2×2 impact × probability placement with
per-milestone tile and risk-rated border.

Matrix family: ≥4 quadrant patches. Distinct from `team_expertise_matrix`
(team × competency heatmap).
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


class Milestone(RecipeContract):
    id: str
    title: str
    probability: float = Field(..., ge=0.0, le=1.0,
                               description="risk probability in [0, 1]")
    impact: float = Field(..., ge=0.0, le=1.0,
                          description="risk impact in [0, 1]")
    mitigation: str = ""


class MilestoneRiskInput(RecipeContract):
    milestones: list[Milestone] = Field(..., min_length=3)
    title: str = "Milestone × risk matrix"


def _demo() -> MilestoneRiskInput:
    return MilestoneRiskInput(
        milestones=[
            Milestone(id="M1", title="Data freeze",
                      probability=0.15, impact=0.80,
                      mitigation="redundant cohorts"),
            Milestone(id="M2", title="Model locked",
                      probability=0.30, impact=0.65,
                      mitigation="fallback surrogate"),
            Milestone(id="M3", title="In vivo go/no-go",
                      probability=0.55, impact=0.85,
                      mitigation="stage 3a/3b decision gate"),
            Milestone(id="M4", title="Manuscripts",
                      probability=0.25, impact=0.45,
                      mitigation="rolling submission"),
            Milestone(id="M5", title="Clinical handshake",
                      probability=0.70, impact=0.50,
                      mitigation="industry partner signed LoI"),
            Milestone(id="M6", title="Public release",
                      probability=0.10, impact=0.25,
                      mitigation="open-source already in place"),
        ],
    )


_META = RecipeMetadata(
    name="milestone_vs_risk_matrix",
    modality="grant_and_conceptual",
    family=RecipeFamily.matrix,
    answers_question=(
        "Which milestones are high-risk (high probability of failure) "
        "and high-impact if they fail?"
    ),
    required_fields=("milestones",),
    optional_fields=("title",),
    file_format_hints=("yaml", "csv"),
    alternatives_in_modality=("timeline_gantt_with_milestones",),
)


@register_recipe(
    metadata=_META,
    contract=MilestoneRiskInput,
    demo_contract=_demo,
)
def render(contract: MilestoneRiskInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 4.0))
    AESTHETIC.apply_to_ax(ax)

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    # 2 x 2 quadrant backgrounds (≥4 patches for matrix rule).
    quadrants = [
        # (lo_x, lo_y, color, label)
        (0.0, 0.0, "#E8F5E9", "low impact · low prob"),
        (0.5, 0.0, "#FFF3E0", "low impact · high prob"),
        (0.0, 0.5, "#FFF8E1", "high impact · low prob"),
        (0.5, 0.5, "#FFEBEE", "high impact · high prob"),
    ]
    for (lo_x, lo_y, color, lab) in quadrants:
        ax.add_patch(mpatches.Rectangle(
            (lo_x, lo_y), 0.5, 0.5,
            facecolor=color, edgecolor="none", alpha=0.85, zorder=1,
        ))
        # Quadrant label in subtle corner text.
        if "high impact" in lab and "high prob" in lab:
            ax.text(lo_x + 0.48, lo_y + 0.48, "!!",
                    ha="right", va="top", fontsize=9.6,
                    color="#C62828", fontweight="bold",
                    alpha=0.5, zorder=2)

    # Axis reference lines.
    ax.axhline(0.5, color="#888888", lw=0.6, ls="--", zorder=2)
    ax.axvline(0.5, color="#888888", lw=0.6, ls="--", zorder=2)

    # Place milestones.
    for m in contract.milestones:
        # Border colour by risk quadrant.
        if m.probability >= 0.5 and m.impact >= 0.5:
            border = "#C62828"
        elif m.impact >= 0.5:
            border = "#F57C00"
        elif m.probability >= 0.5:
            border = "#E65100"
        else:
            border = "#2E7D32"
        # Tile.
        tile_w, tile_h = 0.09, 0.07
        x = m.probability - tile_w / 2
        y = m.impact - tile_h / 2
        # Clamp inside the 2x2.
        x = max(0.01, min(x, 0.99 - tile_w))
        y = max(0.01, min(y, 0.99 - tile_h))
        ax.add_patch(mpatches.FancyBboxPatch(
            (x, y), tile_w, tile_h,
            boxstyle="round,pad=0.004,rounding_size=0.008",
            facecolor="white", edgecolor=border, linewidth=1.3,
            alpha=0.95, zorder=5,
        ))
        ax.text(x + tile_w / 2, y + tile_h / 2, m.id,
                ha="center", va="center", fontsize=7.0,
                color="#222222", fontweight="bold", zorder=6)
        # Title above tile.
        ax.text(x + tile_w / 2, y + tile_h + 0.01, m.title,
                ha="center", va="bottom", fontsize=6.2,
                color="#333333", zorder=6)

    # Axis labels & ticks.
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticklabels(["0.0", "0.25", "0.50", "0.75", "1.0"],
                       fontsize=6.8)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0.0", "0.25", "0.50", "0.75", "1.0"],
                       fontsize=6.8)
    ax.set_xlabel("probability of occurrence")
    ax.set_ylabel("impact if it occurs")
    ax.set_title(contract.title, fontsize=9.0, pad=4)

    # Axis corner labels (low / high).
    ax.text(0.02, -0.04, "low", transform=ax.transAxes,
            ha="left", va="top", fontsize=6.2, color="#666666")
    ax.text(0.98, -0.04, "high", transform=ax.transAxes,
            ha="right", va="top", fontsize=6.2, color="#666666")
    ax.text(-0.02, 0.02, "low", transform=ax.transAxes,
            ha="right", va="bottom", fontsize=6.2, color="#666666",
            rotation=90)
    ax.text(-0.02, 0.98, "high", transform=ax.transAxes,
            ha="right", va="top", fontsize=6.2, color="#666666",
            rotation=90)
    return ax
