"""Sphericity × elongation hero scatter with marginal densities + convex hulls."""

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


class SphericityElongationInput(RecipeContract):
    sphericity: list[float] = Field(..., description="per-cell sphericity in [0, 1]")
    elongation: list[float] = Field(..., description="per-cell elongation (≥ 1)")
    condition: list[str] | None = None
    title: str = "Sphericity vs elongation"


def _demo() -> SphericityElongationInput:
    rng = np.random.default_rng(717)
    # Three populations occupying different regions of the shape plane.
    sph_c = rng.beta(6, 2, 80)            # roundish controls
    elo_c = 1.0 + rng.gamma(1.4, 0.35, 80)
    sph_m = rng.beta(2, 4, 80)            # elongated mutants
    elo_m = 1.2 + rng.gamma(2.8, 0.55, 80)
    sph_r = rng.beta(4, 3, 80)            # mid-phenotype rescue
    elo_r = 1.1 + rng.gamma(2.0, 0.45, 80)
    sphericity = np.concatenate([sph_c, sph_m, sph_r])
    elongation = np.concatenate([elo_c, elo_m, elo_r])
    condition = (["control"] * 80) + (["mutant"] * 80) + (["rescue"] * 80)
    return SphericityElongationInput(
        sphericity=sphericity.tolist(),
        elongation=elongation.tolist(),
        condition=condition,
    )


_META = RecipeMetadata(
    name="sphericity_vs_elongation_scatter",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "Where do cells sit in the (sphericity, elongation) shape plane, "
        "and how do condition groups separate?"
    ),
    required_fields=("sphericity", "elongation"),
    optional_fields=("condition", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("protrusion_length_velocity_joint",),
)


@register_recipe(
    metadata=_META,
    contract=SphericityElongationInput,
    demo_contract=_demo,
)
def render(contract: SphericityElongationInput, ax=None, **_):
    import matplotlib.pyplot as plt
    from scipy.spatial import ConvexHull

    if ax is None:
        fig = plt.figure(figsize=(5.2, 4.2))
    else:
        fig = ax.figure
        pos = ax.get_subplotspec()
        ax.remove()
        gs = pos.subgridspec(2, 2, width_ratios=[4, 1], height_ratios=[1, 4],
                             wspace=0.04, hspace=0.04)
        ax_top = fig.add_subplot(gs[0, 0])
        ax_right = fig.add_subplot(gs[1, 1])
        ax = fig.add_subplot(gs[1, 0])
        AESTHETIC.apply_to_ax(ax)
    if "ax_top" not in dir():
        gs = fig.add_gridspec(2, 2, width_ratios=[4, 1], height_ratios=[1, 4],
                              wspace=0.04, hspace=0.04)
        ax_top = fig.add_subplot(gs[0, 0])
        ax_right = fig.add_subplot(gs[1, 1])
        ax = fig.add_subplot(gs[1, 0])
        AESTHETIC.apply_to_ax(ax)

    palette = get_palette(AESTHETIC.primary_palette)
    sph = np.asarray(contract.sphericity, float)
    elo = np.asarray(contract.elongation, float)
    cond = (np.asarray(contract.condition)
            if contract.condition is not None
            else np.array(["all"] * sph.size))
    uniques = list(dict.fromkeys(cond.tolist()))

    # Main scatter + convex hulls per condition.
    for i, name in enumerate(uniques):
        m = cond == name
        color = palette[i % len(palette.colors)]
        ax.scatter(sph[m], elo[m], s=14, color=color, alpha=0.65,
                   edgecolor="white", linewidth=0.3, zorder=3,
                   label=f"{name} (n={int(m.sum())})")
        pts = np.column_stack([sph[m], elo[m]])
        if pts.shape[0] >= 3:
            try:
                hull = ConvexHull(pts)
                verts = pts[hull.vertices]
                verts = np.vstack([verts, verts[0]])
                ax.plot(verts[:, 0], verts[:, 1], color=color, lw=1.1,
                        alpha=0.75, zorder=4)
            except Exception:
                pass

    # Regression line across all points.
    slope, intercept = np.polyfit(sph, elo, 1)
    xs = np.linspace(float(sph.min()), float(sph.max()), 100)
    ax.plot(xs, slope * xs + intercept, color="#111111", lw=1.1, ls="--",
            zorder=5, label=f"fit (slope = {smart_fmt(float(slope))})")

    # Marginal densities.
    for i, name in enumerate(uniques):
        m = cond == name
        color = palette[i % len(palette.colors)]
        ax_top.hist(sph[m], bins=24, density=True, color=color, alpha=0.45,
                    edgecolor="white", linewidth=0.3, histtype="stepfilled")
        ax_right.hist(elo[m], bins=24, density=True, color=color, alpha=0.45,
                      edgecolor="white", linewidth=0.3,
                      histtype="stepfilled", orientation="horizontal")

    for a in (ax_top, ax_right):
        a.set_xticks([])
        a.set_yticks([])
        for side in ("top", "right", "left", "bottom"):
            a.spines[side].set_visible(False)

    ax.set_xlabel("sphericity")
    ax.set_ylabel("elongation")
    ax.legend(fontsize=6.6, frameon=False, loc="upper right",
              handlelength=1.4)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    ax_top.set_title(contract.title, fontsize=9.0, pad=4)
    return ax
