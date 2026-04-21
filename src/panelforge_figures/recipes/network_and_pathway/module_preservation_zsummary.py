"""WGCNA module-preservation Zsummary ladder with Z=2 / Z=10 thresholds."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class ModulePreservationInput(RecipeContract):
    module_names: list[str] = Field(..., min_length=3)
    zsummary: list[float] = Field(...)
    module_size: list[int] | None = None
    title: str = "Module preservation Zsummary"


def _demo() -> ModulePreservationInput:
    rng = np.random.default_rng(911)
    modules = ["turquoise", "blue", "brown", "yellow", "green",
               "red", "black", "pink", "magenta", "purple", "grey"]
    z = np.array([18.2, 14.5, 11.3, 8.7, 6.2, 4.8, 3.1, 2.2, 1.6, 0.9, 0.3])
    z = z + rng.normal(0, 0.4, z.size)
    sizes = rng.integers(40, 400, len(modules)).tolist()
    return ModulePreservationInput(
        module_names=modules,
        zsummary=z.tolist(),
        module_size=sizes,
    )


_META = RecipeMetadata(
    name="module_preservation_zsummary",
    modality="network_and_pathway",
    family=RecipeFamily.ladder,
    answers_question=(
        "How strongly is each module preserved across studies / "
        "datasets, by WGCNA Zsummary?"
    ),
    required_fields=("module_names", "zsummary"),
    optional_fields=("module_size", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("centrality_degree_distribution",),
)


@register_recipe(
    metadata=_META,
    contract=ModulePreservationInput,
    demo_contract=_demo,
)
def render(contract: ModulePreservationInput, ax=None, **_):
    import matplotlib.patches as mpatches

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 3.6))
    AESTHETIC.apply_to_ax(ax)

    names = list(contract.module_names)
    z = np.asarray(contract.zsummary, float)
    order = np.argsort(-z)
    names = [names[i] for i in order]
    z = z[order]
    sizes = (np.asarray(contract.module_size, float)[order]
             if contract.module_size is not None
             else np.full(len(names), 100.0))

    y = np.arange(len(names))[::-1]
    xmax = float(z.max()) * 1.25

    # Background tier shading.
    tiers = [(0, 2, "#FFEBEE"),   # not preserved
             (2, 10, "#FFF8E1"),  # weak / moderate
             (10, xmax, "#E8F5E9")]  # strong
    for lo, hi, fc in tiers:
        ax.add_patch(mpatches.Rectangle(
            (lo, -0.5), hi - lo, len(names),
            facecolor=fc, edgecolor="none", alpha=0.55, zorder=0,
        ))

    # Bar per module, coloured by tier.
    def tier_color(zv: float) -> str:
        if zv < 2:
            return "#C62828"
        if zv < 10:
            return "#F9A825"
        return "#2E7D32"

    for yi, zi, sz, nm in zip(y, z, sizes, names):
        color = tier_color(float(zi))
        ax.barh(yi, zi, height=0.52, color=color, alpha=0.85,
                edgecolor="white", linewidth=0.5, zorder=3)
        ax.text(zi + xmax * 0.01, yi,
                f"Z={smart_fmt(float(zi))}   n={int(sz)}",
                va="center", ha="left", fontsize=6.4, color=color,
                zorder=5)

    # Tier reference lines.
    for x_tier, lab in [(2, "Z = 2 (weak)"), (10, "Z = 10 (strong)")]:
        ax.axvline(x_tier, color="#111111", lw=0.7, ls="--", zorder=4)
        ax.text(x_tier, len(names) - 0.3, lab,
                ha="center", va="bottom", fontsize=6.2, color="#111111",
                bbox=dict(boxstyle="round,pad=0.14", fc="white",
                          ec="none", alpha=0.92), zorder=5)

    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=7.0)
    ax.set_xlabel("Zsummary")
    ax.set_xlim(0, xmax)
    n_strong = int((z >= 10).sum())
    n_weak = int(((z >= 2) & (z < 10)).sum())
    n_none = int((z < 2).sum())
    ax.set_title(
        f"{contract.title}  ·  strong={n_strong}, weak={n_weak}, not-pres={n_none}",
        fontsize=8.6, pad=4,
    )
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
