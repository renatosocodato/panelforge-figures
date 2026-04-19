"""Colocalization coefficient matrix — condition × coefficient heatmap."""

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


class ColocCoefficientMatrixInput(RecipeContract):
    conditions: list[str] = Field(..., min_length=2)
    coefficient_names: list[str] = Field(..., min_length=2)
    coefficient_mean: list[list[float]] = Field(
        ..., description="rows = conditions, cols = coefficients; mean values in [-1, 1]"
    )
    coefficient_sem: list[list[float]] | None = None
    title: str = "Colocalization coefficients"


def _demo() -> ColocCoefficientMatrixInput:
    rng = np.random.default_rng(839)
    conds = ["control", "mutant", "rescue", "double_ko"]
    coefs = ["M1", "M2", "Pearson r", "Manders", "ICQ"]
    base = np.array([
        [0.72, 0.58, 0.61, 0.48, 0.14],
        [0.28, 0.18, 0.20, 0.35, -0.08],
        [0.65, 0.52, 0.55, 0.44, 0.12],
        [0.18, 0.12, 0.10, 0.25, -0.12],
    ])
    noise = rng.normal(0, 0.03, base.shape)
    means = np.clip(base + noise, -1.0, 1.0)
    sem = np.abs(rng.normal(0.04, 0.012, base.shape))
    return ColocCoefficientMatrixInput(
        conditions=conds,
        coefficient_names=coefs,
        coefficient_mean=means.tolist(),
        coefficient_sem=sem.tolist(),
    )


_META = RecipeMetadata(
    name="colocalization_coefficient_matrix",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.matrix,
    answers_question=(
        "Across conditions, how do M1 / M2 / Pearson / Manders / ICQ "
        "colocalization coefficients compare, in a condition-level "
        "heatmap with SEM annotations?"
    ),
    required_fields=("conditions", "coefficient_names", "coefficient_mean"),
    optional_fields=("coefficient_sem", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("colocalization_vs_morphology_correlation",),
)


@register_recipe(
    metadata=_META,
    contract=ColocCoefficientMatrixInput,
    demo_contract=_demo,
)
def render(contract: ColocCoefficientMatrixInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.4))
    AESTHETIC.apply_to_ax(ax)

    conds = contract.conditions
    coefs = contract.coefficient_names
    M = np.asarray(contract.coefficient_mean, float)
    S = (np.asarray(contract.coefficient_sem, float)
         if contract.coefficient_sem is not None else None)

    im = ax.imshow(
        M, cmap=AESTHETIC.ratio_cmap or "RdBu_r",
        vmin=-1.0, vmax=1.0, aspect="auto",
        interpolation="nearest",
    )

    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            val = M[i, j]
            label = smart_fmt(val)
            if S is not None:
                label += f"\n±{smart_fmt(float(S[i, j]))}"
            colour = "white" if abs(val) > 0.55 else "#111111"
            ax.text(j, i, label, ha="center", va="center",
                    fontsize=6.2, color=colour, linespacing=1.1)

    ax.set_xticks(range(len(coefs)))
    ax.set_xticklabels(coefs, fontsize=6.8, rotation=25, ha="right")
    ax.set_yticks(range(len(conds)))
    ax.set_yticklabels(conds, fontsize=6.8)
    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.04, pad=0.04)
    cbar.set_label("coefficient value", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.2)

    # Row-mean summary in title.
    row_means = M.mean(axis=1)
    summary = "  ·  ".join(
        f"{c}: {smart_fmt(float(m))}" for c, m in zip(conds, row_means)
    )
    ax.set_title(
        f"{contract.title}  ·  {len(conds)} × {len(coefs)} coefficients  ·  {summary}",
        fontsize=7.8, pad=4,
    )
    return ax
