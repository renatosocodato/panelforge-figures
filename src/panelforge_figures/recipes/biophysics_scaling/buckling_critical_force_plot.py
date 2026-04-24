"""Buckling critical-force plot — Euler curves + experimental points."""

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


class BucklingInput(RecipeContract):
    lengths: list[float] = Field(..., description="rod length (μm)")
    forces: list[float] = Field(..., description="measured critical buckling force (pN)")
    youngs_modulus: float = Field(2e9, description="Pa, for theoretical Euler")
    radius: float = Field(12.5e-9, description="rod radius in m (actin ≈ 3.5 nm, MT ≈ 12.5 nm)")
    title: str = "Buckling critical force"


def _demo() -> BucklingInput:
    rng = np.random.default_rng(97)
    L_um = np.linspace(1, 20, 20)
    # F_c (pN) = π²EI / L². I = π r⁴ / 4. Convert to μm for L.
    E = 2e9
    r = 12.5e-9
    inertia = np.pi * r ** 4 / 4
    L = L_um * 1e-6
    F_th = np.pi ** 2 * E * inertia / L ** 2 * 1e12   # convert N → pN
    noise = rng.lognormal(0, 0.12, len(L_um))
    F_meas = F_th * noise
    return BucklingInput(
        lengths=L_um.tolist(),
        forces=F_meas.tolist(),
        youngs_modulus=E,
        radius=r,
        title="Microtubule buckling",
    )


_META = RecipeMetadata(
    name="buckling_critical_force_plot",
    modality="biophysics_scaling",
    family=RecipeFamily.diagnostic_curve,
    answers_question="Does the critical buckling force of a filament follow F ∝ L-2 (Euler), and what does that tell us about bending stiffness?",
    required_fields=("lengths", "forces"),
    optional_fields=("youngs_modulus", "radius", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("force_length_characteristic",),
)


@register_recipe(metadata=_META, contract=BucklingInput, demo_contract=_demo)
def render(contract: BucklingInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)
    accent = palette[6]           # vermillion

    L_um = np.array(contract.lengths, dtype=float)
    F = np.array(contract.forces, dtype=float)

    # Theoretical Euler.
    E = contract.youngs_modulus
    r = contract.radius
    inertia = np.pi * r ** 4 / 4
    L_m = L_um * 1e-6
    F_th = np.pi ** 2 * E * inertia / L_m ** 2 * 1e12

    ax.plot(L_um, F_th, color="#333333", lw=1.1, ls="--", zorder=3,
            label=r"Euler: $F_c = \pi^2 E I / L^2$")
    ax.scatter(L_um, F, s=34, color=accent, alpha=0.8,
               edgecolor="white", linewidth=0.6, zorder=4,
               label="measured")

    # Fit observed exponent.
    lx = np.log(L_um)
    ly = np.log(F)
    slope, intercept = np.polyfit(lx, ly, 1)
    # Overlay observed best-fit line for visual comparison.
    xfit = np.linspace(L_um.min(), L_um.max(), 80)
    yfit = np.exp(intercept) * xfit ** slope
    ax.plot(xfit, yfit, color=accent, lw=1.0, zorder=3,
            label=f"observed (slope {smart_fmt(float(slope))})")
    ax.text(0.02, 0.05,
            f"observed slope = {smart_fmt(float(slope))}\n"
            rf"EI = {smart_fmt(E * inertia * 1e24)} $\times$ 10$^{{-24}}$ N m$^2$",
            transform=ax.transAxes, ha="left", va="bottom",
            fontsize=6.8, color="#333333",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=5)

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("length (μm)")
    ax.set_ylabel(r"$F_c$ (pN)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="upper right",
              handlelength=1.8)
    ax.grid(axis="both", which="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
