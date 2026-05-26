"""Per-cell parameterization heatmap — input layer of a parameterized model.

Rows = cells (color-coded by group), columns = model input parameters, fill = z-scored value.
Use case: when a forward-simulation figure wants an input layer separate
from the simulation outputs themselves, scoped to a single empirical
cohort. Keeps the parameterization-to-validation argument self-contained
in the empirical input distribution.
"""

from __future__ import annotations

from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
)
from ._aesthetic import AESTHETIC


class PerCellParameterizationInput(RecipeContract):
    cell_ids: list[str] = Field(description="Per-cell labels (Y-axis rows)")
    parameter_names: list[str] = Field(description="Per-parameter labels (X-axis cols)")
    values: list[list[float]] = Field(description="Row-major matrix: cells × parameters")
    group_per_cell: list[str] = Field(description="Genotype/group per cell (row color strip)")
    z_score_per_column: bool = True
    title: str = "Per-cell parameterization heatmap"


def _demo() -> PerCellParameterizationInput:
    import random
    rng = random.Random(42)
    cells = [f"WT_{i}" for i in range(7)] + [f"LI_{i}" for i in range(16)]
    params = ["Lp_actin (μm)", "Lp_MT (μm)", "MT coherency",
              "width (μm)", "z-span (μm)", "λ_c (μm)"]
    groups = ["WT"]*7 + ["LI"]*16
    vals = []
    for i, c in enumerate(cells):
        bias = 0.2 if "LI" in c else -0.2
        vals.append([rng.gauss(bias, 1.0) for _ in params])
    return PerCellParameterizationInput(
        cell_ids=cells, parameter_names=params, values=vals,
        group_per_cell=groups,
        title="Per-cell parameterization (z-scored)",
    )


_META = RecipeMetadata(
    name="per_cell_parameterization_heatmap",
    modality="meta_and_diagnostic",
    family=RecipeFamily.heatmap,
    answers_question="What are the per-cell input parameter values that feed a parameterized model?",
    required_fields=("cell_ids", "parameter_names", "values", "group_per_cell"),
    optional_fields=("z_score_per_column", "title"),
    file_format_hints=("csv", "json"),
    alternatives_in_modality=("pca_loadings_heatmap", "data_quality_heatmap"),
)


@register_recipe(metadata=_META, contract=PerCellParameterizationInput, demo_contract=_demo)
def render(contract: PerCellParameterizationInput, ax=None, **_):
    import matplotlib.patches as mpatches
    import matplotlib.pyplot as plt
    import numpy as np

    if ax is None:
        fig, ax = plt.subplots(figsize=(9, 7.5))
    else:
        fig = ax.figure
    AESTHETIC.apply_to_ax(ax)
    ax.axis("off")

    vals = np.asarray(contract.values, dtype=float)
    n_cells, n_params = vals.shape

    if contract.z_score_per_column:
        col_mean = np.nanmean(vals, axis=0, keepdims=True)
        col_std = np.nanstd(vals, axis=0, keepdims=True) + 1e-12
        zvals = (vals - col_mean) / col_std
    else:
        zvals = vals.copy()

    # Two-column layout: narrow row-color strip on the left + heatmap
    gs = fig.add_gridspec(1, 2, width_ratios=[0.04, 1.0], wspace=0.02,
                          left=0.18, right=0.92, top=0.92, bottom=0.10)
    ax_grp = fig.add_subplot(gs[0, 0])
    ax_main = fig.add_subplot(gs[0, 1])

    # Row color strip
    groups = list(contract.group_per_cell)
    unique_groups = sorted(set(groups))
    group_colors = {g: c for g, c in zip(unique_groups, ["#1f6f8b", "#c0392b", "#5b8aa4", "#e58e7d"])}
    grp_matrix = np.array([[unique_groups.index(g)] for g in groups])
    ax_grp.imshow(grp_matrix, aspect="auto", cmap=plt.cm.RdYlBu_r,
                   extent=[0, 1, n_cells - 0.5, -0.5], interpolation="nearest")
    # Override with explicit colors
    for i, g in enumerate(groups):
        ax_grp.add_patch(mpatches.Rectangle((0, i - 0.5), 1, 1,
                                              facecolor=group_colors[g],
                                              edgecolor="white", linewidth=0.3))
    ax_grp.set_xlim(0, 1)
    ax_grp.set_ylim(n_cells - 0.5, -0.5)
    ax_grp.set_xticks([])
    ax_grp.set_yticks(range(n_cells))
    ax_grp.set_yticklabels(contract.cell_ids, fontsize=7.0)
    ax_grp.tick_params(axis="y", length=0)
    for s in ax_grp.spines.values():
        s.set_visible(False)

    # Main heatmap
    vmax = float(np.nanmax(np.abs(zvals)))
    vmax = max(vmax, 2.5)
    im = ax_main.imshow(zvals, aspect="auto", cmap="RdBu_r",
                         vmin=-vmax, vmax=vmax, interpolation="nearest")
    ax_main.set_xticks(range(n_params))
    ax_main.set_xticklabels(contract.parameter_names, rotation=25, ha="right", fontsize=9.0)
    ax_main.set_yticks([])
    for s in ax_main.spines.values():
        s.set_color("#bbb")
        s.set_linewidth(0.4)

    # Colorbar
    cbar = fig.colorbar(im, ax=ax_main, fraction=0.05, pad=0.02, shrink=0.7)
    cbar.set_label("z-score" if contract.z_score_per_column else "value",
                   fontsize=9.0)
    cbar.ax.tick_params(labelsize=8)

    # Group legend — upper-right corner to avoid x-axis label collision
    handles = [mpatches.Patch(color=group_colors[g], label=g) for g in unique_groups]
    fig.legend(handles=handles, fontsize=9.0, frameon=True, framealpha=0.9,
               edgecolor="#bbb", loc="upper right", ncol=len(unique_groups),
               bbox_to_anchor=(0.98, 0.97), title="genotype",
               title_fontsize=8.4)

    fig.suptitle(contract.title, fontsize=9.6, color="#2c3e50", y=0.99)
    return ax
