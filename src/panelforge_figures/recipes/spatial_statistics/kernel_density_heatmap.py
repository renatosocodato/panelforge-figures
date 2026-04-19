"""2D kernel density heatmap over a tissue field."""

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


class KDEInput(RecipeContract):
    x_um: list[float] = Field(...)
    y_um: list[float] = Field(...)
    bandwidth_um: float = 6.0
    extent_um: tuple[float, float, float, float] = Field(
        default=(0.0, 100.0, 0.0, 100.0),
    )
    title: str = "Cell density (KDE)"


def _demo() -> KDEInput:
    rng = np.random.default_rng(411)
    # Two tight clusters + a diffuse background.
    bg = np.column_stack([rng.uniform(0, 100, 80), rng.uniform(0, 100, 80)])
    c1 = rng.multivariate_normal([30, 70], [[40, 0], [0, 40]], 60)
    c2 = rng.multivariate_normal([70, 30], [[50, 10], [10, 30]], 50)
    pts = np.vstack([bg, c1, c2])
    pts = np.clip(pts, 0, 100)
    return KDEInput(
        x_um=pts[:, 0].tolist(),
        y_um=pts[:, 1].tolist(),
        bandwidth_um=6.0,
    )


_META = RecipeMetadata(
    name="kernel_density_heatmap",
    modality="spatial_statistics",
    family=RecipeFamily.heatmap,
    answers_question="Where are the hot and cold density regions of a point pattern across a tissue field?",
    required_fields=("x_um", "y_um"),
    optional_fields=("bandwidth_um", "extent_um", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("voronoi_territory_map",),
)


@register_recipe(metadata=_META, contract=KDEInput, demo_contract=_demo)
def render(contract: KDEInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.4, 3.6))
    AESTHETIC.apply_to_ax(ax)

    x = np.array(contract.x_um, dtype=float)
    y = np.array(contract.y_um, dtype=float)
    x0, x1, y0, y1 = contract.extent_um
    h = float(contract.bandwidth_um)

    # Gaussian KDE on a regular grid (simple, no scipy dependency beyond core).
    nx, ny = 60, 60
    gx = np.linspace(x0, x1, nx)
    gy = np.linspace(y0, y1, ny)
    XX, YY = np.meshgrid(gx, gy)
    ZZ = np.zeros_like(XX)
    inv_2h2 = 1.0 / (2 * h * h)
    for xi, yi in zip(x, y):
        ZZ += np.exp(-(((XX - xi) ** 2 + (YY - yi) ** 2) * inv_2h2))
    ZZ /= (2 * np.pi * h * h) * len(x)

    im = ax.imshow(
        ZZ, origin="lower", extent=(x0, x1, y0, y1),
        cmap=AESTHETIC.continuous_cmap, aspect="equal",
        interpolation="bilinear",
    )
    ax.scatter(x, y, s=3, color="white", alpha=0.55, edgecolor="none", zorder=4)

    # Scale bar (10 μm).
    sb_x, sb_y = x0 + 5, y0 + 5
    ax.plot([sb_x, sb_x + 10], [sb_y, sb_y], color="white",
            lw=3.0, solid_capstyle="butt", zorder=6)
    ax.text(sb_x + 5, sb_y + 2.5, r"10 $\mu$m",
            ha="center", va="bottom", fontsize=6.2, color="white",
            bbox=dict(boxstyle="round,pad=0.14", fc="#333333",
                      ec="none", alpha=0.7))

    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("left", "bottom"):
        ax.spines[side].set_visible(False)
    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.045, pad=0.04)
    cbar.set_label("density", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.2)

    ax.set_title(
        f"{contract.title}  ·  N = {len(x)},  h = {smart_fmt(h)} $\\mu$m",
        fontsize=9.0, pad=4,
    )
    return ax
