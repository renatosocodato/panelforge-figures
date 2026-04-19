"""Correlation matrix: colocalization metrics × shape metrics with FDR-starred cells."""

from __future__ import annotations

import numpy as np
from pydantic import Field
from scipy import stats

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class CorrelationFDRInput(RecipeContract):
    coloc_metrics: dict[str, list[float]] = Field(
        ..., description="coloc metric name → per-cell values"
    )
    shape_metrics: dict[str, list[float]] = Field(
        ..., description="shape metric name → per-cell values"
    )
    fdr_method: str = "bh"
    title: str = "Colocalization × morphology correlations"


def _demo() -> CorrelationFDRInput:
    rng = np.random.default_rng(783)
    n = 140
    # Latent structure: 'apical_localization' drives both M1 coloc and sphericity.
    z = rng.normal(0, 1, n)
    m1 = 0.4 + 0.7 * z + rng.normal(0, 0.3, n)
    m2 = 0.5 + 0.3 * z + rng.normal(0, 0.35, n)
    pearson = 0.35 * m1 + 0.35 * m2 + rng.normal(0, 0.25, n)
    mander = 0.1 * z + rng.normal(0, 0.4, n)
    sphericity = 0.7 + 0.08 * z + rng.normal(0, 0.08, n)
    elongation = 1.6 - 0.20 * z + rng.normal(0, 0.25, n)
    solidity = 0.85 - 0.02 * z + rng.normal(0, 0.04, n)
    n_branches = 5 + 1.8 * z + rng.normal(0, 1.4, n)
    return CorrelationFDRInput(
        coloc_metrics={
            "M1":      m1.tolist(),
            "M2":      m2.tolist(),
            "Pearson": pearson.tolist(),
            "Manders": mander.tolist(),
        },
        shape_metrics={
            "sphericity":  sphericity.tolist(),
            "elongation":  elongation.tolist(),
            "solidity":    solidity.tolist(),
            "n_branches":  n_branches.tolist(),
        },
    )


_META = RecipeMetadata(
    name="colocalization_vs_morphology_correlation",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.matrix,
    answers_question=(
        "Do colocalization metrics predict shape metrics at the per-cell "
        "level, after FDR correction?"
    ),
    required_fields=("coloc_metrics", "shape_metrics"),
    optional_fields=("fdr_method", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("branch_point_density_map",),
)


def _benjamini_hochberg(pvals: np.ndarray) -> np.ndarray:
    """Return BH-adjusted p-values (same shape as input)."""
    p_flat = pvals.flatten()
    m = p_flat.size
    order = np.argsort(p_flat)
    ranked = p_flat[order]
    adj = np.empty(m, dtype=float)
    running_min = 1.0
    for k_inv in range(m - 1, -1, -1):
        rank = k_inv + 1
        v = ranked[k_inv] * m / rank
        running_min = min(running_min, v)
        adj[k_inv] = running_min
    out = np.empty(m, dtype=float)
    out[order] = adj
    return out.reshape(pvals.shape)


@register_recipe(
    metadata=_META,
    contract=CorrelationFDRInput,
    demo_contract=_demo,
)
def render(contract: CorrelationFDRInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.6))
    AESTHETIC.apply_to_ax(ax)

    coloc_names = list(contract.coloc_metrics.keys())
    shape_names = list(contract.shape_metrics.keys())

    r_matrix = np.zeros((len(coloc_names), len(shape_names)))
    p_matrix = np.ones_like(r_matrix)
    for i, c_name in enumerate(coloc_names):
        cv = np.asarray(contract.coloc_metrics[c_name], float)
        for j, s_name in enumerate(shape_names):
            sv = np.asarray(contract.shape_metrics[s_name], float)
            n = min(cv.size, sv.size)
            if n < 3:
                continue
            try:
                rv, pv = stats.pearsonr(cv[:n], sv[:n])
                r_matrix[i, j] = float(rv)
                p_matrix[i, j] = float(pv)
            except Exception:
                continue

    q_matrix = _benjamini_hochberg(p_matrix)

    # Render correlation heatmap.
    im = ax.imshow(
        r_matrix, cmap=AESTHETIC.ratio_cmap or "RdBu_r",
        vmin=-1.0, vmax=1.0, aspect="auto",
        interpolation="nearest",
    )

    # Annotate each cell with r and FDR stars.
    for i in range(r_matrix.shape[0]):
        for j in range(r_matrix.shape[1]):
            q = q_matrix[i, j]
            stars = ("***" if q < 1e-3
                     else "**" if q < 1e-2
                     else "*" if q < 5e-2 else "")
            label = f"{smart_fmt(r_matrix[i, j])}"
            if stars:
                label += f" {stars}"
            # Use contrast-adjusted text colour.
            colour = "white" if abs(r_matrix[i, j]) > 0.55 else "#111111"
            ax.text(j, i, label, ha="center", va="center",
                    fontsize=6.2, color=colour)

    ax.set_xticks(range(len(shape_names)))
    ax.set_xticklabels(shape_names, fontsize=6.8, rotation=25, ha="right")
    ax.set_yticks(range(len(coloc_names)))
    ax.set_yticklabels(coloc_names, fontsize=6.8)
    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.04, pad=0.04)
    cbar.set_label("Pearson r", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.2)

    # Fold the FDR significance legend into the title — a figure-level
    # footer at y=0.01 collided with the rotated x-tick labels.
    ax.set_title(
        f"{contract.title}  ·  "
        f"{len(coloc_names)} × {len(shape_names)} correlations  ·  "
        "FDR-adjusted: *** q < 0.001, ** q < 0.01, * q < 0.05",
        fontsize=7.8, pad=4,
    )
    return ax
