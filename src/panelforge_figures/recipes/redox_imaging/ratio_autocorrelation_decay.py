"""Temporal autocorrelation of ratio(t) per redox state.

Plots the autocorrelation function ACF(τ) of ratio(t) separately for
cells in the reduced and oxidized states, with single-exponential fits
τ_reduced, τ_oxidized and a crossover-τ annotation.

Distinct from `drift_diffusion_decomposition` (drift + diffusion
coefficients, not ACF) and `ratio_trajectory_with_phase_annotation`
(raw trajectory, not ACF).
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


class RatioACFInput(RecipeContract):
    tau_s: list[float] = Field(..., min_length=3)
    acf_by_state: dict[str, list[float]] = Field(
        ..., description="state name ('reduced','oxidized','intermediate') → ACF(τ)"
    )
    tau_fit_by_state: dict[str, float] | None = Field(
        None, description="fitted decay constants per state (s)"
    )
    title: str = "Ratio autocorrelation by state"


def _demo() -> RatioACFInput:
    rng = np.random.default_rng(631)
    tau = np.linspace(0.0, 60.0, 50)
    t_red = 18.0
    t_ox = 32.0
    t_int = 24.0
    acf = {
        "reduced":  np.exp(-tau / t_red) + rng.normal(0, 0.015, tau.size),
        "oxidized": np.exp(-tau / t_ox) + rng.normal(0, 0.015, tau.size),
        "intermediate": np.exp(-tau / t_int) + rng.normal(0, 0.015, tau.size),
    }
    return RatioACFInput(
        tau_s=tau.tolist(),
        acf_by_state={k: v.tolist() for k, v in acf.items()},
        tau_fit_by_state={
            "reduced": t_red, "oxidized": t_ox, "intermediate": t_int,
        },
    )


_META = RecipeMetadata(
    name="ratio_autocorrelation_decay",
    modality="redox_imaging",
    family=RecipeFamily.diagnostic_curve,
    answers_question=(
        "How fast does the redox ratio decorrelate in time, broken "
        "down by state (reduced vs oxidized)?"
    ),
    required_fields=("tau_s", "acf_by_state"),
    optional_fields=("tau_fit_by_state", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=(
        "drift_diffusion_decomposition",
        "ratio_trajectory_with_phase_annotation",
    ),
)


@register_recipe(
    metadata=_META,
    contract=RatioACFInput,
    demo_contract=_demo,
)
def render(contract: RatioACFInput, ax=None, **_):
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
        ax.plot(tau, v, color=color, lw=1.1, alpha=0.55,
                zorder=2, label=f"{name} (data)")
        # Fitted exponential overlay.
        t_fit = fits.get(name)
        if t_fit is not None:
            ax.plot(tau, np.exp(-tau / float(t_fit)),
                    color=color, lw=1.5, zorder=3,
                    label=rf"{name}  $\tau$={smart_fmt(float(t_fit))} s")

    # 1/e reference.
    ax.axhline(1.0 / np.e, color="#888888", lw=0.6, ls="--", zorder=1,
               label="1/e")

    # Crossover callout: pair with longest - shortest τ difference.
    if fits:
        taus = fits
        if len(taus) >= 2:
            slowest = max(taus, key=lambda k: taus[k])
            fastest = min(taus, key=lambda k: taus[k])
            ratio = taus[slowest] / max(taus[fastest], 1e-9)
            ax.text(
                0.98, 0.98,
                f"τ({slowest}) / τ({fastest}) = {smart_fmt(ratio)}",
                transform=ax.transAxes, ha="right", va="top",
                fontsize=6.6, color="#111111",
                bbox=dict(boxstyle="round,pad=0.22", fc="white",
                          ec="#BBBBBB", lw=0.5, alpha=0.95),
                zorder=6,
            )

    ax.set_xlabel(r"lag $\tau$ (s)")
    ax.set_ylabel("ACF")
    ax.set_xlim(0, tau.max())
    ax.set_ylim(-0.05, 1.05)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.4, frameon=False, loc="center right",
              handlelength=1.6)
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
