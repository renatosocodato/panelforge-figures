"""Voronoi cell-area distribution — per-condition ridge stack of cell
territory-area distributions with mean markers.

Distinct from `voronoi_territory_map` (spatial map of cells, no
distribution).
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


class VoronoiAreasInput(RecipeContract):
    areas_by_condition: dict[str, list[float]] = Field(
        ..., description="condition → list of Voronoi cell areas (μm²)"
    )
    title: str = "Voronoi cell-area distribution"


def _demo() -> VoronoiAreasInput:
    rng = np.random.default_rng(1511)
    return VoronoiAreasInput(
        areas_by_condition={
            "control":    rng.lognormal(3.0, 0.45, 300).tolist(),
            "LPS":        rng.lognormal(2.7, 0.55, 300).tolist(),
            "rescue":     rng.lognormal(3.1, 0.40, 300).tolist(),
        },
    )


_META = RecipeMetadata(
    name="voronoi_area_distribution",
    modality="spatial_statistics",
    family=RecipeFamily.ridge_by_group,
    answers_question=(
        "How are per-cell Voronoi territory areas distributed, and "
        "does the distribution shift across conditions?"
    ),
    required_fields=("areas_by_condition",),
    optional_fields=("title",),
    file_format_hints=("csv",),
    alternatives_in_modality=("voronoi_territory_map",),
)


@register_recipe(
    metadata=_META,
    contract=VoronoiAreasInput,
    demo_contract=_demo,
)
def render(contract: VoronoiAreasInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    conditions = list(contract.areas_by_condition.keys())
    all_vals = np.concatenate([
        np.asarray(contract.areas_by_condition[c], float)
        for c in conditions
    ])
    # Log-space x for areas.
    log_vals = np.log10(np.clip(all_vals, 1e-6, None))
    xg = np.linspace(log_vals.min(), log_vals.max(), 240)

    kdes = {c: gaussian_kde(
        np.log10(np.clip(np.asarray(contract.areas_by_condition[c], float),
                         1e-6, None)))
            for c in conditions}
    max_d = max(k(xg).max() for k in kdes.values())

    y_step = 1.0
    for i, c in enumerate(conditions[::-1]):
        color = palette[(len(conditions) - 1 - i) % len(palette.colors)]
        vals = np.asarray(contract.areas_by_condition[c], float)
        log_v = np.log10(np.clip(vals, 1e-6, None))
        dens = kdes[c](xg)
        dens_s = (dens / max_d) * 0.85 * y_step
        y_base = i * y_step
        ax.fill_between(xg, y_base, y_base + dens_s, color=color,
                        alpha=0.55, linewidth=0, zorder=3)
        ax.plot(xg, y_base + dens_s, color=color, lw=0.8, zorder=4)

        med_v = float(np.median(vals))
        mean_v = float(np.mean(vals))
        ax.scatter([np.log10(med_v)], [y_base + 0.08],
                   s=22, marker="v", color=color,
                   edgecolor="white", linewidth=0.4, zorder=6)
        ax.text(xg[0], y_base + 0.45 * y_step, c,
                ha="left", va="center", fontsize=7.0, color="#222222")
        ax.text(xg[-1] * 0.98, y_base + 0.82 * y_step,
                f"med {smart_fmt(med_v)} μm²   mean {smart_fmt(mean_v)}",
                ha="right", va="top", fontsize=6.4, color=color)

    ax.set_xlim(xg.min(), xg.max())
    ax.set_ylim(-0.3, len(conditions) - 0.1)
    ax.set_yticks([])
    # Display original μm² values on tick labels.
    tick_decades = np.arange(int(np.floor(xg.min())),
                             int(np.ceil(xg.max())) + 1)
    ax.set_xticks(tick_decades)
    ax.set_xticklabels([f"$10^{{{int(t)}}}$" for t in tick_decades])
    ax.set_xlabel("Voronoi cell area (μm²)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)

    for side in ("left",):
        ax.spines[side].set_visible(False)
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
