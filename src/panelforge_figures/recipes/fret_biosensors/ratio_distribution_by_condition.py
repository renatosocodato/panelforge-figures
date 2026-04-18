"""Ratio distribution by condition — ridge-style KDE overlay."""

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


class RatioDistInput(RecipeContract):
    ratios_by_condition: dict[str, list[float]] = Field(
        ..., description="condition -> per-cell ratios"
    )
    title: str = "Ratio distribution by condition"


def _demo() -> RatioDistInput:
    rng = np.random.default_rng(197)
    return RatioDistInput(
        ratios_by_condition={
            "vehicle": rng.normal(1.00, 0.07, 400).tolist(),
            "FSK 5 μM": rng.normal(1.35, 0.12, 400).tolist(),
            "FSK 50 μM": rng.normal(1.70, 0.14, 400).tolist(),
            "FSK 50 μM + H89": rng.normal(1.15, 0.10, 400).tolist(),
        },
    )


_META = RecipeMetadata(
    name="ratio_distribution_by_condition",
    modality="fret_biosensors",
    family=RecipeFamily.ridge_by_group,
    answers_question="How does the per-cell FRET-ratio distribution shift across experimental conditions?",
    required_fields=("ratios_by_condition",),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("single_cell_ratio_trajectories",),
)


@register_recipe(metadata=_META, contract=RatioDistInput, demo_contract=_demo)
def render(contract: RatioDistInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)
    fallback = [palette.pick("donor"), palette.pick("acceptor"),
                palette.pick("ratio_up"), palette.pick("ratio_down")]

    conditions = list(contract.ratios_by_condition.keys())
    all_vals = np.concatenate([
        np.array(contract.ratios_by_condition[c], float)
        for c in conditions
    ])
    xlo, xhi = np.quantile(all_vals, [0.005, 0.995])
    span = xhi - xlo
    xg = np.linspace(xlo - 0.05 * span, xhi + 0.05 * span, 240)

    # Compute all KDEs first to normalize.
    kdes = {c: gaussian_kde(np.array(contract.ratios_by_condition[c], float))
            for c in conditions}
    max_d = max(k(xg).max() for k in kdes.values())

    # Ratio-neutral reference.
    ax.axvline(1.0, color="#AAAAAA", lw=0.5, ls="--", zorder=1)

    y_step = 1.0
    for i, c in enumerate(conditions[::-1]):
        color = fallback[(len(conditions) - 1 - i) % len(fallback)]
        dens = kdes[c](xg)
        dens_s = (dens / max_d) * 0.85 * y_step
        y_base = i * y_step
        ax.fill_between(xg, y_base, y_base + dens_s,
                        color=color, alpha=0.55, linewidth=0, zorder=3)
        ax.plot(xg, y_base + dens_s, color=color, lw=0.8, zorder=4)

        # Label on the left, median value on the right.
        vals = np.array(contract.ratios_by_condition[c], float)
        ax.text(xg[0], y_base + 0.4 * y_step, c,
                ha="right", va="center", fontsize=7.0, color="#222222")
        ax.text(xhi + 0.03 * span, y_base + 0.02,
                f"med = {smart_fmt(float(np.median(vals)))}",
                ha="left", va="center", fontsize=6.6, color=color)

    ax.set_xlim(xlo - 0.15 * span, xhi + 0.20 * span)
    ax.set_ylim(-0.3, len(conditions) - 0.1)
    ax.set_yticks([])
    ax.set_xlabel(r"F$_\mathrm{A}$/F$_\mathrm{D}$")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    for side in ("left",):
        ax.spines[side].set_visible(False)
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
