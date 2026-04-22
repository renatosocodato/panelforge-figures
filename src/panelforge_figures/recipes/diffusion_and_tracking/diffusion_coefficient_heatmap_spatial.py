"""Spatial diffusion-coefficient heatmap — gridded D(x, y) from binned
track statistics with contour overlay. Distinct from
`confinement_radius_map` (scatter of per-track R_conf values).
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


class DSpatialInput(RecipeContract):
    x_edges: list[float] = Field(..., min_length=3)
    y_edges: list[float] = Field(..., min_length=3)
    D_map: list[list[float]] = Field(
        ..., description="(n_y × n_x) diffusion coefficient in μm²/s"
    )
    track_count_map: list[list[int]] | None = Field(
        None, description="per-bin track count for transparency gating"
    )
    title: str = "Spatial diffusion map"


def _demo() -> DSpatialInput:
    rng = np.random.default_rng(2113)
    nx, ny = 24, 18
    x_edges = np.linspace(0, 60, nx + 1)
    y_edges = np.linspace(0, 45, ny + 1)
    X, Y = np.meshgrid(0.5 * (x_edges[:-1] + x_edges[1:]),
                       0.5 * (y_edges[:-1] + y_edges[1:]))
    # Two low-D patches on a high-D background.
    D_base = 0.18
    D = D_base * np.ones_like(X)
    for cx, cy, r in [(20, 12, 7), (42, 28, 5)]:
        D -= 0.12 * np.exp(-((X - cx) ** 2 + (Y - cy) ** 2) / (2 * r ** 2))
    D += rng.normal(0, 0.01, D.shape)
    counts = rng.integers(0, 40, D.shape)
    return DSpatialInput(
        x_edges=x_edges.tolist(),
        y_edges=y_edges.tolist(),
        D_map=D.tolist(),
        track_count_map=counts.tolist(),
    )


_META = RecipeMetadata(
    name="diffusion_coefficient_heatmap_spatial",
    modality="diffusion_and_tracking",
    family=RecipeFamily.heatmap,
    answers_question=(
        "Where in the field of view is diffusion fast vs slow?"
    ),
    required_fields=("x_edges", "y_edges", "D_map"),
    optional_fields=("track_count_map", "title"),
    file_format_hints=("csv", "npz"),
    alternatives_in_modality=("confinement_radius_map",),
)


@register_recipe(
    metadata=_META,
    contract=DSpatialInput,
    demo_contract=_demo,
)
def render(contract: DSpatialInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 3.8))
    AESTHETIC.apply_to_ax(ax)

    x_edges = np.asarray(contract.x_edges, float)
    y_edges = np.asarray(contract.y_edges, float)
    D = np.asarray(contract.D_map, float)

    # Transparency-gate bins with few tracks.
    if contract.track_count_map is not None:
        counts = np.asarray(contract.track_count_map, float)
        alpha_mask = np.clip(counts / max(counts.max(), 1), 0.25, 1.0)
        D_plot = np.ma.array(D, mask=(counts < 1))
    else:
        alpha_mask = None
        D_plot = D

    im = ax.pcolormesh(x_edges, y_edges, D_plot,
                       cmap="viridis", shading="auto", zorder=2)
    # Contour overlay at quartiles.
    xc = 0.5 * (x_edges[:-1] + x_edges[1:])
    yc = 0.5 * (y_edges[:-1] + y_edges[1:])
    Xc, Yc = np.meshgrid(xc, yc)
    q = np.quantile(D[~np.isnan(D)], [0.25, 0.5, 0.75])
    ax.contour(Xc, Yc, D, levels=q,
               colors=["#FFFFFF", "#222222", "#FFFFFF"],
               linewidths=[0.5, 0.7, 0.5],
               linestyles=["--", "-", "--"], zorder=4)

    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.036, pad=0.03)
    cbar.set_label(r"D (μm$^2$/s)", fontsize=6.8)
    cbar.ax.tick_params(labelsize=6.4)

    ax.set_xlabel("x (μm)")
    ax.set_ylabel("y (μm)")
    ax.set_aspect("equal")
    ax.set_title(contract.title, fontsize=9.0, pad=4)

    slow_mask = D < q[0]
    fast_mask = D > q[2]
    ax.text(0.02, 0.97,
            f"slow-patch area = {smart_fmt(float(slow_mask.mean()))}\n"
            f"fast-patch area = {smart_fmt(float(fast_mask.mean()))}\n"
            f"median D = {smart_fmt(float(np.median(D)))}",
            transform=ax.transAxes, ha="left", va="top",
            fontsize=6.4, color="#FFFFFF",
            bbox=dict(boxstyle="round,pad=0.22", fc="#222222",
                      ec="none", alpha=0.7),
            zorder=6)
    return ax
