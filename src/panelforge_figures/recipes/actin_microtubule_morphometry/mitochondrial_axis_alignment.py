"""Mitochondrial axis alignment — polar rose of Δ-angles vs filament axis."""

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


class MitoAxisAlignmentInput(RecipeContract):
    delta_angle_deg: list[float] = Field(
        ..., description="Δ-angle (deg) between mito long-axis and filament axis"
    )
    condition: list[str] | None = None
    title: str = "Mitochondrial axis alignment"


def _demo() -> MitoAxisAlignmentInput:
    rng = np.random.default_rng(737)
    # Control aligned (tight around 0), mutant broad (near-uniform).
    ctrl = (rng.normal(0.0, 15.0, 320)) % 180.0
    mut = (rng.uniform(0.0, 180.0, 300) + rng.normal(0, 5.0, 300)) % 180.0
    delta = np.concatenate([ctrl, mut])
    cond = ["control"] * 320 + ["mutant"] * 300
    return MitoAxisAlignmentInput(
        delta_angle_deg=delta.tolist(),
        condition=cond,
    )


_META = RecipeMetadata(
    name="mitochondrial_axis_alignment",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.radar,
    answers_question=(
        "Do mitochondria orient their long axis along the cytoskeletal axis "
        "of the cell, and by how much?"
    ),
    required_fields=("delta_angle_deg",),
    optional_fields=("condition", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("filament_orientation_histogram",),
)


@register_recipe(
    metadata=_META,
    contract=MitoAxisAlignmentInput,
    demo_contract=_demo,
)
def render(contract: MitoAxisAlignmentInput, ax=None, **_):
    import matplotlib.pyplot as plt

    if ax is None:
        fig = plt.figure(figsize=(4.8, 3.8))
        ax = fig.add_subplot(111, polar=True)
    elif not hasattr(ax, "set_theta_offset"):
        fig = ax.figure
        pos = ax.get_subplotspec()
        ax.remove()
        ax = fig.add_subplot(pos, polar=True)
    AESTHETIC.apply_to_fig(ax.figure)
    palette = get_palette(AESTHETIC.primary_palette)

    delta = np.asarray(contract.delta_angle_deg, float) % 180.0
    cond = (np.asarray(contract.condition)
            if contract.condition is not None
            else np.array(["all"] * delta.size))
    uniques = list(dict.fromkeys(cond.tolist()))

    ax.set_theta_zero_location("E")
    ax.set_theta_direction(1)

    n_bins = 36
    edges = np.linspace(0, np.pi, n_bins + 1)   # 0-180° physical
    centers = 0.5 * (edges[:-1] + edges[1:])
    width = edges[1] - edges[0]

    # Draw bars mirrored over 0-360° so the undirected-axis nature reads.
    for i, name in enumerate(uniques):
        m = cond == name
        a = np.deg2rad(delta[m])
        counts, _ = np.histogram(a, bins=edges)
        density = counts / max(counts.sum(), 1)
        color = palette[i % len(palette.colors)]
        ax.bar(centers, density, width=width,
               color=color, alpha=0.55, edgecolor="white", linewidth=0.5,
               zorder=3, label=f"{name} (n={int(m.sum())})")
        ax.bar(centers + np.pi, density, width=width,
               color=color, alpha=0.55, edgecolor="white", linewidth=0.5,
               zorder=3)
        # Outline ring for each condition.
        angular = np.concatenate([centers, centers + np.pi, centers[:1]])
        radial = np.concatenate([density, density, density[:1]])
        ax.plot(angular, radial, color=color, lw=0.9, alpha=0.75, zorder=4)

    # Reference 0° spoke — perfect alignment.
    r_max = ax.get_ylim()[1]
    ax.plot([0, 0], [0, r_max], color="#111111", lw=0.8, ls="--", zorder=5)
    ax.plot([np.pi, np.pi], [0, r_max], color="#111111", lw=0.8, ls="--", zorder=5)

    # Angular-tick display only 0/45/90/135 (since distribution is on 0-180°).
    ax.set_xticks(np.deg2rad([0, 45, 90, 135, 180, 225, 270, 315]))
    ax.set_xticklabels(["0°", "45°", "90°", "135°", "180°", "225°", "270°", "315°"],
                       fontsize=6.4)
    ax.set_yticklabels([])

    # Summary: order parameter S per condition on [0, 1].
    summary_parts = []
    for name in uniques:
        m = cond == name
        a = np.deg2rad(delta[m])
        if a.size == 0:
            continue
        S = np.sqrt(np.mean(np.cos(2 * a)) ** 2 + np.mean(np.sin(2 * a)) ** 2)
        summary_parts.append(f"{name}: S = {smart_fmt(float(S))}")
    ax.figure.text(
        0.5, 0.01, "  ·  ".join(summary_parts),
        ha="center", va="bottom", fontsize=6.2, color="#333333",
    )

    ax.set_title(contract.title, fontsize=9.0, pad=14)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.10),
              fontsize=6.6, ncol=len(uniques),
              frameon=False, handlelength=1.2)
    return ax
