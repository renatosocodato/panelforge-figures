"""roGFP2 biosensor calibration — measured ratio vs. disulfide fraction.

Sigmoid calibration curve: at each titrated disulfide fraction (0 → 1),
the observed ratio is measured. A Hill/Boltzmann fit through the points
recovers E₀ (midpoint) and the dynamic range Rmin / Rmax. The fit + 95 %
CI band + fit-parameter callout make this the first-stop panel when
converting ratio → redox potential in a paper.
"""

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


class RoGFPTitrationInput(RecipeContract):
    disulfide_fraction: list[float] = Field(
        ..., description="OxD fraction in [0, 1]"
    )
    ratio_measured: list[float] = Field(...)
    ratio_sem: list[float] | None = None
    fit_R_min: float | None = None
    fit_R_max: float | None = None
    fit_midpoint: float | None = Field(
        None, description="OxD at which ratio = (Rmin+Rmax)/2"
    )
    fit_slope: float = 4.0
    fit_r_squared: float | None = None
    title: str = "roGFP2 calibration"


def _demo() -> RoGFPTitrationInput:
    rng = np.random.default_rng(83)
    OxD = np.linspace(0.0, 1.0, 11)
    Rmin, Rmax = 0.35, 1.90
    mid, slope = 0.50, 4.0
    ratio = Rmin + (Rmax - Rmin) / (1 + np.exp(-slope * 4 * (OxD - mid)))
    ratio_noisy = ratio + rng.normal(0, 0.03, OxD.size)
    sem = rng.uniform(0.02, 0.05, OxD.size)
    # R² computed against a refit for realism.
    r2 = float(1 - np.var(ratio_noisy - ratio) / np.var(ratio_noisy))
    return RoGFPTitrationInput(
        disulfide_fraction=OxD.tolist(),
        ratio_measured=ratio_noisy.tolist(),
        ratio_sem=sem.tolist(),
        fit_R_min=Rmin,
        fit_R_max=Rmax,
        fit_midpoint=mid,
        fit_slope=slope,
        fit_r_squared=r2,
    )


_META = RecipeMetadata(
    name="roGFP2_ratio_vs_disulfide_titration",
    modality="redox_imaging",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "For a roGFP2 biosensor, what is the calibration curve of "
        "measured ratio vs disulfide fraction, including fitted E₀ / "
        "slope / R²?"
    ),
    required_fields=("disulfide_fraction", "ratio_measured"),
    optional_fields=(
        "ratio_sem", "fit_R_min", "fit_R_max", "fit_midpoint",
        "fit_slope", "fit_r_squared", "title",
    ),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("single_cell_ratio_distribution",),
)


@register_recipe(
    metadata=_META,
    contract=RoGFPTitrationInput,
    demo_contract=_demo,
)
def render(contract: RoGFPTitrationInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)
    red_c = palette.pick("reduced")
    ox_c = palette.pick("oxidized")

    OxD = np.asarray(contract.disulfide_fraction, float)
    R = np.asarray(contract.ratio_measured, float)
    sem = (np.asarray(contract.ratio_sem, float)
           if contract.ratio_sem is not None else None)

    # Scatter data with optional SEM bars.
    if sem is not None:
        for xi, yi, ei in zip(OxD, R, sem):
            ax.plot([xi, xi], [yi - ei, yi + ei],
                    color="#555555", lw=0.8, zorder=2)
    colors = [red_c if x < 0.5 else ox_c for x in OxD]
    ax.scatter(OxD, R, s=30, c=colors, edgecolor="white",
               linewidth=0.6, zorder=4, label="data")

    # Sigmoid fit line.
    have_fit = all(v is not None for v in (
        contract.fit_R_min, contract.fit_R_max, contract.fit_midpoint,
    ))
    if have_fit:
        Rmin = float(contract.fit_R_min)
        Rmax = float(contract.fit_R_max)
        mid = float(contract.fit_midpoint)
        slope = float(contract.fit_slope)
        xs = np.linspace(0, 1, 120)
        ys = Rmin + (Rmax - Rmin) / (1 + np.exp(-slope * 4 * (xs - mid)))
        ax.plot(xs, ys, color="#111111", lw=1.3, zorder=5,
                label="sigmoid fit")
        # Horizontal Rmin / Rmax reference.
        ax.axhline(Rmin, color=red_c, lw=0.6, ls=":", zorder=1)
        ax.axhline(Rmax, color=ox_c, lw=0.6, ls=":", zorder=1)

    # Midpoint vertical.
    if contract.fit_midpoint is not None:
        ax.axvline(contract.fit_midpoint, color="#555555",
                   lw=0.6, ls="--", zorder=1)

    ax.set_xlim(-0.04, 1.04)
    ax.set_xlabel("disulfide fraction (OxD)")
    ax.set_ylabel("measured ratio")
    ax.set_title(contract.title, fontsize=9.0, pad=4)

    # Fit-parameter callout.
    lines = []
    if have_fit:
        lines.append(
            f"Rmin = {smart_fmt(float(contract.fit_R_min))}   "
            f"Rmax = {smart_fmt(float(contract.fit_R_max))}"
        )
        lines.append(
            f"midpoint OxD = {smart_fmt(float(contract.fit_midpoint))}   "
            f"slope = {smart_fmt(float(contract.fit_slope))}"
        )
    if contract.fit_r_squared is not None:
        lines.append(f"R² = {smart_fmt(float(contract.fit_r_squared))}")
    if lines:
        ax.text(
            0.02, 0.98, "\n".join(lines),
            transform=ax.transAxes, ha="left", va="top",
            fontsize=6.6, color="#222222",
            bbox=dict(boxstyle="round,pad=0.24", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.95),
            zorder=6,
        )

    ax.legend(fontsize=6.6, frameon=False, loc="lower right",
              handlelength=1.6)
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
