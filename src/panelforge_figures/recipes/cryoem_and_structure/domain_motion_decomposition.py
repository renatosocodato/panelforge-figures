"""Domain-motion / normal-mode decomposition — per-mode variance bars
with cumulative-variance line.

Ladder family: ≥3 horizontal bars.
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


class ModeDecompositionInput(RecipeContract):
    mode_names: list[str] = Field(..., min_length=3)
    variance_explained: list[float] = Field(
        ..., description="per-mode variance share in [0, 1]"
    )
    mode_description: list[str] | None = Field(
        None, description="short description per mode (e.g. 'hinge opening')"
    )
    title: str = "Normal-mode variance"


def _demo() -> ModeDecompositionInput:
    names = [f"mode {i + 1}" for i in range(8)]
    # Steeply decaying variance spectrum.
    var = np.array([0.38, 0.22, 0.14, 0.08, 0.06, 0.05, 0.04, 0.03])
    var = var / var.sum()
    descs = [
        "hinge-open",
        "domain twist",
        "loop gating",
        "cap shift",
        "shear",
        "breathing",
        "rocking",
        "residual",
    ]
    return ModeDecompositionInput(
        mode_names=names,
        variance_explained=var.tolist(),
        mode_description=descs,
    )


_META = RecipeMetadata(
    name="domain_motion_decomposition",
    modality="cryoem_and_structure",
    family=RecipeFamily.ladder,
    answers_question=(
        "Which normal modes / PCs capture most of the concerted-"
        "motion variance?"
    ),
    required_fields=("mode_names", "variance_explained"),
    optional_fields=("mode_description", "title"),
    file_format_hints=("csv",),
    alternatives_in_modality=("bfactor_vs_residue",),
)


@register_recipe(
    metadata=_META,
    contract=ModeDecompositionInput,
    demo_contract=_demo,
)
def render(contract: ModeDecompositionInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 3.6))
    AESTHETIC.apply_to_ax(ax)

    names = contract.mode_names
    var = np.asarray(contract.variance_explained, float)
    descs = (contract.mode_description
             if contract.mode_description is not None
             else [""] * len(names))

    # Sort by variance descending (typical convention).
    order = np.argsort(-var)
    names_s = [names[i] for i in order]
    var_s = var[order]
    descs_s = [descs[i] for i in order]

    y = np.arange(len(names_s))

    # Colour gradient by rank.
    gradient = ["#1565C0", "#1976D2", "#1E88E5", "#42A5F5",
                "#64B5F6", "#90CAF9", "#BBDEFB", "#E3F2FD"]
    bar_colors = [gradient[min(i, len(gradient) - 1)] for i in range(len(y))]

    ax.barh(y, var_s, color=bar_colors,
            edgecolor="white", linewidth=0.7, alpha=0.92, zorder=3)

    # Per-bar numeric + cumulative + description. Cumulative fraction
    # shown inline so we don't need a secondary-axis line that would
    # cross bar labels.
    cum = np.cumsum(var_s)
    for yi, v, c, desc in zip(y, var_s, cum, descs_s):
        label = f"{v:.0%}  (cum {c:.0%})"
        if desc:
            label += f"   {desc}"
        ax.text(v + 0.005, yi, label,
                va="center", ha="left", fontsize=6.6, color="#333333",
                zorder=5)

    ax.set_yticks(y)
    ax.set_yticklabels(names_s, fontsize=7.0)
    ax.invert_yaxis()
    ax.set_xlabel("variance explained")
    ax.set_xlim(0, float(var_s.max()) * 1.6)

    # Cumulative-variance callout — top-N for 80 %.
    n_80 = int(np.searchsorted(cum, 0.8) + 1)
    ax.set_title(
        f"{contract.title}  ·  top-{n_80} modes capture 80 % of "
        f"variance  (top-1 = {smart_fmt(float(var_s[0] * 100))} %)",
        fontsize=8.2, pad=4,
    )
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    return ax
