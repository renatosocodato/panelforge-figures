"""Per-cell strip summary — one continuous measurement, stratified by genotype.

Covers panel slots that need a clean per-cell view of a single biophysical
quantity (e.g. z-span, viscoelastic extent, protrusion count) with genotype
strip + median bar + Welch-t test stat box.
"""

from __future__ import annotations

from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
)
from ._aesthetic import AESTHETIC


class PerCellStripInput(RecipeContract):
    values_by_group: dict[str, list[float]] = Field(
        description="group label → list of per-cell values"
    )
    y_label: str = "value"
    title: str = "Per-cell strip summary"
    show_welch_t: bool = True
    threshold: float | None = Field(default=None, description="Optional horizontal reference line")
    threshold_label: str = "threshold"


def _demo() -> PerCellStripInput:
    import random
    rng = random.Random(42)
    return PerCellStripInput(
        values_by_group={
            "WT": [rng.gauss(0.30, 0.04) for _ in range(7)],
            "LI": [rng.gauss(0.34, 0.07) for _ in range(16)],
        },
        y_label="MT z-span (μm)",
        title="z-span by genotype",
        show_welch_t=True,
    )


_META = RecipeMetadata(
    name="per_cell_strip_summary",
    modality="biophysics_scaling",
    family=RecipeFamily.coef_forest,
    answers_question="How does a per-cell biophysical measurement distribute by group?",
    required_fields=("values_by_group",),
    optional_fields=("y_label", "title", "show_welch_t", "threshold", "threshold_label"),
    file_format_hints=("csv", "json"),
    alternatives_in_modality=(
        "persistence_length_lp_with_equivalence_bounds",
        "confinement_ratio_distribution_by_genotype",
        "compartment_paired_delta_scatter",
    ),
)


@register_recipe(metadata=_META, contract=PerCellStripInput, demo_contract=_demo)
def render(contract: PerCellStripInput, ax=None, **_):
    import matplotlib.pyplot as plt
    import numpy as np
    from scipy import stats

    if ax is None:
        _, ax = plt.subplots(figsize=(7, 5))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    groups = list(contract.values_by_group.keys())
    rng = np.random.default_rng(42)
    for i, g in enumerate(groups):
        vals = np.asarray(contract.values_by_group[g], dtype=float)
        vals = vals[np.isfinite(vals)]
        if len(vals) == 0:
            continue
        color = palette[i]
        x = np.full(len(vals), i) + rng.uniform(-0.13, 0.13, len(vals))
        ax.scatter(x, vals, s=48, color=color, edgecolor="white",
                   linewidth=0.8, alpha=0.85, label=g, zorder=3)
        ax.plot([i - 0.25, i + 0.25], [np.median(vals), np.median(vals)], color=color, linewidth=2.4, zorder=4)

    ax.set_xticks(range(len(groups)))
    ax.set_xticklabels(groups, fontsize=9.6)
    ax.set_ylabel(contract.y_label, fontsize=9.6)
    ax.set_xlim(-0.5, len(groups) - 0.5)

    if contract.threshold is not None:
        ax.axhline(contract.threshold, ls=":", color="#777", lw=1.0,
                   label=contract.threshold_label, zorder=2)

    title = contract.title
    if contract.show_welch_t and len(groups) == 2:
        a = np.asarray(contract.values_by_group[groups[0]], dtype=float)
        b = np.asarray(contract.values_by_group[groups[1]], dtype=float)
        a = a[np.isfinite(a)]
        b = b[np.isfinite(b)]
        if len(a) >= 2 and len(b) >= 2:
            t, p = stats.ttest_ind(a, b, equal_var=False)
            title = f"{title}  (Welch t={t:.2f}, p={p:.3g})"

    ax.set_title(title, fontsize=9.6, color="#2c3e50", pad=6)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(fontsize=9.0, frameon=False, loc="best")
    return ax
