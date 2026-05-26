"""Edge enrichment gradient panel — distance-from-edge intensity profile."""

from __future__ import annotations

from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
)
from ._aesthetic import AESTHETIC


class EdgeGradientCurve(RecipeContract):
    label: str
    distance_um: list[float]
    intensity: list[float]
    intensity_ci_lo: list[float] | None = None
    intensity_ci_hi: list[float] | None = None


class EdgeGradientInput(RecipeContract):
    curves: list[EdgeGradientCurve]
    title: str = "Edge enrichment gradient (intensity vs distance from cell edge)"
    enrichment_band: tuple[float, float] | None = Field(
        default=(0.0, 1.0),
        description="Optional shaded band marking the edge-enrichment zone"
    )


def _demo() -> EdgeGradientInput:
    import math
    d = [0.1 * i for i in range(60)]
    return EdgeGradientInput(
        curves=[
            EdgeGradientCurve(label="WT actin", distance_um=d,
                              intensity=[1.0 + 0.6 * math.exp(-x / 0.8) for x in d]),
            EdgeGradientCurve(label="LI actin", distance_um=d,
                              intensity=[1.0 + 0.3 * math.exp(-x / 1.5) for x in d]),
            EdgeGradientCurve(label="WT MT", distance_um=d,
                              intensity=[1.0 + 0.2 * math.exp(-x / 0.6) for x in d]),
            EdgeGradientCurve(label="LI MT", distance_um=d,
                              intensity=[1.0 + 0.5 * math.exp(-x / 1.2) for x in d]),
        ],
    )


_META = RecipeMetadata(
    name="edge_enrichment_gradient_panel",
    modality="spatial_statistics",
    family=RecipeFamily.diagnostic_curve,
    answers_question="How does intensity vary with distance from the cell edge?",
    required_fields=("curves",),
    optional_fields=("title", "enrichment_band"),
    file_format_hints=("csv", "json"),
)


_PALETTE = ["#1f6f8b", "#c0392b", "#5b8aa4", "#e58e7d"]


@register_recipe(metadata=_META, contract=EdgeGradientInput, demo_contract=_demo)
def render(contract: EdgeGradientInput, ax=None, **_):
    import matplotlib.pyplot as plt

    if ax is None:
        _, ax = plt.subplots(figsize=(7.5, 5.0))
    AESTHETIC.apply_to_ax(ax)

    if contract.enrichment_band:
        ax.axvspan(contract.enrichment_band[0], contract.enrichment_band[1],
                   color="#fff3e0", alpha=0.6, zorder=0,
                   label="edge enrichment band")

    for i, c in enumerate(contract.curves):
        color = _PALETTE[i % len(_PALETTE)]
        ax.plot(c.distance_um, c.intensity, lw=1.5, color=color, label=c.label, zorder=2)
        if c.intensity_ci_lo and c.intensity_ci_hi:
            ax.fill_between(c.distance_um, c.intensity_ci_lo, c.intensity_ci_hi,
                            color=color, alpha=0.15, edgecolor="none", zorder=1)

    ax.axhline(1.0, color="#888", ls=":", lw=1.0, zorder=1)
    ax.set_xlabel("distance from cell edge (μm)")
    ax.set_ylabel("relative intensity")
    ax.set_title(contract.title, fontsize=9.6, color="#2c3e50", pad=6)
    ax.legend(fontsize=9.0, frameon=False, loc="upper right")
    ax.spines[["top", "right"]].set_visible(False)
    return ax
