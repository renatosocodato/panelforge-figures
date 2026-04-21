"""Pathway × pathway crosstalk matrix — shared-gene / correlation heatmap."""

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


class PathwayCrosstalkInput(RecipeContract):
    pathway_names: list[str] = Field(..., min_length=3)
    crosstalk: list[list[float]] = Field(
        ..., description="symmetric N × N crosstalk matrix; diagonal = 1"
    )
    annotate_threshold: float = 0.35
    units_label: str = "crosstalk score"
    title: str = "Pathway crosstalk"


def _demo() -> PathwayCrosstalkInput:
    rng = np.random.default_rng(733)
    pathways = [
        "OXPHOS", "glycolysis", "TCA", "fatty-acid β-ox",
        "autophagy", "ER stress", "NFkB", "IFN-γ response",
        "MAPK", "PI3K-AKT",
    ]
    n = len(pathways)
    M = np.clip(rng.normal(0.15, 0.10, (n, n)), 0.0, 1.0)
    M = (M + M.T) / 2
    np.fill_diagonal(M, 1.0)
    # Inject strong crosstalk clusters.
    M[0, 1] = M[1, 0] = 0.72
    M[0, 2] = M[2, 0] = 0.65
    M[6, 7] = M[7, 6] = 0.78
    M[8, 9] = M[9, 8] = 0.70
    return PathwayCrosstalkInput(
        pathway_names=pathways,
        crosstalk=M.tolist(),
    )


_META = RecipeMetadata(
    name="pathway_crosstalk_matrix",
    modality="network_and_pathway",
    family=RecipeFamily.matrix,
    answers_question=(
        "How strongly does each pathway 'talk' to each other (shared "
        "genes, correlated activity)?"
    ),
    required_fields=("pathway_names", "crosstalk"),
    optional_fields=("annotate_threshold", "units_label", "title"),
    file_format_hints=("csv", "parquet", "npz"),
    alternatives_in_modality=("module_eigengene_heatmap",),
)


@register_recipe(
    metadata=_META,
    contract=PathwayCrosstalkInput,
    demo_contract=_demo,
)
def render(contract: PathwayCrosstalkInput, ax=None, **_):
    import matplotlib as mpl

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 4.4))
    AESTHETIC.apply_to_ax(ax)

    pathways = contract.pathway_names
    M = np.asarray(contract.crosstalk, float)
    n = M.shape[0]

    cmap = mpl.colormaps["viridis"]
    im = ax.imshow(M, cmap=cmap, vmin=0.0, vmax=1.0,
                   aspect="equal", interpolation="nearest")
    ax.set_xticks(range(n))
    ax.set_xticklabels(pathways, rotation=45, ha="right", fontsize=6.4)
    ax.set_yticks(range(n))
    ax.set_yticklabels(pathways, fontsize=6.6)

    # Annotate strong off-diagonal pairs.
    pairs = []
    for i in range(n):
        for j in range(i):
            v = M[i, j]
            if v >= contract.annotate_threshold:
                pairs.append((i, j, v))
                if v > 0.55:
                    ax.text(j, i, smart_fmt(v), ha="center", va="center",
                            fontsize=6.0, color="white")

    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.040, pad=0.03)
    cbar.set_label(contract.units_label, fontsize=6.8)
    cbar.ax.tick_params(labelsize=6.4)

    # Top-pair callout.
    pairs.sort(key=lambda t: -t[2])
    top = pairs[:3]
    text = ("top crosstalk: "
            + ", ".join(f"{pathways[i]}×{pathways[j]}={smart_fmt(v)}"
                        for i, j, v in top)
            if top else "no pair above threshold")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    fig = ax.figure
    fig.text(
        0.5, -0.16, text,
        ha="center", va="top", fontsize=6.4, color="#333333",
        transform=ax.transAxes,
        bbox=dict(boxstyle="round,pad=0.22", fc="white",
                  ec="#BBBBBB", lw=0.5, alpha=0.92),
    )
    return ax
