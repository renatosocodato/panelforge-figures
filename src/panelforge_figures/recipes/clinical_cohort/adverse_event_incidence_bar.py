"""Adverse-event incidence — horizontal bar per AE category comparing
arm incidence rates with risk-ratio annotation.

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


class AERow(RecipeContract):
    name: str
    rate_arm_a: float = Field(..., ge=0.0, le=1.0)
    rate_arm_b: float = Field(..., ge=0.0, le=1.0)
    serious: bool = False


class AEIncidenceInput(RecipeContract):
    rows: list[AERow] = Field(..., min_length=3)
    arm_a_label: str = "arm A"
    arm_b_label: str = "arm B"
    title: str = "Adverse-event incidence"


def _demo() -> AEIncidenceInput:
    rng = np.random.default_rng(2617)
    ae_names = ["any AE", "serious AE",
                "nausea", "headache", "fatigue",
                "injection-site reaction",
                "elevated ALT", "hypotension", "infection"]
    # Arm A = treatment (higher rates for some).
    a = [0.48, 0.08, 0.22, 0.18, 0.25, 0.14, 0.06, 0.05, 0.07]
    b = [0.41, 0.06, 0.17, 0.18, 0.19, 0.05, 0.04, 0.05, 0.08]
    serious = [False, True, False, False, False,
               False, True, True, False]
    rows = [
        AERow(name=n, rate_arm_a=float(aa), rate_arm_b=float(bb),
              serious=s)
        for n, aa, bb, s in zip(ae_names, a, b, serious)
    ]
    return AEIncidenceInput(
        rows=rows,
        arm_a_label="treatment",
        arm_b_label="control",
    )


_META = RecipeMetadata(
    name="adverse_event_incidence_bar",
    modality="clinical_cohort",
    family=RecipeFamily.ladder,
    answers_question=(
        "Per adverse-event category, how do incidence rates compare "
        "across arms (and how many are serious)?"
    ),
    required_fields=("rows",),
    optional_fields=("arm_a_label", "arm_b_label", "title"),
    file_format_hints=("csv",),
    alternatives_in_modality=("subgroup_forest_plot",),
)


@register_recipe(
    metadata=_META, contract=AEIncidenceInput, demo_contract=_demo,
)
def render(contract: AEIncidenceInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.0, 4.2))
    AESTHETIC.apply_to_ax(ax)

    rows = list(contract.rows)
    names = [r.name for r in rows]
    a = np.asarray([r.rate_arm_a for r in rows], float)
    b = np.asarray([r.rate_arm_b for r in rows], float)
    serious = [r.serious for r in rows]

    # Sort by treatment (arm A) rate descending.
    order = np.argsort(-a)
    names_s = [names[i] for i in order]
    a_s = a[order]
    b_s = b[order]
    serious_s = [serious[i] for i in order]

    y = np.arange(len(names_s))
    height = 0.36

    ax.barh(y + height / 2, a_s, height=height,
            color="#1565C0", edgecolor="white", linewidth=0.6,
            alpha=0.92, zorder=3,
            label=contract.arm_a_label)
    ax.barh(y - height / 2, b_s, height=height,
            color="#BDBDBD", edgecolor="white", linewidth=0.6,
            alpha=0.92, zorder=3,
            label=contract.arm_b_label)

    # Per-bar numeric + RR.
    for yi, ai, bi in zip(y, a_s, b_s):
        # Place numeric labels RIGHT of longer of the two bars.
        max_w = max(ai, bi)
        rr = ai / max(bi, 1e-6)
        ax.text(max_w + 0.01, yi,
                f"{ai:.0%} vs {bi:.0%}   RR = {smart_fmt(float(rr))}",
                ha="left", va="center", fontsize=6.4,
                color="#333333", zorder=5)

    # Serious-event marker to the left of the name.
    for yi, is_serious in zip(y, serious_s):
        if is_serious:
            ax.text(-0.01, yi, "!",
                    ha="right", va="center", fontsize=9.0,
                    color="#C62828", fontweight="bold",
                    transform=ax.get_yaxis_transform(), zorder=6)

    ax.set_yticks(y)
    ax.set_yticklabels(names_s, fontsize=7.0)
    ax.invert_yaxis()
    ax.set_xlabel("incidence rate")
    ax.set_xlim(0, max(a.max(), b.max()) * 1.55)
    ax.legend(fontsize=6.8, frameon=False, loc="lower right",
              handlelength=1.2)
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    n_serious = sum(1 for s in serious if s)
    ax.set_title(
        f"{contract.title}  ·  {len(rows)} AE categories  "
        f"({n_serious} serious; ! markers)",
        fontsize=8.6, pad=4,
    )
    return ax
