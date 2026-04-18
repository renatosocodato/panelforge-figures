"""Hill-equation dose-response fit with bootstrap CI band."""

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


def _hill(x, bot, top, ec50, n):
    return bot + (top - bot) / (1 + (ec50 / np.maximum(x, 1e-12)) ** n)


class HillFitInput(RecipeContract):
    doses: list[float] = Field(..., description="concentrations (log-scale friendly)")
    responses: list[float] = Field(...)
    compound: str = "compound"
    ic50_guess: float | None = None
    y_label: str = "response (%)"
    title: str = "Dose-response · Hill fit"


def _demo() -> HillFitInput:
    rng = np.random.default_rng(71)
    doses_set = np.logspace(-9, -4, 10)
    # True EC50 ~ 1e-7, hill ~ 1.2, bot 5, top 95.
    true_mean = _hill(doses_set, 5, 95, 1e-7, 1.2)
    reps_per_dose = 3
    doses = []
    responses = []
    for d, m in zip(doses_set, true_mean):
        doses.extend([d] * reps_per_dose)
        responses.extend((m + rng.normal(0, 5, reps_per_dose)).tolist())
    return HillFitInput(
        doses=doses,
        responses=responses,
        compound="CompoundA",
        ic50_guess=1e-7,
        title="CompoundA · Hill fit",
    )


_META = RecipeMetadata(
    name="hill_fit_with_ci",
    modality="dose_response_pharmacology",
    family=RecipeFamily.diagnostic_curve,
    answers_question="What is the compound's EC50 (or IC50) and Hill slope, and with what uncertainty?",
    required_fields=("doses", "responses"),
    optional_fields=("compound", "ic50_guess", "y_label", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("ic50_forest_across_compounds",),
    n_points_typical="6-12 doses × 3 replicates",
)


@register_recipe(metadata=_META, contract=HillFitInput, demo_contract=_demo)
def render(contract: HillFitInput, ax=None, **_):
    from scipy.optimize import curve_fit

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)
    accent = palette.pick("signaling") if "signaling" in palette.semantic else palette[0]

    doses = np.array(contract.doses, dtype=float)
    resp = np.array(contract.responses, dtype=float)

    # Main fit.
    ec50_init = contract.ic50_guess or float(np.median(doses))
    try:
        popt, _ = curve_fit(
            _hill, doses, resp,
            p0=[resp.min(), resp.max(), ec50_init, 1.0],
            maxfev=2000,
        )
    except Exception:
        popt = np.array([resp.min(), resp.max(), ec50_init, 1.0])

    bot, top, ec50, n_hill = popt

    # Bootstrap CI band.
    rng = np.random.default_rng(0)
    x_grid = np.logspace(np.log10(max(doses.min(), 1e-12)),
                         np.log10(doses.max()), 120)
    draws = []
    for _b in range(200):
        idx = rng.integers(0, len(doses), len(doses))
        try:
            popt_b, _ = curve_fit(
                _hill, doses[idx], resp[idx],
                p0=popt, maxfev=1000,
            )
            draws.append(_hill(x_grid, *popt_b))
        except Exception:
            continue
    if draws:
        D = np.array(draws)
        lo = np.quantile(D, 0.025, axis=0)
        hi = np.quantile(D, 0.975, axis=0)
        ax.fill_between(x_grid, lo, hi, color=accent, alpha=0.18,
                        linewidth=0, zorder=2)

    # Fit line.
    ax.plot(x_grid, _hill(x_grid, *popt), color=accent, lw=1.2, zorder=3,
            label=contract.compound)

    # Data points.
    ax.scatter(doses, resp, s=18, color=accent, alpha=0.8,
               edgecolor="white", linewidth=0.5, zorder=4)

    # EC50 vertical marker.
    ax.axvline(ec50, color="#555555", lw=0.7, ls="--", zorder=1)

    ax.set_xscale("log")
    ax.set_xlabel("dose (M)")
    ax.set_ylabel(contract.y_label)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="lower right",
              handlelength=1.6)

    # Fit-parameter callout.
    txt = (
        r"$\mathrm{EC}_{50}$ = "
        f"{smart_fmt(ec50 * 1e9)} nM\n"
        f"Hill n = {smart_fmt(float(n_hill))}\n"
        f"bottom = {smart_fmt(float(bot))}   top = {smart_fmt(float(top))}"
    )
    ax.text(0.02, 0.97, txt,
            transform=ax.transAxes, ha="left", va="top",
            fontsize=6.6, color="#333333",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=5)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
