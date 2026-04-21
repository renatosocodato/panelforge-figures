"""Pathway-flux streamgraph — stacked normalised flux over time."""

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


class PathwayStreamInput(RecipeContract):
    time: list[float] = Field(..., min_length=3)
    pathway_flux: dict[str, list[float]] = Field(
        ..., description="pathway → flux(t), same length as time"
    )
    normalise: bool = True
    time_label: str = "time"
    title: str = "Pathway flux streamgraph"


def _demo() -> PathwayStreamInput:
    t = np.linspace(0, 60, 50)
    pathways = {
        "OXPHOS":      1.2 * np.exp(-((t - 5) / 10) ** 2) + 0.2,
        "glycolysis":  0.9 * np.exp(-((t - 20) / 8) ** 2) + 0.2,
        "NFkB":        1.4 * np.exp(-((t - 35) / 9) ** 2) + 0.2,
        "autophagy":   0.8 * np.exp(-((t - 45) / 7) ** 2) + 0.2,
        "ER stress":   0.6 + 0.4 * np.sin(t / 9),
    }
    return PathwayStreamInput(
        time=t.tolist(),
        pathway_flux={k: v.tolist() for k, v in pathways.items()},
    )


_META = RecipeMetadata(
    name="pathway_flux_streamgraph",
    modality="network_and_pathway",
    family=RecipeFamily.timecourse_hierarchical_ci,
    answers_question=(
        "How does pathway-activity flux redistribute across pathways "
        "over time?"
    ),
    required_fields=("time", "pathway_flux"),
    optional_fields=("normalise", "time_label", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("pathway_flux_sankey_like",),
)


@register_recipe(
    metadata=_META,
    contract=PathwayStreamInput,
    demo_contract=_demo,
)
def render(contract: PathwayStreamInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.8, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    t = np.asarray(contract.time, float)
    pathways = list(contract.pathway_flux.keys())
    values = np.asarray(
        [contract.pathway_flux[p] for p in pathways], float
    )  # n_pathways × n_time
    if contract.normalise:
        col_sum = values.sum(axis=0)
        col_sum = np.where(col_sum > 0, col_sum, 1.0)
        values = values / col_sum

    # Streamgraph via symmetric centering.
    total = values.sum(axis=0)
    base = -total / 2
    top = base.copy()
    # Mean trace across all pathways (Line2D for family rule).
    ax.plot(t, total / 2, color="#111111", lw=0.8, ls="--",
            alpha=0.55, zorder=3, label="half-envelope")

    for i, p in enumerate(pathways):
        color = palette[i % len(palette.colors)]
        layer = values[i]
        ax.fill_between(t, top, top + layer, color=color, alpha=0.80,
                        linewidth=0, zorder=2, label=p)
        top = top + layer

    ax.set_xlabel(contract.time_label)
    y_lab = "flux share" if contract.normalise else "flux (a.u.)"
    ax.set_ylabel(y_lab)
    ax.set_xlim(t.min(), t.max())
    # Dominant-pathway-per-window callout.
    splits = np.array_split(np.arange(values.shape[1]), 3)
    bits = []
    for sp in splits:
        if sp.size == 0:
            continue
        dominant = int(np.argmax(values[:, sp].mean(axis=1)))
        a, b = float(t[sp[0]]), float(t[sp[-1]])
        bits.append(f"[{smart_fmt(a)}, {smart_fmt(b)}]: {pathways[dominant]}")

    ax.set_title(
        f"{contract.title}  ·  {len(pathways)} pathways",
        fontsize=9.0, pad=4,
    )
    ax.legend(fontsize=6.4, frameon=False, loc="center left",
              bbox_to_anchor=(1.02, 0.5), handlelength=1.2)
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    fig = ax.figure
    fig.text(
        0.5, -0.16,
        "dominant per window: " + "   ·   ".join(bits),
        ha="center", va="top", fontsize=6.4, color="#333333",
        transform=ax.transAxes,
        bbox=dict(boxstyle="round,pad=0.22", fc="white",
                  ec="#BBBBBB", lw=0.5, alpha=0.92),
    )
    return ax
