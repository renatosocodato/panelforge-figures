"""Actin protrusion count per-cell strip summary."""

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


class ActinProtrusionCountInput(RecipeContract):
    counts_by_group: dict[str, list[int]] = Field(
        description="group → per-cell protrusion count"
    )
    breakdown_by_group: dict[str, dict[str, list[int]]] | None = Field(
        default=None,
        description="Optional group → {kind: per-cell counts} for lamellipodia/filopodia breakdown"
    )
    title: str = "Actin protrusion count"


def _demo() -> ActinProtrusionCountInput:
    return ActinProtrusionCountInput(
        counts_by_group={
            "WT": [5, 7, 6, 8, 5, 9, 6],
            "LI": [3, 4, 5, 4, 3, 5, 6, 4, 5, 3, 4, 4, 5, 3, 4, 5],
        },
        title="Per-cell protrusion count by genotype",
    )


_META = RecipeMetadata(
    name="actin_protrusion_count_panel",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.coef_forest,
    answers_question="How does per-cell protrusion count distribute by group?",
    required_fields=("counts_by_group",),
    optional_fields=("breakdown_by_group", "title"),
    file_format_hints=("csv", "json"),
    alternatives_in_modality=(),
)


@register_recipe(metadata=_META, contract=ActinProtrusionCountInput, demo_contract=_demo)
def render(contract: ActinProtrusionCountInput, ax=None, **_):
    import matplotlib.pyplot as plt
    import numpy as np
    from scipy import stats

    if ax is None:
        _, ax = plt.subplots(figsize=(7, 5))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    groups = list(contract.counts_by_group.keys())
    rng = np.random.default_rng(42)
    for i, g in enumerate(groups):
        vals = np.asarray(contract.counts_by_group[g], dtype=float)
        vals = vals[np.isfinite(vals)]
        if not len(vals):
            continue
        color = palette[i]
        x = np.full(len(vals), i) + rng.uniform(-0.13, 0.13, len(vals))
        ax.scatter(x, vals, s=46, color=color, edgecolor="white",
                   linewidth=0.8, alpha=0.85, label=f"{g} (n={len(vals)})")
        ax.plot([i - 0.25, i + 0.25], [np.median(vals), np.median(vals)], color=color, linewidth=2.2)

    ax.set_xticks(range(len(groups)))

    ax.set_xticklabels(groups, fontsize=9.6)
    ax.set_ylabel("Protrusion count per cell", fontsize=9.6)
    ax.set_xlim(-0.5, len(groups) - 0.5)
    title = contract.title
    if len(groups) == 2:
        a = np.asarray(contract.counts_by_group[groups[0]], dtype=float)
        b = np.asarray(contract.counts_by_group[groups[1]], dtype=float)
        if len(a) >= 2 and len(b) >= 2:
            u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
            title = f"{title}  (Mann-Whitney U={u:.0f}, p={p:.3g})"
    ax.set_title(title, fontsize=9.6, color="#2c3e50", pad=6)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(fontsize=9.0, frameon=False)
    return ax
