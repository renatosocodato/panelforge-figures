"""Sobol second-order interaction matrix — parameter×parameter heatmap."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    add_halo_label,
    callout_box,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class InteractionMatrixInput(RecipeContract):
    parameter_names: list[str] = Field(..., min_length=3)
    S2: list[list[float]] = Field(..., description="symmetric parameter × parameter matrix")
    annotate_threshold: float = 0.02
    output_label: str = "output"


def _demo() -> InteractionMatrixInput:
    rng = np.random.default_rng(37)
    names = ["k_on", "k_off", "V_max", "Km", "D", "α", "β"]
    n = len(names)
    M = np.abs(rng.normal(0.01, 0.015, (n, n)))
    M = (M + M.T) / 2
    np.fill_diagonal(M, 0)
    # Inject strong interactions.
    M[0, 3] = M[3, 0] = 0.22
    M[2, 3] = M[3, 2] = 0.12
    M[1, 5] = M[5, 1] = 0.08
    return InteractionMatrixInput(
        parameter_names=names,
        S2=M.tolist(),
        annotate_threshold=0.05,
        output_label="steady-state activity",
    )


_META = RecipeMetadata(
    name="interaction_matrix_sobol",
    modality="sensitivity_analysis",
    family=RecipeFamily.matrix,
    answers_question="Which pairs of parameters interact strongly in driving the output?",
    required_fields=("parameter_names", "S2"),
    optional_fields=("annotate_threshold", "output_label"),
    file_format_hints=("parquet", "npz"),
    alternatives_in_modality=("sobol_first_total_pair", "fast_subspace_detection"),
)


@register_recipe(metadata=_META, contract=InteractionMatrixInput, demo_contract=_demo)
def render(contract: InteractionMatrixInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.4, 3.8))
    AESTHETIC.apply_to_ax(ax)
    M = np.array(contract.S2, dtype=float)
    n = M.shape[0]

    # Mask the upper triangle to show only lower-triangular half.
    display = np.ma.masked_where(np.triu(np.ones_like(M), k=1) == 1, M)
    im = ax.imshow(display, cmap=AESTHETIC.ratio_cmap or AESTHETIC.continuous_cmap,
                   vmin=-M.max() * 0.15, vmax=M.max(), aspect="equal")

    names = contract.parameter_names
    ax.set_xticks(range(n))
    ax.set_xticklabels(names, rotation=35, ha="right", fontsize=7.0)
    ax.set_yticks(range(n))
    ax.set_yticklabels(names, fontsize=7.0)

    # Halo'd labels for interactions above the threshold.
    annotated = []
    for i in range(n):
        for j in range(i):
            v = M[i, j]
            if v >= contract.annotate_threshold:
                annotated.append((i, j, v))
                add_halo_label(
                    ax, j, i, smart_fmt(v),
                    fontsize=6.6, fontweight="bold", color="#111111",
                    halo_width=2.2,
                )

    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("S₂ (interaction)", fontsize=6.8)
    cbar.ax.tick_params(labelsize=6.6)

    ax.set_title(
        f"Pairwise interactions — {contract.output_label}",
        fontsize=8.6,
        fontweight="bold",
    )

    # Callout: top-3 strongest pairs.
    annotated.sort(key=lambda t: -t[2])
    top = annotated[:3]
    text = "Top pairs: " + ", ".join(
        f"{names[i]}×{names[j]}={smart_fmt(v)}" for i, j, v in top
    ) if top else "No interaction above threshold."
    callout_box(
        ax,
        0.03,
        0.03,
        text,
        accent=AESTHETIC.annotation_style.callout_accent,
        transform=ax.transAxes,
    )
    return ax
