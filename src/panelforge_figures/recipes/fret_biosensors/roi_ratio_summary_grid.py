"""ROI ratio summary grid — ROI × timepoint matrix with mean/CV overlay."""

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


class ROISummaryInput(RecipeContract):
    roi_ids: list[str]
    timepoints: list[str]
    ratio_matrix: list[list[float]] = Field(
        ..., description="matrix[roi][t] = F_A/F_D at that ROI and time"
    )
    title: str = "ROI ratio summary"


def _demo() -> ROISummaryInput:
    rng = np.random.default_rng(211)
    n_roi = 10
    times = ["-30 s", "0 s", "15 s", "30 s", "60 s", "120 s", "240 s"]
    M = 1.0 + rng.normal(0, 0.03, (n_roi, len(times)))
    # Build response pattern (high responders on top).
    response = np.outer(np.linspace(0, 0.8, n_roi),
                       np.clip(np.arange(len(times)) - 1, 0, None) / len(times))
    M = M + response
    return ROISummaryInput(
        roi_ids=[f"ROI {i+1:02d}" for i in range(n_roi)],
        timepoints=times,
        ratio_matrix=M.tolist(),
    )


_META = RecipeMetadata(
    name="roi_ratio_summary_grid",
    modality="fret_biosensors",
    family=RecipeFamily.heatmap,
    answers_question="How does the FRET ratio behave across ROIs and timepoints, at a glance?",
    required_fields=("roi_ids", "timepoints", "ratio_matrix"),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("ratio_heatmap_over_field",),
)


@register_recipe(metadata=_META, contract=ROISummaryInput, demo_contract=_demo)
def render(contract: ROISummaryInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.6))
    AESTHETIC.apply_to_ax(ax)

    M = np.array(contract.ratio_matrix, dtype=float)
    vmax = max(abs(M.max() - 1.0), abs(M.min() - 1.0))
    im = ax.imshow(
        M, cmap=AESTHETIC.ratio_cmap or "RdBu_r",
        vmin=1 - vmax, vmax=1 + vmax,
        aspect="auto", interpolation="nearest",
    )

    # Overlay small numeric values for the largest cell per row (peak time).
    for i in range(M.shape[0]):
        j_peak = int(np.argmax(M[i]))
        ax.scatter([j_peak], [i], s=28, facecolor="none",
                   edgecolor="#111111", linewidth=0.8, zorder=4, marker="o")

    ax.set_xticks(range(len(contract.timepoints)))
    ax.set_xticklabels(contract.timepoints, rotation=30, ha="right", fontsize=6.6)
    ax.set_yticks(range(len(contract.roi_ids)))
    ax.set_yticklabels(contract.roi_ids, fontsize=6.8)
    ax.set_title(
        f"{contract.title}  ·  N ROI = {M.shape[0]},  "
        f"median peak $\\Delta$ratio = "
        f"{smart_fmt(float(np.median(M.max(axis=1) - M[:, 0])))}",
        fontsize=8.4, pad=4,
    )

    # Per-ROI mean, anchored in axes fraction just right of the heatmap so it
    # never bleeds into the colorbar.
    means = M.mean(axis=1)
    trans = ax.get_yaxis_transform()
    for i, m in enumerate(means):
        ax.text(1.015, i, smart_fmt(float(m)),
                transform=trans, ha="left", va="center",
                fontsize=6.0, color="#444444")

    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.12)
    cbar.set_label(r"F$_\mathrm{A}$/F$_\mathrm{D}$", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.2)
    return ax
