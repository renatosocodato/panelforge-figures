"""Filament orientation — polar histogram (rose) of filament angles."""

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


class OrientationInput(RecipeContract):
    angles_deg_by_component: dict[str, list[float]] = Field(
        ..., description="component → list of filament orientation angles (deg, 0-180)"
    )
    title: str = "Filament orientations"


def _demo() -> OrientationInput:
    rng = np.random.default_rng(483)
    actin = np.concatenate([rng.normal(60, 16, 280),
                            rng.normal(120, 18, 220)]) % 180
    mt = np.concatenate([rng.normal(0, 14, 260),
                         rng.normal(90, 12, 120)]) % 180
    return OrientationInput(
        angles_deg_by_component={
            "actin": actin.tolist(),
            "microtubule": mt.tolist(),
        },
    )


_META = RecipeMetadata(
    name="filament_orientation_histogram",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.radar,
    answers_question="How are filament orientations distributed for actin vs. microtubules in a region of interest?",
    required_fields=("angles_deg_by_component",),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("fiber_anisotropy_wedges",),
)


@register_recipe(metadata=_META, contract=OrientationInput, demo_contract=_demo)
def render(contract: OrientationInput, ax=None, **_):
    import matplotlib.pyplot as plt

    if ax is None:
        fig = plt.figure(figsize=(4.8, 3.6))
        ax = fig.add_subplot(111, polar=True)
    elif not hasattr(ax, "set_theta_offset"):
        fig = ax.figure
        pos = ax.get_subplotspec()
        ax.remove()
        ax = fig.add_subplot(pos, polar=True)

    AESTHETIC.apply_to_fig(ax.figure)
    palette = get_palette(AESTHETIC.primary_palette)

    # 0-180° is the physical range (filaments are undirected); we mirror it.
    ax.set_theta_zero_location("E")
    ax.set_theta_direction(1)

    n_bins = 36
    edges = np.linspace(0, np.pi, n_bins + 1)  # only half-circle physical
    centers = 0.5 * (edges[:-1] + edges[1:])
    width = edges[1] - edges[0]

    max_density = 0.0
    for i, (name, angles) in enumerate(contract.angles_deg_by_component.items()):
        a = np.deg2rad(np.mod(np.array(angles, dtype=float), 180))
        counts, _ = np.histogram(a, bins=edges)
        density = counts / max(counts.sum(), 1)
        max_density = max(max_density, density.max())
        color = (palette.pick(name) if name in palette.semantic
                 else palette[i % len(palette.colors)])
        # Draw twice: 0-180° and 180-360° (mirror) so the rose reads
        # as undirected orientations.
        ax.bar(centers, density, width=width,
               color=color, alpha=0.55, edgecolor="white", linewidth=0.5,
               zorder=3, label=name)
        ax.bar(centers + np.pi, density, width=width,
               color=color, alpha=0.55, edgecolor="white", linewidth=0.5,
               zorder=3)
        # Outline curve for readability + to satisfy the radar quality rule.
        angular = np.concatenate([centers, centers + np.pi, centers[:1]])
        radial = np.concatenate([density, density, density[:1]])
        ax.plot(angular, radial, color=color, lw=0.9, alpha=0.75, zorder=4)

    # Angle ticks at 0/45/90/135.
    ax.set_xticks(np.linspace(0, 2 * np.pi, 8, endpoint=False))
    ax.set_xticklabels(["0°", "45°", "90°", "135°", "180°", "225°", "270°", "315°"],
                       fontsize=6.4)
    ax.set_yticklabels([])

    # Anisotropy / order summary (via 2nd moment).
    summary_parts = []
    for name, angles in contract.angles_deg_by_component.items():
        a = np.deg2rad(np.mod(np.array(angles, dtype=float), 180))
        if a.size == 0:
            continue
        # Order parameter: S = <cos(2θ)>² + <sin(2θ)>².
        S = np.sqrt(np.mean(np.cos(2 * a)) ** 2 + np.mean(np.sin(2 * a)) ** 2)
        summary_parts.append(f"{name}: S={smart_fmt(float(S))}")
    ax.figure.text(
        0.5, 0.01, "   ".join(summary_parts),
        ha="center", va="bottom", fontsize=6.2, color="#333333",
    )

    ax.set_title(contract.title, fontsize=9.0, pad=14)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.10),
              fontsize=6.6, ncol=len(contract.angles_deg_by_component),
              frameon=False, handlelength=1.2)
    return ax
