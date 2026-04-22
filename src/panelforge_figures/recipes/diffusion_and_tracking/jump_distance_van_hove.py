"""Jump-distance van Hove self-correlation — P(Δr, Δt) stacked by lag
time with a Gaussian (Brownian) reference overlay.

Distinct from `step_size_distribution` (single-lag per-condition
ridges): here the axis-grammar is **multi-lag same-condition** with a
theoretical Gaussian reference.
"""

from __future__ import annotations

import numpy as np
from pydantic import Field
from scipy.stats import gaussian_kde

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class VanHoveInput(RecipeContract):
    lag_s: list[float] = Field(..., min_length=2,
                               description="lag times in seconds")
    jumps_by_lag: dict[str, list[float]] = Field(
        ...,
        description="lag label (e.g. 'τ=0.1') → list of Δr jump values",
    )
    title: str = "Van Hove self-correlation"


def _demo() -> VanHoveInput:
    rng = np.random.default_rng(1721)
    lags = [0.1, 0.3, 1.0, 3.0]
    # Heavy-tailed non-Gaussian process: mix of Gaussian + occasional long jumps.
    by_lag: dict[str, list[float]] = {}
    for t in lags:
        sigma = 0.25 * np.sqrt(t)
        base = rng.normal(0, sigma, 3000)
        heavy = rng.normal(0, sigma * 3.0, 300)
        arr = np.concatenate([base, heavy])
        by_lag[f"τ = {t:g} s"] = arr.tolist()
    return VanHoveInput(
        lag_s=lags,
        jumps_by_lag=by_lag,
    )


_META = RecipeMetadata(
    name="jump_distance_van_hove",
    modality="diffusion_and_tracking",
    family=RecipeFamily.ridge_by_group,
    answers_question=(
        "Does P(Δr, Δt) follow a pure Gaussian (Brownian), or is it "
        "non-Gaussian — a signature of heterogeneity or anomalous "
        "diffusion?"
    ),
    required_fields=("lag_s", "jumps_by_lag"),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("step_size_distribution",),
)


@register_recipe(
    metadata=_META,
    contract=VanHoveInput,
    demo_contract=_demo,
)
def render(contract: VanHoveInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.8))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    labels = list(contract.jumps_by_lag.keys())
    all_vals = np.concatenate([
        np.asarray(contract.jumps_by_lag[k], float) for k in labels
    ])
    # Plot |Δr| in log x for easier tail comparison.
    xg = np.linspace(0.0, float(np.percentile(np.abs(all_vals), 99.5)), 300)

    kdes = {k: gaussian_kde(np.abs(np.asarray(contract.jumps_by_lag[k], float)))
            for k in labels}
    max_d = max(k(xg).max() for k in kdes.values())

    # Ridge stack from bottom (shortest lag) to top (longest).
    y_step = 1.0
    non_gauss_max = 0.0
    for i, lab in enumerate(labels):
        color = palette[i % len(palette.colors)]
        vals = np.abs(np.asarray(contract.jumps_by_lag[lab], float))
        dens = kdes[lab](xg)
        dens_s = (dens / max_d) * 0.85 * y_step
        y_base = i * y_step
        ax.fill_between(xg, y_base, y_base + dens_s, color=color,
                        alpha=0.55, linewidth=0, zorder=3)
        ax.plot(xg, y_base + dens_s, color=color, lw=0.8, zorder=4)

        # Theoretical Gaussian reference with the same variance.
        sigma = float(np.std(vals))
        mu = 0.0
        gaussian = (np.exp(-0.5 * ((xg - mu) / max(sigma, 1e-9)) ** 2) /
                    (sigma * np.sqrt(2 * np.pi)))
        # Rayleigh-like for |Δr|: 2 * pdf * (xg > 0) since we fold to |Δr|.
        gaussian_half = 2 * gaussian * (xg >= 0)
        gauss_s = (gaussian_half / max(max_d, 1e-9)) * 0.85 * y_step
        ax.plot(xg, y_base + gauss_s, color="#444444", lw=0.6, ls="--",
                zorder=5)

        # Non-Gaussian parameter α₂ = <r⁴>/(3<r²>²) - 1.
        r2 = float(np.mean(vals ** 2))
        r4 = float(np.mean(vals ** 4))
        alpha_2 = r4 / max(3 * r2 ** 2, 1e-12) - 1
        non_gauss_max = max(non_gauss_max, alpha_2)

        ax.text(xg[0], y_base + 0.45 * y_step, lab,
                ha="left", va="center", fontsize=7.0, color="#222222")
        ax.text(xg[-1] * 0.98, y_base + 0.82 * y_step,
                rf"α$_2$ = {smart_fmt(alpha_2)}",
                ha="right", va="top", fontsize=6.4, color=color)

    ax.set_xlim(0, xg.max())
    ax.set_ylim(-0.3, len(labels) - 0.1)
    ax.set_yticks([])
    ax.set_xlabel("|Δr| (μm)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)

    ax.text(0.02, 0.97,
            f"max α$_2$ = {smart_fmt(non_gauss_max)}   "
            "(α$_2$ > 0 ↔ non-Gaussian)".replace("↔", "<->"),
            transform=ax.transAxes, ha="left", va="top",
            fontsize=6.4, color="#333333",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=6)

    for s in ("left",):
        ax.spines[s].set_visible(False)
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
