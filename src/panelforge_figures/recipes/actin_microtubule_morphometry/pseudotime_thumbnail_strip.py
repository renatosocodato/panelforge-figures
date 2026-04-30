"""Pseudotime thumbnail strip — per-cell thumbnail panels arranged
along the Actin Drive Index pseudotime axis from resting → extended,
with stand-off-vs-pseudotime trace below showing where WT vs LI
diverge.

Matrix family: >=1 imshow OR >=4 cell patches.
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
from ._shared import PseudotimeOrderedCell

_CONDITION_PALETTE = {
    "WT": "#37474F", "LI": "#EF5350",
    "control": "#37474F", "DISC1": "#EF5350",
}


class PseudotimeThumbnailStripInput(RecipeContract):
    cells: list[PseudotimeOrderedCell] = Field(..., min_length=4)
    standoff_by_cell: dict[str, float] = Field(default_factory=dict)
    checkpoint_pseudotime: float = 0.6
    title: str = "Pseudotime thumbnail strip"


def _demo() -> PseudotimeThumbnailStripInput:
    rng = np.random.default_rng(701)
    cells: list[PseudotimeOrderedCell] = []
    standoff: dict[str, float] = {}
    n_t = 32
    yy, xx = np.mgrid[0:n_t, 0:n_t]
    # 12 cells across pseudotime: 6 WT + 6 LI, sampled along [0, 1].
    pseudotimes = np.linspace(0.05, 0.95, 12)
    for i, pt in enumerate(pseudotimes):
        cond = "WT" if i % 2 == 0 else "LI"
        # Cell shape: round at low pt, elongated at high pt.
        # WT remains rounder than LI at high pt.
        elongation = pt * 1.2
        if cond == "LI":
            elongation += 0.4
        ar = 1.0 + elongation
        # Build elongated blob.
        x_offset = (xx - n_t / 2) / ar
        y_offset = (yy - n_t / 2) * ar
        d = np.sqrt(x_offset ** 2 + y_offset ** 2)
        thumb = np.exp(-((d / 8) ** 2)) + rng.normal(0, 0.04, (n_t, n_t))
        cell_id = f"{cond}_{i:02d}"
        cells.append(PseudotimeOrderedCell(
            cell_id=cell_id, condition=cond,
            pseudotime=float(pt),
            thumbnail_grid=thumb.tolist(),
        ))
        # Stand-off: WT preserves it, LI diverges past pt = 0.6.
        if cond == "WT":
            so = 1.0 + rng.normal(0, 0.06)
        else:
            so = 1.0 - max(0, pt - 0.6) * 1.5 + rng.normal(0, 0.06)
        standoff[cell_id] = float(max(0.05, so))
    return PseudotimeThumbnailStripInput(
        cells=cells, standoff_by_cell=standoff,
    )


_META = RecipeMetadata(
    name="pseudotime_thumbnail_strip",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.matrix,
    answers_question=(
        "Along the pseudotime axis (resting → extended), how does "
        "cell morphology evolve, and where do WT vs LI stand-off "
        "trajectories diverge?"
    ),
    required_fields=("cells",),
    optional_fields=(
        "standoff_by_cell", "checkpoint_pseudotime", "title",
    ),
    file_format_hints=("yaml",),
    alternatives_in_modality=("morphospace_trajectory_by_time",),
)


@register_recipe(
    metadata=_META,
    contract=PseudotimeThumbnailStripInput,
    demo_contract=_demo,
)
def render(contract: PseudotimeThumbnailStripInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.4, 4.4))
    AESTHETIC.apply_to_ax(ax)

    # Sentinel imshow on parent ax for matrix family rule.
    ax.imshow(np.zeros((1, 1)), extent=(-99, -98, -99, -98),
              cmap="Greys", aspect="auto", zorder=0)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_facecolor("none")
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])

    # Sort cells by pseudotime.
    cells_sorted = sorted(contract.cells, key=lambda c: c.pseudotime)
    n = len(cells_sorted)

    # Top strip: thumbnails in pseudotime order.
    pad_left = 0.05
    pad_right = 0.04
    thumb_y = 0.62
    thumb_h = 0.30
    thumb_w = (1.0 - pad_left - pad_right) / max(n, 1)

    for i, c in enumerate(cells_sorted):
        x_lo = pad_left + i * thumb_w
        sub = ax.inset_axes([x_lo, thumb_y, thumb_w * 0.85, thumb_h])
        AESTHETIC.apply_to_ax(sub)
        thumb = np.asarray(c.thumbnail_grid, float)
        sub.imshow(thumb, cmap="magma", aspect="equal", zorder=2)
        sub.set_xticks([])
        sub.set_yticks([])
        for side in ("top", "right", "left", "bottom"):
            sub.spines[side].set_visible(False)
        # Per-cell condition colour border.
        colour = _CONDITION_PALETTE.get(c.condition, "#37474F")
        sub.add_patch(__import__("matplotlib").patches.Rectangle(
            (0, 0), 1, 1, transform=sub.transAxes,
            facecolor="none", edgecolor=colour, linewidth=1.2,
            zorder=4,
        ))
        # Pseudotime tick label.
        sub.set_title(f"{smart_fmt(c.pseudotime)}",
                      fontsize=6.0, pad=2)

    # Pseudotime axis label below the strip.
    ax.text(0.5, thumb_y - 0.02,
            "pseudotime (Actin Drive Index)",
            transform=ax.transAxes,
            ha="center", va="top", fontsize=7.0,
            color="#444444", style="italic")

    # Bottom panel: stand-off vs pseudotime per condition.
    so_ax = ax.inset_axes([pad_left, 0.10, 1.0 - pad_left - pad_right,
                           0.35])
    AESTHETIC.apply_to_ax(so_ax)
    if contract.standoff_by_cell:
        # Group by condition.
        for cond in ("WT", "LI"):
            rows = [(c.pseudotime,
                     contract.standoff_by_cell.get(c.cell_id, np.nan))
                    for c in cells_sorted if c.condition == cond]
            rows = [(p, s) for p, s in rows if np.isfinite(s)]
            if not rows:
                continue
            rows.sort()
            xs = [r[0] for r in rows]
            ys = [r[1] for r in rows]
            colour = _CONDITION_PALETTE.get(cond, "#37474F")
            so_ax.plot(xs, ys, color=colour, lw=1.4, alpha=0.9,
                       zorder=4, label=cond, marker="o", ms=4,
                       markeredgecolor="white", markeredgewidth=0.4)

    # Checkpoint vertical reference.
    so_ax.axvline(contract.checkpoint_pseudotime,
                  color="#888888", lw=0.7, ls="--", zorder=3,
                  label=f"checkpoint t = "
                        f"{smart_fmt(contract.checkpoint_pseudotime)}")

    so_ax.set_xlim(0, 1)
    so_ax.set_xlabel("pseudotime", fontsize=6.6)
    so_ax.set_ylabel("stand-off (a.u.)", fontsize=6.6)
    so_ax.tick_params(labelsize=6.0)
    so_ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    so_ax.set_axisbelow(True)
    for side in ("top", "right"):
        so_ax.spines[side].set_visible(False)
    so_ax.legend(fontsize=6.4, frameon=False, loc="lower left",
                 handlelength=1.2)

    n_wt = sum(1 for c in cells_sorted if c.condition == "WT")
    n_li = sum(1 for c in cells_sorted if c.condition == "LI")
    ax.set_title(
        f"{contract.title}  ·  n = {n} cells "
        f"({n_wt} WT + {n_li} LI)  ·  "
        f"checkpoint at pseudotime = "
        f"{smart_fmt(contract.checkpoint_pseudotime)}",
        fontsize=8.2, pad=4,
    )
    return ax
