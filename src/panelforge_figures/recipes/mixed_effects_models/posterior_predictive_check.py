"""Posterior predictive check — observed density + posterior draw densities overlaid."""

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


class PostPredInput(RecipeContract):
    observed: list[float] = Field(...)
    posterior_draws: list[list[float]] = Field(
        ..., description="each entry is a simulated dataset under the posterior"
    )
    x_label: str = "outcome"
    title: str = "Posterior predictive check"


def _demo() -> PostPredInput:
    rng = np.random.default_rng(53)
    observed = rng.normal(0.0, 1.0, 200)
    observed = np.concatenate([observed, rng.normal(2.5, 0.7, 80)])  # bimodal
    draws = [rng.normal(0.6, 1.1, 280).tolist() for _ in range(80)]
    return PostPredInput(
        observed=observed.tolist(),
        posterior_draws=draws,
    )


_META = RecipeMetadata(
    name="posterior_predictive_check",
    modality="mixed_effects_models",
    family=RecipeFamily.diagnostic_curve,
    answers_question="Does the fitted model reproduce the shape of the observed data distribution?",
    required_fields=("observed", "posterior_draws"),
    optional_fields=("x_label", "title"),
    file_format_hints=("csv", "npz"),
    alternatives_in_modality=("mixed_model_residual_diagnostic",),
)


@register_recipe(metadata=_META, contract=PostPredInput, demo_contract=_demo)
def render(contract: PostPredInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    obs = np.array(contract.observed, dtype=float)
    draws = [np.array(d, dtype=float) for d in contract.posterior_draws]

    # Grid spanning observed ± 1 std.
    x_lo = min(obs.min(), min(d.min() for d in draws))
    x_hi = max(obs.max(), max(d.max() for d in draws))
    span = x_hi - x_lo
    xg = np.linspace(x_lo - 0.05 * span, x_hi + 0.05 * span, 200)

    # Posterior draws — thin grey curves.
    for d in draws[:60]:
        if d.size < 3 or np.std(d) == 0:
            continue
        kde = gaussian_kde(d)
        ax.plot(xg, kde(xg), color="#BBBBBB", lw=0.6, alpha=0.35, zorder=2)

    # Observed density — thick accent curve.
    if obs.size >= 3:
        kde_obs = gaussian_kde(obs)
        ax.fill_between(xg, kde_obs(xg), 0,
                        color=palette[0], alpha=0.18, zorder=3)
        ax.plot(xg, kde_obs(xg), color=palette[0], lw=1.4, zorder=4,
                label="observed")
    # Posterior mean density.
    pm = np.mean(
        [gaussian_kde(d)(xg) if d.size >= 3 and np.std(d) > 0 else np.zeros_like(xg)
         for d in draws],
        axis=0,
    )
    ax.plot(xg, pm, color="#333333", lw=1.1, ls="--", zorder=5,
            label="posterior mean")

    ax.set_xlabel(contract.x_label)
    ax.set_ylabel("density")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="upper right",
              handlelength=1.6)

    # Summary stats.
    ax.text(0.01, 0.99,
            f"N obs = {obs.size}   N draws = {len(draws)}   "
            f"obs μ={smart_fmt(float(obs.mean()))}",
            transform=ax.transAxes, ha="left", va="top",
            fontsize=6.4, color="#444444",
            bbox=dict(boxstyle="round,pad=0.20", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=6)
    return ax
