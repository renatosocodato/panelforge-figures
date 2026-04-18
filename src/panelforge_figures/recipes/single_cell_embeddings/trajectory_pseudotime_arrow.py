"""Pseudotime trajectory — UMAP colored by pseudotime with direction arrow."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    density_alpha,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class TrajectoryInput(RecipeContract):
    umap1: list[float] = Field(...)
    umap2: list[float] = Field(...)
    pseudotime: list[float] = Field(...)
    start_point: tuple[float, float] | None = None
    end_point: tuple[float, float] | None = None
    title: str = "Pseudotime trajectory"


def _demo() -> TrajectoryInput:
    rng = np.random.default_rng(311)
    n = 1400
    # S-shaped trajectory in UMAP.
    t = np.linspace(0, 1, n)
    u1 = -4 + 8 * t + rng.normal(0, 0.5, n)
    u2 = 2 * np.sin(np.pi * t) + rng.normal(0, 0.4, n) - 0.5
    return TrajectoryInput(
        umap1=u1.tolist(),
        umap2=u2.tolist(),
        pseudotime=t.tolist(),
        start_point=(-4.0, -0.5),
        end_point=(4.0, -0.5),
    )


_META = RecipeMetadata(
    name="trajectory_pseudotime_arrow",
    modality="single_cell_embeddings",
    family=RecipeFamily.scatter_collapse,
    answers_question="What is the pseudotime trajectory in UMAP space, and what direction does development / activation flow?",
    required_fields=("umap1", "umap2", "pseudotime"),
    optional_fields=("start_point", "end_point", "title"),
    file_format_hints=("h5ad", "parquet"),
    alternatives_in_modality=("diffusion_map_2d",),
)


@register_recipe(metadata=_META, contract=TrajectoryInput, demo_contract=_demo)
def render(contract: TrajectoryInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.4))
    AESTHETIC.apply_to_ax(ax)

    x = np.array(contract.umap1, dtype=float)
    y = np.array(contract.umap2, dtype=float)
    t = np.array(contract.pseudotime, dtype=float)

    alpha = density_alpha(x, y, alpha_min=0.35, alpha_max=0.9)
    sc = ax.scatter(x, y, s=8, c=t, cmap=AESTHETIC.continuous_cmap,
                    alpha=alpha, edgecolor="none", zorder=3)

    # Smooth trajectory line: bin by pseudotime, take mean position.
    n_bins = 24
    bins = np.linspace(0, 1, n_bins + 1)
    xs_line = []
    ys_line = []
    for lo, hi in zip(bins[:-1], bins[1:]):
        mask = (t >= lo) & (t < hi)
        if mask.sum() >= 3:
            xs_line.append(np.median(x[mask]))
            ys_line.append(np.median(y[mask]))
    ax.plot(xs_line, ys_line, color="#111111", lw=1.2, zorder=5,
            label="pseudotime median path")

    # Arrow at end of path.
    if len(xs_line) >= 2:
        ax.annotate(
            "", xy=(xs_line[-1], ys_line[-1]),
            xytext=(xs_line[-2], ys_line[-2]),
            arrowprops=dict(arrowstyle="-|>", color="#111111", lw=1.4),
            zorder=6,
        )

    # Start and end markers.
    if contract.start_point is not None:
        ax.scatter([contract.start_point[0]], [contract.start_point[1]],
                   s=80, marker="o", facecolor="white",
                   edgecolor="#111111", linewidth=1.5, zorder=7)
        ax.text(contract.start_point[0], contract.start_point[1] - 0.4,
                "start", ha="center", va="top", fontsize=6.4, color="#111111",
                bbox=dict(boxstyle="round,pad=0.14", fc="white",
                          ec="none", alpha=0.9))
    if contract.end_point is not None:
        ax.scatter([contract.end_point[0]], [contract.end_point[1]],
                   s=80, marker="*", facecolor="#D32F2F",
                   edgecolor="white", linewidth=0.8, zorder=7)
        ax.text(contract.end_point[0], contract.end_point[1] - 0.4,
                "end", ha="center", va="top", fontsize=6.4, color="#D32F2F",
                bbox=dict(boxstyle="round,pad=0.14", fc="white",
                          ec="none", alpha=0.9))

    ax.set_xlabel("UMAP1")
    ax.set_ylabel("UMAP2")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    cbar = ax.figure.colorbar(sc, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("pseudotime", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.2)

    ax.text(0.01, 0.99,
            f"N = {len(t)}   pseudotime range "
            f"[{smart_fmt(float(t.min()))}, {smart_fmt(float(t.max()))}]",
            transform=ax.transAxes, ha="left", va="top",
            fontsize=6.2, color="#444444",
            bbox=dict(boxstyle="round,pad=0.16", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=8)
    return ax
