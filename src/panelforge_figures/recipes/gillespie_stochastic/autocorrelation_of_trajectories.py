"""Temporal autocorrelation ACF(τ) of sampled SSA trajectories.

Per-state (or per-condition) ACF(τ) of the sampled SSA trajectory,
with an exponential fit and a 1/e reference line. Fitted decay
constants τ_c are shown in the legend.
"""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class TrajectoryACFInput(RecipeContract):
    tau_s: list[float] = Field(..., min_length=3)
    acf_by_state: dict[str, list[float]] = Field(
        ..., description="state → ACF(τ)"
    )
    tau_fit_by_state: dict[str, float] | None = None
    title: str = "Trajectory autocorrelation"


def _demo() -> TrajectoryACFInput:
    rng = np.random.default_rng(523)
    tau = np.linspace(0.0, 40.0, 60)
    taus = {"HOME": 8.0, "GATE": 3.5, "TRAP": 14.0}
    acf = {
        s: (np.exp(-tau / t) + rng.normal(0, 0.015, tau.size)).tolist()
        for s, t in taus.items()
    }
    return TrajectoryACFInput(
        tau_s=tau.tolist(),
        acf_by_state=acf,
        tau_fit_by_state=taus,
    )


_META = RecipeMetadata(
    name="autocorrelation_of_trajectories",
    modality="gillespie_stochastic",
    family=RecipeFamily.diagnostic_curve,
    answers_question=(
        "How fast do the sampled SSA trajectories decorrelate in "
        "time, and does the decay differ by state?"
    ),
    required_fields=("tau_s", "acf_by_state"),
    optional_fields=("tau_fit_by_state", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("noise_power_spectrum",),
)


@register_recipe(
    metadata=_META,
    contract=TrajectoryACFInput,
    demo_contract=_demo,
)
def render(contract: TrajectoryACFInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    tau = np.asarray(contract.tau_s, float)
    fits = contract.tau_fit_by_state or {}

    for name, vals in contract.acf_by_state.items():
        v = np.asarray(vals, float)
        color = (palette.pick(name) if name in palette.semantic
                 else palette[0])
        ax.plot(tau, v, color=color, lw=1.0, alpha=0.55, zorder=2,
                label=f"{name} (data)")
        t_fit = fits.get(name)
        if t_fit is not None:
            ax.plot(tau, np.exp(-tau / float(t_fit)),
                    color=color, lw=1.4, zorder=3,
                    label=rf"{name}  $\tau_c$={smart_fmt(float(t_fit))} s")

    # 1/e reference.
    ax.axhline(1.0 / np.e, color="#888888", lw=0.6, ls="--", zorder=1,
               label="1/e")

    ax.set_xlabel(r"lag $\tau$ (s)")
    ax.set_ylabel("ACF")
    ax.set_xlim(0, tau.max())
    ax.set_ylim(-0.05, 1.05)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.4, frameon=False, loc="center right",
              handlelength=1.6)
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    if fits:
        slowest = max(fits, key=lambda k: fits[k])
        fastest = min(fits, key=lambda k: fits[k])
        ratio = fits[slowest] / max(fits[fastest], 1e-9)
        ax.text(
            0.98, 0.97,
            rf"$\tau_c$({slowest}) / $\tau_c$({fastest}) = {smart_fmt(ratio)}",
            transform=ax.transAxes, ha="right", va="top",
            fontsize=6.6, color="#111111",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.95),
            zorder=6,
        )
    return ax
