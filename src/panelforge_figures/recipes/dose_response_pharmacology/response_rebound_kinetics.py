"""Washout / recovery kinetics with rebound-peak annotation."""

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


class ReboundKineticsInput(RecipeContract):
    time_min: list[float] = Field(..., min_length=3)
    response: list[float] = Field(...)
    response_sem: list[float] | None = None
    washout_onset_min: float = Field(default=30.0)
    baseline: float = Field(default=0.0)
    recovery_tau_min: float | None = None
    title: str = "Response rebound / recovery"


def _demo() -> ReboundKineticsInput:
    rng = np.random.default_rng(173)
    t = np.linspace(0, 90, 180)
    washout = 30.0
    # Drug-on from 0-30 min (response suppressed), washout triggers
    # rebound that overshoots then decays back to 0.
    resp = np.where(
        t < washout,
        -50.0 + rng.normal(0, 2.0, t.size),
        40.0 * np.exp(-(t - washout) / 12.0) * np.sin(0.12 * (t - washout))
        + rng.normal(0, 2.0, t.size),
    )
    sem = 3.0 * np.ones_like(t)
    return ReboundKineticsInput(
        time_min=t.tolist(),
        response=resp.tolist(),
        response_sem=sem.tolist(),
        washout_onset_min=washout,
        baseline=0.0,
        recovery_tau_min=12.0,
    )


_META = RecipeMetadata(
    name="response_rebound_kinetics",
    modality="dose_response_pharmacology",
    family=RecipeFamily.diagnostic_curve,
    answers_question=(
        "After washout, how does the response recover — does it "
        "overshoot (rebound) before returning to baseline?"
    ),
    required_fields=("time_min", "response"),
    optional_fields=(
        "response_sem", "washout_onset_min", "baseline",
        "recovery_tau_min", "title",
    ),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("hill_fit_with_ci",),
)


@register_recipe(
    metadata=_META,
    contract=ReboundKineticsInput,
    demo_contract=_demo,
)
def render(contract: ReboundKineticsInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 3.2))
    AESTHETIC.apply_to_ax(ax)

    t = np.asarray(contract.time_min, float)
    r = np.asarray(contract.response, float)
    sem = (np.asarray(contract.response_sem, float)
           if contract.response_sem is not None else None)

    color = "#5E35B1"
    if sem is not None:
        ax.fill_between(t, r - sem / 2, r + sem / 2, color=color,
                        alpha=0.18, linewidth=0, zorder=2)
    ax.plot(t, r, color=color, lw=1.2, zorder=3, label="response")

    # Baseline reference.
    ax.axhline(contract.baseline, color="#888888", lw=0.6, ls="--",
               zorder=1, label=f"baseline = {smart_fmt(contract.baseline)}")

    # Washout onset.
    ax.axvline(contract.washout_onset_min, color="#D32F2F", lw=0.8,
               ls="--", zorder=4, label="washout onset")
    ax.text(contract.washout_onset_min, ax.get_ylim()[1],
            "  washout", ha="left", va="top", fontsize=6.6,
            color="#D32F2F", zorder=5)

    # Rebound peak (post-washout maximum).
    post_mask = t >= contract.washout_onset_min
    if post_mask.any():
        pk_idx = np.argmax(r[post_mask])
        pk_t = float(t[post_mask][pk_idx])
        pk_r = float(r[post_mask][pk_idx])
        ax.scatter([pk_t], [pk_r], s=60, marker="*", color="#D32F2F",
                   edgecolor="white", linewidth=0.8, zorder=6)
        ax.text(pk_t + 1, pk_r,
                f"rebound peak: {smart_fmt(pk_r)} at t={smart_fmt(pk_t)} min",
                ha="left", va="center", fontsize=6.4, color="#D32F2F")

    ax.set_xlabel("time (min)")
    ax.set_ylabel(r"$\Delta$ response")
    ax.set_xlim(t.min(), t.max())
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.6, frameon=False, loc="lower right",
              handlelength=1.6)
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    if contract.recovery_tau_min is not None:
        ax.text(
            0.02, 0.04,
            rf"recovery $\tau$ = {smart_fmt(float(contract.recovery_tau_min))} min",
            transform=ax.transAxes, ha="left", va="bottom",
            fontsize=6.4, color="#333333",
            bbox=dict(boxstyle="round,pad=0.18", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=7,
        )
    return ax
