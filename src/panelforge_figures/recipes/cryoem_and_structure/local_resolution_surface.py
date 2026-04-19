"""Local resolution map — 2D slice of local-resolution estimates over a density map."""

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


class LocalResInput(RecipeContract):
    resolution_ang: list[list[float]] = Field(
        ..., description="2D array of local resolution (Å) per voxel in slice"
    )
    voxel_size_ang: float = 1.08
    title: str = "Local resolution (slice)"


def _demo() -> LocalResInput:
    rng = np.random.default_rng(447)
    H, W = 80, 80
    yy, xx = np.mgrid[:H, :W]
    # Radially varying resolution: best at centre (3 Å), worst at periphery (~6 Å).
    r = np.sqrt((xx - W // 2) ** 2 + (yy - H // 2) ** 2)
    res = 3.0 + 0.05 * r + rng.normal(0, 0.10, (H, W))
    # Mask the outer shell as nan (outside particle).
    mask = r > 35
    res[mask] = np.nan
    return LocalResInput(
        resolution_ang=res.tolist(),
        voxel_size_ang=1.08,
    )


_META = RecipeMetadata(
    name="local_resolution_surface",
    modality="cryoem_and_structure",
    family=RecipeFamily.heatmap,
    answers_question="Which regions of the reconstruction are well-resolved vs. flexible/poorly-resolved?",
    required_fields=("resolution_ang",),
    optional_fields=("voxel_size_ang", "title"),
    file_format_hints=("mrc", "npz"),
    alternatives_in_modality=("fsc_resolution_curve",),
)


@register_recipe(metadata=_META, contract=LocalResInput, demo_contract=_demo)
def render(contract: LocalResInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.6, 3.6))
    AESTHETIC.apply_to_ax(ax)

    res = np.array(contract.resolution_ang, dtype=float)
    vox = float(contract.voxel_size_ang)
    H, W = res.shape
    extent = (0, W * vox, 0, H * vox)

    vmin = float(np.nanpercentile(res, 2))
    vmax = float(np.nanpercentile(res, 98))
    im = ax.imshow(
        res, origin="lower", extent=extent,
        cmap="viridis_r", vmin=vmin, vmax=vmax,
        aspect="equal", interpolation="bilinear",
    )

    # Scale bar (10 Å).
    ax.plot([3 * vox, 3 * vox + 10], [3 * vox, 3 * vox],
            color="white", lw=3.0, solid_capstyle="butt", zorder=5)
    ax.text(3 * vox + 5, 3 * vox + 2.5, r"10 $\AA$",
            ha="center", va="bottom", fontsize=6.2, color="white",
            bbox=dict(boxstyle="round,pad=0.14", fc="#333333",
                      ec="none", alpha=0.7))

    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("left", "bottom"):
        ax.spines[side].set_visible(False)
    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(r"resolution ($\AA$)", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.2)

    best = float(np.nanmin(res))
    median_res = float(np.nanmedian(res))
    ax.set_title(
        f"{contract.title}  ·  best {smart_fmt(best)} $\\AA$, "
        f"median {smart_fmt(median_res)} $\\AA$",
        fontsize=8.4, pad=4,
    )
    return ax
