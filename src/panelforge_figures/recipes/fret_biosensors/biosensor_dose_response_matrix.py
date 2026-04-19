"""Dose × time FRET-ratio response matrix — heatmap integrating both axes."""

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


class DoseTimeMatrixInput(RecipeContract):
    doses: list[float] = Field(..., description="compound concentrations (M, log-scale friendly)")
    times_s: list[float] = Field(..., description="time points in seconds")
    delta_ratio: list[list[float]] = Field(
        ..., description="2-D array [n_dose × n_time] of Δ(F_A / F_D)"
    )
    contour_levels: list[float] = Field(
        default_factory=lambda: [0.1, 0.2, 0.3],
        description="isocontour levels to overlay",
    )
    title: str = "Dose × time response"


def _demo() -> DoseTimeMatrixInput:
    rng = np.random.default_rng(607)
    doses = np.logspace(-9, -5, 24)        # 1 nM … 10 µM
    times = np.linspace(0, 300, 60)        # 0-300 s
    # Hill-in-dose × sigmoidal-in-time response surface.
    log_dose = np.log10(doses)
    ec50 = np.log10(1e-7)
    dose_axis = 0.42 / (1 + 10 ** (-(log_dose - ec50) * 1.2))
    time_axis = 1.0 / (1 + np.exp(-(times - 60.0) / 18.0))
    matrix = np.outer(dose_axis, time_axis)
    matrix = matrix + rng.normal(0, 0.012, matrix.shape)
    return DoseTimeMatrixInput(
        doses=doses.tolist(),
        times_s=times.tolist(),
        delta_ratio=matrix.tolist(),
    )


_META = RecipeMetadata(
    name="biosensor_dose_response_matrix",
    modality="fret_biosensors",
    family=RecipeFamily.heatmap,
    answers_question=(
        "How does the FRET ratio change jointly as a function of dose and "
        "time, and where in (dose, time) space is the response maximal?"
    ),
    required_fields=("doses", "times_s", "delta_ratio"),
    optional_fields=("contour_levels", "title"),
    file_format_hints=("csv", "parquet", "npz"),
    alternatives_in_modality=(
        "dose_response_hill_fret",
        "ratio_timecourse_hierarchical_ci",
    ),
)


@register_recipe(
    metadata=_META,
    contract=DoseTimeMatrixInput,
    demo_contract=_demo,
)
def render(contract: DoseTimeMatrixInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.4))
    AESTHETIC.apply_to_ax(ax)

    doses = np.asarray(contract.doses, dtype=float)
    times = np.asarray(contract.times_s, dtype=float)
    M = np.asarray(contract.delta_ratio, dtype=float)

    # Symmetric RdBu_r around 0 so "up" and "down" responses are legible.
    vmax = float(np.nanmax(np.abs(M)))
    vmax = max(vmax, 0.01)
    extent = (float(times.min()), float(times.max()),
              float(np.log10(doses.min())), float(np.log10(doses.max())))
    im = ax.imshow(
        M, origin="lower", extent=extent, aspect="auto",
        cmap=AESTHETIC.ratio_cmap or "RdBu_r",
        vmin=-vmax, vmax=vmax,
        interpolation="bilinear",
    )

    # Iso-contour lines at requested Δ levels.
    TT, DD = np.meshgrid(times, np.log10(doses))
    try:
        cs = ax.contour(
            TT, DD, M,
            levels=sorted(float(lv) for lv in contract.contour_levels),
            colors="#111111", linewidths=0.7, alpha=0.8, zorder=3,
        )
        ax.clabel(cs, fontsize=5.8, fmt="%.2f", inline=True,
                  inline_spacing=2)
    except Exception:
        pass

    # Peak-response marker.
    iy, ix = np.unravel_index(int(np.argmax(M)), M.shape)
    peak_t = float(times[ix])
    peak_log_dose = float(np.log10(doses[iy]))
    ax.scatter([peak_t], [peak_log_dose], s=54, facecolor="none",
               edgecolor="black", linewidth=1.3, zorder=5, marker="o")
    # Axes-fraction anchoring keeps the callout inside the figure regardless
    # of where the peak lands (offset-points anchoring clipped on the right
    # when the peak sits at max time).
    ax.annotate(
        f"peak $\\Delta$ = {smart_fmt(float(M.max()))}\n"
        f"t = {int(peak_t)} s,  dose = {smart_fmt(float(doses[iy]) * 1e9)} nM",
        xy=(peak_t, peak_log_dose),
        xytext=(0.03, 0.96), textcoords="axes fraction",
        ha="left", va="top",
        fontsize=6.2, color="#111111",
        bbox=dict(boxstyle="round,pad=0.18", fc="white",
                  ec="#BBBBBB", lw=0.5, alpha=0.92),
        arrowprops=dict(arrowstyle="-", color="#666666", lw=0.6),
        zorder=7,
    )

    ax.set_xlabel("time post-stimulus (s)")
    ax.set_ylabel(r"$\log_{10}$ dose (M)")
    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(r"$\Delta$ F$_A$/F$_D$", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.2)
    ax.set_title(
        f"{contract.title}  ·  {doses.size} doses × {times.size} time points",
        fontsize=8.6, pad=4,
    )
    return ax
