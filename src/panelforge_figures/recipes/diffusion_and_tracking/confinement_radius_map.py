"""Confinement-radius map — per-track radius-of-gyration pooled across field."""

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


class ConfinementMapInput(RecipeContract):
    track_centers_um: list[tuple[float, float]] = Field(...)
    radius_of_gyration_um: list[float] = Field(...)
    field_size_um: tuple[float, float] = (100.0, 80.0)
    title: str = "Track confinement"


def _demo() -> ConfinementMapInput:
    rng = np.random.default_rng(379)
    n = 120
    centers = list(zip(rng.uniform(5, 95, n), rng.uniform(5, 75, n)))
    # Mixture: confined (small R_g) and free (large R_g).
    rg = np.concatenate([
        rng.lognormal(np.log(0.4), 0.4, n // 2),
        rng.lognormal(np.log(2.0), 0.4, n - n // 2),
    ])
    rng.shuffle(rg)
    return ConfinementMapInput(
        track_centers_um=centers,
        radius_of_gyration_um=rg.tolist(),
    )


_META = RecipeMetadata(
    name="confinement_radius_map",
    modality="diffusion_and_tracking",
    family=RecipeFamily.scatter_collapse,
    answers_question="Where in the field are tracks confined (small radius) vs free (large radius)?",
    required_fields=("track_centers_um", "radius_of_gyration_um"),
    optional_fields=("field_size_um", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("msd_by_condition",),
)


@register_recipe(metadata=_META, contract=ConfinementMapInput, demo_contract=_demo)
def render(contract: ConfinementMapInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.4))
    AESTHETIC.apply_to_ax(ax)

    xs = np.array([c[0] for c in contract.track_centers_um], dtype=float)
    ys = np.array([c[1] for c in contract.track_centers_um], dtype=float)
    rg = np.array(contract.radius_of_gyration_um, dtype=float)

    # Scatter with marker radius ∝ R_g.
    sizes = 20 + 50 * (rg / max(rg.max(), 1e-9))
    sc = ax.scatter(xs, ys, s=sizes, c=rg,
                    cmap=AESTHETIC.continuous_cmap,
                    alpha=0.8, edgecolor="white", linewidth=0.3, zorder=3,
                    norm=None)

    # Circle marker for each track showing actual R_g in data coords.
    from matplotlib.patches import Circle
    for x, y, r in zip(xs, ys, rg):
        ax.add_patch(Circle((x, y), r, facecolor="none",
                            edgecolor="#333333", linewidth=0.3,
                            alpha=0.22, zorder=2))

    # Scale bar (10 μm).
    x0 = contract.field_size_um[0] * 0.05
    y0 = contract.field_size_um[1] * 0.05
    ax.plot([x0, x0 + 10], [y0, y0], color="#111111", lw=2.2,
            solid_capstyle="butt", zorder=6)
    ax.text(x0 + 5, y0 + 1.2, "10 μm",
            ha="center", va="bottom", fontsize=6.2, color="#111111",
            bbox=dict(boxstyle="round,pad=0.14", fc="white",
                      ec="none", alpha=0.8))

    ax.set_xlim(0, contract.field_size_um[0])
    ax.set_ylim(0, contract.field_size_um[1])
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel("x (μm)")
    ax.set_ylabel("y (μm)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)

    cbar = ax.figure.colorbar(sc, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(r"$R_g$ (μm)", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.2)

    confined_frac = float((rg < np.median(rg)).mean())
    ax.text(0.99, 0.02,
            f"N tracks = {len(rg)}\n"
            f"median Rg = {smart_fmt(float(np.median(rg)))} μm\n"
            f"confined (<median) = {confined_frac*100:.0f}%",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=6.2, color="#111111",
            bbox=dict(boxstyle="round,pad=0.16", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=7)
    return ax
