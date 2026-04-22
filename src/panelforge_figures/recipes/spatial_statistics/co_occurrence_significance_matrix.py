"""Cell-type co-occurrence significance matrix — type × type z-score
matrix with star-significance overlay. Summarises pairwise tile-level
co-occurrence without the r-dependence of a bivariate PCF.
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


class CooccurrenceInput(RecipeContract):
    type_names: list[str] = Field(..., min_length=3)
    zscore_matrix: list[list[float]] = Field(
        ..., description="symmetric n_types × n_types z-score matrix"
    )
    p_matrix: list[list[float]] = Field(
        ..., description="n_types × n_types two-sided p-value matrix"
    )
    title: str = "Cell-type co-occurrence"


def _demo() -> CooccurrenceInput:
    rng = np.random.default_rng(1613)
    names = ["microglia", "astrocyte", "neuron", "endothelial", "oligo"]
    n = len(names)
    z = rng.normal(0, 1.5, (n, n))
    z = (z + z.T) / 2
    np.fill_diagonal(z, 0)
    # Inject a strong co-occurrence and a strong avoidance.
    z[0, 2] = z[2, 0] = 3.8   # microglia × neuron: co-occur
    z[3, 4] = z[4, 3] = -3.1  # endo × oligo: avoid
    # Derive two-sided p-values from a Gaussian null.
    p = 2 * (1 - 0.5 * (1 + np.tanh(np.abs(z) / np.sqrt(2))))
    np.fill_diagonal(p, 1.0)
    return CooccurrenceInput(
        type_names=names,
        zscore_matrix=z.tolist(),
        p_matrix=p.tolist(),
    )


_META = RecipeMetadata(
    name="co_occurrence_significance_matrix",
    modality="spatial_statistics",
    family=RecipeFamily.matrix,
    answers_question=(
        "Which cell-type pairs significantly co-occur vs avoid each "
        "other across tiles?"
    ),
    required_fields=("type_names", "zscore_matrix", "p_matrix"),
    optional_fields=("title",),
    file_format_hints=("csv",),
    alternatives_in_modality=("bivariate_pair_correlation",),
)


@register_recipe(
    metadata=_META,
    contract=CooccurrenceInput,
    demo_contract=_demo,
)
def render(contract: CooccurrenceInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 4.0))
    AESTHETIC.apply_to_ax(ax)

    names = contract.type_names
    Z = np.asarray(contract.zscore_matrix, float)
    P = np.asarray(contract.p_matrix, float)
    n = len(names)

    v_abs = float(max(abs(Z).max(), 1e-6))
    im = ax.imshow(Z, cmap="RdBu_r", vmin=-v_abs, vmax=v_abs,
                   aspect="equal", interpolation="nearest", zorder=2)
    ax.set_xticks(range(n))
    ax.set_xticklabels(names, rotation=45, ha="right", fontsize=7.0)
    ax.set_yticks(range(n))
    ax.set_yticklabels(names, fontsize=7.0)

    # Numeric z + significance stars.
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            z = Z[i, j]
            p = P[i, j]
            if p < 0.001:
                stars = "***"
            elif p < 0.01:
                stars = "**"
            elif p < 0.05:
                stars = "*"
            else:
                stars = ""
            label = f"{smart_fmt(float(z))}\n{stars}" if stars else smart_fmt(float(z))
            ax.text(j, i, label,
                    ha="center", va="center", fontsize=6.2,
                    color=("white" if abs(z) > v_abs * 0.55 else "#222222"),
                    zorder=4)

    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.036, pad=0.03)
    cbar.set_label("z-score", fontsize=6.8)
    cbar.ax.tick_params(labelsize=6.4)

    # Top-pair callouts.
    triu = np.triu_indices(n, k=1)
    triu_z = Z[triu]
    triu_p = P[triu]
    triu_pairs = list(zip(*triu))
    if len(triu_z) > 0:
        top_pos_i = int(np.argmax(triu_z))
        top_neg_i = int(np.argmin(triu_z))
        a_pos, b_pos = triu_pairs[top_pos_i]
        a_neg, b_neg = triu_pairs[top_neg_i]
        ax.set_title(
            f"{contract.title}  ·  strongest co-occur: "
            f"{names[a_pos]} × {names[b_pos]} "
            f"(z = {smart_fmt(float(triu_z[top_pos_i]))})  ·  "
            f"strongest avoid: {names[a_neg]} × {names[b_neg]} "
            f"(z = {smart_fmt(float(triu_z[top_neg_i]))})",
            fontsize=7.4, pad=4,
        )
    else:
        ax.set_title(contract.title, fontsize=9.0, pad=4)
    return ax
