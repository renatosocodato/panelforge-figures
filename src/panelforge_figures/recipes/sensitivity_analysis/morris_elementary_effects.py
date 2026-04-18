"""Morris elementary effects (μ* vs σ) screening scatter."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    add_halo_label,
    callout_box,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class MorrisEEInput(RecipeContract):
    parameter_names: list[str] = Field(..., min_length=2)
    mu_star: list[float] = Field(...)
    sigma: list[float] = Field(...)
    output_label: str = "model output"
    label_top_n: int = 5


def _demo() -> MorrisEEInput:
    rng = np.random.default_rng(11)
    params = [f"p{i+1}" for i in range(14)]
    mu_star = np.abs(rng.normal(0.3, 0.25, len(params))) + 0.01
    sigma = np.abs(rng.normal(0.25, 0.2, len(params))) + 0.01
    # Force a known driver.
    mu_star[0] = 0.95
    sigma[0] = 0.5
    return MorrisEEInput(
        parameter_names=params,
        mu_star=mu_star.tolist(),
        sigma=sigma.tolist(),
        output_label="steady-state concentration",
    )


_META = RecipeMetadata(
    name="morris_elementary_effects",
    modality="sensitivity_analysis",
    family=RecipeFamily.sobol_bar,
    answers_question="Among many parameters, which are important (high μ*) and which are important mainly via interactions or nonlinearity (high σ)?",
    required_fields=("parameter_names", "mu_star", "sigma"),
    optional_fields=("output_label", "label_top_n"),
    file_format_hints=("parquet", "csv", "pickle"),
    n_points_typical="10-40 parameters",
    alternatives_in_modality=("sobol_first_total_pair", "fast_subspace_detection"),
)


@register_recipe(metadata=_META, contract=MorrisEEInput, demo_contract=_demo)
def render(contract: MorrisEEInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.6))
    AESTHETIC.apply_to_ax(ax)
    mu = np.array(contract.mu_star)
    sig = np.array(contract.sigma)
    names = list(contract.parameter_names)
    magnitude = np.hypot(mu, sig)
    order = np.argsort(-magnitude)

    # Scatter colored by overall magnitude; size proportional to mu*.
    import matplotlib as mpl
    cmap = mpl.colormaps[AESTHETIC.continuous_cmap]
    sc = ax.scatter(
        mu,
        sig,
        s=120 * (mu / max(mu.max(), 1e-9)) + 20,
        c=magnitude,
        cmap=cmap,
        edgecolor="white",
        linewidth=0.8,
        zorder=3,
    )

    # Screening dividers.
    mu_med = np.median(mu)
    sig_med = np.median(sig)
    ax.axvline(mu_med, color="#888888", lw=0.5, ls=":", zorder=1)
    ax.axhline(sig_med, color="#888888", lw=0.5, ls=":", zorder=1)

    # Label top-N by magnitude.
    top = order[: max(1, contract.label_top_n)]
    for k, idx in enumerate(top):
        nudge_x = (k + 1) * 0.008 * (mu.max() - mu.min())
        nudge_y = (-1 if k % 2 else 1) * 0.03 * (sig.max() - sig.min())
        add_halo_label(
            ax, mu[idx] + nudge_x, sig[idx] + nudge_y,
            names[idx], color="#222222",
            fontsize=7.2, halo_width=2.6,
            ha="left", va="center",
        )

    # μ* = σ reference line — draw only inside the data box.
    x_hi = mu.max() * 1.12
    y_hi = sig.max() * 1.15
    m = min(x_hi, y_hi)
    ax.plot([0, m], [0, m], color="#AAAAAA", ls="--", lw=0.8, zorder=1)

    cbar = ax.figure.colorbar(sc, ax=ax, fraction=0.04, pad=0.04)
    cbar.set_label("magnitude", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.2)

    # Top-driver summary — below x-axis in figure coords, pushed further
    # down (-0.14) so it clears the tick labels and x-axis title cleanly.
    fig = ax.figure
    fig.text(
        0.5, -0.22,
        rf"Top driver: {names[order[0]]} ($\mu^*$={smart_fmt(mu[order[0]])}, "
        rf"$\sigma$={smart_fmt(sig[order[0]])})",
        ha="center", va="top", fontsize=7.0,
        bbox=dict(boxstyle="round,pad=0.28", fc="white",
                  ec=AESTHETIC.annotation_style.callout_accent, lw=0.6),
        transform=ax.transAxes,
    )
    _ = callout_box
    ax.set_xlabel(r"$\mu^*$ (mean |elementary effect|)", fontsize=7.8)
    ax.set_ylabel(r"$\sigma$ (std elementary effect)", fontsize=7.8)
    ax.set_title("Morris screening", fontsize=9.0, pad=4)
    ax.set_xlim(0, x_hi)
    ax.set_ylim(0, y_hi)
    # μ* = σ inline label placed at the end of the diagonal (inside the box).
    ax.text(m * 0.97, m * 0.90, r"$\mu^*\,=\,\sigma$", color="#666666",
            fontsize=6.4, ha="right", va="top", rotation=36)
    return ax
