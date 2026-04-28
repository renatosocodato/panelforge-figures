"""Protrusion outline + Cleveland summary — left-side icons of
representative protrusion outlines (one per condition) and a
right-side Cleveland strip plot of per-cell protrusion width and
erosion-depth scalars.

Scatter-collapse family: >=1 scatter + >=1 fit line.
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
from ._shared import ProtrusionOutlineWithCleveland

_CONDITION_PALETTE = {
    "WT": "#37474F", "LI": "#EF5350",
    "control": "#37474F", "DISC1": "#EF5350",
}


class ProtrusionOutlineClevelandInput(RecipeContract):
    cells: list[ProtrusionOutlineWithCleveland] = Field(..., min_length=4)
    title: str = "Protrusion outline + Cleveland summary"


def _demo() -> ProtrusionOutlineClevelandInput:
    rng = np.random.default_rng(611)
    cells: list[ProtrusionOutlineWithCleveland] = []
    # WT: wide protrusions (width ~ 4 um), shallow erosion (~ 1 um).
    # LI: narrow protrusions (width ~ 2 um), deeper erosion (~ 2.2 um).
    for cond, w_mu, e_mu, n in (
        ("WT", 4.0, 1.0, 8),
        ("LI", 2.1, 2.2, 8),
    ):
        for k in range(n):
            w = float(max(0.5, rng.normal(w_mu, w_mu * 0.18)))
            e_d = float(max(0.2, rng.normal(e_mu, e_mu * 0.20)))
            # Outline: tapered teardrop.  Wider at base, narrower at tip.
            # Build per-side polyline.
            n_pts = 24
            t = np.linspace(0, 1, n_pts)
            # Half-width along length (tapers from base to tip).
            half_w = (w / 2.0) * (1.0 - 0.85 * t ** 2)
            # Length scaled to 6 um.
            length = 6.0
            xs = np.concatenate([
                t * length,
                (1.0 - t)[::-1] * length,
            ])
            ys = np.concatenate([
                half_w,
                (-half_w)[::-1],
            ])
            outline = list(zip(xs.tolist(), ys.tolist()))
            cells.append(ProtrusionOutlineWithCleveland(
                cell_id=f"{cond}_{k:02d}",
                condition=cond,
                outline_xy=[[float(p[0]), float(p[1])] for p in outline],
                width_um=w, erosion_depth_um=e_d,
            ))
    return ProtrusionOutlineClevelandInput(cells=cells)


_META = RecipeMetadata(
    name="protrusion_outline_with_cleveland_summary",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "Per condition, how do representative protrusion outlines "
        "differ, and how do per-cell width / erosion-depth scalars "
        "distribute on a Cleveland strip plot?"
    ),
    required_fields=("cells",),
    optional_fields=("title",),
    file_format_hints=("yaml",),
    alternatives_in_modality=("cell_shape_descriptors_by_state",),
)


@register_recipe(
    metadata=_META,
    contract=ProtrusionOutlineClevelandInput,
    demo_contract=_demo,
)
def render(contract: ProtrusionOutlineClevelandInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.4, 3.8))
    AESTHETIC.apply_to_ax(ax)

    # Sentinel scatter + line (real data on insets).
    ax.scatter([], [], s=1)
    ax.plot([], [], color="none", lw=0.5, alpha=0.0)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])

    conditions = list(dict.fromkeys(c.condition for c in contract.cells))

    # --- Left third: representative outline icons (one per condition). ---
    icon_ax = ax.inset_axes([0.02, 0.10, 0.30, 0.80])
    AESTHETIC.apply_to_ax(icon_ax)
    icon_ax.set_aspect("equal")
    icon_ax.set_xticks([])
    icon_ax.set_yticks([])
    for side in ("top", "right", "left", "bottom"):
        icon_ax.spines[side].set_visible(False)

    # Stack representative outlines vertically.
    y_offset = 0.0
    icon_extents_x = []
    for cond in conditions:
        # First cell of each condition is the representative.
        rep = next((c for c in contract.cells if c.condition == cond), None)
        if rep is None:
            continue
        outline = np.asarray(rep.outline_xy, float)
        ox = outline[:, 0]
        oy = outline[:, 1] + y_offset
        colour = _CONDITION_PALETTE.get(cond, "#37474F")
        from matplotlib.patches import Polygon
        icon_ax.add_patch(Polygon(
            np.column_stack([ox, oy]),
            facecolor=colour, alpha=0.55,
            edgecolor=colour, linewidth=1.0, zorder=4,
        ))
        icon_ax.text(-1.5, y_offset, cond,
                     ha="right", va="center", fontsize=7.0,
                     color=colour, fontweight="bold")
        icon_extents_x.append((ox.min(), ox.max()))
        y_offset -= 4.0

    if icon_extents_x:
        x_lo = min(p[0] for p in icon_extents_x) - 1.5
        x_hi = max(p[1] for p in icon_extents_x) + 0.5
        icon_ax.set_xlim(x_lo, x_hi)
        icon_ax.set_ylim(y_offset + 1, 2.0)
    icon_ax.set_title("representative outlines",
                      fontsize=6.6, pad=2)

    # --- Right two-thirds: Cleveland strip for width + erosion depth. ---
    cleveland_ax = ax.inset_axes([0.40, 0.18, 0.55, 0.72])
    AESTHETIC.apply_to_ax(cleveland_ax)

    rows = []
    for cond in conditions:
        for c in contract.cells:
            if c.condition == cond:
                rows.append(c)

    n_rows = len(rows)
    y_pos = np.arange(n_rows)

    bits = []
    for cond in conditions:
        widths = np.array([c.width_um for c in contract.cells
                           if c.condition == cond])
        erosions = np.array([c.erosion_depth_um for c in contract.cells
                             if c.condition == cond])
        bits.append(f"{cond}: width "
                    f"{smart_fmt(float(np.median(widths)))} um, "
                    f"erosion {smart_fmt(float(np.median(erosions)))} um")

    # Plot per-cell points (width on left axis, erosion on parallel
    # twin axis).  Use a single shared scatter axis with two
    # x-coordinates: the cell index for spacing, but plot width and
    # erosion as separate dot families on a single y-row each.
    for i, cell in enumerate(rows):
        colour = _CONDITION_PALETTE.get(cell.condition, "#37474F")
        cleveland_ax.scatter([cell.width_um], [i],
                             s=44, marker="o",
                             facecolor=colour, edgecolor="white",
                             linewidth=0.6, zorder=5)
        cleveland_ax.scatter([cell.erosion_depth_um + 6.5], [i],
                             s=44, marker="s",
                             facecolor=colour, edgecolor="white",
                             linewidth=0.6, zorder=5)

    # Reference vertical line at zero (and at boundary between width
    # and erosion strips).
    cleveland_ax.axvline(0, color="#888888", lw=0.4, zorder=2)
    cleveland_ax.axvline(6.0, color="#CCCCCC", lw=0.6, ls="--",
                         zorder=2)

    cleveland_ax.set_yticks(y_pos)
    cleveland_ax.set_yticklabels([c.cell_id for c in rows],
                                 fontsize=6.0)
    cleveland_ax.invert_yaxis()
    cleveland_ax.set_xticks([0, 2, 4, 6, 6.5, 8.5, 10.5])
    cleveland_ax.set_xticklabels(
        ["0", "2", "4", "6", "0", "2", "4"], fontsize=6.4,
    )
    cleveland_ax.set_xlabel(
        "width (um)            erosion depth (um)",
        fontsize=6.6,
    )
    cleveland_ax.tick_params(axis="x", which="major", pad=2)
    cleveland_ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    cleveland_ax.set_axisbelow(True)
    for side in ("top", "right"):
        cleveland_ax.spines[side].set_visible(False)

    # Legend (marker shape).
    from matplotlib.lines import Line2D
    handles = [
        Line2D([0], [0], marker="o", color="none",
               markerfacecolor="#888888", markeredgecolor="white",
               markersize=6, label="width"),
        Line2D([0], [0], marker="s", color="none",
               markerfacecolor="#888888", markeredgecolor="white",
               markersize=6, label="erosion depth"),
    ]
    cleveland_ax.legend(handles=handles, fontsize=6.4,
                        frameon=False, loc="lower right",
                        handlelength=1.0)

    ax.set_title(
        f"{contract.title}  ·  " + "   ".join(bits),
        fontsize=8.2, pad=4,
    )
    return ax
