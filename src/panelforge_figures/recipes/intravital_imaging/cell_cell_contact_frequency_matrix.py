"""Pairwise cell × cell contact-frequency matrix — heatmap with top-pair callouts.

For N cells observed over a window, counts the number of (or rate of)
pairwise contacts. Rendered as a symmetric heatmap (lower triangular)
with the top-three most-contacting pairs annotated.
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


class ContactMatrixInput(RecipeContract):
    cell_ids: list[str] = Field(..., min_length=3)
    contact_counts: list[list[float]] = Field(
        ..., description="symmetric N × N matrix; diagonal = 0"
    )
    annotate_threshold: float = 0.08
    units_label: str = "contacts / min"
    title: str = "Cell-cell contact frequency"


def _demo() -> ContactMatrixInput:
    rng = np.random.default_rng(877)
    n = 10
    ids = [f"c{i:02d}" for i in range(n)]
    M = np.abs(rng.normal(0.03, 0.04, (n, n)))
    M = (M + M.T) / 2
    np.fill_diagonal(M, 0)
    # Inject strong pairs.
    M[0, 3] = M[3, 0] = 0.52
    M[2, 7] = M[7, 2] = 0.38
    M[1, 4] = M[4, 1] = 0.32
    M[5, 6] = M[6, 5] = 0.21
    return ContactMatrixInput(
        cell_ids=ids,
        contact_counts=M.tolist(),
        annotate_threshold=0.15,
    )


_META = RecipeMetadata(
    name="cell_cell_contact_frequency_matrix",
    modality="intravital_imaging",
    family=RecipeFamily.matrix,
    answers_question=(
        "For N cells, how often does each pair make contact over time?"
    ),
    required_fields=("cell_ids", "contact_counts"),
    optional_fields=("annotate_threshold", "units_label", "title"),
    file_format_hints=("csv", "npz"),
    alternatives_in_modality=("cell_track_trajectory_field",),
)


@register_recipe(
    metadata=_META,
    contract=ContactMatrixInput,
    demo_contract=_demo,
)
def render(contract: ContactMatrixInput, ax=None, **_):
    import matplotlib as mpl

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.6, 4.0))
    AESTHETIC.apply_to_ax(ax)

    M = np.asarray(contract.contact_counts, float)
    n = M.shape[0]
    display = np.ma.masked_where(np.triu(np.ones_like(M), k=1) == 1, M)
    cmap = mpl.colormaps["inferno"]
    im = ax.imshow(display, cmap=cmap, vmin=0.0, vmax=max(M.max(), 1e-9),
                   aspect="equal")

    ids = contract.cell_ids
    ax.set_xticks(range(n))
    ax.set_xticklabels(ids, rotation=45, ha="right", fontsize=6.4)
    ax.set_yticks(range(n))
    ax.set_yticklabels(ids, fontsize=6.4)

    # Annotate strong pairs.
    pairs = []
    v_hi = max(M.max(), 1e-9)
    for i in range(n):
        for j in range(i):
            v = M[i, j]
            if v >= contract.annotate_threshold:
                pairs.append((i, j, v))
                if v > v_hi * 0.55:
                    ax.text(j, i, smart_fmt(v), ha="center", va="center",
                            fontsize=6.0, color="white")
                else:
                    ax.text(j, i, smart_fmt(v), ha="center", va="center",
                            fontsize=6.0, color="#111111",
                            bbox=dict(boxstyle="round,pad=0.10",
                                      fc="white", ec="none", alpha=0.85))

    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(contract.units_label, fontsize=6.8)
    cbar.ax.tick_params(labelsize=6.4)

    ax.set_title(contract.title, fontsize=9.0, pad=4)

    # Top-3 pairs footer.
    pairs.sort(key=lambda t: -t[2])
    top = pairs[:3]
    text = ("top pairs: "
            + ", ".join(f"{ids[i]}×{ids[j]}={smart_fmt(v)}"
                        for i, j, v in top)
            if top else "no pair above threshold.")
    fig = ax.figure
    fig.text(
        0.5, -0.16, text,
        ha="center", va="top", fontsize=6.6, color="#333333",
        transform=ax.transAxes,
        bbox=dict(boxstyle="round,pad=0.22", fc="white",
                  ec=AESTHETIC.annotation_style.callout_accent, lw=0.5),
    )
    return ax
