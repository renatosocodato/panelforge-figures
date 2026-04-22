"""Interdisciplinary contribution spider — radar showing the
disciplinary coverage of the proposal across biology, maths,
engineering, clinical, industry, outreach.

Radar family: polar axis with ≥1 filled polygon.
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


class InterdisciplinaryInput(RecipeContract):
    discipline_names: list[str] = Field(..., min_length=4)
    coverage: list[float] = Field(
        ...,
        description="coverage score per discipline, 0 to 1",
    )
    reference_coverage: list[float] | None = Field(
        None,
        description=(
            "optional comparator (e.g. typical MRes / MEng proposal) "
            "— same length as discipline_names"
        ),
    )
    title: str = "Interdisciplinary contribution"


def _demo() -> InterdisciplinaryInput:
    return InterdisciplinaryInput(
        discipline_names=[
            "biology",
            "maths /\nmodelling",
            "engineering /\nhardware",
            "clinical",
            "industry",
            "outreach /\npolicy",
        ],
        coverage=[0.92, 0.80, 0.55, 0.65, 0.50, 0.60],
        reference_coverage=[0.75, 0.35, 0.30, 0.45, 0.20, 0.35],
    )


_META = RecipeMetadata(
    name="interdisciplinary_contribution_spider",
    modality="grant_and_conceptual",
    family=RecipeFamily.radar,
    answers_question=(
        "How interdisciplinary is the proposal across biology, maths, "
        "engineering, clinical, industry, and outreach disciplines?"
    ),
    required_fields=("discipline_names", "coverage"),
    optional_fields=("reference_coverage", "title"),
    file_format_hints=("yaml", "csv"),
    alternatives_in_modality=("team_expertise_matrix",),
)


@register_recipe(
    metadata=_META,
    contract=InterdisciplinaryInput,
    demo_contract=_demo,
)
def render(contract: InterdisciplinaryInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        fig = plt.figure(figsize=(5.0, 4.6))
        ax = fig.add_subplot(111, projection="polar")
    elif getattr(ax, "name", "") != "polar":
        # Replace rectangular axes with polar.
        fig = ax.figure
        pos = ax.get_position()
        fig.delaxes(ax)
        ax = fig.add_subplot(111, projection="polar")
        ax.set_position(pos)
    _ = AESTHETIC.apply_to_ax

    names = contract.discipline_names
    vals = np.asarray(contract.coverage, float)
    ref = (np.asarray(contract.reference_coverage, float)
           if contract.reference_coverage is not None else None)

    n = len(names)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
    # Close the polygon.
    angles_closed = np.concatenate([angles, angles[:1]])
    vals_closed = np.concatenate([vals, vals[:1]])

    # Reference polygon (if provided).
    if ref is not None:
        ref_closed = np.concatenate([ref, ref[:1]])
        ax.fill(angles_closed, ref_closed, color="#888888",
                alpha=0.18, linewidth=0, zorder=2)
        ax.plot(angles_closed, ref_closed, color="#888888", lw=0.8,
                ls="--", zorder=3, label="reference")

    # Proposal polygon.
    ax.fill(angles_closed, vals_closed, color="#1976D2", alpha=0.30,
            linewidth=0, zorder=4)
    ax.plot(angles_closed, vals_closed, color="#0D47A1", lw=1.4,
            zorder=5, label="proposal")
    # Vertex markers.
    ax.scatter(angles, vals, s=30, color="#0D47A1",
               edgecolor="white", linewidth=0.6, zorder=6)

    # Radial grid at 0.25 / 0.50 / 0.75.
    for r in [0.25, 0.5, 0.75]:
        ring_x = np.linspace(0, 2 * np.pi, 361)
        ax.plot(ring_x, np.full_like(ring_x, r),
                color="#DDDDDD", lw=0.5, zorder=1)

    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_rlim(0, 1.0)
    ax.set_rticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels([])
    ax.set_xticks(angles)
    ax.set_xticklabels(names, fontsize=7.0)
    ax.grid(False)

    # Overall score callout.
    mean_cov = float(vals.mean())
    ax.set_title(
        f"{contract.title}  ·  mean coverage = {smart_fmt(mean_cov)}",
        fontsize=8.6, pad=18,
    )
    ax.legend(fontsize=6.8, frameon=False, loc="upper right",
              bbox_to_anchor=(1.18, 1.06), handlelength=1.2)
    return ax
