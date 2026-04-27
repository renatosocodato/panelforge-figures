"""Protrusion commitment survival — KM step curves of P(still alive
at tau) per condition, with Greenwood CI ribbons and a median-
lifetime callout per condition.

Diagnostic-curve family: >=2 curves + >=1 legend.
"""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    kaplan_meier,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC
from ._shared import ProtrusionPolyline

_CONDITION_PALETTE = {
    "control": "#37474F", "DISC1": "#EF5350",
    "WT": "#37474F", "LI": "#EF5350",
    "treated": "#26A69A", "rescue": "#AB47BC",
}


class ProtrusionCommitmentSurvivalInput(RecipeContract):
    protrusions: list[ProtrusionPolyline] = Field(..., min_length=4)
    condition_by_protrusion: dict[str, str] = Field(...)
    title: str = "Protrusion commitment survival"


def _demo() -> ProtrusionCommitmentSurvivalInput:
    rng = np.random.default_rng(3001)
    protrusions: list[ProtrusionPolyline] = []
    cond_by: dict[str, str] = {}
    for cond, scale in (("control", 80.0), ("DISC1", 50.0)):
        for k in range(80):
            pid = f"{cond}_p{k:03d}"
            protrusions.append(ProtrusionPolyline(
                protrusion_id=pid,
                xy_um=[[0.0, 0.0], [1.0, 1.0]],
                parent_cell_id=f"{cond}_c{k // 4:02d}",
                born_s=0.0,
                died_s=float(rng.exponential(scale)),
            ))
            cond_by[pid] = cond
    return ProtrusionCommitmentSurvivalInput(
        protrusions=protrusions,
        condition_by_protrusion=cond_by,
    )


_META = RecipeMetadata(
    name="protrusion_commitment_survival",
    modality="intravital_imaging",
    family=RecipeFamily.diagnostic_curve,
    answers_question=(
        "Once nucleated, what fraction of protrusions are still "
        "alive at time tau, per condition?"
    ),
    required_fields=("protrusions", "condition_by_protrusion"),
    optional_fields=("title",),
    file_format_hints=("yaml", "json"),
    alternatives_in_modality=("commitment_hazard_with_age",),
)


@register_recipe(
    metadata=_META,
    contract=ProtrusionCommitmentSurvivalInput,
    demo_contract=_demo,
)
def render(contract: ProtrusionCommitmentSurvivalInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 3.8))
    AESTHETIC.apply_to_ax(ax)

    by_cond: dict[str, list[float]] = {}
    censored_by: dict[str, list[bool]] = {}
    for proto in contract.protrusions:
        cond = contract.condition_by_protrusion.get(proto.protrusion_id, "?")
        if proto.died_s is None:
            duration = 1.0
            cens = True
        else:
            duration = float(proto.died_s - (proto.born_s or 0.0))
            cens = False
        by_cond.setdefault(cond, []).append(duration)
        censored_by.setdefault(cond, []).append(cens)

    medians: dict[str, float] = {}
    for cond, durations in by_cond.items():
        cens = censored_by[cond]
        t, s, lo, hi = kaplan_meier(durations, cens)
        if t.size == 0:
            continue
        ts = np.r_[0.0, t]
        ss = np.r_[1.0, s]
        colour = _CONDITION_PALETTE.get(cond, "#37474F")
        ax.step(ts, ss, where="post",
                color=colour, lw=1.4, zorder=4, label=cond)
        ax.fill_between(ts, np.r_[1.0, lo], np.r_[1.0, hi],
                        step="post", color=colour, alpha=0.18,
                        linewidth=0, zorder=2)
        # Median lifetime (S = 0.5 crossing).
        below = np.where(s < 0.5)[0]
        if below.size:
            medians[cond] = float(t[below[0]])

    ax.set_xlabel("time tau (s)")
    ax.set_ylabel("S(tau)  ·  P(still alive)")
    ax.set_ylim(0, 1.05)
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(fontsize=6.8, frameon=False, loc="upper right",
              handlelength=1.4)

    bits = [f"{c}: med {smart_fmt(m)} s" for c, m in medians.items()]
    ax.set_title(
        f"{contract.title}  ·  " + "   ".join(bits),
        fontsize=8.4, pad=4,
    )
    return ax
