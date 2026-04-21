"""RNA-velocity quiver field overlaid on a UMAP.

Background scatter of cells coloured by cluster, with a per-grid-cell
average velocity vector overlaid as a quiver. Distinct from
`trajectory_pseudotime_arrow` (single summary arrow, no field).
"""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    density_alpha,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class RNAVelocityInput(RecipeContract):
    umap1: list[float] = Field(...)
    umap2: list[float] = Field(...)
    velocity_u: list[float] = Field(..., description="per-cell ΔUMAP1")
    velocity_v: list[float] = Field(..., description="per-cell ΔUMAP2")
    cluster: list[str] | None = None
    grid_n: int = 22
    title: str = "RNA-velocity field"


def _demo() -> RNAVelocityInput:
    rng = np.random.default_rng(1013)
    xs = []
    ys = []
    us = []
    vs = []
    labels = []
    centres = [
        ("homeostatic", -4, 0, 0.8, 180),
        ("surveillant", -1, 3, 0.8, 220),
        ("activated", 2, 4, 0.8, 240),
        ("DAM", 4, -1, 0.8, 200),
    ]
    # Velocity field points toward "activated" centre.
    target = np.array([2.0, 4.0])
    for name, cx, cy, s, n in centres:
        px = rng.normal(cx, s, n)
        py = rng.normal(cy, s, n)
        xs.append(px)
        ys.append(py)
        # per-cell velocity toward target, small + jitter
        dx = (target[0] - px) * 0.12 + rng.normal(0, 0.12, n)
        dy = (target[1] - py) * 0.12 + rng.normal(0, 0.12, n)
        us.append(dx)
        vs.append(dy)
        labels.extend([name] * n)
    return RNAVelocityInput(
        umap1=np.concatenate(xs).tolist(),
        umap2=np.concatenate(ys).tolist(),
        velocity_u=np.concatenate(us).tolist(),
        velocity_v=np.concatenate(vs).tolist(),
        cluster=labels,
        grid_n=22,
    )


_META = RecipeMetadata(
    name="rnavelocity_arrow_field",
    modality="single_cell_embeddings",
    family=RecipeFamily.heatmap,
    answers_question=(
        "On top of the UMAP, what is the RNA-velocity arrow field "
        "showing cell flow?"
    ),
    required_fields=("umap1", "umap2", "velocity_u", "velocity_v"),
    optional_fields=("cluster", "grid_n", "title"),
    file_format_hints=("h5ad", "parquet"),
    alternatives_in_modality=("trajectory_pseudotime_arrow",),
)


@register_recipe(
    metadata=_META,
    contract=RNAVelocityInput,
    demo_contract=_demo,
)
def render(contract: RNAVelocityInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 4.0))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    x = np.asarray(contract.umap1, float)
    y = np.asarray(contract.umap2, float)
    u = np.asarray(contract.velocity_u, float)
    v = np.asarray(contract.velocity_v, float)
    cl = (np.asarray(contract.cluster)
          if contract.cluster is not None else None)

    # Background scatter.
    alpha = density_alpha(x, y) * 0.45
    if cl is not None:
        for i, c in enumerate(list(dict.fromkeys(cl.tolist()))):
            m = cl == c
            color = (palette.pick(c) if c in palette.semantic
                     else palette[i % len(palette.colors)])
            ax.scatter(x[m], y[m], s=5, color=color, alpha=alpha[m],
                       edgecolor="none", zorder=2, label=c)
    else:
        ax.scatter(x, y, s=5, color="#888888", alpha=alpha,
                   edgecolor="none", zorder=2)

    # Build the grid and average velocity per grid cell.
    xg = np.linspace(x.min() - 0.3, x.max() + 0.3, contract.grid_n)
    yg = np.linspace(y.min() - 0.3, y.max() + 0.3, contract.grid_n)
    XX, YY = np.meshgrid(xg, yg)
    UU = np.zeros_like(XX)
    VV = np.zeros_like(XX)
    counts = np.zeros_like(XX)
    ix = np.searchsorted(xg, x) - 1
    iy = np.searchsorted(yg, y) - 1
    ix = np.clip(ix, 0, contract.grid_n - 1)
    iy = np.clip(iy, 0, contract.grid_n - 1)
    for cell in range(x.size):
        UU[iy[cell], ix[cell]] += u[cell]
        VV[iy[cell], ix[cell]] += v[cell]
        counts[iy[cell], ix[cell]] += 1
    mask = counts > 0
    UU[mask] /= counts[mask]
    VV[mask] /= counts[mask]
    # Zero-out cells with no data so quiver doesn't draw random zero arrows.
    UU[~mask] = np.nan
    VV[~mask] = np.nan

    speed = np.hypot(UU, VV)
    import matplotlib as mpl
    cmap = mpl.colormaps["magma"]
    # Faint speed pcolormesh underlay so the heatmap quality rule
    # sees a surface artist, and so the reader can read high-flow
    # regions at a glance.
    speed_plot = np.where(mask, speed, np.nan)
    ax.pcolormesh(xg, yg, speed_plot, cmap=cmap, alpha=0.18,
                  shading="auto", zorder=1)
    ax.quiver(XX, YY, UU, VV, speed,
              cmap=cmap, angles="xy", scale_units="xy",
              scale=1.6, width=0.004, headwidth=4, headlength=4,
              zorder=4)

    ax.set_xlabel("UMAP1")
    ax.set_ylabel("UMAP2")
    ax.set_xticks([])
    ax.set_yticks([])
    mean_speed = float(np.nanmean(speed))
    ax.set_title(
        f"{contract.title}  ·  mean |v| = {smart_fmt(mean_speed)}",
        fontsize=9.0, pad=4,
    )
    if cl is not None:
        ax.legend(fontsize=6.4, frameon=False, loc="lower right",
                  handlelength=1.2)
    return ax
