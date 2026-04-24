"""Per-condition ridge of Ca2+ event amplitudes.

Plots stacked density ridges of per-cell event amplitudes (ΔF/F peak),
one ridge per condition. A shared x-axis compares distributions; the
ridge height is density-normalised and each ridge is annotated with
median and N.
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


class AmplitudeRidgeInput(RecipeContract):
    amplitudes_by_condition: dict[str, list[float]] = Field(
        ..., description="condition → list of per-cell event amplitudes (ΔF/F)"
    )
    amplitude_label: str = r"event amplitude ($\Delta F/F$)"
    title: str = "Ca2+ event amplitudes"


def _demo() -> AmplitudeRidgeInput:
    rng = np.random.default_rng(131)
    return AmplitudeRidgeInput(
        amplitudes_by_condition={
            "baseline":  rng.gamma(3.0, 0.12, 320).tolist(),
            "KCl":       rng.gamma(3.5, 0.18, 340).tolist(),
            "TTX":       rng.gamma(2.0, 0.08, 280).tolist(),
            "washout":   rng.gamma(3.0, 0.14, 310).tolist(),
        },
    )


_META = RecipeMetadata(
    name="calcium_event_amplitude_distribution",
    modality="calcium_signaling",
    family=RecipeFamily.ridge_by_group,
    answers_question=(
        "Across cells, how are Ca2+ event amplitudes distributed, "
        "per condition?"
    ),
    required_fields=("amplitudes_by_condition",),
    optional_fields=("amplitude_label", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("event_frequency_by_condition",),
)


@register_recipe(
    metadata=_META,
    contract=AmplitudeRidgeInput,
    demo_contract=_demo,
)
def render(contract: AmplitudeRidgeInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 3.6))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    conditions = list(contract.amplitudes_by_condition.keys())
    all_vals = np.concatenate([
        np.asarray(v, float) for v in contract.amplitudes_by_condition.values()
    ])
    all_vals = all_vals[np.isfinite(all_vals) & (all_vals > 0)]
    xlo, xhi = np.quantile(all_vals, [0.005, 0.995])
    span = xhi - xlo
    xg = np.linspace(xlo - 0.05 * span, xhi + 0.05 * span, 240)

    # Pre-compute per-condition densities so they share a common max.
    dens_by_cond = {}
    for cond in conditions:
        vals = np.asarray(contract.amplitudes_by_condition[cond], float)
        vals = vals[np.isfinite(vals) & (vals > 0)]
        if vals.size < 5:
            continue
        kde = gaussian_kde(vals)
        dens_by_cond[cond] = (kde(xg), vals)
    max_density = max((d.max() for d, _ in dens_by_cond.values()), default=1.0)

    y_step = 1.0
    for i, cond in enumerate(conditions[::-1]):
        if cond not in dens_by_cond:
            continue
        dens, vals = dens_by_cond[cond]
        color = (palette[i % len(palette.colors)])
        y_base = i * y_step
        dens_s = (dens / max_density) * 0.85 * y_step
        ax.fill_between(xg, y_base, y_base + dens_s,
                        color=color, alpha=0.55, linewidth=0, zorder=3)
        ax.plot(xg, y_base + dens_s, color=color, lw=0.9, zorder=4)
        # Median marker.
        med = float(np.median(vals))
        ax.plot([med, med], [y_base - 0.04, y_base + 0.85 * 0.18],
                color="#111111", lw=1.2, zorder=5)
        ax.scatter([med], [y_base - 0.04], s=16, color="#111111",
                   zorder=6)
        # Left label.
        ax.text(xg[0], y_base + 0.4 * y_step, cond,
                ha="right", va="center", fontsize=7.0,
                color="#222222")
        # Right annotation.
        ax.text(xhi + 0.04 * span, y_base + 0.02,
                f"med={smart_fmt(med)}  n={vals.size}",
                ha="left", va="center", fontsize=6.2, color=color)

    ax.set_xlim(xlo - 0.18 * span, xhi + 0.22 * span)
    ax.set_ylim(-0.3, len(conditions) - 0.05)
    ax.set_yticks([])
    ax.set_xlabel(contract.amplitude_label)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    for side in ("left",):
        ax.spines[side].set_visible(False)
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
