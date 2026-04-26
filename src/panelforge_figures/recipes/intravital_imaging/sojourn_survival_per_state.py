"""Sojourn survival per decoded state — Kaplan-Meier S(tau) curve per
state with Greenwood 95% CI ribbon and a dashed geometric reference
for HMM compatibility.

Companion to A.4 (dwell-time distribution): when S(tau) follows a
straight line on log-y, dwells are geometric and HMM is fine; when
S(tau) bends (concave or convex), dwells are non-geometric and HSMM
is needed.

Diagnostic-curve family: >=2 curves + >=1 legend. Satisfied by per-
state KM curves (>=2 by demo) + dashed geometric reference + legend.
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
from ._shared import _demo_state_palette


class SojournSurvivalPerStateInput(RecipeContract):
    dwells_by_state: dict[str, list[float]] = Field(...)
    decoder_label: str = "HMM"
    reference_geometric: bool = True
    log_y: bool = False
    title: str = "Sojourn survival per state"


def _demo() -> SojournSurvivalPerStateInput:
    rng = np.random.default_rng(1721)
    return SojournSurvivalPerStateInput(
        dwells_by_state={
            "S0": rng.geometric(p=0.20, size=120).astype(float).tolist(),
            "S1": rng.gamma(shape=4.0, scale=1.5, size=120).tolist(),
            "S2": rng.lognormal(mean=2.0, sigma=0.4, size=120).tolist(),
        },
        decoder_label="HMM",
    )


_META = RecipeMetadata(
    name="sojourn_survival_per_state",
    modality="intravital_imaging",
    family=RecipeFamily.diagnostic_curve,
    answers_question=(
        "Per decoded state, how does the sojourn survival S(tau) behave, "
        "and is it consistent with HMM (geometric / log-linear)?"
    ),
    required_fields=("dwells_by_state",),
    optional_fields=(
        "decoder_label", "reference_geometric", "log_y", "title",
    ),
    file_format_hints=("yaml", "json"),
    alternatives_in_modality=("dwell_time_distribution_per_state",),
)


@register_recipe(
    metadata=_META,
    contract=SojournSurvivalPerStateInput,
    demo_contract=_demo,
)
def render(contract: SojournSurvivalPerStateInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.8, 3.8))
    AESTHETIC.apply_to_ax(ax)

    states = list(contract.dwells_by_state.keys())
    palette = _demo_state_palette(states)
    median_dwells: dict[str, float] = {}

    for state in states:
        vals = np.asarray(contract.dwells_by_state[state], float)
        if vals.size == 0:
            continue
        t, s, lo, hi = kaplan_meier(vals)
        if t.size == 0:
            continue
        # Step-style curve.
        ts = np.r_[0.0, t]
        ss = np.r_[1.0, s]
        colour = palette.get(state, "#555555")
        ax.step(ts, ss, where="post",
                color=colour, lw=1.2, zorder=4, label=state)
        # CI ribbon as a stepped fill_between.
        lo_pad = np.r_[1.0, lo]
        hi_pad = np.r_[1.0, hi]
        ax.fill_between(ts, lo_pad, hi_pad, step="post",
                        color=colour, alpha=0.18, linewidth=0,
                        zorder=2)
        median_dwells[state] = float(np.median(vals))

    # Dashed geometric reference at mean dwell of state 0.
    if contract.reference_geometric and median_dwells:
        ref_state = states[0]
        mean_d = float(np.mean(contract.dwells_by_state[ref_state]))
        if mean_d > 1.0:
            t_ref = np.linspace(0, max(median_dwells.values()) * 3, 100)
            s_ref = np.exp(-t_ref / mean_d)
            ax.plot(t_ref, s_ref, color="#888888", lw=0.7, ls="--",
                    zorder=3,
                    label=f"geometric (mean {smart_fmt(mean_d)})")

    if contract.log_y:
        ax.set_yscale("log")
        ax.set_ylim(1e-3, 1.05)
    else:
        ax.set_ylim(0, 1.05)
    ax.set_xlabel("dwell time (frames)")
    ax.set_ylabel("S(tau)")
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(fontsize=6.8, frameon=False, loc="upper right",
              handlelength=1.4)
    ax.set_title(
        f"{contract.title}  ·  {contract.decoder_label}  ·  "
        + "  ".join(f"{s}: med {smart_fmt(m)}"
                    for s, m in median_dwells.items()),
        fontsize=8.2, pad=4,
    )
    return ax
