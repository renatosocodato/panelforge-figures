"""Voronoi territory map — tessellation colored by cell area."""

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


class VoronoiInput(RecipeContract):
    x_um: list[float] = Field(...)
    y_um: list[float] = Field(...)
    extent_um: tuple[float, float, float, float] = Field(
        default=(0.0, 100.0, 0.0, 100.0),
        description="(x0, x1, y0, y1) in μm",
    )
    title: str = "Voronoi territories"


def _demo() -> VoronoiInput:
    rng = np.random.default_rng(409)
    n = 80
    x = rng.uniform(5, 95, n)
    y = rng.uniform(5, 95, n)
    return VoronoiInput(
        x_um=x.tolist(),
        y_um=y.tolist(),
        extent_um=(0.0, 100.0, 0.0, 100.0),
    )


_META = RecipeMetadata(
    name="voronoi_territory_map",
    modality="spatial_statistics",
    family=RecipeFamily.heatmap,
    answers_question="How are cells distributed across a tissue field, and what are their exclusive territory sizes?",
    required_fields=("x_um", "y_um"),
    optional_fields=("extent_um", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("kernel_density_heatmap",),
)


@register_recipe(metadata=_META, contract=VoronoiInput, demo_contract=_demo)
def render(contract: VoronoiInput, ax=None, **_):
    from matplotlib.collections import PolyCollection
    from scipy.spatial import Voronoi

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.4, 3.6))
    AESTHETIC.apply_to_ax(ax)

    x = np.array(contract.x_um, dtype=float)
    y = np.array(contract.y_um, dtype=float)
    pts = np.column_stack([x, y])
    x0, x1, y0, y1 = contract.extent_um

    # Add far-away sentinel points so bounded Voronoi regions exist inside the
    # extent (scipy's Voronoi has unbounded regions by default).
    pad = max(x1 - x0, y1 - y0) * 2
    sentinels = np.array([
        [x0 - pad, y0 - pad], [x1 + pad, y0 - pad],
        [x0 - pad, y1 + pad], [x1 + pad, y1 + pad],
    ])
    all_pts = np.vstack([pts, sentinels])
    vor = Voronoi(all_pts)

    polys, areas = [], []
    for idx in range(len(pts)):
        region_idx = vor.point_region[idx]
        region = vor.regions[region_idx]
        if not region or -1 in region:
            continue
        poly = np.array([vor.vertices[v] for v in region])
        # Clip to extent bounds.
        poly[:, 0] = np.clip(poly[:, 0], x0, x1)
        poly[:, 1] = np.clip(poly[:, 1], y0, y1)
        polys.append(poly)
        # Shoelace area.
        a = 0.5 * np.abs(
            np.dot(poly[:, 0], np.roll(poly[:, 1], 1))
            - np.dot(poly[:, 1], np.roll(poly[:, 0], 1))
        )
        areas.append(float(a))

    areas_arr = np.array(areas, dtype=float)
    coll = PolyCollection(
        polys,
        array=areas_arr,
        cmap=AESTHETIC.continuous_cmap,
        edgecolors="white", linewidths=0.5,
    )
    ax.add_collection(coll)
    ax.scatter(x, y, s=6, color="#111111", alpha=0.7, zorder=5)

    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("left", "bottom"):
        ax.spines[side].set_visible(False)

    cbar = ax.figure.colorbar(coll, ax=ax, fraction=0.045, pad=0.04)
    cbar.set_label(r"territory area ($\mu$m$^2$)", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.2)

    ax.set_title(
        f"{contract.title}  ·  N = {len(x)}  median {smart_fmt(float(np.median(areas_arr)))} $\\mu$m$^2$",
        fontsize=8.4, pad=4,
    )
    return ax
