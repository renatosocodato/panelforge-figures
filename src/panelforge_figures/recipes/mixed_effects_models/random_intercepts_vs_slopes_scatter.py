"""Per-cluster random (intercept, slope) scatter with shrinkage ellipse.

Captures the `cor(int, slope)` term of a random-slopes model: each point
is a cluster (animal, batch) in (intercept, slope) space, sized by cluster
n, with a whole-population shrinkage ellipse and marginal rug densities.
Lines through the two axis zeros help call out the cluster quadrants.
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


class RandomIntSlopeInput(RecipeContract):
    cluster_ids: list[str] = Field(..., min_length=4)
    intercepts: list[float] = Field(...)
    slopes: list[float] = Field(...)
    n_per_cluster: list[int] | None = Field(
        None, description="observations per cluster (sets marker size)"
    )
    grouping: str = "animal"
    title: str = "Random (intercept, slope) per cluster"


def _demo() -> RandomIntSlopeInput:
    rng = np.random.default_rng(221)
    n = 32
    ints = rng.normal(0, 0.32, n)
    slps = 0.35 * ints + rng.normal(0, 0.18, n)
    return RandomIntSlopeInput(
        cluster_ids=[f"A{i+1:02d}" for i in range(n)],
        intercepts=ints.tolist(),
        slopes=slps.tolist(),
        n_per_cluster=rng.integers(18, 62, n).tolist(),
        grouping="animal",
    )


_META = RecipeMetadata(
    name="random_intercepts_vs_slopes_scatter",
    modality="mixed_effects_models",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "Per cluster, how do random intercept and random slope covary — "
        "do fast-baseline clusters also respond more steeply?"
    ),
    required_fields=("cluster_ids", "intercepts", "slopes"),
    optional_fields=("n_per_cluster", "grouping", "title"),
    file_format_hints=("csv", "rds"),
    alternatives_in_modality=(
        "random_effects_caterpillar",
        "random_slopes_per_cluster",
    ),
)


@register_recipe(
    metadata=_META,
    contract=RandomIntSlopeInput,
    demo_contract=_demo,
)
def render(contract: RandomIntSlopeInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.8))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    ints = np.asarray(contract.intercepts, float)
    slps = np.asarray(contract.slopes, float)
    ns = (np.asarray(contract.n_per_cluster, float)
          if contract.n_per_cluster is not None
          else np.full(ints.size, 30.0))
    # Normalise marker sizes to a legible 10-54 range.
    if ns.max() > ns.min():
        sizes = 10 + 44 * (ns - ns.min()) / (ns.max() - ns.min())
    else:
        sizes = np.full(ns.size, 22.0)

    # Zero cross-hair.
    ax.axhline(0, color="#888888", lw=0.7, ls="--", zorder=1)
    ax.axvline(0, color="#888888", lw=0.7, ls="--", zorder=1)

    # Color by quadrant of (int, slope) sign.
    colors = []
    for b, s in zip(ints, slps):
        if b >= 0 and s >= 0:
            colors.append(palette.pick("F_WT") if "F_WT" in palette.semantic else palette[0])
        elif b < 0 and s >= 0:
            colors.append(palette.pick("M_WT") if "M_WT" in palette.semantic else palette[1])
        elif b >= 0 and s < 0:
            colors.append(palette.pick("F_KO") if "F_KO" in palette.semantic else palette[2])
        else:
            colors.append(palette.pick("M_KO") if "M_KO" in palette.semantic else palette[3])

    ax.scatter(ints, slps, s=sizes, c=colors, alpha=0.82,
               edgecolor="white", linewidth=0.5, zorder=3)

    # Shrinkage ellipse — 95% coverage of the joint (int, slope) cloud.
    mean = np.array([ints.mean(), slps.mean()])
    cov = np.cov(np.stack([ints, slps]))
    vals, vecs = np.linalg.eigh(cov)
    order = np.argsort(vals)[::-1]
    vals, vecs = vals[order], vecs[:, order]
    theta = np.degrees(np.arctan2(vecs[1, 0], vecs[0, 0]))
    width = 2.0 * np.sqrt(5.991 * max(vals[0], 1e-9))
    height = 2.0 * np.sqrt(5.991 * max(vals[1], 1e-9))
    from matplotlib.patches import Ellipse
    ax.add_patch(Ellipse(
        mean, width=width, height=height, angle=theta,
        facecolor="none", edgecolor="#444444",
        linewidth=1.1, linestyle="--", zorder=4,
    ))

    # OLS fit line through the cloud for the visible int-slope correlation.
    if ints.std() > 0:
        m, b_ = np.polyfit(ints, slps, 1)
        xs = np.linspace(ints.min(), ints.max(), 50)
        ax.plot(xs, m * xs + b_, color="#222222", lw=0.9,
                alpha=0.75, zorder=3, label=f"slope = {smart_fmt(m)}")

    r = float(np.corrcoef(ints, slps)[0, 1]) if ints.std() > 0 else 0.0
    ax.set_xlabel(f"random intercept ({contract.grouping})")
    ax.set_ylabel(f"random slope ({contract.grouping})")
    ax.set_title(f"{contract.title}  ·  r = {smart_fmt(r)}",
                 fontsize=9.0, pad=4)

    # Legend pill — quadrant semantics.
    ax.text(
        0.02, 0.97,
        f"n clusters = {ints.size}\ncircle size ~ obs / cluster",
        transform=ax.transAxes, ha="left", va="top",
        fontsize=6.4, color="#333333",
        bbox=dict(boxstyle="round,pad=0.22", fc="white",
                  ec="#BBBBBB", lw=0.5, alpha=0.92),
        zorder=6,
    )
    ax.legend(fontsize=6.6, frameon=False, loc="lower right",
              handlelength=1.4)
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
