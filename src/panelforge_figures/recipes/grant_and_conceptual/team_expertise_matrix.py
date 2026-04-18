"""Team expertise matrix — members × competencies coverage grid."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
)
from ._aesthetic import AESTHETIC


class TeamExpertiseInput(RecipeContract):
    members: list[str] = Field(..., min_length=2)
    competencies: list[str] = Field(..., min_length=2)
    matrix: list[list[float]] = Field(..., description="members × competencies coverage 0..3")
    palette_cmap: str = "cividis"
    show_values: bool = True


def _demo() -> TeamExpertiseInput:
    members = ["PI (systems bio)", "Co-I (biophysics)", "PDRA (imaging)",
               "PDRA (ML)", "Clinical collaborator", "Data steward"]
    competencies = [
        "Microscopy", "FRET sensors", "ODE/PDE",
        "Stochastic sim", "Single-cell omics",
        "Statistical models", "Translational", "Data engineering",
    ]
    m = [
        [2, 3, 3, 2, 2, 3, 1, 2],
        [1, 1, 3, 3, 0, 3, 0, 2],
        [3, 3, 0, 0, 1, 1, 0, 1],
        [0, 0, 2, 2, 3, 3, 0, 3],
        [0, 1, 0, 0, 1, 1, 3, 0],
        [0, 0, 0, 0, 2, 2, 1, 3],
    ]
    return TeamExpertiseInput(members=members, competencies=competencies, matrix=m)


_META = RecipeMetadata(
    name="team_expertise_matrix",
    modality="grant_and_conceptual",
    family=RecipeFamily.matrix,
    answers_question="How is the team's expertise distributed across the competencies the proposal requires?",
    required_fields=("members", "competencies", "matrix"),
    optional_fields=("palette_cmap", "show_values"),
    file_format_hints=("yaml", "csv"),
    alternatives_in_modality=("work_package_flow", "executive_summary_tile"),
)


@register_recipe(metadata=_META, contract=TeamExpertiseInput, demo_contract=_demo)
def render(contract: TeamExpertiseInput, ax=None, **_):
    """Matrix heatmap with row/column margin totals."""
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.8, 3.6))
    AESTHETIC.apply_to_ax(ax)
    M = np.array(contract.matrix, dtype=float)
    im = ax.imshow(M, cmap=contract.palette_cmap, aspect="auto", vmin=0,
                   vmax=max(3.0, float(M.max())))
    ax.set_xticks(range(len(contract.competencies)))
    ax.set_xticklabels(contract.competencies, rotation=35, ha="right", fontsize=7.0)
    ax.set_yticks(range(len(contract.members)))
    ax.set_yticklabels(contract.members, fontsize=7.2)
    if contract.show_values:
        for (i, j), v in np.ndenumerate(M):
            if v < 1.0:  # suppress very faint cells to cut visual noise
                continue
            color = "white" if v >= 2 else "#222222"
            ax.text(j, i, f"{int(round(v))}", ha="center", va="center",
                    fontsize=7.0, color=color)
    # No explicit margin totals — they crowd the axes at small sizes.
    # Reviewers read coverage directly from the cmap; the bar summarizes totals.
    ax.set_title("Team × competency coverage", fontsize=8.6, pad=4)
    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.036, pad=0.03)
    cbar.set_label("coverage (0–3)", fontsize=6.8)
    cbar.ax.tick_params(labelsize=6.6)
    return ax
