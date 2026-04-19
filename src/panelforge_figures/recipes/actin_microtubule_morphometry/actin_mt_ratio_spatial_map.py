"""Actin / microtubule intensity-ratio spatial map with cell outline overlay."""

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


class ActinMTRatioMapInput(RecipeContract):
    ratio_image: list[list[float]] = Field(
        ..., description="2-D actin/MT intensity ratio (neutral at 1.0)"
    )
    pixel_size_um: float = 0.1
    cell_outline_polygon: list[tuple[float, float]] | None = Field(
        None, description="optional (x, y) polygon for the cell boundary (µm)"
    )
    scale_bar_um: float = 2.0
    title: str = "Actin / MT intensity ratio"


def _demo() -> ActinMTRatioMapInput:
    rng = np.random.default_rng(771)
    H, W = 80, 120
    yy, xx = np.mgrid[:H, :W]
    cx, cy = W // 2, H // 2
    # Radial gradient: actin-enriched at periphery, MT-enriched centrally.
    r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    ratio = 1.0 + 0.55 * np.tanh((r - 28.0) / 8.0)  # < 1 near centre, > 1 at rim
    ratio += 0.08 * np.sin((xx - cx) * 0.25)         # subtle lateral structure
    ratio += rng.normal(0, 0.04, (H, W))
    # Mask anything outside an ellipse to mimic a cell outline.
    ell = ((xx - cx) / 48.0) ** 2 + ((yy - cy) / 32.0) ** 2
    outside = ell > 1.0
    ratio[outside] = 1.0
    # Construct the cell outline polygon in µm.
    t = np.linspace(0, 2 * np.pi, 80)
    px = 0.1
    hull_x = (cx + 48.0 * np.cos(t)) * px
    hull_y = (cy + 32.0 * np.sin(t)) * px
    return ActinMTRatioMapInput(
        ratio_image=ratio.tolist(),
        pixel_size_um=0.1,
        cell_outline_polygon=[(float(hx), float(hy))
                              for hx, hy in zip(hull_x, hull_y)],
        scale_bar_um=2.0,
    )


_META = RecipeMetadata(
    name="actin_mt_ratio_spatial_map",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.heatmap,
    answers_question=(
        "At each point within a cell, what is the local ratio of actin to "
        "microtubule intensity?"
    ),
    required_fields=("ratio_image",),
    optional_fields=("pixel_size_um", "cell_outline_polygon", "scale_bar_um", "title"),
    file_format_hints=("tif", "npz"),
    alternatives_in_modality=("branch_point_density_map",),
)


@register_recipe(
    metadata=_META,
    contract=ActinMTRatioMapInput,
    demo_contract=_demo,
)
def render(contract: ActinMTRatioMapInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.4))
    AESTHETIC.apply_to_ax(ax)

    R = np.asarray(contract.ratio_image, float)
    H, W = R.shape
    px = float(contract.pixel_size_um)
    extent = (0.0, W * px, 0.0, H * px)

    # RdBu_r anchored at 1.0 (modality convention).
    anchor = 1.0
    vrange = max(float(np.max(np.abs(R - anchor))), 0.01)
    im = ax.imshow(
        R, origin="lower", extent=extent,
        cmap=AESTHETIC.ratio_cmap or "RdBu_r",
        vmin=anchor - vrange, vmax=anchor + vrange,
        aspect="equal", interpolation="bilinear",
    )

    # Cell outline overlay (white polyline).
    if contract.cell_outline_polygon:
        xs, ys = zip(*contract.cell_outline_polygon)
        xs_closed = list(xs) + [xs[0]]
        ys_closed = list(ys) + [ys[0]]
        ax.plot(xs_closed, ys_closed, color="white", lw=1.1,
                alpha=0.9, zorder=5)

    # Mandatory scale bar.
    sb_len = float(contract.scale_bar_um)
    sb_x = extent[0] + (extent[1] - extent[0]) * 0.05
    sb_y = extent[2] + (extent[3] - extent[2]) * 0.08
    ax.plot([sb_x, sb_x + sb_len], [sb_y, sb_y], color="white",
            lw=3.0, solid_capstyle="butt", zorder=7)
    ax.text(sb_x + sb_len / 2, sb_y + (extent[3] - extent[2]) * 0.04,
            rf"{smart_fmt(sb_len)} $\mu$m",
            ha="center", va="bottom", fontsize=6.2, color="white",
            bbox=dict(boxstyle="round,pad=0.14", fc="#333333",
                      ec="none", alpha=0.7))

    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("left", "bottom"):
        ax.spines[side].set_visible(False)
    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(r"actin / MT ratio", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.2)

    # Summary: median & extremum deviation from neutral.
    median_r = float(np.median(R))
    max_dev = float(np.max(np.abs(R - anchor)))
    ax.set_title(
        f"{contract.title}  ·  median {smart_fmt(median_r)},  "
        f"max $\\Delta$ = {smart_fmt(max_dev)}",
        fontsize=8.4, pad=4,
    )
    return ax
