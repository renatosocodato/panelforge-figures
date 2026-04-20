"""Mean first-passage time matrix MFPT(i → j) across states.

Lower-triangular heatmap of pairwise MFPTs in units of the fastest
transition. The diagonal is zero (trivial). Top-3 fastest pairs are
annotated below the axis.
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


class MFPTMatrixInput(RecipeContract):
    state_labels: list[str] = Field(..., min_length=3)
    mfpt: list[list[float]] = Field(
        ..., description="N × N matrix in seconds (0 on diagonal)"
    )
    annotate_threshold: float | None = None
    units_label: str = "MFPT (s)"
    title: str = "Mean first-passage time"


def _demo() -> MFPTMatrixInput:
    states = ["HOME", "GATE", "TRAP", "RETURN", "RESCUE"]
    rng = np.random.default_rng(191)
    M = np.abs(rng.lognormal(mean=0.0, sigma=0.8, size=(5, 5)))
    M = (M + M.T) / 2
    np.fill_diagonal(M, 0)
    # Inject structure: HOME→TRAP is slow, GATE→RESCUE is fast.
    M[0, 2] = M[2, 0] = 12.4
    M[1, 4] = M[4, 1] = 0.8
    M[0, 1] = M[1, 0] = 1.2
    M[2, 4] = M[4, 2] = 5.3
    return MFPTMatrixInput(
        state_labels=states,
        mfpt=M.tolist(),
    )


_META = RecipeMetadata(
    name="mean_first_passage_time_matrix",
    modality="gillespie_stochastic",
    family=RecipeFamily.matrix,
    answers_question=(
        "Between every pair of states, what is the expected "
        "first-passage time MFPT(i, j)?"
    ),
    required_fields=("state_labels", "mfpt"),
    optional_fields=("annotate_threshold", "units_label", "title"),
    file_format_hints=("csv", "npz"),
    alternatives_in_modality=("trajectory_fan_with_fpt",),
)


@register_recipe(
    metadata=_META,
    contract=MFPTMatrixInput,
    demo_contract=_demo,
)
def render(contract: MFPTMatrixInput, ax=None, **_):
    import matplotlib as mpl

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 4.2))
    AESTHETIC.apply_to_ax(ax)

    M = np.asarray(contract.mfpt, float)
    n = M.shape[0]
    display = np.ma.masked_where(np.triu(np.ones_like(M), k=1) == 1, M)
    cmap = mpl.colormaps["viridis"]
    im = ax.imshow(display, cmap=cmap,
                   vmin=0.0, vmax=max(M.max(), 1e-9),
                   aspect="equal")

    states = contract.state_labels
    ax.set_xticks(range(n))
    ax.set_xticklabels(states, rotation=35, ha="right", fontsize=6.8)
    ax.set_yticks(range(n))
    ax.set_yticklabels(states, fontsize=6.8)

    # Annotate every off-diagonal pair (usually small N).
    v_hi = max(M.max(), 1e-9)
    thr = (contract.annotate_threshold
           if contract.annotate_threshold is not None else 0.0)
    pairs = []
    for i in range(n):
        for j in range(i):
            v = M[i, j]
            if v >= thr:
                pairs.append((i, j, v))
                if v > v_hi * 0.55:
                    ax.text(j, i, smart_fmt(v), ha="center", va="center",
                            fontsize=6.2, color="white")
                else:
                    ax.text(j, i, smart_fmt(v), ha="center", va="center",
                            fontsize=6.2, color="#111111",
                            bbox=dict(boxstyle="round,pad=0.10",
                                      fc="white", ec="none", alpha=0.85))

    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(contract.units_label, fontsize=6.8)
    cbar.ax.tick_params(labelsize=6.4)

    ax.set_title(contract.title, fontsize=9.0, pad=4)

    # Top-3 fastest transitions callout.
    pairs.sort(key=lambda t: t[2])
    fastest = pairs[:3]
    text = ("fastest: "
            + ", ".join(f"{states[i]}↔{states[j]}={smart_fmt(v)}"
                        for i, j, v in fastest)
            if fastest else "no MFPT data.")
    # Replace unicode arrow with ASCII for Liberation Sans safety.
    text = text.replace("↔", "-")
    fig = ax.figure
    fig.text(
        0.5, -0.16, text,
        ha="center", va="top", fontsize=6.6, color="#333333",
        transform=ax.transAxes,
        bbox=dict(boxstyle="round,pad=0.22", fc="white",
                  ec=AESTHETIC.annotation_style.callout_accent, lw=0.5),
    )
    return ax
