"""Dose-response Hill fit for a FRET readout — per-cell points + mean fit."""

from __future__ import annotations

import numpy as np
from pydantic import Field
from scipy.optimize import curve_fit

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


class HillFRETInput(RecipeContract):
    doses: list[float] = Field(...)
    ratios: list[float] = Field(..., description="per-cell FRET ratio")
    cell_ids: list[str] | None = None
    compound: str = "forskolin"
    title: str = "FRET dose response"


def _demo() -> HillFRETInput:
    rng = np.random.default_rng(191)
    doses_grid = np.logspace(-9, -4, 10)
    cells_per_dose = 12
    true = _hill(doses_grid, 1.0, 2.0, 1e-7, 1.1)
    doses: list[float] = []
    ratios: list[float] = []
    ids: list[str] = []
    for i, (d, m) in enumerate(zip(doses_grid, true)):
        for k in range(cells_per_dose):
            doses.append(float(d))
            ratios.append(float(m + rng.normal(0, 0.09)))
            ids.append(f"c{i}_{k}")
    return HillFRETInput(doses=doses, ratios=ratios, cell_ids=ids)


_META = RecipeMetadata(
    name="dose_response_hill_fret",
    modality="fret_biosensors",
    family=RecipeFamily.diagnostic_curve,
    answers_question="What is the compound's EC50 on the FRET readout, accounting for per-cell variability?",
    required_fields=("doses", "ratios"),
    optional_fields=("cell_ids", "compound", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("sensor_calibration_curve",),
)


@register_recipe(metadata=_META, contract=HillFRETInput, demo_contract=_demo)
def render(contract: HillFRETInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)
    accent = palette.pick("donor")
    peak = palette.pick("ratio_up")

    doses = np.array(contract.doses, dtype=float)
    ratios = np.array(contract.ratios, dtype=float)

    # Mean per dose.
    unique_d = np.unique(doses)
    mean_per = np.array([ratios[doses == d].mean() for d in unique_d])

    try:
        popt, _ = curve_fit(
            _hill, unique_d, mean_per,
            p0=[mean_per.min(), mean_per.max(), float(np.median(unique_d)), 1.0],
            maxfev=2000,
        )
    except Exception:
        popt = np.array([mean_per.min(), mean_per.max(), float(np.median(unique_d)), 1.0])
    bot, top, ec50, n_hill = popt

    # Per-cell scatter with jitter on log x.
    jitter = (np.random.default_rng(2).uniform(-0.05, 0.05, doses.size)
              * np.log10(np.maximum(doses, 1e-12)))
    doses_j = doses * 10 ** (jitter / 50)
    ax.scatter(doses_j, ratios, s=10, color=accent, alpha=0.35,
               edgecolor="none", zorder=3, label="per-cell")

    # Mean overlay.
    ax.scatter(unique_d, mean_per, s=38, color=peak,
               edgecolor="white", linewidth=0.8, zorder=5,
               label="mean per dose")

    xg = np.logspace(np.log10(unique_d.min()), np.log10(unique_d.max()), 120)
    ax.plot(xg, _hill(xg, *popt), color="#111111", lw=1.2, zorder=4,
            label="Hill fit")

    ax.axvline(ec50, color="#D32F2F", lw=0.7, ls="--", zorder=2)

    ax.set_xscale("log")
    ax.set_xlabel("dose (M)")
    ax.set_ylabel(r"F$_\mathrm{A}$/F$_\mathrm{D}$")
    ax.set_title(f"{contract.title} · {contract.compound}",
                 fontsize=9.0, pad=4)
    ax.legend(fontsize=6.6, frameon=False, loc="upper left",
              handlelength=1.6)

    ax.text(0.99, 0.02,
            r"$\mathrm{EC}_{50}$ = "
            f"{smart_fmt(ec50 * 1e9)} nM\n"
            f"Hill n = {smart_fmt(float(n_hill))}",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=6.6, color="#333333",
            bbox=dict(boxstyle="round,pad=0.20", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=6)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
