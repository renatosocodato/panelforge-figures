"""Photobleaching-corrected intensity traces — raw vs corrected
per-cell intensity over time, with bi-exponential bleach fit
overlay and per-cell residual histogram inset.

Diagnostic-curve family: >=2 curves + >=1 legend.
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


class PhotobleachCellTrace(RecipeContract):
    cell_id: str
    t_s: list[float]
    raw_intensity: list[float]


class PhotobleachInput(RecipeContract):
    cells: list[PhotobleachCellTrace] = Field(..., min_length=3)
    title: str = "Photobleaching-corrected intensity traces"


def _demo() -> PhotobleachInput:
    rng = np.random.default_rng(3221)
    cells: list[PhotobleachCellTrace] = []
    n_t = 200
    t = np.arange(n_t).astype(float)
    for k in range(8):
        # Bi-exponential bleach.
        a1, a2 = 0.6, 0.4
        tau1, tau2 = 30.0, 200.0
        bleach = a1 * np.exp(-t / tau1) + a2 * np.exp(-t / tau2)
        true_signal = 1.0 + 0.05 * np.sin(2 * np.pi * t / 60.0)
        raw = (true_signal * bleach + rng.normal(0, 0.02, n_t)) * 100.0
        cells.append(PhotobleachCellTrace(
            cell_id=f"C{k:02d}",
            t_s=t.tolist(),
            raw_intensity=raw.tolist(),
        ))
    return PhotobleachInput(cells=cells)


_META = RecipeMetadata(
    name="photobleaching_corrected_intensity_traces",
    modality="intravital_imaging",
    family=RecipeFamily.diagnostic_curve,
    answers_question=(
        "After bi-exponential photobleach correction, are the "
        "biosensor traces flat over the recording duration?"
    ),
    required_fields=("cells",),
    optional_fields=("title",),
    file_format_hints=("yaml", "csv"),
    alternatives_in_modality=("biosensor_dose_response_curve",),
)


def _bi_exp(t, a1, tau1, a2, tau2, baseline):
    return baseline + a1 * np.exp(-t / np.maximum(tau1, 1e-3)) \
        + a2 * np.exp(-t / np.maximum(tau2, 1e-3))


@register_recipe(
    metadata=_META,
    contract=PhotobleachInput,
    demo_contract=_demo,
)
def render(contract: PhotobleachInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.0, 3.8))
    AESTHETIC.apply_to_ax(ax)

    raw_color = "#90A4AE"      # slate-grey for raw
    corr_color = "#26A69A"     # teal for corrected
    fit_color = "#EF5350"      # coral for bi-exp fit

    # Pool all cells, fit a single global bi-exponential bleach
    # curve to the population mean (the demo / typical protocol uses
    # a shared bleach correction).
    all_raw = []
    all_t = None
    for cell in contract.cells:
        if all_t is None:
            all_t = np.asarray(cell.t_s, float)
        all_raw.append(np.asarray(cell.raw_intensity, float))
    arr = np.asarray(all_raw)
    mean_raw = arr.mean(axis=0)
    if mean_raw.size > 0:
        mean_raw_init = float(mean_raw[0])
    else:
        mean_raw_init = 1.0

    fit_ok = False
    bleach_norm = np.ones_like(all_t)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            popt, _ = curve_fit(
                _bi_exp, all_t, mean_raw,
                p0=[0.6 * mean_raw_init, 30.0, 0.4 * mean_raw_init,
                    200.0, 0.0],
                maxfev=4000,
            )
        bleach_curve = _bi_exp(all_t, *popt)
        bleach_norm = bleach_curve / max(bleach_curve[0], 1e-9)
        fit_ok = True
    except Exception:
        popt = None

    # Plot raw + corrected per cell (alpha-thinned).
    for i, cell in enumerate(contract.cells):
        t = np.asarray(cell.t_s, float)
        raw = np.asarray(cell.raw_intensity, float)
        corrected = raw / np.maximum(bleach_norm[: raw.size], 1e-9)
        label_raw = "raw" if i == 0 else None
        label_corr = "corrected" if i == 0 else None
        ax.plot(t, raw, color=raw_color, lw=0.6, alpha=0.45,
                zorder=3, label=label_raw)
        ax.plot(t, corrected, color=corr_color, lw=0.7, alpha=0.55,
                zorder=4, label=label_corr)

    # Bi-exp fit dashed reference (the ≥1 fit-line component).
    if fit_ok and popt is not None:
        ax.plot(all_t, _bi_exp(all_t, *popt), color=fit_color,
                lw=1.4, ls="--", zorder=6, label="bi-exp fit")

    ax.set_xlabel("time (s)")
    ax.set_ylabel("intensity (a.u.)")
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(fontsize=6.8, frameon=False, loc="upper right",
              handlelength=1.6)

    # Residual histogram inset (corrected − mean over all cells).
    if fit_ok and arr.size > 0:
        corrected_pop = arr / np.maximum(bleach_norm, 1e-9)
        residuals = corrected_pop - corrected_pop.mean()
        sub = ax.inset_axes([0.66, 0.18, 0.30, 0.26])
        AESTHETIC.apply_to_ax(sub)
        sub.hist(residuals.ravel(), bins=30, color=corr_color,
                 alpha=0.75, edgecolor="white", linewidth=0.4,
                 zorder=3)
        sub.axvline(0, color="#888888", lw=0.7, ls="--", zorder=4)
        sub.set_title("corrected residuals", fontsize=6.4, pad=2)
        sub.tick_params(labelsize=6.0)

    if popt is not None:
        tau1, tau2 = popt[1], popt[3]
        title_bits = (f"tau_fast = {smart_fmt(min(tau1, tau2))} s, "
                      f"tau_slow = {smart_fmt(max(tau1, tau2))} s")
    else:
        title_bits = "fit failed"
    ax.set_title(
        f"{contract.title}  ·  n = {len(contract.cells)} cells  ·  "
        f"{title_bits}",
        fontsize=8.2, pad=4,
    )
    return ax
