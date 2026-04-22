"""Track-directionality polar histogram — angular distribution of
per-track mean direction, with uniform-reference overlay and Rayleigh
test r statistic.

Radar family — one polar axis, at least one filled polygon.
"""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class TrackPolarInput(RecipeContract):
    angles_rad: list[float] = Field(
        ..., min_length=10,
        description="per-track mean direction (radians, [-π, π] or [0, 2π])",
    )
    n_bins: int = Field(24, description="number of angular bins")
    title: str = "Track directionality"


def _demo() -> TrackPolarInput:
    rng = np.random.default_rng(2213)
    # Biased towards +x (angle ≈ 0) but with isotropic background.
    n = 400
    biased = rng.vonmises(0.0, 1.5, n * 3 // 5)
    uniform = rng.uniform(-np.pi, np.pi, n - len(biased))
    angles = np.concatenate([biased, uniform])
    return TrackPolarInput(
        angles_rad=angles.tolist(),
        n_bins=28,
    )


_META = RecipeMetadata(
    name="track_directionality_polar",
    modality="diffusion_and_tracking",
    family=RecipeFamily.radar,
    answers_question=(
        "Is motion isotropic, or is there a preferred direction of "
        "travel across all tracks in the field?"
    ),
    required_fields=("angles_rad",),
    optional_fields=("n_bins", "title"),
    file_format_hints=("csv",),
    alternatives_in_modality=("angle_correlation_decay",),
)


@register_recipe(
    metadata=_META,
    contract=TrackPolarInput,
    demo_contract=_demo,
)
def render(contract: TrackPolarInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        fig = plt.figure(figsize=(4.8, 4.2))
        ax = fig.add_subplot(111, projection="polar")
    elif getattr(ax, "name", "") != "polar":
        # The caller handed us a rectangular axes; replace with polar.
        fig = ax.figure
        pos = ax.get_position()
        fig.delaxes(ax)
        ax = fig.add_subplot(111, projection="polar")
        ax.set_position(pos)
    _ = AESTHETIC.apply_to_ax

    angles = np.asarray(contract.angles_rad, float)
    # Wrap to [0, 2π).
    angles = np.mod(angles, 2 * np.pi)
    n_bins = int(contract.n_bins)
    counts, edges = np.histogram(angles, bins=n_bins, range=(0, 2 * np.pi))
    widths = np.diff(edges)
    centres = 0.5 * (edges[:-1] + edges[1:])

    # Normalise counts to density.
    density = counts / (counts.sum() * widths)
    # Uniform reference.
    uniform = np.full_like(density, 1.0 / (2 * np.pi))

    # Bars.
    ax.bar(centres, density, width=widths, bottom=0.0,
           color="#1565C0", edgecolor="white", linewidth=0.4,
           alpha=0.8, zorder=3)
    # Uniform reference ring (as a filled thin annulus).
    ring = np.linspace(0, 2 * np.pi, 361)
    ax.fill_between(ring, 0, uniform[0],
                    color="#888888", alpha=0.15, linewidth=0, zorder=2)
    ax.plot(ring, np.full_like(ring, uniform[0]),
            color="#222222", lw=0.6, ls="--", zorder=4,
            label="isotropic")

    # Resultant vector & Rayleigh r.
    R_x = float(np.mean(np.cos(angles)))
    R_y = float(np.mean(np.sin(angles)))
    R = float(np.sqrt(R_x ** 2 + R_y ** 2))
    theta_bar = float(np.arctan2(R_y, R_x)) % (2 * np.pi)
    r_peak = float(density.max()) * 0.95
    ax.plot([theta_bar, theta_bar], [0, r_peak], color="#C62828",
            lw=1.2, zorder=5)
    ax.scatter([theta_bar], [r_peak], s=22, color="#C62828",
               edgecolor="white", linewidth=0.5, zorder=6,
               label="mean dir")

    ax.set_theta_zero_location("E")
    ax.set_theta_direction(1)
    ax.set_rticks([])
    ax.set_xticks(np.linspace(0, 2 * np.pi, 8, endpoint=False))
    ax.set_xticklabels([r"0°", r"45°", r"90°", r"135°",
                        r"180°", r"225°", r"270°", r"315°"],
                       fontsize=7.0)
    ax.grid(True, color="#E0E0E0", lw=0.4, zorder=0)
    ax.set_title(contract.title, fontsize=9.0, pad=10)

    # Callout.
    callout_deg = np.degrees(theta_bar)
    ax.figure.text(0.02, 0.02,
                   f"N = {len(angles)}   Rayleigh r = {smart_fmt(R)}   "
                   f"mean dir ≈ {smart_fmt(callout_deg)}°",
                   ha="left", va="bottom", fontsize=6.6, color="#333333",
                   bbox=dict(boxstyle="round,pad=0.22", fc="white",
                             ec="#BBBBBB", lw=0.5, alpha=0.92),
                   zorder=6)

    ax.legend(fontsize=6.8, frameon=False, loc="upper right",
              bbox_to_anchor=(1.24, 1.06),
              handlelength=1.2)
    return ax
