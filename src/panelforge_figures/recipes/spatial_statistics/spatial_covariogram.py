"""Spatial covariogram C(h) — covariance of a continuous field vs
spatial lag, with nugget/sill/range annotation and exponential fit.

Distinct from `moran_i_by_lag` (Moran's I autocorrelation coefficient
for categorical / binary marks): here the statistic is the **covariance**
of a continuous mark, and the target is the correlation length (range).
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


class CovariogramInput(RecipeContract):
    lag_um: list[float] = Field(..., min_length=5)
    covariance: list[float] = Field(..., description="C(h) per lag")
    title: str = "Spatial covariogram"


def _demo() -> CovariogramInput:
    rng = np.random.default_rng(1217)
    h = np.linspace(0, 40, 45)
    sill = 1.0
    nugget = 0.1
    range_ = 12.0
    C = nugget + (sill - nugget) * np.exp(-h / range_)
    C[0] = sill
    C += rng.normal(0, 0.02, h.size)
    return CovariogramInput(
        lag_um=h.tolist(),
        covariance=C.tolist(),
    )


_META = RecipeMetadata(
    name="spatial_covariogram",
    modality="spatial_statistics",
    family=RecipeFamily.diagnostic_curve,
    answers_question=(
        "At what spatial lag does the covariance of a continuous field "
        "decay to zero (correlation length)?"
    ),
    required_fields=("lag_um", "covariance"),
    optional_fields=("title",),
    file_format_hints=("csv",),
    alternatives_in_modality=("moran_i_by_lag",),
)


@register_recipe(
    metadata=_META,
    contract=CovariogramInput,
    demo_contract=_demo,
)
def render(contract: CovariogramInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    h = np.asarray(contract.lag_um, float)
    C = np.asarray(contract.covariance, float)

    # Fit exponential: C(h) = nugget + (sill - nugget) * exp(-h/range).
    # Simple estimates: sill ≈ C(h_small), nugget from decorrelated tail.
    sill_est = float(np.max(C))
    nugget_est = float(np.min(C))
    # Range: first lag where C drops to nugget + (sill-nugget)*exp(-1).
    target = nugget_est + (sill_est - nugget_est) * np.exp(-1)
    range_idx = int(np.argmin(np.abs(C - target)))
    range_est = float(h[range_idx])

    ax.scatter(h, C, s=26, color=palette[1], alpha=0.8,
               edgecolor="white", linewidth=0.5, zorder=3,
               label="observed")
    hfit = np.linspace(0, h.max(), 100)
    Cfit = nugget_est + (sill_est - nugget_est) * np.exp(-hfit / range_est)
    ax.plot(hfit, Cfit, color="#222222", lw=1.1, zorder=4,
            label=f"fit (range = {smart_fmt(range_est)} μm)")
    # Sill / nugget reference lines.
    ax.axhline(sill_est, color="#2E7D32", lw=0.6, ls=":", zorder=2,
               label=f"sill = {smart_fmt(sill_est)}")
    ax.axhline(nugget_est, color="#C62828", lw=0.6, ls=":", zorder=2,
               label=f"nugget = {smart_fmt(nugget_est)}")
    ax.axvline(range_est, color="#888888", lw=0.6, ls="--", zorder=2)

    ax.set_xlabel("lag h (μm)")
    ax.set_ylabel("C(h)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="upper right",
              handlelength=1.6)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    ax.text(0.02, 0.04,
            f"correlation length ≈ {smart_fmt(range_est)} μm",
            transform=ax.transAxes, ha="left", va="bottom",
            fontsize=6.4, color="#333333",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=6)
    return ax
