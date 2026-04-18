"""Hypothesis diagram — central claim with supporting evidence + predictions."""

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


class HypothesisDiagramInput(RecipeContract):
    claim: str = Field(..., description="Central hypothesis in one sentence.")
    evidence: list[str] = Field(default_factory=list, min_length=0, max_length=5)
    predictions: list[str] = Field(default_factory=list, min_length=0, max_length=5)
    mechanism: str | None = None
    claim_color_key: str = "signaling"


def _demo() -> HypothesisDiagramInput:
    return HypothesisDiagramInput(
        claim=(
            "RhoA activity in microglia forms a tristable landscape whose "
            "GATE well is sex-dimorphic and pharmacologically collapsible."
        ),
        evidence=[
            "FRET bistability in live microglia (N=27 mice)",
            "Bimodal process-velocity CV (♀>♂ at baseline)",
            "ROCK inhibition abolishes GATE in acute slices",
        ],
        predictions=[
            "SRCi shifts basal population TRAP→HOME within 20 min",
            "LPS flips ♂ into GATE at ~90 min post-challenge",
            "Paracrine H2O2 broadens bimodality in space",
        ],
        mechanism="RhoA / Rac1 antagonism → actin protrusion topology",
        claim_color_key="cytoskeletal",
    )


_META = RecipeMetadata(
    name="hypothesis_diagram",
    modality="grant_and_conceptual",
    family=RecipeFamily.conceptual,
    answers_question="What is the central hypothesis, and which observations support it versus which predictions test it?",
    required_fields=("claim",),
    optional_fields=("evidence", "predictions", "mechanism", "claim_color_key"),
    file_format_hints=("yaml", "toml", "dict"),
    alternatives_in_modality=("work_package_flow", "conceptual_triptych"),
    example_manifest="skill/example_manifests/horizon_grant.yaml",
)


@register_recipe(metadata=_META, contract=HypothesisDiagramInput, demo_contract=_demo)
def render(contract: HypothesisDiagramInput, ax=None, **_):
    """Central claim bubble, flanked by evidence (left) and predictions (right)."""
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.4, 3.8))
    AESTHETIC.apply_to_ax(ax)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ("left", "bottom"):
        ax.spines[s].set_visible(False)
    palette = get_palette(AESTHETIC.primary_palette)
    claim_c = (
        palette.pick(contract.claim_color_key)
        if contract.claim_color_key in palette.semantic
        else palette[0]
    )

    # Central claim bubble.
    claim_box = mpatches.FancyBboxPatch(
        (25, 38),
        50,
        28,
        boxstyle="round,pad=0.02,rounding_size=0.04",
        facecolor=claim_c,
        edgecolor="white",
        linewidth=2.0,
        alpha=0.95,
    )
    ax.add_patch(claim_box)
    ax.text(50, 58, "HYPOTHESIS", ha="center", va="top",
            color="white", fontsize=7.5, fontweight="bold", alpha=0.7,
            transform=ax.transData)
    ax.text(50, 52, contract.claim, ha="center", va="center",
            color="white", fontsize=8.2, wrap=True, fontweight="bold")
    if contract.mechanism:
        add_halo_label(ax, 50, 32, f"via {contract.mechanism}",
                       color=claim_c, fontsize=7.2, fontweight="bold",
                       halo_width=2.6)

    # Evidence (left column).
    ev_color = "#37474F"
    ax.text(3, 82, "EVIDENCE", ha="left", va="bottom",
            fontsize=7.8, color=ev_color, fontweight="bold")
    for i, e in enumerate(contract.evidence[:5]):
        y = 74 - i * 11
        ax.add_patch(mpatches.FancyBboxPatch(
            (2, y - 3.6), 22, 7.8,
            boxstyle="round,pad=0.02,rounding_size=0.04",
            facecolor="white", edgecolor=ev_color, linewidth=0.8,
        ))
        ax.text(13, y, e, ha="center", va="center", fontsize=6.6, color="#222222")
        ax.annotate("", xy=(26, 52), xytext=(24.2, y),
                    arrowprops=dict(arrowstyle="-|>", color=ev_color, lw=0.9,
                                    shrinkA=0, shrinkB=0,
                                    connectionstyle="arc3,rad=-0.2"))

    # Predictions (right column).
    pr_color = "#D84315"
    ax.text(97, 82, "PREDICTIONS", ha="right", va="bottom",
            fontsize=7.8, color=pr_color, fontweight="bold")
    for i, p in enumerate(contract.predictions[:5]):
        y = 74 - i * 11
        ax.add_patch(mpatches.FancyBboxPatch(
            (76, y - 3.6), 22, 7.8,
            boxstyle="round,pad=0.02,rounding_size=0.04",
            facecolor="white", edgecolor=pr_color, linewidth=0.8,
        ))
        ax.text(87, y, p, ha="center", va="center", fontsize=6.6, color="#222222")
        ax.annotate("", xy=(75.8, y), xytext=(74, 52),
                    arrowprops=dict(arrowstyle="-|>", color=pr_color, lw=0.9,
                                    shrinkA=0, shrinkB=0,
                                    connectionstyle="arc3,rad=0.2"))
    return ax
