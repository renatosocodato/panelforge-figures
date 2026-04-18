"""Sensor calibration curve — ratio vs analyte concentration with sigmoidal fit."""

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


def _hill(x, bot, top, kd, n):
    return bot + (top - bot) / (1 + (kd / np.maximum(x, 1e-12)) ** n)


class CalibrationInput(RecipeContract):
    concentrations: list[float] = Field(...)
    ratios: list[float] = Field(...)
    replicate_id: list[str] | None = None
    sensor_name: str = "ExRai-AKAR"
    analyte: str = "cAMP"
    title: str = "Sensor calibration"


def _demo() -> CalibrationInput:
    rng = np.random.default_rng(181)
    c = np.logspace(-9, -5, 10)
    true = _hill(c, bot=1.0, top=2.2, kd=1e-7, n=1.3)
    reps = 3
    conc = []
    ratio = []
    ids = []
    for ci, m in zip(c, true):
        conc.extend([ci] * reps)
        ratio.extend((m + rng.normal(0, 0.06, reps)).tolist())
        ids.extend([f"rep{k}" for k in range(reps)])
    return CalibrationInput(
        concentrations=conc,
        ratios=ratio,
        replicate_id=ids,
    )


_META = RecipeMetadata(
    name="sensor_calibration_curve",
    modality="fret_biosensors",
    family=RecipeFamily.diagnostic_curve,
    answers_question="What is the FRET sensor's dynamic range and Kd for its target analyte?",
    required_fields=("concentrations", "ratios"),
    optional_fields=("replicate_id", "sensor_name", "analyte", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("dose_response_hill_fret",),
)


@register_recipe(metadata=_META, contract=CalibrationInput, demo_contract=_demo)
def render(contract: CalibrationInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)
    accent = palette.pick("donor")

    c = np.array(contract.concentrations, dtype=float)
    r = np.array(contract.ratios, dtype=float)

    try:
        popt, _ = curve_fit(
            _hill, c, r,
            p0=[r.min(), r.max(), float(np.median(c)), 1.0],
            maxfev=2000,
        )
    except Exception:
        popt = np.array([r.min(), r.max(), float(np.median(c)), 1.0])
    bot, top, kd, n_hill = popt
    dyn_range = top - bot

    ax.scatter(c, r, s=22, color=accent, alpha=0.7,
               edgecolor="white", linewidth=0.5, zorder=3)

    xg = np.logspace(np.log10(c.min()), np.log10(c.max()), 120)
    ax.plot(xg, _hill(xg, *popt), color="#111111", lw=1.2, zorder=4,
            label="Hill fit")

    ax.axvline(kd, color="#D32F2F", lw=0.7, ls="--", zorder=2,
               label=f"Kd = {smart_fmt(kd * 1e9)} nM")

    ax.set_xscale("log")
    ax.set_xlabel(f"[{contract.analyte}] (M)")
    ax.set_ylabel(r"F$_\mathrm{A}$/F$_\mathrm{D}$")
    ax.set_title(f"{contract.sensor_name} calibration",
                 fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="upper left",
              handlelength=1.8)

    ax.text(0.99, 0.02,
            rf"$\Delta$R = {smart_fmt(dyn_range)}"
            "\n"
            f"Hill n = {smart_fmt(float(n_hill))}",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=6.6, color="#333333",
            bbox=dict(boxstyle="round,pad=0.20", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=5)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
