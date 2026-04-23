"""Competing-risks cumulative incidence — CIF per cause with Gray's
test p-value. Distinct from `kaplan_meier_by_stratum` (single-endpoint
survival 1-S).
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


class CompetingRisksInput(RecipeContract):
    time_points: list[float] = Field(..., min_length=5)
    cif_by_cause: dict[str, list[float]] = Field(
        ...,
        description="cause name -> CIF value at each time point",
    )
    grays_test_p: float | None = Field(
        None, description="Gray's test p-value comparing CIFs"
    )
    title: str = "Competing-risks CIF"


def _demo() -> CompetingRisksInput:
    t = np.linspace(0, 60, 100)
    # Cause A (disease-specific): steady increase to 0.25.
    cif_a = 0.25 * (1 - np.exp(-t / 20))
    # Cause B (other mortality): slower, plateau at 0.08.
    cif_b = 0.08 * (1 - np.exp(-t / 35))
    return CompetingRisksInput(
        time_points=t.tolist(),
        cif_by_cause={
            "disease-specific": cif_a.tolist(),
            "other mortality":  cif_b.tolist(),
        },
        grays_test_p=0.003,
    )


_META = RecipeMetadata(
    name="competing_risks_cumulative_incidence",
    modality="clinical_cohort",
    family=RecipeFamily.diagnostic_curve,
    answers_question=(
        "In the presence of competing risks, what are the per-cause "
        "cumulative-incidence functions, and do they differ (Gray's "
        "test)?"
    ),
    required_fields=("time_points", "cif_by_cause"),
    optional_fields=("grays_test_p", "title"),
    file_format_hints=("csv",),
    alternatives_in_modality=("kaplan_meier_by_stratum",),
)


@register_recipe(
    metadata=_META,
    contract=CompetingRisksInput,
    demo_contract=_demo,
)
def render(contract: CompetingRisksInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.6))
    AESTHETIC.apply_to_ax(ax)

    t = np.asarray(contract.time_points, float)
    cause_colors = ["#1565C0", "#E65100", "#6A1B9A", "#2E7D32", "#C2185B"]

    max_cif = 0.0
    for i, (name, cif) in enumerate(contract.cif_by_cause.items()):
        cif_arr = np.asarray(cif, float)
        color = cause_colors[i % len(cause_colors)]
        ax.plot(t, cif_arr, color=color, lw=1.4, zorder=4,
                label=f"{name} (final CIF {smart_fmt(float(cif_arr[-1]))})")
        # Shade under curve.
        ax.fill_between(t, 0, cif_arr, color=color, alpha=0.10,
                        linewidth=0, zorder=2)
        max_cif = max(max_cif, float(cif_arr.max()))

    ax.axhline(0, color="#BBBBBB", lw=0.5, zorder=1)
    ax.set_xlabel("follow-up time")
    ax.set_ylabel("cumulative incidence")
    ax.set_xlim(t.min(), t.max())
    ax.set_ylim(0, max_cif * 1.15)
    ax.legend(fontsize=6.8, frameon=False, loc="upper left",
              handlelength=1.4)
    ax.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    if contract.grays_test_p is not None:
        p = float(contract.grays_test_p)
        verdict = ("different CIFs (p < 0.05)" if p < 0.05
                   else "no evidence of difference")
        ax.set_title(
            f"{contract.title}  ·  Gray's p = {smart_fmt(p)}  "
            f"· {verdict}",
            fontsize=8.4, pad=4,
        )
    else:
        ax.set_title(contract.title, fontsize=9.0, pad=4)
    return ax
