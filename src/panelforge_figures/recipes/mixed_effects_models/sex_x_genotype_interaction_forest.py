"""Sex × genotype interaction forest — canonical hierarchical-model output.

Draws a horizontal forest of fixed-effect estimates with 95% CIs. Terms
flagged as interactions (name contains ":") are highlighted with a thicker
stroke and a dark accent to immediately surface sex × genotype effects.
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


class ForestInput(RecipeContract):
    terms: list[str] = Field(..., min_length=2)
    estimates: list[float] = Field(...)
    ci_lo: list[float] = Field(...)
    ci_hi: list[float] = Field(...)
    interaction_mask: list[bool] | None = None
    title: str = "Fixed-effect estimates"
    x_label: str = "estimate (95% CI)"


def _demo() -> ForestInput:
    terms = [
        "Intercept",
        "sexF",
        "genotypeKO",
        "age_z",
        "treatment",
        "sexF:genotypeKO",
        "sexF:treatment",
        "genotypeKO:treatment",
    ]
    rng = np.random.default_rng(41)
    est = np.array([1.20, 0.10, -0.30, 0.05, 0.45, -0.58, 0.22, -0.15])
    se = rng.uniform(0.08, 0.18, est.size)
    lo = (est - 1.96 * se).tolist()
    hi = (est + 1.96 * se).tolist()
    interaction = [":" in t for t in terms]
    return ForestInput(
        terms=terms,
        estimates=est.tolist(),
        ci_lo=lo,
        ci_hi=hi,
        interaction_mask=interaction,
    )


_META = RecipeMetadata(
    name="sex_x_genotype_interaction_forest",
    modality="mixed_effects_models",
    family=RecipeFamily.coef_forest,
    answers_question="Which fixed effects and which sex × genotype interactions drive the outcome, and with what uncertainty?",
    required_fields=("terms", "estimates", "ci_lo", "ci_hi"),
    optional_fields=("interaction_mask", "title", "x_label"),
    file_format_hints=("csv", "parquet", "rds"),
    alternatives_in_modality=("random_effects_caterpillar", "emmeans_contrast_grid"),
)


@register_recipe(metadata=_META, contract=ForestInput, demo_contract=_demo)
def render(contract: ForestInput, ax=None, **_):
    """Horizontal forest with dashed zero line, right-side value labels."""
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.6))
    AESTHETIC.apply_to_ax(ax)

    palette = get_palette(AESTHETIC.primary_palette)
    term_color = palette[0]
    interaction_color = "#C62828"

    est = np.array(contract.estimates, dtype=float)
    lo = np.array(contract.ci_lo, dtype=float)
    hi = np.array(contract.ci_hi, dtype=float)
    n = len(contract.terms)
    ypos = np.arange(n)[::-1]     # top-to-bottom in user order
    is_inter = (
        np.array(contract.interaction_mask, dtype=bool)
        if contract.interaction_mask is not None
        else np.array([":" in t for t in contract.terms])
    )

    # Zero reference line.
    ax.axvline(0, color="#888888", lw=0.7, ls="--", zorder=1)

    # CI error bars + estimate markers.
    for y, e, l, h, inter in zip(ypos, est, lo, hi, is_inter):
        color = interaction_color if inter else term_color
        lw = 1.3 if inter else 1.0
        ax.plot([l, h], [y, y], color=color, lw=lw, zorder=3)
        # Caps on CI ends.
        for x_end in (l, h):
            ax.plot([x_end, x_end], [y - 0.15, y + 0.15],
                    color=color, lw=lw, zorder=3)
        ax.scatter([e], [y], s=30 if not inter else 48,
                   color=color, edgecolor="white", linewidth=0.9,
                   zorder=4)

    # Right-of-CI value labels — sign-independent position.
    xlo_axis, xhi_axis = ax.get_xlim()
    # Provisional xlim so labels can be placed cleanly; finalized below.
    span = max(hi.max() - lo.min(), 0.1)
    ax.set_xlim(lo.min() - 0.05 * span, hi.max() + 0.22 * span)
    xlo_axis, xhi_axis = ax.get_xlim()
    gap = 0.015 * (xhi_axis - xlo_axis)
    for y, e, h in zip(ypos, est, hi):
        ax.text(h + gap, y, smart_fmt(float(e)),
                ha="left", va="center", fontsize=6.8, color="#222222")

    ax.set_yticks(ypos)
    ax.set_yticklabels(contract.terms, fontsize=7.2)
    ax.set_xlabel(contract.x_label)
    ax.set_title(contract.title, fontsize=9.0, pad=4)

    # Interaction-row subtle highlight band.
    for y, inter in zip(ypos, is_inter):
        if inter:
            ax.axhspan(y - 0.40, y + 0.40, color=interaction_color,
                       alpha=0.06, zorder=0)

    # Legend hint (interaction vs fixed).
    ax.text(0.99, 0.99,
            "■ interaction  ■ main effect",
            transform=ax.transAxes, ha="right", va="top",
            fontsize=6.4, color="#444444",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=5)
    ax.grid(axis="x", color="#DDDDDD", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
