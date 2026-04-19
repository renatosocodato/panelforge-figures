"""Ratio map with cell-segmentation outlines overlaid — single-cell attribution."""

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


class RatioSegMapInput(RecipeContract):
    x_um: list[float] = Field(..., description="x-axis values (μm)")
    y_um: list[float] = Field(..., description="y-axis values (μm)")
    ratio: list[list[float]] = Field(
        ..., description="2-D ratio array shape (n_y, n_x), FRET-neutral at 1.0"
    )
    segmentation_polygons: list[list[tuple[float, float]]] = Field(
        ..., description="list of per-cell (x, y) vertex lists (μm)"
    )
    cell_labels: list[str] | None = None
    title: str = "FRET ratio · cells outlined"


def _demo() -> RatioSegMapInput:
    rng = np.random.default_rng(611)
    xs = np.linspace(0, 60, 140)
    ys = np.linspace(0, 45, 108)
    XX, YY = np.meshgrid(xs, ys)
    R = np.full_like(XX, 1.0)
    # Synthesise ~6 cells, each a soft disc with a random bias.
    centres = [(12, 10), (26, 14), (44, 11), (14, 30), (34, 32), (50, 30)]
    biases = rng.uniform(-0.25, 0.35, len(centres))
    radii = rng.uniform(5.5, 8.0, len(centres))
    polys: list[list[tuple[float, float]]] = []
    for (cx, cy), bias, rad in zip(centres, biases, radii):
        disk = np.exp(-((XX - cx) ** 2 + (YY - cy) ** 2) / (rad * 0.8) ** 2)
        R = R + bias * disk
        theta = np.linspace(0, 2 * np.pi, 60)
        r_jitter = rad + rng.normal(0, 0.25, theta.size)
        verts = [(float(cx + r_jitter[i] * np.cos(theta[i])),
                  float(cy + r_jitter[i] * np.sin(theta[i])))
                 for i in range(theta.size)]
        polys.append(verts)
    R = R + rng.normal(0, 0.015, R.shape)
    labels = [f"c{i + 1}" for i in range(len(polys))]
    return RatioSegMapInput(
        x_um=xs.tolist(), y_um=ys.tolist(),
        ratio=R.tolist(),
        segmentation_polygons=polys,
        cell_labels=labels,
    )


_META = RecipeMetadata(
    name="ratio_map_with_segmentation_overlay",
    modality="fret_biosensors",
    family=RecipeFamily.heatmap,
    answers_question=(
        "What is the spatial FRET-ratio pattern of the field, with cell "
        "outlines overlaid so per-cell contributions are identifiable?"
    ),
    required_fields=("x_um", "y_um", "ratio", "segmentation_polygons"),
    optional_fields=("cell_labels", "title"),
    file_format_hints=("tif", "npz"),
    alternatives_in_modality=("ratio_heatmap_over_field",),
)


@register_recipe(
    metadata=_META,
    contract=RatioSegMapInput,
    demo_contract=_demo,
)
def render(contract: RatioSegMapInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.6))
    AESTHETIC.apply_to_ax(ax)

    xs = np.asarray(contract.x_um, dtype=float)
    ys = np.asarray(contract.y_um, dtype=float)
    R = np.asarray(contract.ratio, dtype=float)

    # Ratio heatmap anchored at 1.0 per modality convention.
    anchor = 1.0
    vrange = max(float(np.max(np.abs(R - anchor))), 0.01)
    extent = (float(xs.min()), float(xs.max()),
              float(ys.min()), float(ys.max()))
    im = ax.imshow(
        R, origin="lower", extent=extent, aspect="equal",
        cmap=AESTHETIC.ratio_cmap or "RdBu_r",
        vmin=anchor - vrange, vmax=anchor + vrange,
        interpolation="bilinear",
    )

    # White cell-outline polygons + optional centroid labels.
    labels = contract.cell_labels or [""] * len(contract.segmentation_polygons)
    for verts, label in zip(contract.segmentation_polygons, labels):
        if not verts:
            continue
        xs_p, ys_p = zip(*verts)
        xs_closed = list(xs_p) + [xs_p[0]]
        ys_closed = list(ys_p) + [ys_p[0]]
        ax.plot(xs_closed, ys_closed, color="white", lw=0.9,
                alpha=0.95, zorder=5)
        if label:
            cx = float(np.mean(xs_p))
            cy = float(np.mean(ys_p))
            ax.text(cx, cy, label, ha="center", va="center",
                    fontsize=6.4, color="white",
                    bbox=dict(boxstyle="round,pad=0.12", fc="#00000088",
                              ec="none"), zorder=6)

    # Mandatory scale bar (10 μm).
    sb_x, sb_y = extent[0] + 2.5, extent[2] + 2.5
    ax.plot([sb_x, sb_x + 10], [sb_y, sb_y], color="white",
            lw=3.0, solid_capstyle="butt", zorder=7)
    ax.text(sb_x + 5, sb_y + 1.2, r"10 $\mu$m",
            ha="center", va="bottom", fontsize=6.2, color="white",
            bbox=dict(boxstyle="round,pad=0.14", fc="#333333",
                      ec="none", alpha=0.7))

    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("left", "bottom"):
        ax.spines[side].set_visible(False)
    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(r"F$_A$/F$_D$", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.2)

    ax.set_title(
        f"{contract.title}  ·  {len(contract.segmentation_polygons)} cells,  "
        f"range {smart_fmt(float(R.min()))}-{smart_fmt(float(R.max()))}",
        fontsize=8.6, pad=4,
    )
    return ax
