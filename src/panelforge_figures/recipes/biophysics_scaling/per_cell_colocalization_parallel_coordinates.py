"""Per-cell colocalization parallel coordinates — three vertical
spines (Manders M1, Pearson r, Spearman rho), one polyline per cell
coloured by group, scatter rug at each spine.

Wins over a 3-panel split violin when the *co-movement* of the three
metrics is the finding (Fig. 2c convention). Parallel-coordinates
emphasises within-cell consistency across metrics.

Scatter-collapse family: >=1 scatter + >=1 fit line. Satisfied by
per-spine scatter rugs and the per-cell connecting Line2D segments.
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

_GROUP_COLOURS = {"WT": "#1565C0", "LI": "#C62828",
                  "control": "#1565C0", "treated": "#C62828"}


class ColocPCoordsInput(RecipeContract):
    metrics_by_cell: dict[str, dict[str, float]] = Field(...)
    group_by_cell: dict[str, str] = Field(...)
    axis_order: list[str] = Field(
        default_factory=lambda: ["manders_m1", "pearson_r", "spearman_rho"],
    )
    z_score_within_metric: bool = False
    title: str = "Per-cell colocalization (parallel coords)"


def _demo() -> ColocPCoordsInput:
    rng = np.random.default_rng(7373)
    n = 50
    cells = [f"C{i:03d}" for i in range(n)]
    groups = ["WT"] * (n // 2) + ["LI"] * (n - n // 2)
    metrics_by_cell: dict[str, dict[str, float]] = {}
    for c, g in zip(cells, groups):
        if g == "WT":
            shared = rng.normal(0.66, 0.08)
        else:
            shared = rng.normal(0.50, 0.10)
        m1 = float(np.clip(shared + rng.normal(0, 0.04), 0, 1))
        pr = float(np.clip(shared + rng.normal(0, 0.05), 0, 1))
        sp = float(np.clip(shared + rng.normal(0, 0.05), 0, 1))
        metrics_by_cell[c] = {
            "manders_m1": m1, "pearson_r": pr, "spearman_rho": sp,
        }
    return ColocPCoordsInput(
        metrics_by_cell=metrics_by_cell,
        group_by_cell={c: g for c, g in zip(cells, groups)},
    )


_META = RecipeMetadata(
    name="per_cell_colocalization_parallel_coordinates",
    modality="biophysics_scaling",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "Across cells, do the three colocalization metrics "
        "(Manders M1, Pearson r, Spearman rho) move together, and "
        "does the genotype shift the consensus level?"
    ),
    required_fields=("metrics_by_cell", "group_by_cell"),
    optional_fields=("axis_order", "z_score_within_metric", "title"),
    file_format_hints=("csv",),
    alternatives_in_modality=("shared_manifold_scatter_with_residuals",),
)


@register_recipe(
    metadata=_META,
    contract=ColocPCoordsInput,
    demo_contract=_demo,
)
def render(contract: ColocPCoordsInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.8, 4.0))
    AESTHETIC.apply_to_ax(ax)

    axis_names = list(contract.axis_order)
    n_axes = len(axis_names)
    cells = list(contract.metrics_by_cell.keys())

    # Collect per-axis values, normalize to [0, 1] within each axis
    # using min-max scaling (preserves spread), then plot.
    col_data: dict[str, np.ndarray] = {}
    for axis in axis_names:
        vals = np.array([
            contract.metrics_by_cell[c].get(axis, np.nan)
            for c in cells
        ], float)
        col_data[axis] = vals

    # Normalize per axis (min-max).
    norm: dict[str, np.ndarray] = {}
    for axis, vals in col_data.items():
        v_min = float(np.nanmin(vals))
        v_max = float(np.nanmax(vals))
        if v_max - v_min < 1e-9:
            norm[axis] = np.zeros_like(vals)
        else:
            norm[axis] = (vals - v_min) / (v_max - v_min)

    x_positions = np.arange(n_axes)

    # Per-cell polylines (each is a 'fit line' surrogate).
    for cell, group in contract.group_by_cell.items():
        if cell not in contract.metrics_by_cell:
            continue
        i_cell = cells.index(cell)
        ys = [norm[axis][i_cell] for axis in axis_names]
        colour = _GROUP_COLOURS.get(group, "#333333")
        ax.plot(x_positions, ys, color=colour, lw=0.5, alpha=0.40,
                zorder=3)

    # Per-axis scatter rugs (group-coloured).
    for j, axis in enumerate(axis_names):
        for group in dict.fromkeys(contract.group_by_cell.values()):
            mask_idx = [
                i for i, c in enumerate(cells)
                if contract.group_by_cell.get(c) == group
            ]
            if not mask_idx:
                continue
            ys = norm[axis][mask_idx]
            jitter = (np.linspace(-0.05, 0.05, len(ys))
                      if len(ys) > 1 else np.array([0.0]))
            ax.scatter(np.full(ys.size, j) + jitter, ys, s=14,
                       color=_GROUP_COLOURS.get(group, "#333333"),
                       edgecolor="white", linewidth=0.4, alpha=0.85,
                       zorder=5)

    # Per-group median trace overlaid in bold.
    for group in dict.fromkeys(contract.group_by_cell.values()):
        mask_idx = [
            i for i, c in enumerate(cells)
            if contract.group_by_cell.get(c) == group
        ]
        if not mask_idx:
            continue
        median_y = [float(np.nanmedian(norm[axis][mask_idx]))
                    for axis in axis_names]
        ax.plot(x_positions, median_y,
                color=_GROUP_COLOURS.get(group, "#333333"),
                lw=1.4, zorder=6, label=f"{group} median")

    # Axis labelling.
    ax.set_xticks(x_positions)
    ax.set_xticklabels([a.replace("_", " ") for a in axis_names],
                       fontsize=6.8)
    ax.set_ylabel("metric (min-max normalized)")
    ax.set_xlim(-0.3, n_axes - 0.7)
    ax.set_ylim(-0.05, 1.05)
    ax.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    # Legend below axes — upper-right collides with topmost data
    # markers (parallel-coordinates lines reach y = 1.0).
    ax.legend(fontsize=6.8, frameon=False, loc="upper center",
              bbox_to_anchor=(0.5, -0.10), ncols=2, handlelength=1.2)

    # Per-axis raw-range annotation along the top.
    for j, axis in enumerate(axis_names):
        v_min = float(np.nanmin(col_data[axis]))
        v_max = float(np.nanmax(col_data[axis]))
        ax.text(j, 1.06, f"{smart_fmt(v_min)}..{smart_fmt(v_max)}",
                ha="center", va="bottom", fontsize=6.0,
                color="#555555", clip_on=False, zorder=6)

    # Cross-metric Pearson correlation as a one-line callout.
    keys = axis_names
    correlations = []
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            x = col_data[keys[i]]
            y = col_data[keys[j]]
            mask = np.isfinite(x) & np.isfinite(y)
            if mask.sum() < 3:
                continue
            r = float(np.corrcoef(x[mask], y[mask])[0, 1])
            correlations.append(
                f"r({keys[i].split('_')[0]}, {keys[j].split('_')[0]}) = {smart_fmt(r)}"
            )
    callout = "  ·  ".join(correlations)
    ax.set_title(
        f"{contract.title}  ·  {callout}",
        fontsize=7.8, pad=12,
    )
    return ax
