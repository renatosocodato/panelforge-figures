"""Interaction chord diagram — arcs on a ring with weighted chords between groups."""

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


class ChordInput(RecipeContract):
    group_names: list[str] = Field(..., min_length=2)
    interaction_matrix: list[list[float]] = Field(
        ..., description="square matrix of interaction counts (directed OK)"
    )
    title: str = "Interaction chord diagram"


def _demo() -> ChordInput:
    rng = np.random.default_rng(337)
    groups = ["neurons", "microglia", "astro", "oligo", "endothelial"]
    M = rng.integers(2, 30, (len(groups), len(groups)))
    np.fill_diagonal(M, 0)
    return ChordInput(
        group_names=groups,
        interaction_matrix=M.astype(float).tolist(),
    )


_META = RecipeMetadata(
    name="interaction_chord_diagram",
    modality="network_and_pathway",
    family=RecipeFamily.flow,
    answers_question="How many interactions occur between each pair of cell types or modules, arranged as chords on a ring?",
    required_fields=("group_names", "interaction_matrix"),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("regulatory_network_hive",),
)


@register_recipe(metadata=_META, contract=ChordInput, demo_contract=_demo)
def render(contract: ChordInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.4, 4.0))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    M = np.array(contract.interaction_matrix, dtype=float)
    n = len(contract.group_names)
    totals = M.sum(axis=1) + M.sum(axis=0)
    totals = np.maximum(totals, 1e-9)
    # Angular span per group ∝ total interactions.
    fracs = totals / totals.sum()
    angles = np.concatenate([[0], np.cumsum(fracs)]) * 2 * np.pi
    # Group color cycle.
    colors = [palette[i % len(palette.colors)] for i in range(n)]

    # Outer arcs.
    for gi in range(n):
        theta_lo = angles[gi]
        theta_hi = angles[gi + 1]
        theta = np.linspace(theta_lo, theta_hi, 60)
        r_out = 1.0
        r_in = 0.94
        ax.fill(
            np.concatenate([r_out * np.cos(theta),
                            r_in * np.cos(theta[::-1])]),
            np.concatenate([r_out * np.sin(theta),
                            r_in * np.sin(theta[::-1])]),
            color=colors[gi], alpha=0.88, zorder=4,
        )
        # Label.
        mid = 0.5 * (theta_lo + theta_hi)
        ax.text(1.14 * np.cos(mid), 1.14 * np.sin(mid),
                contract.group_names[gi],
                ha="center", va="center",
                rotation=np.degrees(mid) - (180 if np.cos(mid) < 0 else 0),
                fontsize=6.6, color=colors[gi])

    # Chord paths (straight lines with arc3 curvature).
    max_w = max(M.max(), 1e-9)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            w = M[i, j]
            if w <= 0:
                continue
            src_theta = 0.5 * (angles[i] + angles[i + 1])
            dst_theta = 0.5 * (angles[j] + angles[j + 1])
            x0 = 0.9 * np.cos(src_theta)
            y0 = 0.9 * np.sin(src_theta)
            x1 = 0.9 * np.cos(dst_theta)
            y1 = 0.9 * np.sin(dst_theta)
            ax.annotate(
                "", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(
                    arrowstyle="-",
                    color=colors[i],
                    alpha=0.28 + 0.4 * (w / max_w),
                    lw=0.5 + 1.3 * (w / max_w),
                    connectionstyle="arc3,rad=0.35",
                ),
                zorder=2,
            )

    ax.set_xlim(-1.35, 1.35)
    ax.set_ylim(-1.35, 1.35)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ("left", "bottom"):
        ax.spines[s].set_visible(False)
    ax.set_aspect("equal")
    ax.set_title(contract.title, fontsize=9.0, pad=4)

    ax.text(0.0, -1.3,
            f"total interactions = {int(M.sum())}   "
            f"max pair = {smart_fmt(float(M.max()))}",
            ha="center", va="center", fontsize=6.4, color="#444444",
            bbox=dict(boxstyle="round,pad=0.18", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92))
    return ax
