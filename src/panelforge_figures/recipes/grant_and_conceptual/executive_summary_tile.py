"""Executive summary tile — one-glance "why this project matters".

Left half: headline metric + label.
Right half: 3 short payoff bullets + a small cumulative-impact spark line.

Redesigned for robust rendering at any axis aspect (2.5×2.5 gallery thumb
through 6×4 figure panel). All positions are in axes coordinates (0..1) and
every text size is picked to fit the gallery preview.
"""

from __future__ import annotations

import matplotlib.patches as mpatches
import numpy as np
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


class ExecutiveSummaryInput(RecipeContract):
    headline_value: str = Field(..., description="Big number/metric (e.g. '40%', '3×')")
    headline_label: str = Field(...)
    payoffs: list[str] = Field(..., min_length=1, max_length=4)
    impact_xy: tuple[list[float], list[float]] = Field(
        default_factory=lambda: ([0, 1, 2, 3], [0, 0, 0, 0])
    )
    color_key: str = "signaling"


def _demo() -> ExecutiveSummaryInput:
    return ExecutiveSummaryInput(
        headline_value="3.2×",
        headline_label="acceleration\nof discovery",
        payoffs=[
            "Reproducible figures via manifest",
            "Recipes map 1:1 to claims",
            "Embedded repo-survey skill",
        ],
        impact_xy=(list(range(2026, 2030)), [2, 6, 14, 28]),
        color_key="cytoskeletal",
    )


_META = RecipeMetadata(
    name="executive_summary_tile",
    modality="grant_and_conceptual",
    family=RecipeFamily.conceptual,
    answers_question="At a glance, what is the headline impact and how is it structured?",
    required_fields=("headline_value", "headline_label", "payoffs"),
    optional_fields=("impact_xy", "color_key"),
    file_format_hints=("yaml", "toml", "dict"),
    alternatives_in_modality=("conceptual_triptych", "hypothesis_diagram"),
    example_manifest="skill/example_manifests/fct_grant.yaml",
)


@register_recipe(metadata=_META, contract=ExecutiveSummaryInput, demo_contract=_demo)
def render(contract: ExecutiveSummaryInput, ax=None, **_):
    """Render a left-right executive-summary tile into `ax`."""
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.2))
    AESTHETIC.apply_to_ax(ax)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ("left", "bottom"):
        ax.spines[s].set_visible(False)

    palette = get_palette(AESTHETIC.primary_palette)
    accent = (
        palette.pick(contract.color_key)
        if contract.color_key in palette.semantic
        else palette[0]
    )

    # Left half: accent block + big headline number + label.
    ax.add_patch(mpatches.FancyBboxPatch(
        (2, 6), 38, 88,
        boxstyle="round,pad=0.01,rounding_size=0.02",
        facecolor=accent, alpha=0.93, edgecolor="white", linewidth=1.4,
    ))
    add_halo_label(
        ax, 21, 70, contract.headline_value,
        fontsize=26, fontweight="bold", color="white",
        halo_color=accent, halo_width=1.5,
    )
    ax.text(21, 42, contract.headline_label, ha="center", va="center",
            color="white", fontsize=8.2, fontweight="bold")
    ax.text(21, 15, "HEADLINE", ha="center", va="center",
            color="white", alpha=0.7, fontsize=6.8, fontweight="bold")

    # Right half: payoff bullets.
    n_bullets = min(len(contract.payoffs), 3)
    y_top = 90
    y_step = 12
    for i, text in enumerate(contract.payoffs[:n_bullets]):
        y = y_top - i * y_step
        ax.add_patch(mpatches.Circle((47, y), 1.6, color=accent, zorder=3))
        ax.text(51, y, text, ha="left", va="center",
                fontsize=7.6, color="#222222")

    # Right-bottom: mini impact sparkline.
    xs, ys = contract.impact_xy
    if xs and ys:
        xs = np.asarray(xs, float)
        ys = np.asarray(ys, float)
        # Map to a box: x in [46, 96], y in [10, 42].
        x_span = float(xs.max() - xs.min())
        y_span = float(ys.max() - ys.min())
        x_px = 46 + (xs - xs.min()) / max(x_span, 1.0) * 50
        y_px = 12 + (ys - ys.min()) / max(y_span, 1.0) * 28
        ax.plot(x_px, y_px, color=accent, lw=2.0, marker="o", ms=4.2,
                markerfacecolor="white", markeredgecolor=accent,
                markeredgewidth=1.2, zorder=4)
        ax.text(46, 46, "Cumulative impact",
                fontsize=7.2, color="#444444", fontweight="bold")
        # Year labels only at endpoints to avoid overlap.
        for xi, lab in [(x_px[0], int(xs[0])), (x_px[-1], int(xs[-1]))]:
            ax.text(xi, 7, str(lab), ha="center", va="top",
                    fontsize=6.4, color="#666666")

    return ax
