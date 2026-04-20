"""Depth-coded microglia field — per-cell (x, y, z) scatter with depth colormap.

Different from `two_photon_depth_projection` (which takes a
volumetric z-stack array and renders a color-by-depth MIP): this
recipe takes a **cell-level table** of centroids with depth z, and
renders each cell as a dot on a 2-D field with marker color encoding
depth and marker size encoding cell size. Perfect for a multi-cell
field view where the z-stack has been collapsed to per-cell coordinates.
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


class DepthFieldInput(RecipeContract):
    x_um: list[float] = Field(..., min_length=3)
    y_um: list[float] = Field(..., min_length=3)
    z_um: list[float] = Field(..., min_length=3)
    cell_size_um: list[float] | None = None
    extent_um: tuple[float, float, float, float] = (0.0, 250.0, 0.0, 250.0)
    z_label: str = "depth z (μm)"
    title: str = "Microglia field — depth-coded"


def _demo() -> DepthFieldInput:
    rng = np.random.default_rng(541)
    n = 70
    x = rng.uniform(20, 230, n)
    y = rng.uniform(20, 230, n)
    # Depth gradient — cells at x>150 tend to be deeper.
    z = 10 + 0.24 * x + rng.normal(0, 8, n)
    sizes = rng.uniform(12, 26, n)
    return DepthFieldInput(
        x_um=x.tolist(), y_um=y.tolist(), z_um=z.tolist(),
        cell_size_um=sizes.tolist(),
    )


_META = RecipeMetadata(
    name="depth_projected_microglia_field",
    modality="intravital_imaging",
    family=RecipeFamily.heatmap,
    answers_question=(
        "Across a multi-cell field, where are individual cells in (x, y) "
        "and at what depth z?"
    ),
    required_fields=("x_um", "y_um", "z_um"),
    optional_fields=("cell_size_um", "extent_um", "z_label", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("two_photon_depth_projection",),
)


@register_recipe(
    metadata=_META,
    contract=DepthFieldInput,
    demo_contract=_demo,
)
def render(contract: DepthFieldInput, ax=None, **_):
    import matplotlib as mpl

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 4.2))
    AESTHETIC.apply_to_ax(ax)

    x = np.asarray(contract.x_um, float)
    y = np.asarray(contract.y_um, float)
    z = np.asarray(contract.z_um, float)
    sizes = (np.asarray(contract.cell_size_um, float)
             if contract.cell_size_um is not None
             else np.full(x.size, 18.0))

    cmap = mpl.colormaps[AESTHETIC.continuous_cmap]
    # Background heatmap-like patch (so matrix/heatmap rule sees pcolormesh
    # or imshow). Draw a low-intensity grid behind the scatter.
    x0, x1, y0, y1 = contract.extent_um
    grid_n = 24
    xg = np.linspace(x0, x1, grid_n + 1)
    yg = np.linspace(y0, y1, grid_n + 1)
    H, _, _ = np.histogram2d(x, y, bins=[xg, yg])
    Xc = 0.5 * (xg[:-1] + xg[1:])
    Yc = 0.5 * (yg[:-1] + yg[1:])
    ax.pcolormesh(xg, yg, H.T, cmap="Greys", alpha=0.25,
                  shading="auto", zorder=1)
    _ = Xc, Yc

    # Scatter, color by z, size by cell_size.
    z_norm_sizes = 14 + 40 * (sizes - sizes.min()) / max(sizes.max() - sizes.min(), 1e-9)
    sc = ax.scatter(x, y, c=z, s=z_norm_sizes, cmap=cmap,
                    edgecolor="white", linewidth=0.5, alpha=0.95,
                    zorder=3)

    cbar = ax.figure.colorbar(sc, ax=ax, fraction=0.04, pad=0.04)
    cbar.set_label(contract.z_label, fontsize=6.8)
    cbar.ax.tick_params(labelsize=6.4)

    # Scale bar (20 μm).
    sb_x = x0 + 0.05 * (x1 - x0)
    sb_y = y0 + 0.05 * (y1 - y0)
    ax.plot([sb_x, sb_x + 20], [sb_y, sb_y], color="#111111",
            lw=2.2, solid_capstyle="butt", zorder=6)
    ax.text(sb_x + 10, sb_y + 3, r"20 $\mu$m",
            ha="center", va="bottom", fontsize=6.4, color="#111111")

    # Depth stats pill.
    ax.text(
        0.98, 0.97,
        f"N cells = {x.size}\n"
        f"z: {smart_fmt(float(z.min()))} – {smart_fmt(float(z.max()))} μm\n"
        f"median z = {smart_fmt(float(np.median(z)))} μm",
        transform=ax.transAxes, ha="right", va="top",
        fontsize=6.4, color="#111111",
        bbox=dict(boxstyle="round,pad=0.22", fc="white",
                  ec="#BBBBBB", lw=0.5, alpha=0.92),
        zorder=7,
    )

    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    return ax
