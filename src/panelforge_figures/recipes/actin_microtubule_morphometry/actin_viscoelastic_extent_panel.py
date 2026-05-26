"""Actin viscoelastic extent per-cell strip + summary."""

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


class ActinExtentInput(RecipeContract):
    extent_um_by_group: dict[str, list[float]] = Field(
        description="group → per-cell actin viscoelastic extent (μm)"
    )
    title: str = "Actin viscoelastic extent"


def _demo() -> ActinExtentInput:
    import random
    rng = random.Random(42)
    return ActinExtentInput(
        extent_um_by_group={
            "WT": [rng.gauss(8.0, 3.0) for _ in range(7)],
            "LI": [rng.gauss(5.0, 2.5) for _ in range(16)],
        },
        title="Actin viscoelastic extent by genotype",
    )


_META = RecipeMetadata(
    name="actin_viscoelastic_extent_panel",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.coef_forest,
    answers_question="How does per-cell actin viscoelastic extent distribute by group?",
    required_fields=("extent_um_by_group",),
    optional_fields=("title",),
    file_format_hints=("csv", "json"),
    alternatives_in_modality=(),
)


@register_recipe(metadata=_META, contract=ActinExtentInput, demo_contract=_demo)
def render(contract: ActinExtentInput, ax=None, **_):
    import matplotlib.pyplot as plt
    import numpy as np
    from scipy import stats

    if ax is None:
        _, ax = plt.subplots(figsize=(7, 5))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    groups = list(contract.extent_um_by_group.keys())
    rng = np.random.default_rng(42)
    for i, g in enumerate(groups):
        vals = np.asarray(contract.extent_um_by_group[g], dtype=float)
        vals = vals[np.isfinite(vals)]
        if not len(vals):
            continue
        color = palette[i]
        x = np.full(len(vals), i) + rng.uniform(-0.13, 0.13, len(vals))
        ax.scatter(x, vals, s=44, color=color, edgecolor="white",
                   linewidth=0.8, alpha=0.85, label=f"{g} (n={len(vals)})")
        ax.plot([i - 0.25, i + 0.25], [np.median(vals), np.median(vals)], color=color, linewidth=2.2)

    ax.set_xticks(range(len(groups)))

    ax.set_xticklabels(groups, fontsize=9.6)
    ax.set_ylabel("Actin viscoelastic extent (μm)", fontsize=9.6)
    ax.set_xlim(-0.5, len(groups) - 0.5)
    title = contract.title
    if len(groups) == 2:
        a = np.asarray(contract.extent_um_by_group[groups[0]], dtype=float)
        b = np.asarray(contract.extent_um_by_group[groups[1]], dtype=float)
        a = a[np.isfinite(a)]
        b = b[np.isfinite(b)]
        if len(a) >= 2 and len(b) >= 2:
            t, p = stats.ttest_ind(a, b, equal_var=False)
            title = f"{title}  (Welch t={t:.2f}, p={p:.3g})"
    ax.set_title(title, fontsize=9.6, color="#2c3e50", pad=6)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(fontsize=9.0, frameon=False)
    return ax
