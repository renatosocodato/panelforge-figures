"""State ratio summary — categorical state proportions per group.

Covers splay-vs-taper, lamellipodium-vs-filopodium ratios, and similar
state-fraction visualizations.
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


class StateRatioInput(RecipeContract):
    state_fractions_by_group: dict[str, dict[str, float]] = Field(
        description="group → {state: fraction} (fractions sum ≤ 1 per group)"
    )
    state_order: list[str] | None = Field(
        default=None,
        description="Optional explicit ordering of state keys"
    )
    title: str = "State ratio summary"


def _demo() -> StateRatioInput:
    return StateRatioInput(
        state_fractions_by_group={
            "WT": {"splay": 0.62, "taper": 0.28, "intermediate": 0.10},
            "LI": {"splay": 0.41, "taper": 0.42, "intermediate": 0.17},
        },
        title="Splay-to-taper ratio by genotype",
    )


_META = RecipeMetadata(
    name="state_ratio_summary",
    modality="biophysics_scaling",
    family=RecipeFamily.sobol_bar,
    answers_question="How do categorical state fractions distribute across groups?",
    required_fields=("state_fractions_by_group",),
    optional_fields=("state_order", "title"),
    file_format_hints=("csv", "json"),
    alternatives_in_modality=("splay_taper_polarity_displacement_compound",),
)


@register_recipe(metadata=_META, contract=StateRatioInput, demo_contract=_demo)
def render(contract: StateRatioInput, ax=None, **_):
    import matplotlib.pyplot as plt
    import numpy as np

    if ax is None:
        _, ax = plt.subplots(figsize=(7, 4.5))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    groups = list(contract.state_fractions_by_group.keys())
    state_order = contract.state_order or sorted({
        s for d in contract.state_fractions_by_group.values() for s in d
    })

    n_groups = len(groups)
    n_states = len(state_order)
    x = np.arange(n_groups)
    width = 0.8 / n_states
    state_colors = [palette[i] for i in range(n_states)]
    for j, state in enumerate(state_order):
        vals = [contract.state_fractions_by_group[g].get(state, 0.0) for g in groups]
        offset = (j - (n_states - 1) / 2) * width
        ax.bar(x + offset, vals, width, color=state_colors[j],
               edgecolor="white", linewidth=0.6, label=state)
        for i, v in enumerate(vals):
            ax.text(x[i] + offset, v + 0.012, f"{v:.2f}",
                    ha="center", fontsize=8.4, color="#444")

    ax.set_xticks(x)
    ax.set_xticklabels(groups, fontsize=9.6)
    ax.set_ylabel("fraction")
    ax.set_ylim(0, 1.0)
    ax.set_title(contract.title, fontsize=9.6, color="#2c3e50", pad=6)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(fontsize=9.0, frameon=False, ncol=min(n_states, 4),
              loc="upper center", bbox_to_anchor=(0.5, -0.10))
    return ax
