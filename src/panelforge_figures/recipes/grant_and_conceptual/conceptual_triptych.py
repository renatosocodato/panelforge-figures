"""Conceptual triptych — three linked panels (problem → approach → payoff)."""

from __future__ import annotations

import matplotlib.patches as mpatches
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    add_halo_label,
    get_palette,
    register_recipe,
)
from ._aesthetic import AESTHETIC


class TriptychPanel(RecipeContract):
    label: str
    headline: str
    details: list[str] = Field(default_factory=list, max_length=4)
    color_key: str = "signaling"


class ConceptualTriptychInput(RecipeContract):
    left: TriptychPanel
    middle: TriptychPanel
    right: TriptychPanel
    arrow_labels: tuple[str, str] = ("enables", "delivers")


def _demo() -> ConceptualTriptychInput:
    return ConceptualTriptychInput(
        left=TriptychPanel(
            label="Problem",
            headline="Heterogeneous, sex-dimorphic microglia under-described",
            details=[
                "Bulk readouts hide state mixtures",
                "Single-cell time lacking in vivo",
                "Sex and age rarely co-controlled",
            ],
            color_key="signaling",
        ),
        middle=TriptychPanel(
            label="Approach",
            headline="Modality-first biophysical pipeline",
            details=[
                "FRET + 2P intravital",
                "Tristable ODE + Gillespie",
                "Sex-stratified mixed-effects",
            ],
            color_key="metabolic",
        ),
        right=TriptychPanel(
            label="Payoff",
            headline="Mechanistic, translatable, reproducible",
            details=[
                "Sharable figure manifests",
                "Gate-collapsible pharmacology",
                "Patient-cohort biomarker pipeline",
            ],
            color_key="cytoskeletal",
        ),
        arrow_labels=("because", "delivers"),
    )


_META = RecipeMetadata(
    name="conceptual_triptych",
    modality="grant_and_conceptual",
    family=RecipeFamily.conceptual,
    answers_question="What's the narrative arc from the problem to the approach to the payoff?",
    required_fields=("left", "middle", "right"),
    optional_fields=("arrow_labels",),
    file_format_hints=("yaml", "toml"),
    alternatives_in_modality=("hypothesis_diagram", "executive_summary_tile"),
)


@register_recipe(metadata=_META, contract=ConceptualTriptychInput, demo_contract=_demo)
def render(contract: ConceptualTriptychInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(7.2, 3.6))
    AESTHETIC.apply_to_ax(ax)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ("left", "bottom"):
        ax.spines[s].set_visible(False)
    palette = get_palette(AESTHETIC.primary_palette)

    panels = [
        (contract.left, 2, 28),
        (contract.middle, 36, 28),
        (contract.right, 70, 28),
    ]
    for panel, x0, w in panels:
        color = (
            palette.pick(panel.color_key)
            if panel.color_key in palette.semantic
            else palette[0]
        )
        ax.add_patch(mpatches.FancyBboxPatch(
            (x0, 15), w, 70,
            boxstyle="round,pad=0.02,rounding_size=0.04",
            facecolor=color, edgecolor="white", linewidth=1.4, alpha=0.93,
        ))
        ax.text(x0 + w / 2, 80, panel.label, ha="center", va="top",
                color="white", fontsize=7.2, fontweight="bold", alpha=0.8)
        ax.text(x0 + w / 2, 74, panel.headline, ha="center", va="top",
                color="white", fontsize=7.8, fontweight="bold", wrap=True)
        for i, d in enumerate(panel.details):
            ax.text(x0 + 2, 55 - i * 8, f"• {d}",
                    ha="left", va="top", color="white",
                    fontsize=6.8, alpha=0.92)

    # Arrows between panels.
    for (x0, x1, label) in [
        (30.5, 35.5, contract.arrow_labels[0]),
        (64.5, 69.5, contract.arrow_labels[1]),
    ]:
        ax.annotate(
            "",
            xy=(x1, 50),
            xytext=(x0, 50),
            arrowprops=dict(arrowstyle="-|>", color="#444444", lw=1.6,
                            shrinkA=2, shrinkB=2),
            zorder=3,
        )
        add_halo_label(ax, (x0 + x1) / 2, 54, label,
                       color="#333333", fontsize=7.2, fontweight="bold",
                       halo_width=2.8)
    return ax
