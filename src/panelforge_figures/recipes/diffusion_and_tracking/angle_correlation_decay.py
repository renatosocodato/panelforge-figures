"""Angle autocorrelation decay — ⟨cos(θ_t · θ_0)⟩ vs time-lag with exp fit."""

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


class AngleDecayInput(RecipeContract):
    lag_s: list[float] = Field(...)
    cos_mean: list[float] = Field(..., description=r"⟨cos(θ_t θ_0)⟩ at each lag")
    cos_sem: list[float] = Field(default_factory=list)
    title: str = "Angle correlation decay"


def _demo() -> AngleDecayInput:
    rng = np.random.default_rng(373)
    lags = np.linspace(0, 8, 40)
    # Exponential decay with persistence time 1.8 s.
    tau_p = 1.8
    cos_mean = np.exp(-lags / tau_p) + rng.normal(0, 0.02, lags.size)
    cos_sem = np.full(lags.size, 0.04)
    return AngleDecayInput(
        lag_s=lags.tolist(),
        cos_mean=cos_mean.tolist(),
        cos_sem=cos_sem.tolist(),
    )


_META = RecipeMetadata(
    name="angle_correlation_decay",
    modality="diffusion_and_tracking",
    family=RecipeFamily.diagnostic_curve,
    answers_question="How quickly does directional memory decay, and what is the motion's persistence time?",
    required_fields=("lag_s", "cos_mean"),
    optional_fields=("cos_sem", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("msd_by_condition",),
)


@register_recipe(metadata=_META, contract=AngleDecayInput, demo_contract=_demo)
def render(contract: AngleDecayInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.6, 3.0))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)
    accent = palette[5]

    lags = np.array(contract.lag_s, dtype=float)
    cm = np.array(contract.cos_mean, dtype=float)
    csem = (np.array(contract.cos_sem, dtype=float)
            if contract.cos_sem else np.zeros_like(cm))

    ax.fill_between(lags, cm - csem, cm + csem, color=accent, alpha=0.18,
                    linewidth=0, zorder=2)
    ax.plot(lags, cm, color=accent, lw=1.2, zorder=3, label="data")
    ax.axhline(0, color="#888888", lw=0.5, ls=":", zorder=1)

    # Exponential fit cm = exp(-lag/tau).
    good = cm > 0.02
    if good.sum() >= 3:
        tau = -1.0 / np.polyfit(lags[good], np.log(cm[good]), 1)[0]
    else:
        tau = np.nan
    if np.isfinite(tau):
        ax.plot(lags, np.exp(-lags / tau),
                color="#111111", lw=1.0, ls="--", zorder=4,
                label=rf"fit: $\tau$={smart_fmt(float(tau))} s")

    ax.set_xlabel(r"lag $\tau$ (s)")
    ax.set_ylabel(r"$\langle \cos(\theta_t\,\theta_0) \rangle$")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="upper right",
              handlelength=1.8)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
