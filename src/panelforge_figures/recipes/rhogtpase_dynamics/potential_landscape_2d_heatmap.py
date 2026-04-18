"""2-D potential landscape heatmap — U(x, y) with overlaid contours."""

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


class Potential2DInput(RecipeContract):
    x_grid: list[float]
    y_grid: list[float]
    U: list[list[float]] = Field(..., description="U[j][i] = potential at (x[i], y[j])")
    x_label: str = "RhoA"
    y_label: str = "Rac1"
    title: str = "2-D potential landscape"


def _demo() -> Potential2DInput:
    x = np.linspace(-2, 2, 80)
    y = np.linspace(-2, 2, 80)
    X, Y = np.meshgrid(x, y)
    # 3 wells mutually antagonistic.
    U = 0.5 * (X ** 2 - 1) ** 2 + 0.5 * (Y ** 2 - 1) ** 2 + 0.7 * X * Y
    return Potential2DInput(
        x_grid=x.tolist(), y_grid=y.tolist(), U=U.tolist(),
    )


_META = RecipeMetadata(
    name="potential_landscape_2d_heatmap",
    modality="rhogtpase_dynamics",
    family=RecipeFamily.contour,
    answers_question="How does the joint RhoA/Rac1 potential landscape look — where are the wells and saddles in the 2-D plane?",
    required_fields=("x_grid", "y_grid", "U"),
    optional_fields=("x_label", "y_label", "title"),
    file_format_hints=("npz", "pickle"),
    alternatives_in_modality=("potential_landscape_1d", "basin_of_attraction_map"),
)


@register_recipe(metadata=_META, contract=Potential2DInput, demo_contract=_demo)
def render(contract: Potential2DInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.6, 3.6))
    AESTHETIC.apply_to_ax(ax)
    X, Y = np.meshgrid(contract.x_grid, contract.y_grid)
    U = np.array(contract.U, dtype=float)

    im = ax.pcolormesh(X, Y, U, cmap=AESTHETIC.continuous_cmap,
                       shading="auto")
    cs = ax.contour(X, Y, U, levels=10, colors="white",
                    linewidths=0.5, alpha=0.6)
    ax.clabel(cs, inline=True, fontsize=6.0,
              fmt=lambda v: smart_fmt(v), inline_spacing=4)

    # Minima (approximate).
    # Crude: find grid cells where all neighbors are greater.
    min_mask = np.ones_like(U, dtype=bool)
    min_mask[1:, :] &= U[1:, :] < U[:-1, :]
    min_mask[:-1, :] &= U[:-1, :] < U[1:, :]
    min_mask[:, 1:] &= U[:, 1:] < U[:, :-1]
    min_mask[:, :-1] &= U[:, :-1] < U[:, 1:]
    ys_idx, xs_idx = np.where(min_mask)
    for yi, xi in zip(ys_idx, xs_idx):
        x_w, y_w = contract.x_grid[xi], contract.y_grid[yi]
        ax.scatter([x_w], [y_w], s=34, color="white",
                   edgecolor="black", linewidth=0.8, zorder=6)

    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("U", fontsize=6.8)
    cbar.ax.tick_params(labelsize=6.4)

    ax.set_xlabel(contract.x_label)
    ax.set_ylabel(contract.y_label)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    return ax
