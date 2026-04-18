"""Bimodality coefficient grid — condition × timepoint heatmap of BC values."""

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


class BimodalityGridInput(RecipeContract):
    conditions: list[str]
    timepoints: list[str]
    bc_matrix: list[list[float]] = Field(
        ..., description="bc[i][j] = bimodality coefficient for condition i at time j"
    )
    threshold: float = 5 / 9
    title: str = "Bimodality coefficient"


def _demo() -> BimodalityGridInput:
    rng = np.random.default_rng(149)
    conds = ["basal", "+ROCKi", "+SRCi", "+LPS", "+H2O2"]
    times = ["0 min", "15 min", "30 min", "60 min", "120 min"]
    bc = np.clip(
        0.45 + 0.18 * rng.standard_normal((len(conds), len(times))),
        0.2, 0.85,
    )
    # Force LPS row to cross threshold.
    bc[3] = np.clip(bc[3] + 0.15, 0.2, 0.95)
    return BimodalityGridInput(
        conditions=conds,
        timepoints=times,
        bc_matrix=bc.tolist(),
    )


_META = RecipeMetadata(
    name="bimodality_coefficient_grid",
    modality="redox_imaging",
    family=RecipeFamily.heatmap,
    answers_question="Where in the condition × time plane does the single-cell redox distribution become bimodal?",
    required_fields=("conditions", "timepoints", "bc_matrix"),
    optional_fields=("threshold", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("single_cell_ratio_distribution",),
)


@register_recipe(metadata=_META, contract=BimodalityGridInput, demo_contract=_demo)
def render(contract: BimodalityGridInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.6))
    AESTHETIC.apply_to_ax(ax)

    M = np.array(contract.bc_matrix, dtype=float)
    thr = contract.threshold
    # Use diverging cmap centered at threshold for clear "bimodal vs not".
    vmax = max(abs(M.max() - thr), abs(M.min() - thr))
    im = ax.imshow(
        M, cmap=AESTHETIC.ratio_cmap or "RdBu_r",
        vmin=thr - vmax, vmax=thr + vmax,
        aspect="auto", interpolation="nearest",
    )

    # Cell value labels + threshold highlight edge.
    for (i, j), v in np.ndenumerate(M):
        text_color = "white" if abs(v - thr) > 0.15 else "#222222"
        ax.text(j, i, smart_fmt(v), ha="center", va="center",
                fontsize=6.4, color=text_color)
        if v > thr:
            # Outline bimodal cells subtly.
            from matplotlib.patches import Rectangle
            ax.add_patch(Rectangle(
                (j - 0.5, i - 0.5), 1.0, 1.0,
                facecolor="none", edgecolor="#111111",
                linewidth=0.8, zorder=5,
            ))

    ax.set_xticks(range(len(contract.timepoints)))
    ax.set_xticklabels(contract.timepoints, rotation=30, ha="right", fontsize=6.8)
    ax.set_yticks(range(len(contract.conditions)))
    ax.set_yticklabels(contract.conditions, fontsize=7.0)
    ax.set_title(contract.title, fontsize=9.0, pad=4)

    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("bimodality coefficient", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.2)
    cbar.ax.axhline(thr, color="#333333", lw=0.8)

    ax.text(0.01, -0.22,
            f"threshold (Pearson) = {smart_fmt(thr)}; outlined cells are bimodal",
            transform=ax.transAxes, ha="left", va="top",
            fontsize=6.4, color="#444444",
            bbox=dict(boxstyle="round,pad=0.20", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=6)
    return ax
