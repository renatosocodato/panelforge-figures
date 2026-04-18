"""Executive summary tile — one-glance "why this project matters".

Left column: headline metric block (accent color, big number + label).
Right column (two rows):
  - Top row: up to three icon bullets (short payoffs).
  - Bottom row: small cumulative-impact spark line with endpoint year labels.

Positions are in axis-local coords (0..100 in both dimensions), so the tile
renders consistently at any host figure size — from a 2.5×2.5 gallery
thumbnail to a 6×4 manuscript panel.
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
        headline_label="acceleration of\ndiscovery cycle",
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
    """Render the executive-summary tile into `ax`."""
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 3.2))
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

    # ── LEFT: headline block (full height). ──────────────────────────
    ax.add_patch(mpatches.FancyBboxPatch(
        (2, 4), 40, 92,
        boxstyle="round,pad=0.01,rounding_size=0.02",
        facecolor=accent, alpha=0.93, edgecolor="white", linewidth=1.4,
    ))
    add_halo_label(
        ax, 22, 66, contract.headline_value,
        fontsize=26, fontweight="bold", color="white",
        halo_color=accent, halo_width=1.5,
    )
    ax.text(22, 40, contract.headline_label, ha="center", va="center",
            color="white", fontsize=8.4, fontweight="bold")
    ax.text(22, 14, "HEADLINE", ha="center", va="center",
            color="white", alpha=0.7, fontsize=7.0, fontweight="bold")

    # ── RIGHT TOP: payoff bullets (upper 55%). ───────────────────────
    n_bullets = min(len(contract.payoffs), 3)
    bullet_band_y0 = 56                                # bottom of payoff block
    bullet_band_y1 = 90                                # top of payoff block
    if n_bullets == 1:
        ys = [0.5 * (bullet_band_y0 + bullet_band_y1)]
    else:
        ys = np.linspace(bullet_band_y1 - 4, bullet_band_y0 + 2, n_bullets).tolist()
    ax.text(46, 96, "KEY PAYOFFS", ha="left", va="top",
            color=accent, fontsize=6.8, fontweight="bold", alpha=0.85)
    for i, text in enumerate(contract.payoffs[:n_bullets]):
        y = ys[i]
        ax.add_patch(mpatches.Circle((49, y), 1.5, color=accent, zorder=3))
        ax.text(53, y, text, ha="left", va="center",
                fontsize=7.6, color="#222222")

    # ── RIGHT BOTTOM: cumulative-impact spark line (lower 40%). ──────
    xs, ys_data = contract.impact_xy
    if xs and ys_data:
        xs = np.asarray(xs, float)
        ys_data = np.asarray(ys_data, float)
        x_span = float(xs.max() - xs.min()) or 1.0
        y_span = float(ys_data.max() - ys_data.min()) or 1.0
        # Map to the right-bottom panel: x ∈ [48, 96], y ∈ [12, 38].
        x_px = 48 + (xs - xs.min()) / x_span * 48
        y_px = 12 + (ys_data - ys_data.min()) / y_span * 26
        ax.text(46, 50, "CUMULATIVE IMPACT",
                color=accent, fontsize=6.8, fontweight="bold", alpha=0.85)
        ax.plot(x_px, y_px, color=accent, lw=2.0, marker="o", ms=4.4,
                markerfacecolor="white", markeredgecolor=accent,
                markeredgewidth=1.2, zorder=4)
        for xi, lab in [(x_px[0], int(xs[0])), (x_px[-1], int(xs[-1]))]:
            ax.text(xi, 7, str(lab), ha="center", va="top",
                    fontsize=6.6, color="#666666")
        ax.text(x_px[-1], y_px[-1] + 3, f"{int(ys_data[-1])}",
                ha="center", va="bottom",
                fontsize=7.2, color=accent, fontweight="bold")

    return ax
