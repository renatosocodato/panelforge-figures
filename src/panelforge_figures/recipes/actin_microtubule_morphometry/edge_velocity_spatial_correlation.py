"""Edge-velocity spatial autocorrelation along cell perimeter — decay-scale fit."""

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


class EdgeCorrelationInput(RecipeContract):
    arc_lag_um: list[float] = Field(..., description="arc-length lag (µm)")
    correlation: list[float] = Field(..., description="C(s) edge-velocity autocorrelation")
    correlation_ci_lo: list[float] | None = None
    correlation_ci_hi: list[float] | None = None
    decay_scale_um: float | None = Field(
        None, description="fitted exponential decay length (µm); otherwise fitted from data"
    )
    title: str = "Edge-velocity spatial correlation"


def _demo() -> EdgeCorrelationInput:
    rng = np.random.default_rng(731)
    lags = np.linspace(0, 22, 46)
    lam_true = 4.8
    corr = np.exp(-lags / lam_true) + rng.normal(0, 0.025, lags.size)
    corr = np.clip(corr, -0.2, 1.0)
    sem = 0.04 + 0.015 * lags / lags.max()
    return EdgeCorrelationInput(
        arc_lag_um=lags.tolist(),
        correlation=corr.tolist(),
        correlation_ci_lo=(corr - 1.96 * sem).tolist(),
        correlation_ci_hi=(corr + 1.96 * sem).tolist(),
        decay_scale_um=lam_true,
    )


_META = RecipeMetadata(
    name="edge_velocity_spatial_correlation",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.diagnostic_curve,
    answers_question=(
        "Along a cell perimeter, over what arc-length distance does edge "
        "velocity stay correlated?"
    ),
    required_fields=("arc_lag_um", "correlation"),
    optional_fields=("correlation_ci_lo", "correlation_ci_hi", "decay_scale_um", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("skeleton_overlay_kymograph",),
)


@register_recipe(
    metadata=_META,
    contract=EdgeCorrelationInput,
    demo_contract=_demo,
)
def render(contract: EdgeCorrelationInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)
    accent = palette.pick("actin") if "actin" in palette.semantic else palette[0]

    lags = np.asarray(contract.arc_lag_um, float)
    c = np.asarray(contract.correlation, float)

    # CI band + measured curve.
    if contract.correlation_ci_lo is not None and contract.correlation_ci_hi is not None:
        lo = np.asarray(contract.correlation_ci_lo, float)
        hi = np.asarray(contract.correlation_ci_hi, float)
        ax.fill_between(lags, lo, hi, color=accent, alpha=0.18, linewidth=0,
                        zorder=2, label="95% CI")
    ax.plot(lags, c, color=accent, lw=1.3, zorder=3, label="measured")

    # Fit exponential: log(c) vs s → slope = -1 / λ.
    lam = contract.decay_scale_um
    if lam is None:
        mask = c > 0.02
        if mask.sum() >= 3:
            slope, intercept = np.polyfit(lags[mask], np.log(c[mask]), 1)
            lam = -1.0 / slope if slope < 0 else None
    if lam is not None:
        s_fine = np.linspace(0, float(lags.max()), 200)
        ax.plot(s_fine, np.exp(-s_fine / float(lam)),
                color="#111111", lw=1.1, ls="--", zorder=4,
                label=rf"fit $\exp(-s/\lambda)$,  $\lambda$ = {smart_fmt(float(lam))} $\mu$m")
        ax.axvline(float(lam), color="#888888", lw=0.6, ls=":", zorder=1)

    ax.axhline(0, color="#AAAAAA", lw=0.5, ls=":", zorder=1)
    ax.set_xlabel(r"arc-length lag $s$ ($\mu$m)")
    ax.set_ylabel(r"$C(s)$")
    ax.set_ylim(-0.1, 1.05)
    ax.set_xlim(0, float(lags.max()))
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.6, frameon=False, loc="upper right",
              handlelength=1.8)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
