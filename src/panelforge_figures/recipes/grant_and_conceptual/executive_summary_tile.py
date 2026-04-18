"""Executive summary tile — one-glance "why this project matters".

A compact 2×2 tile laying out:
  - top-left:  headline metric or goal (big number + label)
  - top-right: 3 bullet payoffs (icons + short text)
  - bottom-left: mini horizontal-bar of core outputs by category
  - bottom-right: timeline-of-impact mini plot (cumulative outputs over time)

Used on the first page of grant applications and proposal decks. Family is
`conceptual`; the quality gate only checks that the axis contains at least
one text artist per region plus one bar/line — not geometric invariants.
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
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class ExecutiveSummaryInput(RecipeContract):
    headline_value: str = Field(..., description="Big number/metric (e.g. '40%', '3×')")
    headline_label: str = Field(...)
    payoffs: list[str] = Field(..., min_length=1, max_length=5)
    category_bars: dict[str, float] = Field(default_factory=dict)
    impact_xy: tuple[list[float], list[float]] = Field(
        default_factory=lambda: ([0, 1, 2, 3], [0, 0, 0, 0])
    )
    color_key: str = "signaling"          # semantic key into mechanism_class


def _demo() -> ExecutiveSummaryInput:
    return ExecutiveSummaryInput(
        headline_value="3.2×",
        headline_label="predicted acceleration\nof discovery cycle",
        payoffs=[
            "Reproducible figures from a declarative manifest",
            "Modality-first recipes map 1:1 to scientific claims",
            "Embedded skill surveys any manuscript repo cold",
        ],
        category_bars={"Figures/yr": 18, "Pipelines": 9, "Datasets": 14, "Manuscripts": 5},
        impact_xy=(list(range(2026, 2030)), [2, 6, 14, 28]),
        color_key="signaling",
    )


_META = RecipeMetadata(
    name="executive_summary_tile",
    modality="grant_and_conceptual",
    family=RecipeFamily.conceptual,
    answers_question="At a glance, what is the headline impact and how is it structured?",
    required_fields=("headline_value", "headline_label", "payoffs"),
    optional_fields=("category_bars", "impact_xy", "color_key"),
    file_format_hints=("yaml", "toml", "dict"),
    alternatives_in_modality=("conceptual_triptych", "hypothesis_diagram"),
    example_manifest="skill/example_manifests/fct_grant.yaml",
)


@register_recipe(metadata=_META, contract=ExecutiveSummaryInput, demo_contract=_demo)
def render(contract: ExecutiveSummaryInput, ax=None, **_):
    """Render a 2×2 executive-summary tile into `ax`."""
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.6))
    AESTHETIC.apply_to_ax(ax)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ("left", "bottom"):
        ax.spines[s].set_visible(False)

    palette = get_palette(AESTHETIC.primary_palette)
    accent = palette.pick(contract.color_key) if contract.color_key in palette.semantic else palette[0]

    # Four quadrant backgrounds (faint).
    for (x0, y0, w, h, alpha) in [
        (0, 52, 48, 46, 0.06),
        (52, 52, 46, 46, 0.04),
        (0, 0, 48, 48, 0.04),
        (52, 0, 46, 48, 0.06),
    ]:
        ax.add_patch(mpatches.Rectangle((x0, y0), w, h, facecolor=accent, alpha=alpha,
                                        edgecolor="none"))

    # (1) Headline value + label.
    add_halo_label(
        ax, 24, 82, contract.headline_value,
        fontsize=28, fontweight="bold", color=accent, halo_width=3.5,
    )
    ax.text(24, 62, contract.headline_label, ha="center", va="top",
            fontsize=8.6, color="#222222")

    # (2) Payoff bullets (top-right).
    for i, text in enumerate(contract.payoffs[:4]):
        y = 92 - i * 10
        ax.add_patch(mpatches.Circle((56, y), 1.1, color=accent, zorder=3))
        ax.text(59, y, text, ha="left", va="center", fontsize=8.0, color="#222222")

    # (3) Category bars (bottom-left).
    if contract.category_bars:
        keys = list(contract.category_bars.keys())
        vals = np.array([contract.category_bars[k] for k in keys], dtype=float)
        norm = vals / vals.max() if vals.max() > 0 else vals
        for i, (k, v, n) in enumerate(zip(keys, vals, norm)):
            y = 38 - i * 9
            ax.add_patch(mpatches.Rectangle((8, y - 2.4), 28 * n, 4.8,
                                             facecolor=accent, alpha=0.75, edgecolor="none"))
            ax.text(7, y, k, ha="right", va="center", fontsize=7.5, color="#333333")
            ax.text(8 + 28 * n + 1.0, y, smart_fmt(v), ha="left", va="center",
                    fontsize=7.2, color="#333333", fontweight="bold")

    # (4) Impact timeline (bottom-right).
    xs, ys = contract.impact_xy
    if xs and ys:
        xs = np.asarray(xs, float)
        ys = np.asarray(ys, float)
        x_span = float(xs.max() - xs.min())
        x_px = 56 + (xs - xs.min()) / max(x_span, 1.0) * 40
        y_px = 6 + (ys / max(ys.max(), 1)) * 36
        ax.plot(x_px, y_px, color=accent, lw=2.1, marker="o", ms=4,
                markerfacecolor="white", markeredgecolor=accent, markeredgewidth=1.2)
        ax.text(56, 44, "Cumulative impact", fontsize=7.2, color="#444444", fontweight="bold")
        for xi, yi, lab in zip(x_px, y_px, xs.astype(int)):
            ax.text(xi, 4, str(lab), ha="center", va="top", fontsize=6.6, color="#666666")

    return ax
