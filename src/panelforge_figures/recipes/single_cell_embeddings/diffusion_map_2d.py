"""Diffusion map 2D — DC1 × DC2 scatter colored by pseudotime."""

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


class DiffusionMapInput(RecipeContract):
    dc1: list[float] = Field(...)
    dc2: list[float] = Field(...)
    pseudotime: list[float] = Field(...)
    title: str = "Diffusion map"


def _demo() -> DiffusionMapInput:
    rng = np.random.default_rng(319)
    n = 1200
    t = np.linspace(0, 1, n)
    # Horseshoe-like manifold in diffusion-component space.
    dc1 = np.cos(np.pi * t) + rng.normal(0, 0.1, n)
    dc2 = np.sin(np.pi * t) + rng.normal(0, 0.1, n)
    return DiffusionMapInput(
        dc1=dc1.tolist(),
        dc2=dc2.tolist(),
        pseudotime=t.tolist(),
    )


_META = RecipeMetadata(
    name="diffusion_map_2d",
    modality="single_cell_embeddings",
    family=RecipeFamily.scatter_collapse,
    answers_question="How do cells arrange along the first two diffusion components, and how does pseudotime flow through that manifold?",
    required_fields=("dc1", "dc2", "pseudotime"),
    optional_fields=("title",),
    file_format_hints=("h5ad", "parquet"),
    alternatives_in_modality=("trajectory_pseudotime_arrow",),
)


@register_recipe(metadata=_META, contract=DiffusionMapInput, demo_contract=_demo)
def render(contract: DiffusionMapInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.6, 3.4))
    AESTHETIC.apply_to_ax(ax)

    x = np.array(contract.dc1, dtype=float)
    y = np.array(contract.dc2, dtype=float)
    t = np.array(contract.pseudotime, dtype=float)

    alpha = density_alpha(x, y, alpha_min=0.30, alpha_max=0.9)
    sc = ax.scatter(x, y, s=8, c=t, cmap=AESTHETIC.continuous_cmap,
                    alpha=alpha, edgecolor="none", zorder=3)

    # Smooth manifold curve via binned median along pseudotime.
    order = np.argsort(t)
    xs = x[order]
    ys = y[order]
    n_bins = 30
    bin_idx = np.linspace(0, len(xs), n_bins + 1).astype(int)
    mx = np.array([np.median(xs[bin_idx[i]:bin_idx[i + 1]])
                   for i in range(n_bins) if bin_idx[i + 1] > bin_idx[i]])
    my = np.array([np.median(ys[bin_idx[i]:bin_idx[i + 1]])
                   for i in range(n_bins) if bin_idx[i + 1] > bin_idx[i]])
    ax.plot(mx, my, color="#222222", lw=1.1,
            alpha=0.9, zorder=4, label="pseudotime order")

    # Endpoints.
    ax.scatter([xs[0]], [ys[0]], s=70, marker="o",
               facecolor="white", edgecolor="#111111", linewidth=1.3,
               zorder=6)
    ax.scatter([xs[-1]], [ys[-1]], s=80, marker="*",
               facecolor="#D32F2F", edgecolor="white", linewidth=0.6,
               zorder=6)

    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel("DC1")
    ax.set_ylabel("DC2")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.4, frameon=False, loc="upper right",
              handlelength=1.6)
    cbar = ax.figure.colorbar(sc, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("pseudotime", fontsize=6.4)
    cbar.ax.tick_params(labelsize=6.0)

    ax.figure.text(
        0.5, 0.005,
        f"N cells = {len(t)}   manifold span "
        f"[{smart_fmt(float(xs[0]))},{smart_fmt(float(ys[0]))}] to "
        f"[{smart_fmt(float(xs[-1]))},{smart_fmt(float(ys[-1]))}]",
        ha="center", va="bottom",
        fontsize=6.0, color="#444444",
    )
    return ax
