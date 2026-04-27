"""Biosensor activation field per cell — small-multiples of per-cell
intensity grids on a divergent cmap centred on baseline.

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
from ._shared import BiosensorField


class BiosensorActivationFieldInput(RecipeContract):
    fields: list[BiosensorField] = Field(..., min_length=2)
    condition_by_cell: dict[str, str] = Field(default_factory=dict)
    cmap: str = "RdBu_r"
    title: str = "Biosensor activation field per cell"


def _demo() -> BiosensorActivationFieldInput:
    rng = np.random.default_rng(3201)
    fields: list[BiosensorField] = []
    cond_by: dict[str, str] = {}
    n_rows, n_cols = 32, 32
    for cond, hot_offset in (("control", 0.06), ("DISC1", 0.20)):
        for k in range(2):
            cell_id = f"{cond}_C{k:02d}"
            yy, xx = np.mgrid[0:n_rows, 0:n_cols]
            # Hot zone in upper-right (protrusion tip region).
            hot = np.exp(-(((xx - 24) / 4.0) ** 2
                          + ((yy - 8) / 4.0) ** 2))
            grid = 1.0 + hot * hot_offset + rng.normal(0, 0.02,
                                                       (n_rows, n_cols))
            fields.append(BiosensorField(
                cell_id=cell_id,
                sensor_label="ROCK biosensor",
                intensity_grid=grid.tolist(),
                pixel_um=0.5,
                baseline_intensity=1.0,
            ))
            cond_by[cell_id] = cond
    return BiosensorActivationFieldInput(
        fields=fields, condition_by_cell=cond_by,
    )


_META = RecipeMetadata(
    name="biosensor_activation_field_per_cell",
    modality="intravital_imaging",
    family=RecipeFamily.heatmap,
    answers_question=(
        "Where on a cell does the biosensor signal peak above "
        "baseline, and does the spatial pattern differ between "
        "conditions?"
    ),
    required_fields=("fields",),
    optional_fields=("condition_by_cell", "cmap", "title"),
    file_format_hints=("yaml",),
    alternatives_in_modality=("biosensor_dose_response_curve",),
)


@register_recipe(
    metadata=_META,
    contract=BiosensorActivationFieldInput,
    demo_contract=_demo,
)
def render(contract: BiosensorActivationFieldInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.4, 4.4))
    AESTHETIC.apply_to_ax(ax)

    n_panels = len(contract.fields)
    n_cols = min(4, n_panels)
    n_rows = (n_panels + n_cols - 1) // n_cols

    # Sentinel imshow on parent ax so heatmap family rule sees a
    # mesh (data lives on insets).
    ax.imshow(np.zeros((1, 1)), extent=(-99, -98, -99, -98),
              cmap=contract.cmap, aspect="auto", zorder=0)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])

    pad_left = 0.06
    pad_right = 0.10
    pad_bottom = 0.10
    pad_top = 0.16
    h_gap = 0.03
    v_gap = 0.10
    panel_w = (1.0 - pad_left - pad_right - h_gap * (n_cols - 1)) / n_cols
    panel_h = (1.0 - pad_bottom - pad_top - v_gap * (n_rows - 1)) / n_rows

    # Compute global vmin/vmax centred on baseline for divergent cmap.
    all_vals = np.concatenate([
        np.asarray(f.intensity_grid).ravel() for f in contract.fields
    ])
    base = float(np.median([f.baseline_intensity if f.baseline_intensity
                            is not None else 1.0
                            for f in contract.fields]))
    radius = float(max(abs(all_vals.max() - base),
                       abs(base - all_vals.min())))

    last_im = None
    for idx, field in enumerate(contract.fields):
        col = idx % n_cols
        row = idx // n_cols
        x_lo = pad_left + col * (panel_w + h_gap)
        # Inset axes are positioned from bottom-left in axes
        # fraction; flip row order so panel 0 is top-left.
        y_lo = pad_bottom + (n_rows - 1 - row) * (panel_h + v_gap)
        sub = ax.inset_axes([x_lo, y_lo, panel_w, panel_h])
        AESTHETIC.apply_to_ax(sub)
        grid = np.asarray(field.intensity_grid, float)
        im = sub.imshow(grid, cmap=contract.cmap,
                        vmin=base - radius, vmax=base + radius,
                        aspect="equal", zorder=2)
        last_im = im
        sub.set_xticks([])
        sub.set_yticks([])
        cond = contract.condition_by_cell.get(field.cell_id, "")
        sub.set_title(
            f"{field.cell_id}" + (f"  ({cond})" if cond else ""),
            fontsize=6.6, pad=2,
        )

    if last_im is not None:
        cbar_ax = ax.inset_axes([0.93, pad_bottom, 0.02,
                                 1.0 - pad_bottom - pad_top])
        cbar = ax.figure.colorbar(last_im, cax=cbar_ax)
        cbar.set_label(f"intensity / baseline", fontsize=6.6)
        cbar.ax.tick_params(labelsize=6.0)

    sensor_label = contract.fields[0].sensor_label if contract.fields else ""
    ax.set_title(
        f"{contract.title}  ·  {sensor_label}  ·  "
        f"baseline = {smart_fmt(base)}  ·  range +/- {smart_fmt(radius)}",
        fontsize=8.2, pad=4,
    )
    return ax
