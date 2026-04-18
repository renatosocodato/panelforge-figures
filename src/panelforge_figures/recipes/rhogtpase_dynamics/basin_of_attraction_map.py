"""Basin-of-attraction map — each point colored by which attractor it converges to."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
)
from ._aesthetic import AESTHETIC


class BasinMapInput(RecipeContract):
    x_grid: list[float]
    y_grid: list[float]
    attractor_label: list[list[int]] = Field(
        ..., description="integer attractor id per grid cell"
    )
    attractor_names: list[str] = Field(
        ..., description="names indexed by id, e.g. ['HOME', 'GATE', 'TRAP']"
    )
    attractor_centers: list[tuple[float, float]] = Field(
        default_factory=list
    )
    x_label: str = "RhoA"
    y_label: str = "slow driver"
    title: str = "Basins of attraction"


def _demo() -> BasinMapInput:
    # Three circular basins.
    x = np.linspace(-2, 2, 110)
    y = np.linspace(-1.5, 1.5, 80)
    X, Y = np.meshgrid(x, y)
    centers = [(-1.2, -0.3), (0.0, 0.3), (1.2, -0.2)]
    dists = np.stack(
        [np.hypot(X - c[0], Y - c[1]) for c in centers], axis=0
    )
    labels = np.argmin(dists, axis=0)
    return BasinMapInput(
        x_grid=x.tolist(), y_grid=y.tolist(),
        attractor_label=labels.tolist(),
        attractor_names=["HOME", "GATE", "TRAP"],
        attractor_centers=centers,
    )


_META = RecipeMetadata(
    name="basin_of_attraction_map",
    modality="rhogtpase_dynamics",
    family=RecipeFamily.heatmap,
    answers_question="Which initial condition in the phase plane flows to which RhoA steady state?",
    required_fields=("x_grid", "y_grid", "attractor_label", "attractor_names"),
    optional_fields=("attractor_centers", "x_label", "y_label", "title"),
    file_format_hints=("npz", "pickle"),
    alternatives_in_modality=("potential_landscape_2d_heatmap",),
)


@register_recipe(metadata=_META, contract=BasinMapInput, demo_contract=_demo)
def render(contract: BasinMapInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    from matplotlib.colors import ListedColormap
    # Map attractor ids → palette semantic colors.
    name_color = {
        "HOME": palette.pick("HOME"),
        "GATE": palette.pick("GATE"),
        "TRAP": palette.pick("TRAP"),
    }
    colors = [
        name_color.get(nm, palette[i])
        for i, nm in enumerate(contract.attractor_names)
    ]
    cmap = ListedColormap(colors)

    X, Y = np.meshgrid(contract.x_grid, contract.y_grid)
    labels = np.array(contract.attractor_label, dtype=int)
    ax.pcolormesh(X, Y, labels, cmap=cmap, shading="auto",
                  alpha=0.85, zorder=1)

    # Attractor markers.
    for (xc, yc), nm in zip(contract.attractor_centers, contract.attractor_names):
        color = name_color.get(nm, "#333333")
        ax.scatter([xc], [yc], s=90, color=color, edgecolor="white",
                   linewidth=1.2, zorder=4, marker="*")
        ax.text(xc, yc + 0.08 * (Y.max() - Y.min()),
                nm, ha="center", va="bottom",
                fontsize=7.0, color=color,
                bbox=dict(boxstyle="round,pad=0.18", fc="white",
                          ec="none", alpha=0.92),
                zorder=5)

    ax.set_xlabel(contract.x_label)
    ax.set_ylabel(contract.y_label)
    ax.set_title(contract.title, fontsize=9.0, pad=4)

    # Basin-size summary.
    total = labels.size
    sizes = [
        f"{nm}: {100.0 * (labels == i).sum() / total:.0f}%"
        for i, nm in enumerate(contract.attractor_names)
    ]
    ax.text(0.01, 0.99,
            "   ".join(sizes),
            transform=ax.transAxes, ha="left", va="top",
            fontsize=6.4, color="#444444",
            bbox=dict(boxstyle="round,pad=0.20", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=6)
    return ax
