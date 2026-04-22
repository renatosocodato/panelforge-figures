"""Quadrat-count χ² test — regular quadrat grid overlaying the point
field with per-cell count + χ² residual colouring and overall χ²
p-value pill.
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


class QuadratInput(RecipeContract):
    count_grid: list[list[int]] = Field(
        ..., description="n_rows × n_cols quadrat counts"
    )
    n_total_points: int = Field(..., description="total observed points")
    title: str = "Quadrat-count χ² test"


def _demo() -> QuadratInput:
    rng = np.random.default_rng(1709)
    nrows, ncols = 8, 10
    expected = 6.5
    counts = rng.poisson(expected, (nrows, ncols))
    # Inject a hotspot and a coldspot.
    counts[1:3, 2:4] += 10
    counts[5:7, 7:9] = 0
    return QuadratInput(
        count_grid=counts.tolist(),
        n_total_points=int(counts.sum()),
    )


_META = RecipeMetadata(
    name="quadrat_count_chisq",
    modality="spatial_statistics",
    family=RecipeFamily.matrix,
    answers_question=(
        "Is the overall point pattern non-uniform at the chosen quadrat "
        "scale (χ² test)?"
    ),
    required_fields=("count_grid", "n_total_points"),
    optional_fields=("title",),
    file_format_hints=("csv",),
    alternatives_in_modality=("kernel_density_heatmap",),
)


@register_recipe(
    metadata=_META,
    contract=QuadratInput,
    demo_contract=_demo,
)
def render(contract: QuadratInput, ax=None, **_):
    from scipy.stats import chi2

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 3.8))
    AESTHETIC.apply_to_ax(ax)

    counts = np.asarray(contract.count_grid, int)
    n_rows, n_cols = counts.shape
    n_total = int(contract.n_total_points)
    expected = n_total / (n_rows * n_cols)

    # Pearson residuals: (O - E) / sqrt(E).
    resid = (counts - expected) / np.sqrt(max(expected, 1e-9))
    # χ² statistic.
    chi2_stat = float(np.sum((counts - expected) ** 2 / max(expected, 1e-9)))
    df = n_rows * n_cols - 1
    p_val = float(1.0 - chi2.cdf(chi2_stat, df))

    v_abs = float(max(abs(resid).max(), 1e-6))
    im = ax.imshow(resid, cmap="RdBu_r", vmin=-v_abs, vmax=v_abs,
                   aspect="auto", interpolation="nearest",
                   extent=[0, n_cols, 0, n_rows], zorder=2)

    # Overlay counts.
    for i in range(n_rows):
        for j in range(n_cols):
            c = counts[i, j]
            ax.text(j + 0.5, n_rows - i - 0.5, f"{c}",
                    ha="center", va="center", fontsize=6.2,
                    color=("white" if abs(resid[i, j]) > v_abs * 0.55
                           else "#222222"),
                    zorder=4)

    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.036, pad=0.03)
    cbar.set_label(r"Pearson residual", fontsize=6.8)
    cbar.ax.tick_params(labelsize=6.4)

    ax.set_xlim(0, n_cols)
    ax.set_ylim(0, n_rows)
    ax.set_xticks(range(0, n_cols + 1, max(1, n_cols // 6)))
    ax.set_yticks(range(0, n_rows + 1, max(1, n_rows // 5)))
    ax.set_xlabel("quadrat column")
    ax.set_ylabel("quadrat row")

    # Verdict.
    if p_val < 0.001:
        verdict = "non-uniform (p < 0.001)"
    elif p_val < 0.05:
        verdict = f"non-uniform (p = {smart_fmt(p_val)})"
    else:
        verdict = f"compatible with CSR (p = {smart_fmt(p_val)})"
    ax.set_title(
        f"{contract.title}  ·  N = {n_total}, E = {smart_fmt(expected)}  ·  "
        f"χ² = {smart_fmt(chi2_stat)} (df = {df})",
        fontsize=7.4, pad=4,
    )
    ax.text(0.02, -0.14, verdict,
            transform=ax.transAxes, ha="left", va="top",
            fontsize=6.8, color="#333333",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=6)
    return ax
