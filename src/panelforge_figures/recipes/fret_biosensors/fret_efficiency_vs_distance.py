"""FRET efficiency vs donor-acceptor distance — Förster-radius calibration."""

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


class FRETDistanceInput(RecipeContract):
    distances_nm: list[float] = Field(...)
    efficiency: list[float] = Field(..., description="measured E in [0, 1]")
    efficiency_sem: list[float] | None = None
    fitted_R0_nm: float | None = None
    title: str = "FRET efficiency vs distance"


def _demo() -> FRETDistanceInput:
    rng = np.random.default_rng(603)
    # Theoretical Förster curve with R0 = 5.4 nm; jitter the measurements.
    R0_true = 5.4
    distances = np.linspace(1.5, 14.0, 18)
    E_true = 1.0 / (1.0 + (distances / R0_true) ** 6)
    E_meas = np.clip(E_true + rng.normal(0, 0.035, distances.size), 0.0, 1.0)
    sem = np.clip(0.025 + 0.02 * (1 - E_meas), 0.01, 0.06)

    # Fit R0 via least squares on log-transformed residuals.
    def ssq(r0: float) -> float:
        pred = 1.0 / (1.0 + (distances / r0) ** 6)
        return float(np.sum((pred - E_meas) ** 2))

    r0_grid = np.linspace(3.5, 7.5, 800)
    r0_fit = float(r0_grid[int(np.argmin([ssq(r) for r in r0_grid]))])

    return FRETDistanceInput(
        distances_nm=distances.tolist(),
        efficiency=E_meas.tolist(),
        efficiency_sem=sem.tolist(),
        fitted_R0_nm=r0_fit,
    )


_META = RecipeMetadata(
    name="fret_efficiency_vs_distance",
    modality="fret_biosensors",
    family=RecipeFamily.diagnostic_curve,
    answers_question=(
        "What is the fitted Förster radius R_0, and how closely do measured "
        "FRET efficiencies track the theoretical 1/(1 + (r/R_0)^6) curve?"
    ),
    required_fields=("distances_nm", "efficiency"),
    optional_fields=("efficiency_sem", "fitted_R0_nm", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("sensor_calibration_curve",),
)


@register_recipe(
    metadata=_META,
    contract=FRETDistanceInput,
    demo_contract=_demo,
)
def render(contract: FRETDistanceInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)
    accent = (palette.pick("acceptor") if "acceptor" in palette.semantic
              else palette[1])

    r = np.asarray(contract.distances_nm, dtype=float)
    E = np.asarray(contract.efficiency, dtype=float)

    # Measured points with optional SEM bars.
    if contract.efficiency_sem is not None:
        sem = np.asarray(contract.efficiency_sem, dtype=float)
        ax.errorbar(r, E, yerr=sem, fmt="none", ecolor="#666666",
                    capsize=2.2, elinewidth=0.7, zorder=3)
    ax.scatter(r, E, s=34, color=accent,
               edgecolor="white", linewidth=0.8, zorder=4,
               label="measured")

    # Theoretical curve from the fitted R_0 (or the measured-median R0 otherwise).
    R0 = (contract.fitted_R0_nm
          if contract.fitted_R0_nm is not None
          else float(r[int(np.argmin(np.abs(E - 0.5)))]))
    r_fine = np.linspace(max(float(r.min()) * 0.6, 0.5),
                         float(r.max()) * 1.08, 400)
    E_theory = 1.0 / (1.0 + (r_fine / R0) ** 6)
    ax.plot(r_fine, E_theory, color="#111111", lw=1.3, zorder=5,
            label=r"theory: $E = 1/(1+(r/R_0)^6)$")

    # Vertical dashed line at R_0 with a halo'd label placed below the
    # E = 0.5 crossing so it doesn't sit on top of the theoretical curve.
    ax.axvline(R0, color="#D32F2F", lw=0.7, ls="--", zorder=2)
    ax.axhline(0.5, color="#BBBBBB", lw=0.5, ls=":", zorder=1)
    ax.annotate(
        rf"$R_0$ = {smart_fmt(float(R0))} nm",
        xy=(R0, 0.5),
        xytext=(8, -18), textcoords="offset points",
        fontsize=6.8, color="#D32F2F",
        bbox=dict(boxstyle="round,pad=0.18", fc="white",
                  ec="#D32F2F", lw=0.6, alpha=0.92),
        zorder=7,
    )

    ax.set_xlabel("donor-acceptor distance $r$ (nm)")
    ax.set_ylabel(r"FRET efficiency $E$")
    ax.set_xlim(float(r_fine.min()), float(r_fine.max()))
    ax.set_ylim(-0.03, 1.05)
    ax.set_title(
        f"{contract.title}  ·  n = {r.size} standards",
        fontsize=9.0, pad=4,
    )
    ax.legend(fontsize=6.6, frameon=False, loc="upper right",
              handlelength=1.8)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
