"""Langevin noise model comparison — additive D vs multiplicative D(Y).

For a stochastic-differential-equation fit to ratio(t), decompose the
residual noise ξ(t) after subtracting the drift term μ(Y)·Δt. Plot ξ²
vs Y with two competing fits:
    D_additive  : ξ² ≈ 2·D_add·Δt               (constant)
    D_multiplicative : ξ² ≈ 2·(σ·Y)² ·Δt         (Y²-scaling)
and an AIC-style preference callout.

Distinct from `multiplicative_noise_diagnostic` (σ-vs-μ scaling law
on a log-log scatter with a *single* fit slope — no competing-model
comparison against an additive-noise alternative).
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


class LangevinNoiseInput(RecipeContract):
    Y: list[float] = Field(..., description="state value Y (e.g. ratio)")
    xi_sq: list[float] = Field(
        ..., description="squared residual noise ξ² after drift subtraction"
    )
    dt: float = Field(default=1.0, description="time-step used in drift subtraction")
    fit_D_additive: float | None = None
    fit_sigma_multiplicative: float | None = None
    aic_additive: float | None = None
    aic_multiplicative: float | None = None
    title: str = "Langevin noise: additive vs multiplicative"


def _demo() -> LangevinNoiseInput:
    rng = np.random.default_rng(401)
    n = 400
    Y = rng.uniform(0.3, 2.2, n)
    sigma_mult = 0.25
    dt = 1.0
    # Data model: ξ² = 2·σ²·Y²·dt + noise  (true multiplicative).
    xi_sq = 2 * (sigma_mult ** 2) * Y ** 2 * dt + rng.normal(0, 0.02, n)
    xi_sq = np.clip(xi_sq, 0, None)
    # Fit additive: constant 2·D_add·dt = mean(xi_sq).
    D_add = float(xi_sq.mean() / (2 * dt))
    # Fit multiplicative: σ² from regression of xi_sq on 2·Y²·dt through origin.
    kk = 2 * (Y ** 2) * dt
    sigma_sq_est = float(max(np.sum(xi_sq * kk) / np.sum(kk * kk), 0))
    sigma_est = float(np.sqrt(sigma_sq_est))
    # RSS → pseudo-AIC (same parameter count, compare on RSS).
    rss_add = float(np.sum((xi_sq - 2 * D_add * dt) ** 2))
    rss_mult = float(np.sum((xi_sq - 2 * sigma_sq_est * (Y ** 2) * dt) ** 2))
    aic_add = n * np.log(rss_add / n) + 2 * 1
    aic_mult = n * np.log(rss_mult / n) + 2 * 1
    return LangevinNoiseInput(
        Y=Y.tolist(),
        xi_sq=xi_sq.tolist(),
        dt=dt,
        fit_D_additive=D_add,
        fit_sigma_multiplicative=sigma_est,
        aic_additive=float(aic_add),
        aic_multiplicative=float(aic_mult),
    )


_META = RecipeMetadata(
    name="multiplicative_vs_additive_noise_diagnostic",
    modality="redox_imaging",
    family=RecipeFamily.diagnostic_curve,
    answers_question=(
        "Is the Langevin noise on ratio(t) better explained by a "
        "Y-independent additive model, or a Y-dependent multiplicative "
        "D(Y)?"
    ),
    required_fields=("Y", "xi_sq"),
    optional_fields=(
        "dt", "fit_D_additive", "fit_sigma_multiplicative",
        "aic_additive", "aic_multiplicative", "title",
    ),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("multiplicative_noise_diagnostic",),
)


@register_recipe(
    metadata=_META,
    contract=LangevinNoiseInput,
    demo_contract=_demo,
)
def render(contract: LangevinNoiseInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    Y = np.asarray(contract.Y, float)
    xi2 = np.asarray(contract.xi_sq, float)

    ax.scatter(Y, xi2, s=9, color=palette.pick("intermediate"),
               alpha=0.55, edgecolor="white", linewidth=0.15,
               zorder=3, label="ξ² data")

    ys = np.linspace(Y.min(), Y.max(), 200)
    add_color = palette.pick("reduced")
    mult_color = palette.pick("oxidized")

    if contract.fit_D_additive is not None:
        D_add = float(contract.fit_D_additive)
        ax.axhline(2 * D_add * contract.dt, color=add_color,
                   lw=1.3, ls="--", zorder=4,
                   label=f"additive  D={smart_fmt(D_add)}")
    if contract.fit_sigma_multiplicative is not None:
        sig = float(contract.fit_sigma_multiplicative)
        curve = 2 * (sig * ys) ** 2 * contract.dt
        ax.plot(ys, curve, color=mult_color, lw=1.3, zorder=5,
                label=f"multiplicative  σ={smart_fmt(sig)}")

    ax.set_xlabel("Y (state)")
    ax.set_ylabel("ξ² (noise power)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.set_xlim(Y.min(), Y.max())
    ax.set_ylim(bottom=0)

    # Preference callout.
    if (contract.aic_additive is not None
            and contract.aic_multiplicative is not None):
        d_aic = contract.aic_additive - contract.aic_multiplicative
        if d_aic > 0:
            preferred = "multiplicative"
            pref_color = mult_color
        else:
            preferred = "additive"
            pref_color = add_color
        txt = (
            f"ΔAIC(add − mult) = {smart_fmt(d_aic)}\n"
            f"preferred: {preferred}"
        )
        ax.text(
            0.02, 0.98, txt,
            transform=ax.transAxes, ha="left", va="top",
            fontsize=6.6, color=pref_color,
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.95),
            zorder=6,
        )

    ax.legend(fontsize=6.6, frameon=False, loc="upper right",
              handlelength=1.6)
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
