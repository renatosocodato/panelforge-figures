"""UpSet-style set comparisons — intersection sizes across multiple sets."""

from __future__ import annotations

from itertools import combinations

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


class UpSetInput(RecipeContract):
    set_names: list[str] = Field(..., min_length=2)
    set_members: dict[str, list[str]] = Field(
        ..., description="set name → list of member IDs"
    )
    top_n_intersections: int = 10
    title: str = "Set intersections"


def _demo() -> UpSetInput:
    rng = np.random.default_rng(271)
    universe = [f"g{i:04d}" for i in range(500)]
    sets = {
        "contrast_A": rng.choice(universe, size=120, replace=False).tolist(),
        "contrast_B": rng.choice(universe, size=150, replace=False).tolist(),
        "contrast_C": rng.choice(universe, size=90, replace=False).tolist(),
        "contrast_D": rng.choice(universe, size=110, replace=False).tolist(),
    }
    return UpSetInput(
        set_names=list(sets.keys()),
        set_members=sets,
        top_n_intersections=10,
    )


_META = RecipeMetadata(
    name="upset_set_comparisons",
    modality="omics_differential",
    family=RecipeFamily.matrix,
    answers_question="How do gene sets from multiple contrasts overlap — which intersections are largest?",
    required_fields=("set_names", "set_members"),
    optional_fields=("top_n_intersections", "title"),
    file_format_hints=("json", "csv"),
    alternatives_in_modality=("multi_contrast_volcano_grid",),
)


@register_recipe(metadata=_META, contract=UpSetInput, demo_contract=_demo)
def render(contract: UpSetInput, ax=None, **_):
    """Two-row composite: intersection-size bar above, set-participation dots below."""
    import matplotlib.pyplot as plt
    if ax is None:
        fig = plt.figure(figsize=(5.4, 3.4))
        gs = fig.add_gridspec(2, 1, height_ratios=[2.2, 1], hspace=0.08)
        ax_bar = fig.add_subplot(gs[0])
        ax_dot = fig.add_subplot(gs[1], sharex=ax_bar)
    else:
        fig = ax.figure
        pos = ax.get_subplotspec()
        ax.remove()
        sub = pos.subgridspec(2, 1, height_ratios=[2.2, 1], hspace=0.08)
        ax_bar = fig.add_subplot(sub[0])
        ax_dot = fig.add_subplot(sub[1], sharex=ax_bar)

    AESTHETIC.apply_to_ax(ax_bar)
    AESTHETIC.apply_to_ax(ax_dot)
    palette = get_palette(AESTHETIC.primary_palette)

    names = contract.set_names
    sets = {k: set(v) for k, v in contract.set_members.items()}

    # Compute all non-empty intersections.
    combos: list[tuple[tuple[str, ...], int]] = []
    for r in range(1, len(names) + 1):
        for combo in combinations(names, r):
            inter = set.intersection(*(sets[n] for n in combo))
            excl = set.union(*(sets[n] for n in names if n not in combo)) \
                if len(combo) < len(names) else set()
            only = inter - excl
            if only:
                combos.append((combo, len(only)))
    combos.sort(key=lambda t: -t[1])
    combos = combos[: contract.top_n_intersections]

    x = np.arange(len(combos))
    heights = [c[1] for c in combos]
    ax_bar.bar(x, heights, color=palette[0], alpha=0.85, edgecolor="white",
               linewidth=0.5)
    for xi, h in zip(x, heights):
        ax_bar.text(xi, h, str(h), ha="center", va="bottom",
                    fontsize=5.8, color="#333333")
    ax_bar.set_ylabel("intersection size")
    ax_bar.set_title(contract.title, fontsize=9.0, pad=4)
    ax_bar.tick_params(labelbottom=False)

    # Participation dots: sets × intersections.
    ax_dot.set_yticks(range(len(names)))
    ax_dot.set_yticklabels(names[::-1], fontsize=6.6)
    for xi, (combo, _size) in enumerate(combos):
        for yi, nm in enumerate(names[::-1]):
            if nm in combo:
                ax_dot.scatter([xi], [yi], s=42, color="#222222", zorder=3)
            else:
                ax_dot.scatter([xi], [yi], s=18, color="#DDDDDD", zorder=2)
        # Lines joining active dots.
        active_ys = [yi for yi, nm in enumerate(names[::-1]) if nm in combo]
        if len(active_ys) > 1:
            ax_dot.plot([xi, xi], [min(active_ys), max(active_ys)],
                        color="#222222", lw=1.2, zorder=2)
    ax_dot.set_xticks(x)
    ax_dot.set_xticklabels([])
    ax_dot.set_xlim(-0.5, len(combos) - 0.5)
    for s in ("bottom",):
        ax_dot.spines[s].set_visible(False)
    ax_dot.set_ylim(-0.5, len(names) - 0.5)
    return ax_bar
