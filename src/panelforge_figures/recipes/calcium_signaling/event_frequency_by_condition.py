"""Event frequency by condition — per-cell rates as violins + overlaid medians."""

from __future__ import annotations

import numpy as np
from pydantic import Field
from scipy import stats

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class EventFreqInput(RecipeContract):
    rates_by_condition: dict[str, list[float]] = Field(
        ..., description="condition → per-cell rates (Hz)"
    )
    title: str = "Event frequency by condition"


def _demo() -> EventFreqInput:
    rng = np.random.default_rng(229)
    return EventFreqInput(
        rates_by_condition={
            "baseline": rng.lognormal(-1.6, 0.5, 60).tolist(),
            "LPS 1h":   rng.lognormal(-0.6, 0.5, 60).tolist(),
            "LPS 4h":   rng.lognormal(-0.2, 0.45, 60).tolist(),
            "LPS + ROCKi": rng.lognormal(-1.1, 0.5, 60).tolist(),
        },
    )


_META = RecipeMetadata(
    name="event_frequency_by_condition",
    modality="calcium_signaling",
    family=RecipeFamily.split_violin,
    answers_question="How does the per-cell Ca²⁺ event frequency change across experimental conditions?",
    required_fields=("rates_by_condition",),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("event_raster_with_rate",),
)


@register_recipe(metadata=_META, contract=EventFreqInput, demo_contract=_demo)
def render(contract: EventFreqInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)
    color_cycle = [palette.pick("homeostatic"), palette.pick("activated"),
                   palette.pick("proliferative"), palette.pick("surveillant")]

    conditions = list(contract.rates_by_condition.keys())
    positions = list(range(len(conditions)))
    data = [np.array(contract.rates_by_condition[c], float) for c in conditions]

    parts = ax.violinplot(data, positions=positions, widths=0.72,
                          showmeans=False, showmedians=False, showextrema=False)
    for i, pc in enumerate(parts["bodies"]):
        color = color_cycle[i % len(color_cycle)]
        pc.set_facecolor(color)
        pc.set_edgecolor("#333333")
        pc.set_alpha(0.55)
        pc.set_linewidth(0.6)

    # Quartile segments and medians.
    for pos, vals in zip(positions, data):
        if vals.size < 4:
            continue
        q1, med, q3 = np.quantile(vals, [0.25, 0.5, 0.75])
        ax.plot([pos, pos], [q1, q3], color="black", lw=3.0,
                solid_capstyle="butt", zorder=4)
        ax.scatter([pos], [med], s=36, facecolor="white",
                   edgecolor="black", linewidth=1.0, zorder=5)

    # Extend top y so significance annotations never crowd the title.
    ymax_data = max(float(np.max(v)) if v.size else 0.0 for v in data)
    ax.set_ylim(top=ymax_data * 1.25)

    # Pairwise Mann-Whitney vs first condition.
    ref = data[0]
    for pos, vals in zip(positions[1:], data[1:]):
        if vals.size < 5 or ref.size < 5:
            continue
        _, p = stats.mannwhitneyu(ref, vals)
        star = "**" if p < 1e-3 else "*" if p < 0.05 else "ns"
        ax.text(pos, max(vals) * 1.05, f"{star}  p={smart_fmt(p)}",
                ha="center", va="bottom", fontsize=6.2, color="#333333")

    ax.set_xticks(positions)
    ax.set_xticklabels(conditions, fontsize=7.0)
    ax.set_ylabel("event rate (Hz)")
    ax.set_title(contract.title, fontsize=9.0, pad=8)
    ax.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    # Show N per condition.
    for pos, vals in zip(positions, data):
        ax.text(pos, ax.get_ylim()[0] if False else -0.02 * ax.get_ylim()[1],
                f"N = {vals.size}",
                ha="center", va="top", fontsize=6.2, color="#666666",
                transform=ax.get_xaxis_transform())
    return ax
