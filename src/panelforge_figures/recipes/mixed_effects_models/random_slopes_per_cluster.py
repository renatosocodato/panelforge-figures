"""Random slopes per cluster — spaghetti of per-animal fitted lines + pop mean."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
)
from ._aesthetic import AESTHETIC


class RandomSlopesInput(RecipeContract):
    x: list[float] = Field(...)
    cluster_lines: dict[str, list[float]] = Field(
        ..., description="cluster_id → y values aligned to x"
    )
    population_mean: list[float] | None = None
    x_label: str = "predictor"
    y_label: str = "outcome"
    title: str = "Random slopes per cluster"


def _demo() -> RandomSlopesInput:
    rng = np.random.default_rng(61)
    x = np.linspace(-2, 2, 30)
    lines: dict[str, list[float]] = {}
    for k in range(24):
        b0 = rng.normal(0.3, 0.4)
        b1 = rng.normal(0.55, 0.22)
        y = b0 + b1 * x + rng.normal(0, 0.06, x.size)
        lines[f"A{k+1:02d}"] = y.tolist()
    pop = (0.3 + 0.55 * x).tolist()
    return RandomSlopesInput(
        x=x.tolist(),
        cluster_lines=lines,
        population_mean=pop,
        x_label="age (z)",
        y_label="process length",
        title="Per-animal fitted lines",
    )


_META = RecipeMetadata(
    name="random_slopes_per_cluster",
    modality="mixed_effects_models",
    family=RecipeFamily.timecourse_hierarchical_ci,
    answers_question="How much do individual clusters (animals, subjects) differ in their slope on the predictor?",
    required_fields=("x", "cluster_lines"),
    optional_fields=("population_mean", "x_label", "y_label", "title"),
    file_format_hints=("csv", "rds"),
    alternatives_in_modality=("random_effects_caterpillar",),
)


@register_recipe(metadata=_META, contract=RandomSlopesInput, demo_contract=_demo)
def render(contract: RandomSlopesInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.2))
    AESTHETIC.apply_to_ax(ax)

    palette = get_palette(AESTHETIC.primary_palette)
    accent = palette[0]
    x = np.array(contract.x, dtype=float)

    # Thin spaghetti lines per cluster.
    n = len(contract.cluster_lines)
    for y in contract.cluster_lines.values():
        ax.plot(x, np.asarray(y, float), color=accent,
                lw=0.5, alpha=0.25, zorder=2)

    # Population mean — bold black dashed.
    if contract.population_mean is not None:
        ax.plot(x, np.asarray(contract.population_mean, float),
                color="#111111", lw=1.4, ls="--", zorder=4,
                label="population mean")

    ax.set_xlabel(contract.x_label)
    ax.set_ylabel(contract.y_label)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    if contract.population_mean is not None:
        ax.legend(fontsize=6.8, frameon=False, loc="upper left",
                  handlelength=2.0)

    ax.text(0.99, 0.02,
            f"N clusters = {n}",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=6.4, color="#444444",
            bbox=dict(boxstyle="round,pad=0.20", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=5)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
