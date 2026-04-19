"""Posterior contrast densities — stacked Δ-posteriors with HDI + P(Δ>0).

Different from `bayes_posterior_density_by_term`: this panel plots the
*posteriors of contrasts* (differences between groups), not absolute
term posteriors. Each row shows the full density of Δ, the 95 % HDI,
and the probability-of-direction (P(Δ > 0)).
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


class PosteriorContrastInput(RecipeContract):
    contrast_samples: dict[str, list[float]] = Field(
        ..., description="contrast name → posterior draws of the difference"
    )
    hdi_prob: float = 0.95
    title: str = "Posterior contrast densities"


def _demo() -> PosteriorContrastInput:
    rng = np.random.default_rng(319)
    return PosteriorContrastInput(
        contrast_samples={
            "F_WT − M_WT":  rng.normal(0.25, 0.10, 2000).tolist(),
            "F_KO − M_KO":  rng.normal(-0.15, 0.11, 2000).tolist(),
            "F_WT − F_KO":  rng.normal(0.52, 0.12, 2000).tolist(),
            "M_WT − M_KO":  rng.normal(0.12, 0.09, 2000).tolist(),
            "WT − KO":      rng.normal(0.32, 0.08, 2000).tolist(),
            "F − M":        rng.normal(0.05, 0.08, 2000).tolist(),
        },
    )


def _hdi(samples: np.ndarray, prob: float) -> tuple[float, float]:
    s = np.sort(samples)
    n = len(s)
    width = int(np.floor(prob * n))
    if width <= 0 or width >= n:
        return float(s[0]), float(s[-1])
    diffs = s[width:] - s[: n - width]
    k = int(np.argmin(diffs))
    return float(s[k]), float(s[k + width])


_META = RecipeMetadata(
    name="posterior_contrast_density",
    modality="mixed_effects_models",
    family=RecipeFamily.ridge_by_group,
    answers_question=(
        "What is the full posterior distribution of each *contrast* (Δ "
        "between groups), with 95 % HDI and probability-of-direction?"
    ),
    required_fields=("contrast_samples",),
    optional_fields=("hdi_prob", "title"),
    file_format_hints=("csv", "parquet", "rds"),
    alternatives_in_modality=(
        "bayes_posterior_density_by_term",
        "emmeans_contrast_grid",
    ),
)


@register_recipe(
    metadata=_META,
    contract=PosteriorContrastInput,
    demo_contract=_demo,
)
def render(contract: PosteriorContrastInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 3.8))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    contrasts = list(contract.contrast_samples.keys())
    all_vals = np.concatenate(
        [np.asarray(v) for v in contract.contrast_samples.values()]
    )
    xlo, xhi = np.quantile(all_vals, [0.005, 0.995])
    span = xhi - xlo
    xg = np.linspace(xlo - 0.08 * span, xhi + 0.12 * span, 240)

    # Pre-compute densities for consistent stacking height.
    kdes = {k: gaussian_kde(np.asarray(v, float))
            for k, v in contract.contrast_samples.items()}
    max_dens = max(float(k(xg).max()) for k in kdes.values())

    y_step = 1.0
    # Zero reference across rows.
    ax.axvline(0, color="#888888", lw=0.7, ls="--", zorder=1)

    for i, name in enumerate(contrasts[::-1]):
        s = np.asarray(contract.contrast_samples[name], float)
        dens = kdes[name](xg)
        dens_s = (dens / max_dens) * 0.82 * y_step
        y_base = i * y_step
        color = palette[i % len(palette.colors)]

        # Split the fill at zero: above-zero vs below-zero emphasis.
        pos_mask = xg >= 0
        ax.fill_between(xg[~pos_mask], y_base, y_base + dens_s[~pos_mask],
                        color=color, alpha=0.30, linewidth=0, zorder=2)
        ax.fill_between(xg[pos_mask], y_base, y_base + dens_s[pos_mask],
                        color=color, alpha=0.68, linewidth=0, zorder=3)
        ax.plot(xg, y_base + dens_s, color=color, lw=0.9, zorder=4)

        # HDI bar + median.
        lo, hi = _hdi(s, contract.hdi_prob)
        ax.plot([lo, hi], [y_base - 0.07, y_base - 0.07],
                color="#222222", lw=1.3, zorder=5)
        med = float(np.median(s))
        ax.plot([med], [y_base - 0.07], marker="o", color="#222222",
                ms=3.5, zorder=6)

        # Contrast label (left-justified in data coords).
        ax.text(xg[0], y_base + 0.5 * 0.82,
                name, ha="right", va="center",
                fontsize=7.0, color="#222222")

        # P(Δ > 0) callout on the right.
        p_pos = float((s > 0).mean())
        ax.text(
            xhi + 0.06 * span, y_base + 0.02,
            f"Δ̃={smart_fmt(med)}\nP(Δ>0)={smart_fmt(p_pos)}",
            ha="left", va="center", fontsize=6.2, color=color,
        )

    ax.set_xlim(xlo - 0.18 * span, xhi + 0.26 * span)
    ax.set_ylim(-0.5, len(contrasts) - 0.05)
    ax.set_yticks([])
    ax.set_xlabel("Δ (contrast value)")
    ax.set_title(
        f"{contract.title}  ·  {int(contract.hdi_prob * 100)}% HDI",
        fontsize=9.0, pad=4,
    )
    for side in ("left",):
        ax.spines[side].set_visible(False)
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
