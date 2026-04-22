"""Ensemble- vs time-averaged MSD — ergodicity diagnostic. Overlays
the ensemble-averaged MSD curve with a cloud of per-track time-
averaged MSD curves; an EB (ergodicity-breaking) parameter callout
quantifies the spread.

Distinct from `msd_by_condition` (ensemble only, multiple conditions).
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


class EAvsTAInput(RecipeContract):
    lag_s: list[float] = Field(..., min_length=5)
    ea_msd: list[float] = Field(
        ..., description="ensemble-averaged MSD at each lag"
    )
    ta_msd_per_track: list[list[float]] = Field(
        ..., description="per-track TA-MSD at each lag (n_tracks × n_lags)"
    )
    title: str = "EA-MSD vs TA-MSD — ergodicity"


def _demo() -> EAvsTAInput:
    rng = np.random.default_rng(2311)
    lags = np.logspace(-1, 1.2, 18)
    # Generate heterogeneous tracks: mix of α=0.6 and α=1.0 with
    # different D amplitudes.
    n_tracks = 40
    ta = []
    for _ in range(n_tracks):
        alpha = rng.choice([0.6, 1.0])
        D = rng.lognormal(-1.5, 0.25)
        msd = 4 * D * lags ** alpha * np.exp(rng.normal(0, 0.10, lags.size))
        ta.append(msd.tolist())
    ta_arr = np.array(ta)
    ea = ta_arr.mean(axis=0)
    return EAvsTAInput(
        lag_s=lags.tolist(),
        ea_msd=ea.tolist(),
        ta_msd_per_track=ta,
    )


_META = RecipeMetadata(
    name="ensemble_vs_time_averaged_msd",
    modality="diffusion_and_tracking",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "Is motion ergodic? Do ensemble-averaged and time-averaged MSDs "
        "agree, or is there a population of slow / fast tracks?"
    ),
    required_fields=("lag_s", "ea_msd", "ta_msd_per_track"),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("msd_by_condition",),
)


@register_recipe(
    metadata=_META,
    contract=EAvsTAInput,
    demo_contract=_demo,
)
def render(contract: EAvsTAInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.6))
    AESTHETIC.apply_to_ax(ax)

    lags = np.asarray(contract.lag_s, float)
    ea = np.asarray(contract.ea_msd, float)
    ta = np.asarray(contract.ta_msd_per_track, float)   # (n_tracks, n_lags)

    # Plot each TA-MSD as a thin grey line + endpoint scatter.
    for row in ta:
        ax.plot(lags, row, color="#BBBBBB", lw=0.5, alpha=0.6, zorder=2)
    # Scatter of all (τ, TA) points.
    all_tau = np.repeat(lags[None, :], ta.shape[0], axis=0).ravel()
    all_ta = ta.ravel()
    ax.scatter(all_tau, all_ta, s=6, color="#BBBBBB", alpha=0.4,
               edgecolor="none", zorder=2)

    # Ensemble-averaged MSD.
    ax.plot(lags, ea, color="#222222", lw=1.4, zorder=5,
            label="EA-MSD (ensemble)")

    # Per-track median TA-MSD as a reference.
    ta_median = np.median(ta, axis=0)
    ax.plot(lags, ta_median, color="#1565C0", lw=1.2, ls="--", zorder=5,
            label="TA-MSD (median per track)")

    # Ergodicity-breaking parameter at the smallest useful lag: EB(τ) =
    # <(TA(τ))²>/<TA(τ)>² - 1. Take the smallest lag.
    ta_tau0 = ta[:, 0]
    EB0 = float(np.mean(ta_tau0 ** 2) / max(np.mean(ta_tau0) ** 2, 1e-12) - 1)
    ta_long = ta[:, -1]
    EB_long = float(np.mean(ta_long ** 2) / max(np.mean(ta_long) ** 2, 1e-12) - 1)

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(r"lag time τ (s)")
    ax.set_ylabel(r"MSD (μm$^2$)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="upper left",
              handlelength=1.6)
    ax.grid(axis="both", which="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    ax.text(0.98, 0.04,
            f"EB(τ_min) = {smart_fmt(EB0)}\n"
            f"EB(τ_max) = {smart_fmt(EB_long)}\n"
            "EB -> 0 <-> ergodic",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=6.4, color="#333333",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=6)
    return ax
