"""Migration rose diagram — circular histogram of cell migration headings."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class MigrationRoseInput(RecipeContract):
    heading_deg_by_condition: dict[str, list[float]] = Field(
        ..., description="condition → list of heading angles (deg, 0..360)",
    )
    n_bins: int = 24
    title: str = "Migration heading distribution"


def _demo() -> MigrationRoseInput:
    rng = np.random.default_rng(471)
    # Control: roughly uniform.
    ctrl = (rng.uniform(0, 360, 400) + rng.normal(0, 20, 400)) % 360
    # Chemokine: biased toward 90°.
    bias = np.concatenate([
        rng.normal(90, 22, 260) % 360,
        rng.uniform(0, 360, 80),
    ])
    return MigrationRoseInput(
        heading_deg_by_condition={
            "control": ctrl.tolist(),
            "+ chemokine": bias.tolist(),
        },
    )


_META = RecipeMetadata(
    name="migration_rose_diagram",
    modality="intravital_imaging",
    family=RecipeFamily.radar,
    answers_question="Do cells migrate in a directed way under a chemotactic cue, or are their headings uniformly distributed?",
    required_fields=("heading_deg_by_condition",),
    optional_fields=("n_bins", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("cell_track_trajectory_field",),
)


@register_recipe(metadata=_META, contract=MigrationRoseInput, demo_contract=_demo)
def render(contract: MigrationRoseInput, ax=None, **_):
    import matplotlib.pyplot as plt

    if ax is None:
        fig = plt.figure(figsize=(4.6, 3.6))
        ax = fig.add_subplot(111, polar=True)
    elif not hasattr(ax, "set_theta_offset"):
        fig = ax.figure
        pos = ax.get_subplotspec()
        ax.remove()
        ax = fig.add_subplot(pos, polar=True)

    AESTHETIC.apply_to_fig(ax.figure)
    palette = get_palette(AESTHETIC.primary_palette)

    ax.set_theta_zero_location("E")
    ax.set_theta_direction(-1)
    ax.set_xticks(np.linspace(0, 2 * np.pi, 8, endpoint=False))
    ax.set_xticklabels(["E", "NE", "N", "NW", "W", "SW", "S", "SE"],
                       fontsize=6.8)

    n_bins = contract.n_bins
    edges = np.linspace(0, 2 * np.pi, n_bins + 1)
    centers = 0.5 * (edges[:-1] + edges[1:])
    width = edges[1] - edges[0]

    summaries: list[tuple[str, float, float]] = []
    for i, (name, headings) in enumerate(contract.heading_deg_by_condition.items()):
        h = (np.deg2rad(np.array(headings, dtype=float)) % (2 * np.pi))
        counts, _ = np.histogram(h, bins=edges)
        density = counts / max(counts.sum(), 1)
        color = palette[i % len(palette.colors)]
        ax.bar(centers, density, width=width,
               color=color, alpha=0.55, edgecolor="white", linewidth=0.5,
               zorder=3, label=name)
        # Mean resultant length (R) as a directional summary.
        R = np.abs(np.mean(np.exp(1j * h))) if h.size else 0.0
        mean_theta = np.angle(np.mean(np.exp(1j * h))) if h.size else 0.0
        summaries.append((name, R, mean_theta))
        if h.size:
            ax.plot([mean_theta, mean_theta], [0, density.max() * 1.1],
                    color=color, lw=1.3, zorder=5)

    ax.set_yticklabels([])
    ax.set_title(contract.title, fontsize=9.0, pad=14)

    summary_lines = [
        f"{name}: R={smart_fmt(float(r))} at {np.rad2deg(mt):.0f}°"
        for name, r, mt in summaries
    ]
    ax.figure.text(
        0.5, 0.01, "   ".join(summary_lines),
        ha="center", va="bottom", fontsize=6.2, color="#333333",
    )
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12),
              fontsize=6.6, ncol=len(contract.heading_deg_by_condition),
              frameon=False, handlelength=1.2)
    return ax
