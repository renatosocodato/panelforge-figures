"""Per-cell thumbnail grid with inline metric callouts + scale bar per row."""

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


class CellThumbnailGridInput(RecipeContract):
    cell_thumbnails: list[list[list[float]]] = Field(
        ..., description="list of 2-D arrays (one per cell)"
    )
    cell_metric_labels: list[str] = Field(
        ..., description="one-line metric summary per cell (e.g. 'A=245 μm², φ=0.78')"
    )
    cell_condition: list[str] | None = Field(
        None, description="per-cell condition label (drives row grouping if provided)"
    )
    pixel_size_um: float = 0.3
    scale_bar_um: float = 5.0
    title: str = "Per-cell thumbnails"


def _demo() -> CellThumbnailGridInput:
    rng = np.random.default_rng(741)
    H, W = 42, 42
    yy, xx = np.mgrid[:H, :W]
    thumbs: list[list[list[float]]] = []
    labels: list[str] = []
    conditions: list[str] = []
    for idx in range(16):
        cond = ["control", "mutant", "rescue", "double_ko"][idx // 4]
        # Synthesise a rough cell body + 2-3 processes pointing random ways.
        cx, cy = W // 2 + rng.integers(-3, 4), H // 2 + rng.integers(-3, 4)
        r_body = rng.uniform(5.5, 8.5)
        img = np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (r_body ** 2))
        n_proc = int(rng.integers(2, 5))
        for _ in range(n_proc):
            theta = rng.uniform(0, 2 * np.pi)
            length = rng.uniform(10, 18)
            for t in np.linspace(0, length, 40):
                px = cx + t * np.cos(theta)
                py = cy + t * np.sin(theta)
                if 0 <= px < W and 0 <= py < H:
                    img += 0.9 * np.exp(-((xx - px) ** 2 + (yy - py) ** 2) / 3.0)
        img = img / max(img.max(), 1e-9)
        img = img + rng.normal(0, 0.02, img.shape)
        thumbs.append(img.tolist())
        area = float(np.sum(img > 0.3) * 0.09)  # px × (0.3 μm)²
        sph = float(rng.uniform(0.45, 0.88))
        labels.append(f"A = {smart_fmt(area)} μm²,  φ = {smart_fmt(sph)}")
        conditions.append(cond)
    return CellThumbnailGridInput(
        cell_thumbnails=thumbs,
        cell_metric_labels=labels,
        cell_condition=conditions,
    )


_META = RecipeMetadata(
    name="per_cell_thumbnail_grid_with_metrics",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.matrix,
    answers_question=(
        "What do individual segmented cells look like, and how do their "
        "shape-descriptor values compare at a glance?"
    ),
    required_fields=("cell_thumbnails", "cell_metric_labels"),
    optional_fields=("cell_condition", "pixel_size_um", "scale_bar_um", "title"),
    file_format_hints=("tif", "npz"),
    alternatives_in_modality=("protrusion_length_velocity_joint",),
)


@register_recipe(
    metadata=_META,
    contract=CellThumbnailGridInput,
    demo_contract=_demo,
)
def render(contract: CellThumbnailGridInput, ax=None, **_):
    import matplotlib.pyplot as plt

    n = len(contract.cell_thumbnails)
    ncols = 4
    nrows = (n + ncols - 1) // ncols

    if ax is None:
        fig = plt.figure(figsize=(5.6, 5.2))
        gs = fig.add_gridspec(nrows, ncols, wspace=0.10, hspace=0.22)
        axes = [fig.add_subplot(gs[r, c])
                for r in range(nrows) for c in range(ncols)]
    else:
        fig = ax.figure
        pos = ax.get_subplotspec()
        ax.remove()
        sub = pos.subgridspec(nrows, ncols, wspace=0.10, hspace=0.22)
        axes = [fig.add_subplot(sub[r, c])
                for r in range(nrows) for c in range(ncols)]
    AESTHETIC.apply_to_fig(fig)
    for ai in axes:
        AESTHETIC.apply_to_ax(ai)

    for k, ai in enumerate(axes):
        if k >= n:
            ai.axis("off")
            continue
        img = np.asarray(contract.cell_thumbnails[k], float)
        ai.imshow(img, cmap="gray_r", aspect="equal", interpolation="bilinear")
        ai.set_xticks([])
        ai.set_yticks([])
        for side in ("top", "right", "left", "bottom"):
            ai.spines[side].set_visible(False)
        # Condition label (upper-left) + metric callout (under thumbnail).
        if contract.cell_condition is not None and k < len(contract.cell_condition):
            ai.text(0.04, 0.96, contract.cell_condition[k],
                    transform=ai.transAxes, ha="left", va="top",
                    fontsize=6.0, color="white",
                    bbox=dict(boxstyle="round,pad=0.14", fc="#333333",
                              ec="none", alpha=0.8))
        ai.text(0.5, -0.06, contract.cell_metric_labels[k],
                transform=ai.transAxes, ha="center", va="top",
                fontsize=5.8, color="#222222")

        # Scale bar on the first column of each row.
        col = k % ncols
        if col == 0:
            H, W = img.shape
            px = contract.pixel_size_um
            bar_len_px = contract.scale_bar_um / max(px, 1e-6)
            ai.plot([W * 0.08, W * 0.08 + bar_len_px],
                    [H * 0.92, H * 0.92],
                    color="white", lw=2.2, solid_capstyle="butt", zorder=5)
            ai.text(W * 0.08 + bar_len_px / 2, H * 0.88,
                    rf"{smart_fmt(contract.scale_bar_um)} $\mu$m",
                    ha="center", va="top", fontsize=5.6, color="white",
                    bbox=dict(boxstyle="round,pad=0.10", fc="#333333",
                              ec="none", alpha=0.7))

    fig.suptitle(
        f"{contract.title}  ·  {n} cells",
        fontsize=9.0, y=0.995,
    )
    return axes[0]
