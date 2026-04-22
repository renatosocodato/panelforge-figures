"""Spatial permutation null distribution — observed test statistic vs
label-permutation null distribution, with empirical p-value.

Distinct from `ripley_l_function` (MC envelope on a curve): here the
statistic is a single scalar and the null is a histogram of
permutation outcomes.
"""

from __future__ import annotations

import numpy as np
from pydantic import Field
from scipy.stats import gaussian_kde

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class PermutationNullInput(RecipeContract):
    null_distribution: list[float] = Field(
        ..., min_length=50,
        description="null test statistics from label permutations",
    )
    observed_statistic: float = Field(
        ..., description="observed scalar test statistic"
    )
    statistic_name: str = "test statistic"
    alternative_conditions: dict[str, list[float]] | None = Field(
        None,
        description=(
            "optional: name → null distribution for a second / third "
            "comparison condition (ridge_by_group)"
        ),
    )
    title: str = "Permutation null distribution"


def _demo() -> PermutationNullInput:
    rng = np.random.default_rng(1811)
    # Null: Gaussian around 0.5. Observed: strongly above null.
    null = rng.normal(0.5, 0.08, 1000)
    obs = 0.82
    # Two alt conditions for a stacked view.
    alt = {
        "treated":    rng.normal(0.45, 0.10, 1000).tolist(),
        "rescue":     rng.normal(0.55, 0.07, 1000).tolist(),
    }
    return PermutationNullInput(
        null_distribution=null.tolist(),
        observed_statistic=obs,
        statistic_name="cross-type coloc (Jaccard)",
        alternative_conditions=alt,
    )


_META = RecipeMetadata(
    name="spatial_permutation_null_distribution",
    modality="spatial_statistics",
    family=RecipeFamily.ridge_by_group,
    answers_question=(
        "Given an observed spatial test statistic, how significant is "
        "it against a random label-permutation null distribution?"
    ),
    required_fields=("null_distribution", "observed_statistic"),
    optional_fields=("statistic_name", "alternative_conditions", "title"),
    file_format_hints=("csv",),
    alternatives_in_modality=("ripley_l_function",),
)


@register_recipe(
    metadata=_META,
    contract=PermutationNullInput,
    demo_contract=_demo,
)
def render(contract: PermutationNullInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.6))
    AESTHETIC.apply_to_ax(ax)

    null = np.asarray(contract.null_distribution, float)
    obs = float(contract.observed_statistic)
    alts = contract.alternative_conditions or {}

    # Build ridge stack: "null" first, then each alternative.
    labels = ["null"] + list(alts.keys())
    dists = [null] + [np.asarray(v, float) for v in alts.values()]
    all_vals = np.concatenate([null, obs * np.ones(1)] +
                              [np.asarray(v, float) for v in alts.values()])
    xg = np.linspace(float(all_vals.min()) - 0.05,
                     float(all_vals.max()) + 0.05, 240)
    kdes = [gaussian_kde(d) for d in dists]
    max_d = max(k(xg).max() for k in kdes)

    ridge_colors = ["#888888", "#1565C0", "#2E7D32", "#C62828", "#6A1B9A"]
    y_step = 1.0
    for i, (lab, d, kde) in enumerate(zip(labels[::-1],
                                          dists[::-1], kdes[::-1])):
        color = ridge_colors[(len(labels) - 1 - i) % len(ridge_colors)]
        dens = kde(xg)
        dens_s = (dens / max_d) * 0.85 * y_step
        y_base = i * y_step
        ax.fill_between(xg, y_base, y_base + dens_s, color=color,
                        alpha=0.55, linewidth=0, zorder=3)
        ax.plot(xg, y_base + dens_s, color=color, lw=0.8, zorder=4)
        # Mean marker.
        mean_v = float(np.mean(d))
        ax.scatter([mean_v], [y_base + 0.06],
                   s=22, marker="v", color=color,
                   edgecolor="white", linewidth=0.4, zorder=6)
        ax.text(xg[0], y_base + 0.45 * y_step, lab,
                ha="left", va="center", fontsize=7.0, color="#222222")

    # Observed statistic marker spanning all ridges.
    ax.axvline(obs, color="#111111", lw=1.2, zorder=5,
               label=f"observed = {smart_fmt(obs)}")
    # Empirical p (two-sided).
    p_right = float((null >= obs).sum() + 1) / (len(null) + 1)
    p_left = float((null <= obs).sum() + 1) / (len(null) + 1)
    p_emp = float(min(2 * min(p_right, p_left), 1.0))

    ax.set_xlim(xg.min(), xg.max())
    ax.set_ylim(-0.3, len(labels) - 0.1)
    ax.set_yticks([])
    ax.set_xlabel(contract.statistic_name)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="upper right",
              handlelength=1.2)

    ax.text(0.02, 0.97,
            f"N perms = {len(null)}   empirical p = {smart_fmt(p_emp)}",
            transform=ax.transAxes, ha="left", va="top",
            fontsize=6.4, color="#333333",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=7)

    for side in ("left",):
        ax.spines[side].set_visible(False)
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
