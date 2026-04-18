"""Synchronization matrix — pairwise correlation between cells."""

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


class SyncMatrixInput(RecipeContract):
    cell_ids: list[str] = Field(...)
    sync_matrix: list[list[float]] = Field(
        ..., description="symmetric pairwise correlation ∈ [-1, 1]"
    )
    title: str = "Cell-cell synchronization"


def _demo() -> SyncMatrixInput:
    rng = np.random.default_rng(241)
    n = 16
    # Three clusters with strong within-cluster correlation.
    cluster_ids = np.array([i // 6 for i in range(n)])
    C = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            if cluster_ids[i] == cluster_ids[j]:
                base = 0.7 + rng.normal(0, 0.12)
            else:
                base = 0.15 + rng.normal(0, 0.15)
            C[i, j] = C[j, i] = np.clip(base, -0.3, 1.0)
    np.fill_diagonal(C, 1.0)
    return SyncMatrixInput(
        cell_ids=[f"c{i+1:02d}" for i in range(n)],
        sync_matrix=C.tolist(),
    )


_META = RecipeMetadata(
    name="synchronization_matrix",
    modality="calcium_signaling",
    family=RecipeFamily.matrix,
    answers_question="Which cells fire synchronously with which, and are there clusters of coordinated activity?",
    required_fields=("cell_ids", "sync_matrix"),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("event_raster_with_rate",),
)


@register_recipe(metadata=_META, contract=SyncMatrixInput, demo_contract=_demo)
def render(contract: SyncMatrixInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.6, 3.8))
    AESTHETIC.apply_to_ax(ax)

    C = np.array(contract.sync_matrix, dtype=float)
    n = C.shape[0]

    im = ax.imshow(C, cmap="RdBu_r", vmin=-1, vmax=1,
                   aspect="equal", interpolation="nearest")

    ax.set_xticks(range(n))
    ax.set_xticklabels(contract.cell_ids, rotation=45, ha="right", fontsize=5.8)
    ax.set_yticks(range(n))
    ax.set_yticklabels(contract.cell_ids, fontsize=5.8)
    ax.set_title(contract.title, fontsize=9.0, pad=4)

    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("correlation r", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.2)

    # Cluster-size summary via simple threshold.
    off_diag = C[np.triu_indices(n, k=1)]
    mean_r = float(off_diag.mean())
    high_frac = float((off_diag > 0.5).mean())

    ax.text(0.01, -0.16,
            f"mean r = {smart_fmt(mean_r)}   "
            f"fraction r > 0.5 = {smart_fmt(high_frac)}",
            transform=ax.transAxes, ha="left", va="top",
            fontsize=6.4, color="#333333",
            bbox=dict(boxstyle="round,pad=0.18", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=5)
    return ax
