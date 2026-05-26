"""Cortex competence composites — multi-index radar / parallel coordinates."""

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


class CortexCompetenceInput(RecipeContract):
    indices_by_group_by_cell: dict[str, dict[str, list[float]]] = Field(
        description="group → {index_name: per-cell value list}"
    )
    index_order: list[str] | None = None
    title: str = "Cortex competence composites"


def _demo() -> CortexCompetenceInput:
    import random
    rng = random.Random(42)
    return CortexCompetenceInput(
        indices_by_group_by_cell={
            "WT": {
                "AAI": [rng.gauss(0.65, 0.1) for _ in range(7)],
                "SGI": [rng.gauss(0.55, 0.12) for _ in range(7)],
                "CRI": [rng.gauss(0.70, 0.08) for _ in range(7)],
                "LFI": [rng.gauss(0.42, 0.10) for _ in range(7)],
            },
            "LI": {
                "AAI": [rng.gauss(0.50, 0.15) for _ in range(16)],
                "SGI": [rng.gauss(0.35, 0.13) for _ in range(16)],
                "CRI": [rng.gauss(0.45, 0.12) for _ in range(16)],
                "LFI": [rng.gauss(0.62, 0.14) for _ in range(16)],
            },
        },
    )


_META = RecipeMetadata(
    name="cortex_competence_composites_panel",
    modality="spatial_statistics",
    family=RecipeFamily.coef_forest,
    answers_question="How do composite cortex-competence indices compare across groups?",
    required_fields=("indices_by_group_by_cell",),
    optional_fields=("index_order", "title"),
    file_format_hints=("csv", "json"),
)


@register_recipe(metadata=_META, contract=CortexCompetenceInput, demo_contract=_demo)
def render(contract: CortexCompetenceInput, ax=None, **_):
    import matplotlib.pyplot as plt
    import numpy as np

    if ax is None:
        _, ax = plt.subplots(figsize=(8, 5))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    groups = list(contract.indices_by_group_by_cell.keys())
    indices = contract.index_order or sorted({
        i for d in contract.indices_by_group_by_cell.values() for i in d
    })

    x = np.arange(len(indices))
    width = 0.7 / len(groups)
    rng = np.random.default_rng(42)
    for gi, g in enumerate(groups):
        color = palette[gi]
        offset = (gi - (len(groups) - 1) / 2) * width
        for xi, idx in enumerate(indices):
            vals = np.asarray(contract.indices_by_group_by_cell[g].get(idx, []), dtype=float)
            vals = vals[np.isfinite(vals)]
            if not len(vals):
                continue
            xc = xi + offset
            xs = np.full(len(vals), xc) + rng.uniform(-width * 0.3, width * 0.3, len(vals))
            ax.scatter(xs, vals, s=32, color=color, edgecolor="white",
                       linewidth=0.5, alpha=0.85,
                       label=g if xi == 0 else None)
            ax.plot([xc - width * 0.35, xc + width * 0.35], [np.median(vals), np.median(vals)], color=color, linewidth=1.8)

    ax.set_xticks(x)

    ax.set_xticklabels(indices, fontsize=9.6)
    ax.set_ylabel("index value")
    ax.set_title(contract.title, fontsize=9.6, color="#2c3e50", pad=6)
    ax.legend(fontsize=9.0, frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    return ax
