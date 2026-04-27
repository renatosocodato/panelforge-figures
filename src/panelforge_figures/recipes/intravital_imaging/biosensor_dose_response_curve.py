"""Biosensor dose-response curve — per-dose mean trace + bootstrap CI
ribbon, with EC50 callout from a Hill fit.

Timecourse-hierarchical-CI family: >=1 CI band + >=1 mean line.
"""

from __future__ import annotations

import warnings

import numpy as np
from pydantic import Field
from scipy.optimize import curve_fit

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC
from ._shared import BiosensorTimeTrace

_CONDITION_PALETTE = {
    "control": "#37474F", "DISC1": "#EF5350",
    "WT": "#37474F", "LI": "#EF5350",
}


class BiosensorDoseResponseInput(RecipeContract):
    traces: list[BiosensorTimeTrace] = Field(..., min_length=4)
    condition_by_cell: dict[str, str] = Field(...)
    plateau_window_s: tuple[float, float] = (60.0, 90.0)
    title: str = "Biosensor dose-response curve"


def _demo() -> BiosensorDoseResponseInput:
    rng = np.random.default_rng(3211)
    traces: list[BiosensorTimeTrace] = []
    cond_by: dict[str, str] = {}
    doses = [0.1, 0.3, 1.0, 3.0, 10.0]
    n_t = 90
    t = np.arange(n_t).astype(float)
    # Sigmoid: control EC50 = 1.5, DISC1 EC50 = 4.0.
    for cond, ec50 in (("control", 1.5), ("DISC1", 4.0)):
        for dose in doses:
            for k in range(6):
                cell_id = f"{cond}_d{dose}_C{k}"
                plateau = 1.0 + 0.6 * dose / (dose + ec50)
                ramp = plateau - (plateau - 1.0) * np.exp(-t / 20.0)
                noise = rng.normal(0, 0.04, n_t)
                traces.append(BiosensorTimeTrace(
                    cell_id=cell_id,
                    sensor_label="ROCK biosensor",
                    dose=dose,
                    t_s=t.tolist(),
                    intensity=(ramp + noise).tolist(),
                ))
                cond_by[cell_id] = cond
    return BiosensorDoseResponseInput(
        traces=traces, condition_by_cell=cond_by,
    )


_META = RecipeMetadata(
    name="biosensor_dose_response_curve",
    modality="intravital_imaging",
    family=RecipeFamily.timecourse_hierarchical_ci,
    answers_question=(
        "How does the biosensor plateau response scale with cue "
        "dose, and what is the EC50 per condition?"
    ),
    required_fields=("traces", "condition_by_cell"),
    optional_fields=("plateau_window_s", "title"),
    file_format_hints=("yaml",),
    alternatives_in_modality=("biosensor_activation_field_per_cell",),
)


def _hill(x, top, bottom, ec50, n):
    return bottom + (top - bottom) / (1.0 + (ec50 / np.maximum(x, 1e-9)) ** n)


@register_recipe(
    metadata=_META,
    contract=BiosensorDoseResponseInput,
    demo_contract=_demo,
)
def render(contract: BiosensorDoseResponseInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.8, 3.8))
    AESTHETIC.apply_to_ax(ax)

    # Aggregate per-cell plateau values from time traces.
    t_lo, t_hi = contract.plateau_window_s
    by_cond: dict[str, dict[float, list[float]]] = {}
    for tr in contract.traces:
        cond = contract.condition_by_cell.get(tr.cell_id, "?")
        ts = np.asarray(tr.t_s, float)
        ints = np.asarray(tr.intensity, float)
        mask = (ts >= t_lo) & (ts <= t_hi)
        if mask.any():
            plateau = float(np.mean(ints[mask]))
            by_cond.setdefault(cond, {}).setdefault(tr.dose, []).append(plateau)

    bits = []
    for cond, dose_dict in by_cond.items():
        doses_sorted = sorted(dose_dict)
        means = []
        ci_lo = []
        ci_hi = []
        rng = np.random.default_rng(17)
        for d in doses_sorted:
            vals = np.asarray(dose_dict[d], float)
            means.append(float(vals.mean()))
            boot = [vals[rng.integers(0, vals.size, vals.size)].mean()
                    for _ in range(200)]
            ci_lo.append(float(np.quantile(boot, 0.025)))
            ci_hi.append(float(np.quantile(boot, 0.975)))
        colour = _CONDITION_PALETTE.get(cond, "#37474F")
        ax.fill_between(doses_sorted, ci_lo, ci_hi,
                        color=colour, alpha=0.18, linewidth=0,
                        zorder=2)
        ax.plot(doses_sorted, means, color=colour, lw=1.4,
                zorder=4, label=cond, marker="o", ms=4,
                markeredgecolor="white", markeredgewidth=0.5)
        # Hill fit (top, bottom, EC50, n).
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                popt, _ = curve_fit(
                    _hill,
                    np.asarray(doses_sorted, float),
                    np.asarray(means, float),
                    p0=[max(means), min(means), 1.0, 1.0],
                    maxfev=2000,
                )
            ec50 = float(popt[2])
            xs = np.geomspace(min(doses_sorted), max(doses_sorted), 80)
            ax.plot(xs, _hill(xs, *popt), color=colour, lw=0.9,
                    ls="--", alpha=0.7, zorder=5)
            bits.append(f"{cond}: EC50 = {smart_fmt(ec50)}")
        except Exception:
            bits.append(f"{cond}: EC50 not fit")

    ax.set_xscale("log")
    sensor_label = (contract.traces[0].sensor_label
                    if contract.traces else "")
    dose_unit = (contract.traces[0].dose_unit
                 if contract.traces else "uM")
    ax.set_xlabel(f"dose ({dose_unit})")
    ax.set_ylabel(f"{sensor_label} plateau (a.u.)")
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(fontsize=6.8, frameon=False, loc="lower right",
              handlelength=1.4)
    ax.set_title(
        f"{contract.title}  ·  " + "   ".join(bits),
        fontsize=8.2, pad=4,
    )
    return ax
