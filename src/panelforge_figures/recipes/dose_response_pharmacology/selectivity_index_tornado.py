"""Off-target selectivity tornado — fold-IC50 vs on-target, 10× cliff marker."""

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


class SelectivityTornadoInput(RecipeContract):
    target_names: list[str] = Field(..., min_length=2)
    ic50_on_target_nM: float = Field(..., description="lead compound on-target IC50 in nM")
    ic50_off_target_nM: list[float] = Field(...,
        description="IC50 of the same compound on each off-target (nM)")
    compound: str = "lead"
    title: str = "Selectivity index"


def _demo() -> SelectivityTornadoInput:
    rng = np.random.default_rng(277)
    targets = [f"target_{i+1}" for i in range(9)]
    on_ic50 = 12.0
    off_ic50 = 10 ** rng.uniform(1.1, 3.3, len(targets)) * on_ic50 / 20
    return SelectivityTornadoInput(
        target_names=targets,
        ic50_on_target_nM=on_ic50,
        ic50_off_target_nM=off_ic50.tolist(),
        compound="CompoundY",
    )


_META = RecipeMetadata(
    name="selectivity_index_tornado",
    modality="dose_response_pharmacology",
    family=RecipeFamily.ladder,
    answers_question=(
        "For a lead compound, how selective is it across the target "
        "panel (fold-IC50 ratios), and which off-targets break "
        "selectivity?"
    ),
    required_fields=(
        "target_names", "ic50_on_target_nM", "ic50_off_target_nM",
    ),
    optional_fields=("compound", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("ic50_forest_across_compounds",),
)


@register_recipe(
    metadata=_META,
    contract=SelectivityTornadoInput,
    demo_contract=_demo,
)
def render(contract: SelectivityTornadoInput, ax=None, **_):
    import matplotlib.patches as mpatches

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 3.6))
    AESTHETIC.apply_to_ax(ax)

    targets = contract.target_names
    on_val = float(contract.ic50_on_target_nM)
    off_vals = np.asarray(contract.ic50_off_target_nM, float)
    # Fold = off / on. Sort so the least selective is at top.
    fold = off_vals / max(on_val, 1e-9)
    order = np.argsort(fold)
    targets = [targets[i] for i in order]
    fold = fold[order]

    y = np.arange(len(targets))[::-1]
    selective_color = "#2E7D32"
    unselective_color = "#C62828"
    cliff = 10.0

    # Background shading: green tractable (fold >= 10), red red-flag (< 10).
    xmax = float(fold.max()) * 1.35
    ax.add_patch(mpatches.Rectangle(
        (0, -0.5), cliff, len(targets),
        facecolor="#FFEBEE", alpha=0.45, edgecolor="none", zorder=0,
    ))
    ax.add_patch(mpatches.Rectangle(
        (cliff, -0.5), xmax - cliff, len(targets),
        facecolor="#E8F5E9", alpha=0.45, edgecolor="none", zorder=0,
    ))

    for yi, f in zip(y, fold):
        color = selective_color if f >= cliff else unselective_color
        ax.barh(yi, f, height=0.55, color=color, alpha=0.85,
                edgecolor="white", linewidth=0.5, zorder=3)
        ax.text(f + xmax * 0.01, yi,
                f"×{smart_fmt(float(f))}",
                va="center", ha="left", fontsize=6.8, color=color)

    # 10× cliff reference.
    ax.axvline(cliff, color="#111111", lw=0.9, ls="--", zorder=4)
    ax.text(cliff, len(targets) - 0.2, "  10× cliff",
            ha="left", va="bottom", fontsize=6.6, color="#111111",
            bbox=dict(boxstyle="round,pad=0.14", fc="white",
                      ec="none", alpha=0.92), zorder=5)

    ax.set_yticks(y)
    ax.set_yticklabels(targets, fontsize=7.0)
    ax.set_xlabel("fold IC50 (off / on target)")
    ax.set_xscale("log")
    ax.set_xlim(max(fold.min() * 0.5, 0.5), xmax)
    n_pass = int((fold >= cliff).sum())
    ax.set_title(
        f"{contract.title}  ·  {contract.compound} "
        f"({n_pass}/{len(targets)} above 10×)",
        fontsize=9.0, pad=4,
    )
    ax.grid(axis="x", which="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
