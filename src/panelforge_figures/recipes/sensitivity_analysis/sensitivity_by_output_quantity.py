"""Sobol index matrix across multiple output quantities.

A param × output heatmap: rows are parameters, columns are quantities
of interest (peak, AUC, decay, steady-state, …). Each cell is the
sensitivity index (Sᵀ by default) for that (param, QoI) pair, so a
single panel answers "which parameter matters for which output?".

Distinct from `interaction_matrix_sobol` (param × param for a single
output) and `sobol_first_total_pair` (single output, S1/ST bars).
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


class SensByOutputInput(RecipeContract):
    parameter_names: list[str] = Field(..., min_length=2)
    output_names: list[str] = Field(..., min_length=2)
    indices: list[list[float]] = Field(
        ..., description="n_params × n_outputs sensitivity index matrix"
    )
    index_label: str = r"$S_T$"
    annotate_threshold: float = 0.05
    title: str = "Sensitivity by output quantity"


def _demo() -> SensByOutputInput:
    rng = np.random.default_rng(443)
    params = ["k_on", "k_off", "V_max", "Km", "D", "alpha", "beta"]
    outs = ["peak", "AUC", "decay τ", "steady-state", "rise-time"]
    M = rng.uniform(0.02, 0.65, size=(len(params), len(outs)))
    # Give it structure: k_on drives peak + rise-time; V_max drives AUC + ss.
    M[0, 0] += 0.25
    M[0, 4] += 0.20
    M[2, 1] += 0.30
    M[2, 3] += 0.28
    M[3, 2] += 0.18
    return SensByOutputInput(
        parameter_names=params,
        output_names=outs,
        indices=np.clip(M, 0, 1).tolist(),
    )


_META = RecipeMetadata(
    name="sensitivity_by_output_quantity",
    modality="sensitivity_analysis",
    family=RecipeFamily.matrix,
    answers_question=(
        "Across multiple output quantities, how do the Sobol indices of "
        "each parameter redistribute?"
    ),
    required_fields=("parameter_names", "output_names", "indices"),
    optional_fields=("index_label", "annotate_threshold", "title"),
    file_format_hints=("parquet", "npz"),
    alternatives_in_modality=(
        "sobol_first_total_pair",
        "interaction_matrix_sobol",
    ),
)


@register_recipe(
    metadata=_META,
    contract=SensByOutputInput,
    demo_contract=_demo,
)
def render(contract: SensByOutputInput, ax=None, **_):
    import matplotlib as mpl

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 4.2))
    AESTHETIC.apply_to_ax(ax)

    M = np.asarray(contract.indices, float)
    n_p, n_q = M.shape
    assert len(contract.parameter_names) == n_p
    assert len(contract.output_names) == n_q

    cmap = mpl.colormaps[AESTHETIC.continuous_cmap]
    im = ax.imshow(M, cmap=cmap, vmin=0.0, vmax=max(M.max(), 1e-9),
                   aspect="auto")

    ax.set_xticks(range(n_q))
    ax.set_xticklabels(contract.output_names, rotation=25, ha="right",
                       fontsize=7.0)
    ax.set_yticks(range(n_p))
    ax.set_yticklabels(contract.parameter_names, fontsize=7.2)

    # Annotate cells above threshold; adapt label colour to cell brightness.
    v_hi = max(M.max(), 1e-9)
    for i in range(n_p):
        for j in range(n_q):
            v = M[i, j]
            if v >= contract.annotate_threshold:
                if v > v_hi * 0.5:
                    ax.text(j, i, smart_fmt(v), ha="center", va="center",
                            fontsize=6.4, color="white")
                else:
                    ax.text(j, i, smart_fmt(v), ha="center", va="center",
                            fontsize=6.4, color="#111111",
                            bbox=dict(boxstyle="round,pad=0.10", fc="white",
                                      ec="none", alpha=0.85))

    # Dominant-driver markers on the cell borders so the cell value stays
    # readable: row-max as a left-edge triangle, col-max as a top-edge dot.
    row_max_j = np.argmax(M, axis=1)
    col_max_i = np.argmax(M, axis=0)
    for i in range(n_p):
        j = int(row_max_j[i])
        ax.scatter([j - 0.42], [i], s=22, marker=">",
                   color="#111111", edgecolor="white", linewidth=0.4,
                   zorder=4, clip_on=False)
    for j in range(n_q):
        i = int(col_max_i[j])
        ax.scatter([j], [i - 0.42], s=22, marker="v",
                   color="#111111", edgecolor="white", linewidth=0.4,
                   zorder=4, clip_on=False)

    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.040, pad=0.03)
    cbar.set_label(contract.index_label, fontsize=7.0)
    cbar.ax.tick_params(labelsize=6.6)

    ax.set_title(contract.title, fontsize=9.0, pad=4)

    # Below-axis callout listing dominant driver per output.
    drivers = ", ".join(
        f"{contract.output_names[j]} <- {contract.parameter_names[int(col_max_i[j])]}"
        for j in range(n_q)
    )
    fig = ax.figure
    fig.text(
        0.5, -0.18,
        f"dominant driver per output:  {drivers}",
        ha="center", va="top", fontsize=6.6, color="#333333",
        transform=ax.transAxes,
        bbox=dict(boxstyle="round,pad=0.24", fc="white",
                  ec=AESTHETIC.annotation_style.callout_accent, lw=0.5),
    )
    return ax
