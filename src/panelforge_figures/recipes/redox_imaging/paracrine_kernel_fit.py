"""Fitted paracrine coupling kernel K(r) vs r — 1-D view with λ callout.

Empirical pairwise-cell kernel (correlation of ratios vs pair distance)
overlaid with an exponential or Gaussian fit and a decay-length (λ)
callout with R².

Distinct from `paracrine_coupling_length_map` (2-D ratio field, not
1-D kernel).
"""

from __future__ import annotations

from typing import Literal

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


class ParacrineKernelInput(RecipeContract):
    r_um: list[float] = Field(..., min_length=3)
    K_r: list[float] = Field(...)
    K_sem: list[float] | None = None
    kernel_shape: Literal["exponential", "gaussian"] = "exponential"
    fit_lambda_um: float | None = None
    fit_amplitude: float | None = None
    fit_floor: float = 0.0
    fit_r_squared: float | None = None
    title: str = "Paracrine kernel fit"


def _demo() -> ParacrineKernelInput:
    rng = np.random.default_rng(331)
    r = np.linspace(0.5, 120.0, 24)
    lam = 22.0
    amp = 0.78
    K = amp * np.exp(-r / lam) + 0.04
    K_noisy = K + rng.normal(0, 0.02, r.size)
    sem = rng.uniform(0.01, 0.03, r.size)
    fit_pred = amp * np.exp(-r / lam) + 0.04
    r2 = float(
        1 - np.var(K_noisy - fit_pred) / np.var(K_noisy - K_noisy.mean())
    )
    return ParacrineKernelInput(
        r_um=r.tolist(),
        K_r=K_noisy.tolist(),
        K_sem=sem.tolist(),
        kernel_shape="exponential",
        fit_lambda_um=lam,
        fit_amplitude=amp,
        fit_floor=0.04,
        fit_r_squared=r2,
    )


_META = RecipeMetadata(
    name="paracrine_kernel_fit",
    modality="redox_imaging",
    family=RecipeFamily.diagnostic_curve,
    answers_question=(
        "Fitted to pairwise-cell data, what is the 1-D paracrine "
        "coupling kernel K(r), and what is the decay length λ?"
    ),
    required_fields=("r_um", "K_r"),
    optional_fields=(
        "K_sem", "kernel_shape", "fit_lambda_um", "fit_amplitude",
        "fit_floor", "fit_r_squared", "title",
    ),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("paracrine_coupling_length_map",),
)


@register_recipe(
    metadata=_META,
    contract=ParacrineKernelInput,
    demo_contract=_demo,
)
def render(contract: ParacrineKernelInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    r = np.asarray(contract.r_um, float)
    K = np.asarray(contract.K_r, float)
    sem = (np.asarray(contract.K_sem, float)
           if contract.K_sem is not None else None)

    data_color = palette.pick("intermediate")
    fit_color = "#111111"

    if sem is not None:
        ax.fill_between(r, K - sem, K + sem, color=data_color,
                        alpha=0.22, linewidth=0, zorder=2,
                        label="±SEM")
    ax.scatter(r, K, s=26, color=data_color, edgecolor="white",
               linewidth=0.6, zorder=3, label="data")

    if contract.fit_lambda_um is not None:
        lam = float(contract.fit_lambda_um)
        amp = (float(contract.fit_amplitude)
               if contract.fit_amplitude is not None else float(K.max()))
        floor = float(contract.fit_floor)
        rs = np.linspace(r.min(), r.max(), 200)
        if contract.kernel_shape == "gaussian":
            fit_curve = amp * np.exp(-0.5 * (rs / lam) ** 2) + floor
            label_fit = f"Gaussian  λ={smart_fmt(lam)} μm"
        else:
            fit_curve = amp * np.exp(-rs / lam) + floor
            label_fit = f"exp.  λ={smart_fmt(lam)} μm"
        ax.plot(rs, fit_curve, color=fit_color, lw=1.3, zorder=4,
                label=label_fit)
        # λ-marker vertical.
        ax.axvline(lam, color="#888888", lw=0.6, ls="--", zorder=1)

    ax.set_xlabel("pair distance r (μm)")
    ax.set_ylabel("K(r)  (pairwise correlation)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.set_xlim(0, r.max())
    ax.set_ylim(bottom=0)

    # Fit callout.
    bits = []
    if contract.fit_lambda_um is not None:
        bits.append(f"λ = {smart_fmt(float(contract.fit_lambda_um))} μm")
    if contract.fit_amplitude is not None:
        bits.append(f"amp = {smart_fmt(float(contract.fit_amplitude))}")
    if contract.fit_r_squared is not None:
        bits.append(f"R² = {smart_fmt(float(contract.fit_r_squared))}")
    if bits:
        ax.text(
            0.98, 0.97, "   ".join(bits),
            transform=ax.transAxes, ha="right", va="top",
            fontsize=6.6, color="#111111",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.95),
            zorder=6,
        )

    ax.legend(fontsize=6.6, frameon=False, loc="center right",
              handlelength=1.6)
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
