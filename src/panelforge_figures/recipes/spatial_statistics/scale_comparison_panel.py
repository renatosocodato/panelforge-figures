"""Scale comparison panel — single measurement across multiple length scales."""

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


class ScaleComparisonInput(RecipeContract):
    measurements_by_scale_by_group: dict[str, dict[str, list[float]]] = Field(
        description="scale label → {group: per-cell measurement}"
    )
    y_label: str = "measurement"
    title: str = "Scale comparison"


def _demo() -> ScaleComparisonInput:
    import random
    rng = random.Random(42)
    return ScaleComparisonInput(
        measurements_by_scale_by_group={
            "Airyscan": {"WT": [rng.gauss(0.20, 0.02) for _ in range(7)],
                         "LI": [rng.gauss(0.22, 0.03) for _ in range(16)]},
            "widefield": {"WT": [rng.gauss(0.25, 0.03) for _ in range(7)],
                          "LI": [rng.gauss(0.27, 0.04) for _ in range(16)]},
            "per-protrusion": {"WT": [rng.gauss(0.18, 0.02) for _ in range(7)],
                               "LI": [rng.gauss(0.21, 0.03) for _ in range(16)]},
        },
        y_label="MT mesh size (μm)",
        title="MT mesh size scale comparison",
    )


_META = RecipeMetadata(
    name="scale_comparison_panel",
    modality="spatial_statistics",
    family=RecipeFamily.coef_forest,
    answers_question="How does a measurement compare across length scales or measurement modalities?",
    required_fields=("measurements_by_scale_by_group",),
    optional_fields=("y_label", "title"),
    file_format_hints=("csv", "json"),
)


@register_recipe(metadata=_META, contract=ScaleComparisonInput, demo_contract=_demo)
def render(contract: ScaleComparisonInput, ax=None, **_):
    import matplotlib.pyplot as plt
    import numpy as np

    if ax is None:
        _, ax = plt.subplots(figsize=(8, 5))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    scales = list(contract.measurements_by_scale_by_group.keys())
    groups = sorted({g for d in contract.measurements_by_scale_by_group.values() for g in d})

    n_groups = len(groups)
    width = 0.7 / n_groups
    rng = np.random.default_rng(42)
    for gi, g in enumerate(groups):
        color = palette[gi]
        offset = (gi - (n_groups - 1) / 2) * width
        for si, s in enumerate(scales):
            vals = np.asarray(contract.measurements_by_scale_by_group[s].get(g, []), dtype=float)
            vals = vals[np.isfinite(vals)]
            if not len(vals):
                continue
            xc = si + offset
            xs = np.full(len(vals), xc) + rng.uniform(-width * 0.3, width * 0.3, len(vals))
            ax.scatter(xs, vals, s=32, color=color, edgecolor="white",
                       linewidth=0.5, alpha=0.85, label=g if si == 0 else None)
            ax.plot([xc - width * 0.35, xc + width * 0.35], [np.median(vals), np.median(vals)], color=color, linewidth=1.8)

    ax.set_xticks(range(len(scales)))

    ax.set_xticklabels(scales, fontsize=9.6)
    ax.set_ylabel(contract.y_label, fontsize=9.6)
    ax.set_title(contract.title, fontsize=9.6, color="#2c3e50", pad=6)
    ax.legend(fontsize=9.0, frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    return ax
