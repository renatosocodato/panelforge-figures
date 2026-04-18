"""Bayesian posterior density per term — stacked KDEs with HDI markers."""

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


class PosteriorDensityInput(RecipeContract):
    term_samples: dict[str, list[float]] = Field(
        ..., description="posterior draws per term"
    )
    hdi_prob: float = 0.95
    title: str = "Posterior densities"


def _demo() -> PosteriorDensityInput:
    rng = np.random.default_rng(67)
    terms = {
        "Intercept": rng.normal(1.20, 0.10, 2000),
        "sexF": rng.normal(0.10, 0.08, 2000),
        "genotypeKO": rng.normal(-0.30, 0.09, 2000),
        "treatment": rng.normal(0.45, 0.09, 2000),
        "sexF:genotypeKO": rng.normal(-0.58, 0.12, 2000),
        "sexF:treatment": rng.normal(0.22, 0.10, 2000),
    }
    return PosteriorDensityInput(
        term_samples={k: v.tolist() for k, v in terms.items()},
        hdi_prob=0.95,
    )


def _hdi(samples: np.ndarray, prob: float) -> tuple[float, float]:
    """Highest-density interval via sorted-sweep."""
    s = np.sort(samples)
    n = len(s)
    width = int(np.floor(prob * n))
    if width <= 0 or width >= n:
        return float(s[0]), float(s[-1])
    diffs = s[width:] - s[:n - width]
    k = int(np.argmin(diffs))
    return float(s[k]), float(s[k + width])


_META = RecipeMetadata(
    name="bayes_posterior_density_by_term",
    modality="mixed_effects_models",
    family=RecipeFamily.ridge_by_group,
    answers_question="How is uncertainty distributed across fixed-effect terms in a Bayesian mixed model?",
    required_fields=("term_samples",),
    optional_fields=("hdi_prob", "title"),
    file_format_hints=("csv", "parquet", "rds"),
    alternatives_in_modality=("sex_x_genotype_interaction_forest",),
)


@register_recipe(metadata=_META, contract=PosteriorDensityInput, demo_contract=_demo)
def render(contract: PosteriorDensityInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.6))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    terms = list(contract.term_samples.keys())
    # Shared x-grid across all terms for coherent stacking.
    all_vals = np.concatenate([np.asarray(v) for v in contract.term_samples.values()])
    xlo, xhi = np.quantile(all_vals, [0.005, 0.995])
    span = xhi - xlo
    xg = np.linspace(xlo - 0.05 * span, xhi + 0.05 * span, 220)

    y_step = 1.0
    max_density = 0.0
    kdes = {}
    for term in terms:
        s = np.asarray(contract.term_samples[term], float)
        kde = gaussian_kde(s)
        kdes[term] = kde
        max_density = max(max_density, float(kde(xg).max()))

    # Zero reference.
    ax.axvline(0, color="#888888", lw=0.7, ls="--", zorder=1)

    for i, term in enumerate(terms[::-1]):         # top-to-bottom == first-to-last
        s = np.asarray(contract.term_samples[term], float)
        kde = kdes[term]
        dens = kde(xg)
        # Scale density so rows don't overlap.
        dens_s = (dens / max_density) * 0.85 * y_step
        y_base = i * y_step
        color = palette[i % len(palette.colors)]
        ax.fill_between(xg, y_base, y_base + dens_s,
                        color=color, alpha=0.55, linewidth=0, zorder=3)
        ax.plot(xg, y_base + dens_s, color=color, lw=0.8, zorder=4)

        # HDI marker.
        lo, hi = _hdi(s, contract.hdi_prob)
        ax.plot([lo, hi], [y_base - 0.06, y_base - 0.06],
                color="#333333", lw=1.3, zorder=5)
        ax.plot([float(np.median(s))], [y_base - 0.06],
                marker="o", color="#333333", ms=3.5, zorder=6)

        # Term label on the left.
        ax.text(xg[0], y_base + 0.5 * 0.85 * y_step,
                term, ha="right", va="center",
                fontsize=7.0, color="#222222")

        # Value label on the right (median).
        ax.text(xhi + 0.05 * span, y_base + 0.02,
                smart_fmt(float(np.median(s))),
                ha="left", va="center", fontsize=6.6, color=color)

    ax.set_xlim(xlo - 0.15 * span, xhi + 0.20 * span)
    ax.set_ylim(-0.4, len(terms) - 0.1)
    ax.set_yticks([])
    ax.set_xlabel("posterior value")
    ax.set_title(
        f"{contract.title} · {int(contract.hdi_prob*100)}% HDI",
        fontsize=9.0, pad=4,
    )
    for side in ("left",):
        ax.spines[side].set_visible(False)
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
