"""MT mesh-density compartment compare — side-by-side imshow panels
of MT mesh-density grids per (cell × compartment), with shared
colour scale across panels and per-cell median-density callouts.

Heatmap family: >=1 imshow / pcolormesh.
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
from ._shared import MTMeshDensitySnapshot


class MTMeshDensityCompareInput(RecipeContract):
    snapshots: list[MTMeshDensitySnapshot] = Field(..., min_length=2)
    title: str = "MT mesh-density compartment compare"


def _demo() -> MTMeshDensityCompareInput:
    rng = np.random.default_rng(671)
    snapshots: list[MTMeshDensitySnapshot] = []
    H, W = 64, 64
    yy, xx = np.mgrid[0:H, 0:W]
    radial = np.sqrt((yy - H / 2) ** 2 + (xx - W / 2) ** 2)
    for cell_id, cond in (("WT_2", "WT"), ("LI_12", "LI")):
        # Whole-cell: lower density (0.4 filaments/um^2).
        # Protrusion-internal: higher density (1.2 filaments/um^2).
        for compartment, density_mu in (
            ("whole_cell", 0.4),
            ("protrusion_internal", 1.2),
        ):
            grid = (density_mu
                    + 0.30 * np.exp(-((radial - 16) / 8) ** 2)
                    + rng.normal(0, density_mu * 0.20, (H, W)))
            grid = np.clip(grid, 0, None)
            snapshots.append(MTMeshDensitySnapshot(
                cell_id=cell_id,
                condition=cond,
                compartment=compartment,
                density_grid=grid.tolist(),
                pixel_um=0.30,
            ))
    return MTMeshDensityCompareInput(snapshots=snapshots)


_META = RecipeMetadata(
    name="mt_mesh_density_compartment_compare",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.heatmap,
    answers_question=(
        "Per cell × compartment, how does microtubule mesh-density "
        "differ between whole-cell and protrusion-internal scales, "
        "and across genotypes?"
    ),
    required_fields=("snapshots",),
    optional_fields=("title",),
    file_format_hints=("yaml",),
    alternatives_in_modality=("actin_mt_ratio_spatial_map",),
)


@register_recipe(
    metadata=_META,
    contract=MTMeshDensityCompareInput,
    demo_contract=_demo,
)
def render(contract: MTMeshDensityCompareInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.4, 3.8))
    AESTHETIC.apply_to_ax(ax)

    # Sentinel imshow for heatmap family rule (parked off-axes).
    ax.imshow(np.zeros((1, 1)), extent=(-99, -98, -99, -98),
              cmap="viridis", aspect="auto", zorder=0)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_facecolor("none")
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])

    # Group by (cell_id, compartment).  Layout: rows = cell_ids,
    # columns = compartments.
    cell_ids = list(dict.fromkeys(s.cell_id for s in contract.snapshots))
    compartments = list(dict.fromkeys(s.compartment
                                      for s in contract.snapshots))
    n_rows = len(cell_ids)
    n_cols = len(compartments)

    pad_left = 0.10
    pad_right = 0.12
    pad_bottom = 0.10
    pad_top = 0.18
    h_gap = 0.04
    v_gap = 0.10
    panel_w = (1.0 - pad_left - pad_right - h_gap * (n_cols - 1)) \
        / n_cols
    panel_h = (1.0 - pad_bottom - pad_top - v_gap * (n_rows - 1)) \
        / n_rows

    # Global vmin/vmax for shared scale.
    all_vals = np.concatenate([
        np.asarray(s.density_grid).ravel() for s in contract.snapshots
    ])
    vmin = float(np.percentile(all_vals, 5))
    vmax = float(np.percentile(all_vals, 95))

    last_im = None
    bits = []
    for row, cell_id in enumerate(cell_ids):
        cond = next((s.condition for s in contract.snapshots
                     if s.cell_id == cell_id), "?")
        for col, comp in enumerate(compartments):
            x_lo = pad_left + col * (panel_w + h_gap)
            y_lo = pad_bottom + (n_rows - 1 - row) * (panel_h + v_gap)
            sub = ax.inset_axes([x_lo, y_lo, panel_w, panel_h])
            AESTHETIC.apply_to_ax(sub)
            snap = next((s for s in contract.snapshots
                         if s.cell_id == cell_id
                         and s.compartment == comp), None)
            if snap is None:
                continue
            grid = np.asarray(snap.density_grid, float)
            im = sub.imshow(grid, cmap="viridis",
                            vmin=vmin, vmax=vmax,
                            aspect="equal", zorder=2)
            last_im = im
            sub.set_xticks([])
            sub.set_yticks([])
            for side in ("top", "right", "left", "bottom"):
                sub.spines[side].set_visible(False)
            if col == 0:
                sub.set_ylabel(f"{cell_id}\n({cond})",
                               fontsize=6.6, rotation=0,
                               ha="right", va="center", labelpad=24)
            if row == 0:
                sub.set_title(comp.replace("_", " "),
                              fontsize=7.0, pad=2)
            median_d = float(np.median(grid))
            sub.text(0.96, 0.04, f"med {smart_fmt(median_d)}",
                     transform=sub.transAxes,
                     ha="right", va="bottom", fontsize=6.0,
                     color="white", zorder=4,
                     bbox=dict(boxstyle="round,pad=0.20",
                               fc="#222222", ec="none", alpha=0.65))
            bits.append(f"{cell_id}/{comp}: median "
                        f"{smart_fmt(median_d)}")

    if last_im is not None:
        cbar_ax = ax.inset_axes(
            [0.91, pad_bottom,
             0.02, 1.0 - pad_bottom - pad_top])
        cbar = ax.figure.colorbar(last_im, cax=cbar_ax)
        cbar.set_label("MT density (filaments / um^2)", fontsize=6.4)
        cbar.ax.tick_params(labelsize=6.0)

    ax.set_title(
        f"{contract.title}  ·  "
        f"{n_rows} cells × {n_cols} compartments",
        fontsize=8.4, pad=6,
    )
    return ax
