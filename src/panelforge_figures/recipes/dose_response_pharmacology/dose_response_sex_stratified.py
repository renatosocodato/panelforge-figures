"""Sex-stratified Hill fits with interaction p-value callout."""

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


def _hill(x, bot, top, ec50, n):
    return bot + (top - bot) / (1 + (ec50 / np.maximum(x, 1e-12)) ** n)


class DoseResponseSexInput(RecipeContract):
    doses_female: list[float] = Field(..., min_length=3)
    responses_female: list[float] = Field(...)
    doses_male: list[float] = Field(..., min_length=3)
    responses_male: list[float] = Field(...)
    interaction_p: float | None = None
    compound: str = "compound"
    y_label: str = "response (%)"
    title: str = "Sex-stratified dose response"


def _demo() -> DoseResponseSexInput:
    rng = np.random.default_rng(97)
    doses = np.logspace(-9, -4, 10)
    # Female: EC50 ~ 0.8e-7; Male: 2.2e-7 (right-shifted by ~3x).
    f = _hill(doses, 5, 95, 0.8e-7, 1.1) + rng.normal(0, 4, doses.size)
    m = _hill(doses, 5, 90, 2.2e-7, 1.0) + rng.normal(0, 4, doses.size)
    return DoseResponseSexInput(
        doses_female=doses.tolist(),
        responses_female=f.tolist(),
        doses_male=doses.tolist(),
        responses_male=m.tolist(),
        interaction_p=0.003,
        compound="CompoundX",
    )


_META = RecipeMetadata(
    name="dose_response_sex_stratified",
    modality="dose_response_pharmacology",
    family=RecipeFamily.diagnostic_curve,
    answers_question=(
        "For a sex-stratified dataset, do male and female Hill curves "
        "differ, and is the interaction significant?"
    ),
    required_fields=(
        "doses_female", "responses_female", "doses_male", "responses_male",
    ),
    optional_fields=("interaction_p", "compound", "y_label", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("hill_fit_with_ci",),
)


@register_recipe(
    metadata=_META,
    contract=DoseResponseSexInput,
    demo_contract=_demo,
)
def render(contract: DoseResponseSexInput, ax=None, **_):
    from scipy.optimize import curve_fit

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.4))
    AESTHETIC.apply_to_ax(ax)

    f_color = "#C73E7F"
    m_color = "#1F77B4"
    out_ec50 = {}

    for sex, d, r, color in [
        ("female", contract.doses_female, contract.responses_female, f_color),
        ("male", contract.doses_male, contract.responses_male, m_color),
    ]:
        d_arr = np.asarray(d, float)
        r_arr = np.asarray(r, float)
        try:
            popt, _ = curve_fit(
                _hill, d_arr, r_arr,
                p0=[r_arr.min(), r_arr.max(), float(np.median(d_arr)), 1.0],
                maxfev=2000,
            )
        except Exception:
            popt = np.array([r_arr.min(), r_arr.max(),
                             float(np.median(d_arr)), 1.0])
        xg = np.logspace(np.log10(max(d_arr.min(), 1e-12)),
                         np.log10(d_arr.max()), 120)
        ax.plot(xg, _hill(xg, *popt), color=color, lw=1.3, zorder=4,
                label=f"{sex} (EC50={smart_fmt(popt[2] * 1e9)} nM)")
        ax.scatter(d_arr, r_arr, s=16, color=color, alpha=0.75,
                   edgecolor="white", linewidth=0.4, zorder=3)
        ax.axvline(popt[2], color=color, lw=0.6, ls="--", alpha=0.75, zorder=1)
        out_ec50[sex] = float(popt[2])

    ax.set_xscale("log")
    ax.set_xlabel("dose (M)")
    ax.set_ylabel(contract.y_label)
    ax.set_title(
        f"{contract.title}  ·  {contract.compound}",
        fontsize=9.0, pad=4,
    )
    ax.legend(fontsize=6.8, frameon=False, loc="lower right",
              handlelength=1.6)
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    # Sex × dose interaction callout.
    if contract.interaction_p is not None:
        fold = (out_ec50.get("male", 1.0) / out_ec50.get("female", 1.0)
                if out_ec50.get("female", 0) > 0 else 1.0)
        ax.text(
            0.02, 0.97,
            f"sex × dose p = {smart_fmt(contract.interaction_p)}\n"
            f"EC50 fold (M/F) = {smart_fmt(fold)}",
            transform=ax.transAxes, ha="left", va="top",
            fontsize=6.6, color="#111111",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.95),
            zorder=6,
        )
    return ax
