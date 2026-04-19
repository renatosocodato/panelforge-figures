"""Airyscan raw + segmentation mosaic — 2-column grid with mandatory scale bars."""

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


class AiryscanCell(RecipeContract):
    cell_id: str
    raw_image: list[list[float]]
    segmentation_mask: list[list[float]]
    condition: str | None = None


class AiryscanMosaicInput(RecipeContract):
    cells: list[AiryscanCell] = Field(..., min_length=2)
    pixel_size_um: float = 0.05
    scale_bar_um: float = 2.0
    title: str = "Airyscan raw / segmentation"


def _demo() -> AiryscanMosaicInput:
    rng = np.random.default_rng(831)
    H, W = 48, 64
    yy, xx = np.mgrid[:H, :W]
    cells: list[AiryscanCell] = []
    conditions = ["control", "mutant", "rescue", "double_ko"]
    for idx in range(4):
        cx, cy = W // 2 + rng.integers(-3, 4), H // 2 + rng.integers(-3, 4)
        r_body = rng.uniform(6.0, 10.0)
        raw = np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (r_body ** 2))
        n_proc = int(rng.integers(3, 6))
        for _ in range(n_proc):
            theta = rng.uniform(0, 2 * np.pi)
            for t in np.linspace(0, 18, 60):
                px = cx + t * np.cos(theta)
                py = cy + t * np.sin(theta)
                if 0 <= px < W and 0 <= py < H:
                    raw += 0.85 * np.exp(-((xx - px) ** 2 + (yy - py) ** 2) / 3.0)
        raw = raw / max(raw.max(), 1e-9) + rng.normal(0, 0.02, (H, W))
        # Segmentation: binary mask thresholded.
        mask = (raw > 0.20).astype(float)
        cells.append(AiryscanCell(
            cell_id=f"c{idx + 1:02d}",
            raw_image=raw.tolist(),
            segmentation_mask=mask.tolist(),
            condition=conditions[idx],
        ))
    return AiryscanMosaicInput(cells=cells)


_META = RecipeMetadata(
    name="airyscan_segmentation_mosaic",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.matrix,
    answers_question=(
        "What do multi-cell Airyscan raw images look like side-by-side with "
        "their segmentations, with mandatory scale bars?"
    ),
    required_fields=("cells",),
    optional_fields=("pixel_size_um", "scale_bar_um", "title"),
    file_format_hints=("tif", "npz"),
    alternatives_in_modality=("per_cell_thumbnail_grid_with_metrics",),
)


@register_recipe(
    metadata=_META,
    contract=AiryscanMosaicInput,
    demo_contract=_demo,
)
def render(contract: AiryscanMosaicInput, ax=None, **_):
    import matplotlib.pyplot as plt

    n = len(contract.cells)
    nrows = n
    ncols = 2   # raw / segmentation

    if ax is None:
        fig = plt.figure(figsize=(5.0, max(3.0, 1.2 * n)))
        gs = fig.add_gridspec(nrows, ncols, wspace=0.06, hspace=0.24)
        axes = [[fig.add_subplot(gs[r, c]) for c in range(ncols)]
                for r in range(nrows)]
    else:
        fig = ax.figure
        pos = ax.get_subplotspec()
        ax.remove()
        sub = pos.subgridspec(nrows, ncols, wspace=0.06, hspace=0.24)
        axes = [[fig.add_subplot(sub[r, c]) for c in range(ncols)]
                for r in range(nrows)]
    AESTHETIC.apply_to_fig(fig)
    for row in axes:
        for ai in row:
            AESTHETIC.apply_to_ax(ai)

    for r, cell in enumerate(contract.cells):
        raw = np.asarray(cell.raw_image, float)
        mask = np.asarray(cell.segmentation_mask, float)
        ax_raw = axes[r][0]
        ax_seg = axes[r][1]

        ax_raw.imshow(raw, cmap="gray_r", aspect="equal",
                      interpolation="bilinear")
        ax_seg.imshow(mask, cmap="Greys", aspect="equal",
                      interpolation="nearest")

        for ai in (ax_raw, ax_seg):
            ai.set_xticks([])
            ai.set_yticks([])
            for side in ("top", "right", "left", "bottom"):
                ai.spines[side].set_visible(False)

        # Row header: cell ID + condition.
        header = cell.cell_id if cell.condition is None else f"{cell.cell_id} · {cell.condition}"
        ax_raw.text(-0.06, 0.5, header, transform=ax_raw.transAxes,
                    ha="right", va="center", fontsize=6.8, color="#111111")

        # Column headers (top row only).
        if r == 0:
            ax_raw.set_title("raw Airyscan", fontsize=7.4, pad=3, color="#111111")
            ax_seg.set_title("segmentation", fontsize=7.4, pad=3, color="#111111")

        # Scale bar on the raw image of every row.
        H, W = raw.shape
        bar_len_px = contract.scale_bar_um / max(contract.pixel_size_um, 1e-6)
        ax_raw.plot([W * 0.06, W * 0.06 + bar_len_px],
                    [H * 0.94, H * 0.94],
                    color="white", lw=2.2, solid_capstyle="butt", zorder=5)
        ax_raw.text(W * 0.06 + bar_len_px + W * 0.04, H * 0.94,
                    rf"{smart_fmt(contract.scale_bar_um)} $\mu$m",
                    ha="left", va="center", fontsize=5.8, color="white",
                    bbox=dict(boxstyle="round,pad=0.10", fc="#333333",
                              ec="none", alpha=0.7), zorder=6)

    fig.suptitle(
        f"{contract.title}  ·  {n} cells",
        fontsize=9.0, y=0.995,
    )
    return axes[0][0]
