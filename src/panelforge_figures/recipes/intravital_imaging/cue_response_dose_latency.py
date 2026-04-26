"""Cue-response dose-latency — tau_reorient vs gradient magnitude
|grad c| with fitted curve and 95 % CI band.

Timecourse-hierarchical-CI family: >=1 CI band + >=1 mean line.
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


class CueDoseLatencyRow(RecipeContract):
    cell_id: str
    gradient_um_per_um: float
    latency_s: float
    condition: str = "control"


class CueResponseDoseLatencyInput(RecipeContract):
    rows: list[CueDoseLatencyRow] = Field(..., min_length=10)
    fit_family: str = Field(
        "power",
        description="'power' | 'logistic' | 'none'",
    )
    title: str = "Cue-response dose-latency"


def _demo() -> CueResponseDoseLatencyInput:
    rng = np.random.default_rng(3081)
    rows: list[CueDoseLatencyRow] = []
    # tau ~ |grad|^-0.6 with cohort-distinct prefactor.
    for cond, prefactor in (("control", 60.0), ("DISC1", 110.0)):
        for k in range(40):
            grad = float(np.exp(rng.uniform(np.log(0.05), np.log(2.0))))
            tau = prefactor * grad ** (-0.6) + rng.normal(0, 4.0)
            rows.append(CueDoseLatencyRow(
                cell_id=f"{cond}_C{k:02d}",
                gradient_um_per_um=grad,
                latency_s=max(float(tau), 1.0),
                condition=cond,
            ))
    return CueResponseDoseLatencyInput(rows=rows)


_META = RecipeMetadata(
    name="cue_response_dose_latency",
    modality="intravital_imaging",
    family=RecipeFamily.timecourse_hierarchical_ci,
    answers_question=(
        "Does the reorientation latency tau_reorient scale with "
        "the cue gradient |grad c|, and how?"
    ),
    required_fields=("rows",),
    optional_fields=("fit_family", "title"),
    file_format_hints=("csv",),
    alternatives_in_modality=("chemotaxis_index_trajectory",),
)


_CONDITION_PALETTE = {
    "control": "#37474F", "DISC1": "#EF5350",
    "WT": "#37474F", "LI": "#EF5350",
}


@register_recipe(
    metadata=_META,
    contract=CueResponseDoseLatencyInput,
    demo_contract=_demo,
)
def render(contract: CueResponseDoseLatencyInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 3.8))
    AESTHETIC.apply_to_ax(ax)

    by_cond: dict[str, list[CueDoseLatencyRow]] = {}
    for r in contract.rows:
        by_cond.setdefault(r.condition, []).append(r)

    bits = []
    for cond, rows in by_cond.items():
        g = np.array([r.gradient_um_per_um for r in rows], float)
        t = np.array([r.latency_s for r in rows], float)
        colour = _CONDITION_PALETTE.get(cond, "#37474F")
        ax.scatter(g, t, s=22, color=colour,
                   edgecolor="white", linewidth=0.5, alpha=0.75,
                   zorder=4, label=cond)
        # Fit power-law on log-log.
        if contract.fit_family == "power" and g.size >= 4:
            log_g = np.log(g)
            log_t = np.log(t)
            slope, intercept = np.polyfit(log_g, log_t, 1)
            g_fit = np.linspace(g.min(), g.max(), 60)
            t_fit = np.exp(intercept + slope * np.log(g_fit))
            # Bootstrap CI.
            rng = np.random.default_rng(17)
            boot = []
            for _ in range(200):
                idx = rng.integers(0, g.size, size=g.size)
                s_b, i_b = np.polyfit(np.log(g[idx]), np.log(t[idx]), 1)
                boot.append(np.exp(i_b + s_b * np.log(g_fit)))
            boot_arr = np.asarray(boot)
            lo = np.quantile(boot_arr, 0.025, axis=0)
            hi = np.quantile(boot_arr, 0.975, axis=0)
            ax.plot(g_fit, t_fit, color=colour, lw=1.4, zorder=5)
            ax.fill_between(g_fit, lo, hi, color=colour,
                            alpha=0.18, linewidth=0, zorder=2)
            bits.append(f"{cond}: slope = {smart_fmt(slope)}")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("gradient magnitude |grad c| (um/um)")
    ax.set_ylabel("tau_reorient (s)")
    ax.grid(which="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(fontsize=6.8, frameon=False, loc="upper right",
              handlelength=1.4)
    ax.set_title(
        f"{contract.title}  ·  " + "   ".join(bits),
        fontsize=8.2, pad=4,
    )
    return ax
