"""Hypothesis diagram — central claim band with evidence (left) and predictions (right).

Redesigned as a single horizontal band with two small flanking cards so
the text lines up cleanly at small render sizes. The claim sits in a wide
band across the middle; evidence and predictions are compact 1-sentence
cards stacked outside.
"""

from __future__ import annotations

import textwrap

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
    evidence: list[str] = Field(default_factory=list, min_length=0, max_length=3)
    predictions: list[str] = Field(default_factory=list, min_length=0, max_length=3)
    mechanism: str | None = None
    claim_color_key: str = "signaling"


def _demo() -> HypothesisDiagramInput:
    return HypothesisDiagramInput(
        claim=(
            "RhoA in microglia forms a tristable landscape whose GATE well "
            "is sex-dimorphic and pharmacologically collapsible."
        ),
        evidence=[
            "FRET bistability in live microglia",
            "Bimodal process-velocity CV",
            "ROCKi collapses GATE",
        ],
        predictions=[
            "SRCi shifts TRAP to HOME in 20 min",
            "LPS flips males into GATE at ~90 min",
            "Paracrine H2O2 broadens bimodality",
        ],
        mechanism="RhoA / Rac1 antagonism via actin topology",
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
    """Stacked-band layout: evidence (top) → hypothesis (middle) → predictions (bottom)."""
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.8, 3.4))
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
    ev_color = "#37474F"
    pr_color = "#D84315"

    # Wrap helper — ~24 chars per card width, ~60 chars for the central band.
    def _wrap(s: str, width: int) -> str:
        return "\n".join(textwrap.wrap(s, width=width)) or s

    # ── Evidence band (top 30%) ───────────────────────────────
    ax.text(2, 97, "EVIDENCE", ha="left", va="top",
            fontsize=7.6, color=ev_color)
    n_ev = min(len(contract.evidence), 3)
    for i in range(n_ev):
        w = 100 / 3 - 2
        x0 = 2 + i * (w + 1.5)
        ax.add_patch(mpatches.FancyBboxPatch(
            (x0, 69), w, 18,
            boxstyle="round,pad=0.012,rounding_size=0.02",
            facecolor="white", edgecolor=ev_color, linewidth=0.8,
        ))
        ax.text(x0 + w / 2, 78, _wrap(contract.evidence[i], 24),
                ha="center", va="center", fontsize=6.4, color="#222222")

    # ── Central claim band (middle 30%) ───────────────────────
    ax.add_patch(mpatches.FancyBboxPatch(
        (2, 36), 96, 28,
        boxstyle="round,pad=0.012,rounding_size=0.02",
        facecolor=claim_c, edgecolor="white", linewidth=1.6, alpha=0.95,
    ))
    ax.text(50, 60, "HYPOTHESIS", ha="center", va="center",
            fontsize=7.0, color="white", alpha=0.75)
    ax.text(50, 50, _wrap(contract.claim, 64),
            ha="center", va="center", fontsize=7.6,
            color="white")
    if contract.mechanism:
        ax.text(50, 40, f"via {contract.mechanism}",
                ha="center", va="center", fontsize=6.4,
                color="white", alpha=0.85, style="italic")

    # Connectors from evidence band to claim.
    for i in range(n_ev):
        w = 100 / 3 - 2
        x_mid = 2 + i * (w + 1.5) + w / 2
        ax.annotate("", xy=(x_mid, 64), xytext=(x_mid, 69),
                    arrowprops=dict(arrowstyle="-|>", color=ev_color,
                                    lw=0.9, shrinkA=0, shrinkB=0))

    # ── Predictions band (bottom 30%) ─────────────────────────
    ax.text(2, 32, "PREDICTIONS", ha="left", va="top",
            fontsize=7.6, color=pr_color)
    n_pr = min(len(contract.predictions), 3)
    for i in range(n_pr):
        w = 100 / 3 - 2
        x0 = 2 + i * (w + 1.5)
        ax.add_patch(mpatches.FancyBboxPatch(
            (x0, 3), w, 18,
            boxstyle="round,pad=0.012,rounding_size=0.02",
            facecolor="white", edgecolor=pr_color, linewidth=0.8,
        ))
        ax.text(x0 + w / 2, 12, _wrap(contract.predictions[i], 24),
                ha="center", va="center", fontsize=6.4, color="#222222")
        x_mid = x0 + w / 2
        ax.annotate("", xy=(x_mid, 21), xytext=(x_mid, 36),
                    arrowprops=dict(arrowstyle="<|-", color=pr_color,
                                    lw=0.9, shrinkA=0, shrinkB=0))
    # Unused: add_halo_label — kept imported for API consistency.
    _ = add_halo_label
    return ax
