"""Branch-point density map — 2D heatmap of Arp2/3-style actin branch events."""

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


class BranchDensityInput(RecipeContract):
    x_um: list[float] = Field(...)
    y_um: list[float] = Field(...)
    pixel_size_um: float = 0.3
    grid_size: int = 80
    smoothing_um: float = 0.8
    title: str = "Branch-point density"


def _demo() -> BranchDensityInput:
    rng = np.random.default_rng(487)
    # Two hot-spot regions at the leading edge + a diffuse background.
    edge1 = rng.multivariate_normal([18, 18], [[6, 0], [0, 6]], 260)
    edge2 = rng.multivariate_normal([8, 40], [[4, 0], [0, 12]], 180)
    bg = np.column_stack([rng.uniform(0, 50, 180), rng.uniform(0, 50, 180)])
    pts = np.clip(np.vstack([edge1, edge2, bg]), 0.5, 49.5)
    return BranchDensityInput(
        x_um=pts[:, 0].tolist(),
        y_um=pts[:, 1].tolist(),
        pixel_size_um=0.3,
        grid_size=80,
        smoothing_um=0.8,
    )


_META = RecipeMetadata(
    name="branch_point_density_map",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.heatmap,
    answers_question="Where within a cell do actin-network branch points concentrate?",
    required_fields=("x_um", "y_um"),
    optional_fields=("pixel_size_um", "grid_size", "smoothing_um", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("skeleton_overlay_kymograph",),
)


@register_recipe(metadata=_META, contract=BranchDensityInput, demo_contract=_demo)
def render(contract: BranchDensityInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.4, 3.6))
    AESTHETIC.apply_to_ax(ax)

    x = np.array(contract.x_um, dtype=float)
    y = np.array(contract.y_um, dtype=float)
    ext = (float(x.min()), float(x.max()), float(y.min()), float(y.max()))
    n = contract.grid_size
    h = contract.smoothing_um

    gx = np.linspace(ext[0], ext[1], n)
    gy = np.linspace(ext[2], ext[3], n)
    XX, YY = np.meshgrid(gx, gy)
    ZZ = np.zeros_like(XX)
    inv_2h2 = 1.0 / (2 * h * h)
    for xi, yi in zip(x, y):
        ZZ += np.exp(-(((XX - xi) ** 2 + (YY - yi) ** 2) * inv_2h2))
    # Normalize to branches per μm².
    ZZ /= (2 * np.pi * h * h)

    im = ax.imshow(
        ZZ, origin="lower", extent=ext,
        cmap=AESTHETIC.continuous_cmap, aspect="equal",
        interpolation="bilinear",
    )
    ax.scatter(x, y, s=3, color="white", alpha=0.5,
               edgecolor="none", zorder=3)

    # Scale bar.
    sb_x, sb_y = ext[0] + 1, ext[2] + 1
    ax.plot([sb_x, sb_x + 5], [sb_y, sb_y],
            color="white", lw=2.6, solid_capstyle="butt", zorder=6)
    ax.text(sb_x + 2.5, sb_y + 0.5, r"5 $\mu$m",
            ha="center", va="bottom", fontsize=6.2, color="white",
            bbox=dict(boxstyle="round,pad=0.14", fc="#333333",
                      ec="none", alpha=0.7))

    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("left", "bottom"):
        ax.spines[side].set_visible(False)
    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(r"branches / $\mu$m$^2$", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.2)

    ax.set_title(
        f"{contract.title}  ·  N = {x.size},  peak {smart_fmt(float(ZZ.max()))}",
        fontsize=8.4, pad=4,
    )
    return ax
