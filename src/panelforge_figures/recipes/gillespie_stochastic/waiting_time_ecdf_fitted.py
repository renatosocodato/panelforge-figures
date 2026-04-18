"""Waiting-time ECDF — empirical CDF + fitted exponential / gamma overlay."""

from __future__ import annotations

import numpy as np
from pydantic import Field
from scipy import stats

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class WaitingTimeECDFInput(RecipeContract):
    waiting_times: list[float] = Field(..., description="positive waiting times (s)")
    title: str = "Waiting-time ECDF"


def _demo() -> WaitingTimeECDFInput:
    rng = np.random.default_rng(113)
    # Hypoexponential (gamma-ish) with shape=2.
    x = rng.gamma(shape=2.0, scale=3.0, size=400)
    return WaitingTimeECDFInput(waiting_times=x.tolist())


_META = RecipeMetadata(
    name="waiting_time_ecdf_fitted",
    modality="gillespie_stochastic",
    family=RecipeFamily.diagnostic_curve,
    answers_question="Does the observed waiting-time distribution match an exponential, or does a gamma (multi-step) model fit better?",
    required_fields=("waiting_times",),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("dwell_time_log_violin",),
)


@register_recipe(metadata=_META, contract=WaitingTimeECDFInput, demo_contract=_demo)
def render(contract: WaitingTimeECDFInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    x = np.array(contract.waiting_times, dtype=float)
    x = x[x > 0]
    x_sorted = np.sort(x)
    ecdf = np.arange(1, x.size + 1) / x.size

    # Step-CDF for data.
    ax.step(x_sorted, ecdf, where="post",
            color=palette.pick("HOME"), lw=1.2, zorder=3,
            label="empirical ECDF")

    # Fit exponential (MLE = 1/mean).
    lam = 1.0 / np.mean(x)
    xg = np.linspace(x_sorted.min(), x_sorted.max(), 200)
    ax.plot(xg, stats.expon.cdf(xg, scale=1 / lam),
            color="#D32F2F", lw=1.0, ls="--", zorder=4,
            label=f"expon (λ={smart_fmt(lam)})")

    # Fit gamma (MLE).
    shape, loc, scale = stats.gamma.fit(x, floc=0)
    ax.plot(xg, stats.gamma.cdf(xg, shape, loc=loc, scale=scale),
            color="#6A1B9A", lw=1.0, zorder=5,
            label=f"gamma (k={smart_fmt(shape)})")

    # KS statistics vs both fits.
    ks_exp = stats.kstest(x, "expon", args=(0, 1 / lam)).statistic
    ks_gam = stats.kstest(x, "gamma", args=(shape, 0, scale)).statistic
    better = "gamma" if ks_gam < ks_exp else "exponential"
    ax.text(0.99, 0.04,
            f"KS expon = {smart_fmt(ks_exp)}\n"
            f"KS gamma = {smart_fmt(ks_gam)}\n"
            f"better fit: {better}",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=6.6, color="#333333",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=6)

    ax.set_xlabel("waiting time (s)")
    ax.set_ylabel("cumulative probability")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="upper left",
              handlelength=2.0)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
