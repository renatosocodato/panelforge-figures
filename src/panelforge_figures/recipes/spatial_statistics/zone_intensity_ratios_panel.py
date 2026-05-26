"""Zone intensity ratios panel — per-cell zone-resolved intensity summary."""

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


class ZoneIntensityRatiosInput(RecipeContract):
    intensity_ratios_by_zone: dict[str, dict[str, list[float]]] = Field(
        description="zone → {group: per-cell intensity ratio (actin / mt)}"
    )
    title: str = "Zone-resolved actin/MT intensity ratios"


def _demo() -> ZoneIntensityRatiosInput:
    import random
    rng = random.Random(42)
    return ZoneIntensityRatiosInput(
        intensity_ratios_by_zone={
            "contact":         {"WT": [rng.gauss(1.0, 0.2) for _ in range(7)],
                                "LI": [rng.gauss(1.4, 0.3) for _ in range(16)]},
            "actin_exclusive": {"WT": [rng.gauss(3.5, 0.5) for _ in range(7)],
                                "LI": [rng.gauss(3.2, 0.6) for _ in range(16)]},
            "mt_exclusive":    {"WT": [rng.gauss(0.3, 0.1) for _ in range(7)],
                                "LI": [rng.gauss(0.4, 0.15) for _ in range(16)]},
            "desert":          {"WT": [rng.gauss(0.6, 0.15) for _ in range(7)],
                                "LI": [rng.gauss(0.7, 0.2) for _ in range(16)]},
        },
    )


_META = RecipeMetadata(
    name="zone_intensity_ratios_panel",
    modality="spatial_statistics",
    family=RecipeFamily.coef_forest,
    answers_question="How do actin/MT intensity ratios vary by zone across groups?",
    required_fields=("intensity_ratios_by_zone",),
    optional_fields=("title",),
    file_format_hints=("csv", "json"),
)


@register_recipe(metadata=_META, contract=ZoneIntensityRatiosInput, demo_contract=_demo)
def render(contract: ZoneIntensityRatiosInput, ax=None, **_):
    import matplotlib.pyplot as plt
    import numpy as np

    if ax is None:
        _, ax = plt.subplots(figsize=(8, 5))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    zones = list(contract.intensity_ratios_by_zone.keys())
    groups = sorted({g for d in contract.intensity_ratios_by_zone.values() for g in d})
    n_groups = len(groups)
    width = 0.7 / n_groups
    rng = np.random.default_rng(42)
    for gi, g in enumerate(groups):
        c = palette[gi]
        for zi, z in enumerate(zones):
            vals = np.asarray(contract.intensity_ratios_by_zone[z].get(g, []), dtype=float)
            vals = vals[np.isfinite(vals)]
            if not len(vals):
                continue
            offset = (gi - (n_groups - 1) / 2) * width
            xc = zi + offset
            x = np.full(len(vals), xc) + rng.uniform(-width * 0.3, width * 0.3, len(vals))
            ax.scatter(x, vals, s=32, color=c, edgecolor="white",
                       linewidth=0.6, alpha=0.85,
                       label=g if zi == 0 else None)
            ax.plot([xc - width * 0.35, xc + width * 0.35], [np.median(vals), np.median(vals)], color=c, linewidth=1.8)

    ax.set_xticks(range(len(zones)))
    ax.set_xticklabels(zones, fontsize=9.0, rotation=18, ha="right")
    ax.set_ylabel("actin/MT intensity ratio")
    ax.set_title(contract.title, fontsize=9.6, color="#2c3e50", pad=6)
    ax.legend(fontsize=9.0, frameon=False, loc="best")
    ax.spines[["top", "right"]].set_visible(False)
    return ax
