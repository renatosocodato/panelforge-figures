"""Per-cell branch-point count raincloud — half-violin + strip + box per condition."""

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


class BranchPointCountInput(RecipeContract):
    branch_counts_by_condition: dict[str, list[float]] = Field(
        ..., description="per-cell branch-point counts, keyed by condition"
    )
    animal_ids_by_condition: dict[str, list[str]] | None = Field(
        None, description="optional per-cell animal IDs for animal-level overlay"
    )
    title: str = "Branch-point counts per cell"


def _demo() -> BranchPointCountInput:
    rng = np.random.default_rng(701)
    counts = {
        "control":  rng.poisson(8.0, 52).tolist(),
        "mutant":   rng.poisson(14.0, 48).tolist(),
        "rescue":   rng.poisson(9.6, 50).tolist(),
    }
    animals = {
        "control": [f"a{i % 6}" for i in range(len(counts["control"]))],
        "mutant":  [f"a{i % 7}" for i in range(len(counts["mutant"]))],
        "rescue":  [f"a{i % 6}" for i in range(len(counts["rescue"]))],
    }
    return BranchPointCountInput(
        branch_counts_by_condition=counts,
        animal_ids_by_condition=animals,
    )


_META = RecipeMetadata(
    name="branch_point_count_raincloud",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.split_violin,
    answers_question=(
        "How does the per-cell count of skeleton branch points shift across "
        "conditions, and how does it cluster by animal?"
    ),
    required_fields=("branch_counts_by_condition",),
    optional_fields=("animal_ids_by_condition", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("branch_point_density_map",),
)


@register_recipe(
    metadata=_META,
    contract=BranchPointCountInput,
    demo_contract=_demo,
)
def render(contract: BranchPointCountInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    conditions = list(contract.branch_counts_by_condition.keys())
    positions = list(range(len(conditions)))
    data = [np.asarray(contract.branch_counts_by_condition[c], float)
            for c in conditions]

    # Half-violin: render violinplot then zero-out the right half of each body.
    parts = ax.violinplot(data, positions=positions, widths=0.9,
                          showmeans=False, showmedians=False, showextrema=False)
    for i, pc in enumerate(parts["bodies"]):
        color = palette[i % len(palette.colors)]
        pc.set_facecolor(color)
        pc.set_edgecolor("#333333")
        pc.set_alpha(0.55)
        # Keep only the left half (x ≤ position[i]) of the body.
        verts = pc.get_paths()[0].vertices
        verts[:, 0] = np.clip(verts[:, 0], -np.inf, positions[i])

    rng = np.random.default_rng(703)
    for pos, vals, color_idx in zip(positions, data, range(len(conditions))):
        color = palette[color_idx % len(palette.colors)]
        # Strip: jittered dots on the right side.
        jitter = rng.uniform(0.08, 0.35, vals.size)
        ax.scatter(pos + jitter, vals, s=8, color=color, alpha=0.7,
                   edgecolor="white", linewidth=0.3, zorder=4)
        # Box: Q1-Q3 vertical line + median marker at the strip root.
        if vals.size >= 4:
            q1, med, q3 = np.quantile(vals, [0.25, 0.5, 0.75])
            ax.plot([pos, pos], [q1, q3], color="black",
                    lw=3.0, solid_capstyle="butt", zorder=5)
            ax.scatter([pos], [med], s=38, facecolor="white",
                       edgecolor="black", linewidth=1.0, zorder=6)

    # Animal-level overlay: filled ring markers at per-animal means.
    if contract.animal_ids_by_condition is not None:
        for pos, cond, color_idx in zip(positions, conditions,
                                         range(len(conditions))):
            ids = np.asarray(contract.animal_ids_by_condition.get(cond, []))
            vals = data[conditions.index(cond)]
            if ids.size == 0 or ids.size != vals.size:
                continue
            color = palette[color_idx % len(palette.colors)]
            for aid in np.unique(ids):
                mean_val = float(np.mean(vals[ids == aid]))
                ax.scatter([pos + 0.48], [mean_val], s=34,
                           facecolor="white", edgecolor=color, linewidth=1.3,
                           zorder=7)

    ax.set_xticks(positions)
    ax.set_xticklabels(conditions, fontsize=7.0)
    ax.set_ylabel("branch-point count per cell")
    summary = "  ·  ".join(
        f"{c}: med {smart_fmt(float(np.median(v)))}" for c, v in zip(conditions, data)
    )
    ax.set_title(f"{contract.title}  ·  {summary}", fontsize=8.4, pad=4)
    ax.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
