"""Conceptual triptych — three linked panels (problem → approach → payoff)."""

from __future__ import annotations

import textwrap

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


class TriptychPanel(RecipeContract):
    label: str
    headline: str
    details: list[str] = Field(default_factory=list, max_length=3)
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
            headline="Microglia heterogeneity\nunder-described",
            details=[
                "Bulk hides mixtures",
                "No in-vivo single-cell",
                "Sex × age co-ignored",
            ],
            color_key="signaling",
        ),
        middle=TriptychPanel(
            label="Approach",
            headline="Modality-first\nbiophysical pipeline",
            details=[
                "FRET + 2P intravital",
                "Tristable ODE + SSA",
                "Sex-stratified models",
            ],
            color_key="metabolic",
        ),
        right=TriptychPanel(
            label="Payoff",
            headline="Mechanistic +\ntranslatable",
            details=[
                "Shareable manifests",
                "Collapsible GATE",
                "Patient biomarker",
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
        _, ax = plt.subplots(figsize=(7.2, 3.2))
    AESTHETIC.apply_to_ax(ax)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ("left", "bottom"):
        ax.spines[s].set_visible(False)
    palette = get_palette(AESTHETIC.primary_palette)

    panel_w = 29
    panels = [
        (contract.left, 2),
        (contract.middle, 2 + panel_w + 4),
        (contract.right, 2 + 2 * (panel_w + 4)),
    ]
    # Character widths chosen to fit ~29% panel width at gallery render.
    headline_wrap = 16
    detail_wrap = 18

    def _wrap(text: str, width: int) -> str:
        """Wrap each user-supplied line independently."""
        lines: list[str] = []
        for raw in text.split("\n"):
            lines.extend(textwrap.wrap(raw, width=width) or [""])
        return "\n".join(lines)
    for panel, x0 in panels:
        color = (
            palette.pick(panel.color_key)
            if panel.color_key in palette.semantic
            else palette[0]
        )
        ax.add_patch(mpatches.FancyBboxPatch(
            (x0, 8), panel_w, 84,
            boxstyle="round,pad=0.012,rounding_size=0.025",
            facecolor=color, edgecolor="white", linewidth=1.3, alpha=0.94,
        ))
        # Label strip (top ~10% of the panel).
        ax.text(x0 + panel_w / 2, 88, panel.label,
                ha="center", va="top", color="white",
                fontsize=7.0, fontweight="bold", alpha=0.8)
        ax.text(x0 + panel_w / 2, 76, _wrap(panel.headline, headline_wrap),
                ha="center", va="top", color="white",
                fontsize=7.6, fontweight="bold")
        # Details — three bullets, wrapped per line.
        for i, d in enumerate(panel.details[:3]):
            wrapped = _wrap(d, detail_wrap).replace("\n", "\n  ")
            ax.text(x0 + 2, 52 - i * 11, f"• {wrapped}",
                    ha="left", va="top", color="white",
                    fontsize=6.4, alpha=0.94)

    # Arrows between panels with halo'd labels above.
    gap_centers = [
        (2 + panel_w, 2 + panel_w + 4),
        (2 + panel_w + 4 + panel_w, 2 + panel_w + 4 + panel_w + 4),
    ]
    for (x0, x1), label in zip(gap_centers, contract.arrow_labels):
        ax.annotate(
            "",
            xy=(x1, 50),
            xytext=(x0, 50),
            arrowprops=dict(arrowstyle="-|>", color="#555555", lw=1.4,
                            shrinkA=2, shrinkB=2),
            zorder=3,
        )
        ax.text((x0 + x1) / 2, 56, label,
                ha="center", va="bottom", color="#333333",
                fontsize=6.8, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.15", fc="white",
                          ec="none", alpha=0.92))
    return ax
