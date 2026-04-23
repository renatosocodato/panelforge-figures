"""Number-needed-to-treat forest — per-subgroup NNT ± 95 % CI with
reference band at NNT = ∞ (no benefit).

Distinct from `subgroup_forest_plot` (HR/OR metric); here the scale
is NNT (counts to prevent one event).
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


class NNTRow(RecipeContract):
    subgroup: str
    nnt: float = Field(..., description="NNT estimate (positive number)")
    nnt_lo: float
    nnt_hi: float
    n_treated: int = 0
    events_treated: int = 0
    events_control: int = 0


class NNTForestInput(RecipeContract):
    rows: list[NNTRow] = Field(..., min_length=3)
    title: str = "Number needed to treat"


def _demo() -> NNTForestInput:
    rng = np.random.default_rng(2407)
    subgroups = [
        "overall",
        "age < 65",
        "age ≥ 65",
        "female",
        "male",
        "prior event",
        "no prior event",
        "diabetes",
        "no diabetes",
    ]
    nnts = [18, 16, 22, 28, 14, 10, 32, 12, 24]
    se = [0.08, 0.12, 0.18, 0.22, 0.12, 0.10, 0.26, 0.14, 0.20]
    rows = []
    for s, n, sn in zip(subgroups, nnts, se):
        # Transform NNT to approximately log-normal CI: NNT = 1/ARR.
        # For realism just widen the NNT CI by a multiplicative factor.
        lo = float(n * np.exp(-1.96 * sn))
        hi = float(n * np.exp(+1.96 * sn))
        rows.append(NNTRow(
            subgroup=s,
            nnt=float(n),
            nnt_lo=lo, nnt_hi=hi,
            n_treated=400, events_treated=24,
            events_control=40,
        ))
    return NNTForestInput(rows=rows)


_META = RecipeMetadata(
    name="number_needed_to_treat_forest",
    modality="clinical_cohort",
    family=RecipeFamily.coef_forest,
    answers_question=(
        "Across subgroups / conditions, what is the number needed to "
        "treat (NNT) to prevent one event, with 95 % CI?"
    ),
    required_fields=("rows",),
    optional_fields=("title",),
    file_format_hints=("csv",),
    alternatives_in_modality=("subgroup_forest_plot",),
)


@register_recipe(
    metadata=_META, contract=NNTForestInput, demo_contract=_demo,
)
def render(contract: NNTForestInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 4.0))
    AESTHETIC.apply_to_ax(ax)

    rows = list(contract.rows)
    names = [r.subgroup for r in rows]
    nnt = np.asarray([r.nnt for r in rows], float)
    lo = np.asarray([r.nnt_lo for r in rows], float)
    hi = np.asarray([r.nnt_hi for r in rows], float)

    # Sort by NNT ascending (more effective at top).
    order = np.argsort(nnt)
    names_s = [names[i] for i in order]
    nnt_s = nnt[order]
    lo_s = lo[order]
    hi_s = hi[order]

    y = np.arange(len(names_s))

    # Highlight "overall" if present.
    is_overall = np.array([n.strip().lower() == "overall"
                           for n in names_s])

    # CI whiskers.
    for yi, lo_i, hi_i in zip(y, lo_s, hi_s):
        ax.plot([lo_i, hi_i], [yi, yi],
                color="#555555", lw=1.1, zorder=3)
    # Markers.
    colors = np.where(is_overall, "#C62828", "#1565C0")
    sizes = np.where(is_overall, 80, 50)
    for yi, pt, c, s in zip(y, nnt_s, colors, sizes):
        ax.scatter([pt], [yi], s=s, color=c,
                   edgecolor="white", linewidth=0.6, zorder=5)

    # NNT = ∞ / "no benefit" reference band.
    max_shown = float(hi_s.max()) * 1.4
    ax.axvline(max_shown * 0.95, color="#888888", lw=0.5, ls="--",
               zorder=2, label="no benefit (NNT -> inf)")

    # Numeric annotations at right-edge.
    for yi, pt, lo_i, hi_i in zip(y, nnt_s, lo_s, hi_s):
        ax.text(max_shown * 0.98, yi,
                f"NNT {smart_fmt(float(pt))}  "
                f"[{smart_fmt(float(lo_i))}, {smart_fmt(float(hi_i))}]",
                ha="right", va="center", fontsize=6.4,
                color="#333333", zorder=6)

    ax.set_yticks(y)
    ax.set_yticklabels(names_s, fontsize=7.0)
    ax.set_xlabel("number needed to treat (lower is better)")
    ax.set_xlim(0, max_shown)
    ax.legend(fontsize=6.8, frameon=False, loc="lower right",
              handlelength=1.4)
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    best = int(np.argmin(nnt_s))
    worst = int(np.argmax(nnt_s))
    ax.set_title(
        f"{contract.title}  ·  best: {names_s[best]} "
        f"(NNT {smart_fmt(float(nnt_s[best]))})  ·  "
        f"worst: {names_s[worst]} "
        f"(NNT {smart_fmt(float(nnt_s[worst]))})",
        fontsize=8.2, pad=4,
    )
    return ax
