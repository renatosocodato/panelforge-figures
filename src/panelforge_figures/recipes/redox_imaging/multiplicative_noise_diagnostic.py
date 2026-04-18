"""Multiplicative-noise diagnostic — std vs mean scatter with sqrt and linear overlays."""

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


class MultNoiseDiagInput(RecipeContract):
    means: list[float] = Field(...)
    stds: list[float] = Field(...)
    bin_labels: list[str] | None = None
    title: str = "Multiplicative noise diagnostic"


def _demo() -> MultNoiseDiagInput:
    rng = np.random.default_rng(157)
    mus = np.logspace(-1, 1, 20)
    # σ = 0.3 * μ^1.0 (multiplicative) + noise.
    stds = 0.3 * mus ** 1.0 * np.exp(rng.normal(0, 0.08, mus.size))
    return MultNoiseDiagInput(
        means=mus.tolist(),
        stds=stds.tolist(),
    )


_META = RecipeMetadata(
    name="multiplicative_noise_diagnostic",
    modality="redox_imaging",
    family=RecipeFamily.scatter_collapse,
    answers_question="Is the observed redox noise multiplicative (σ ∝ μ) or additive-dominated (σ const)?",
    required_fields=("means", "stds"),
    optional_fields=("bin_labels", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("drift_diffusion_decomposition",),
)


@register_recipe(metadata=_META, contract=MultNoiseDiagInput, demo_contract=_demo)
def render(contract: MultNoiseDiagInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)
    accent = palette.pick("intermediate")

    mu = np.array(contract.means, dtype=float)
    sd = np.array(contract.stds, dtype=float)
    # Keep positive values only.
    good = (mu > 0) & (sd > 0)
    mu = mu[good]
    sd = sd[good]

    ax.scatter(mu, sd, s=28, color=accent, alpha=0.7,
               edgecolor="white", linewidth=0.5, zorder=3,
               label="data")

    # Fit exponent in log-log.
    lx = np.log(mu)
    ly = np.log(sd)
    slope, intercept = np.polyfit(lx, ly, 1)

    mu_grid = np.logspace(np.log10(mu.min()), np.log10(mu.max()), 80)
    ax.plot(mu_grid, np.exp(intercept) * mu_grid ** slope,
            color="#111111", lw=1.1, zorder=5,
            label=f"fit (slope {smart_fmt(float(slope))})")

    # Reference: pure multiplicative (slope 1).
    anchor_x = mu_grid[0]
    anchor_y = np.exp(intercept) * anchor_x ** slope
    ax.plot(mu_grid, anchor_y * (mu_grid / anchor_x) ** 1.0,
            color=palette.pick("oxidized"), lw=0.8, ls="--", zorder=4,
            label="slope = 1 (multiplicative)")
    # Reference: Poisson-like (slope 0.5).
    ax.plot(mu_grid, anchor_y * (mu_grid / anchor_x) ** 0.5,
            color=palette.pick("reduced"), lw=0.8, ls="--", zorder=4,
            label="slope = 0.5 (Poisson-like)")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(r"$\mu$ (ratio mean)")
    ax.set_ylabel(r"$\sigma$ (ratio std)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.6, frameon=False, loc="upper left",
              handlelength=1.8)
    ax.grid(axis="both", which="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
