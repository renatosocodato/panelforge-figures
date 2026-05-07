"""Pathway-space bridge summary heatmap — theme-level joint-support
heatmap that summarises matched + analog + internal layers into a
compact 1-D bridge view, with per-theme aggregate score and
match-tier breakdown.

Matrix family: >=1 imshow OR >=4 cell patches.
"""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    StatisticalContract,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC
from ._shared import PathwaySupportLayer


class PathwayBridgeSummaryInput(RecipeContract):
    layers: list[PathwaySupportLayer] = Field(..., min_length=4)
    theme_order: list[str] | None = None
    tier_order: list[str] | None = None
    title: str = "Pathway-space bridge summary heatmap"


def _demo() -> PathwayBridgeSummaryInput:
    # Re-use the triangulation demo data shape but compress into
    # a bridge view (theme rows × support layer columns).
    rng = np.random.default_rng(814)
    themes = [
        "energy_mitochondrial",
        "cytoskeletal_Rho",
        "vesicle_trafficking",
        "actin_polymerisation",
        "redox_homeostasis",
    ]
    # Bridge layers: matched = direct pathway match, surrogate =
    # analog-aware extension, internal = imaging-module projection.
    tiers = ["matched", "surrogate", "internal"]
    base = {
        "energy_mitochondrial": [0.55, 0.20, 0.10],
        "cytoskeletal_Rho": [0.85, 0.80, 0.75],
        "vesicle_trafficking": [0.45, 0.55, 0.32],
        "actin_polymerisation": [0.60, 0.42, 0.55],
        "redox_homeostasis": [0.32, 0.18, 0.20],
    }
    layers: list[PathwaySupportLayer] = []
    for theme in themes:
        for ti, tier in enumerate(tiers):
            level = float(np.clip(
                base[theme][ti] + rng.normal(0, 0.04), 0.0, 1.0,
            ))
            layers.append(PathwaySupportLayer(
                theme=theme, match_tier=tier, support_level=level,
            ))
    return PathwayBridgeSummaryInput(
        layers=layers,
        theme_order=themes, tier_order=tiers,
    )


_META = RecipeMetadata(
    name="pathway_space_bridge_summary_heatmap",
    modality="omics_differential",
    family=RecipeFamily.matrix,
    answers_question=(
        "At theme level, which manuscript themes retain joint "
        "support across matched / surrogate / internal layers, and "
        "where does support drop under stricter explicit-surrogate "
        "criteria?"
    ),
    required_fields=("layers",),
    optional_fields=("theme_order", "tier_order", "title"),
    file_format_hints=("yaml", "csv"),
    alternatives_in_modality=("pathway_space_triangulation_heatmap",),
    statistical_contract=StatisticalContract(
        min_n_per_group=10,
        distribution_assumption="approximately_gaussian",
        multiple_comparisons="any_correction_required",
        independence="iid",
        effect_size_in_units="standardized_d",
        rendered_claim_template="Cohen's d = {d:.2f} ({outcome_class})",
        refuses_when=("underpowered",),
    ),
)


@register_recipe(
    metadata=_META,
    contract=PathwayBridgeSummaryInput,
    demo_contract=_demo,
)
def render(contract: PathwayBridgeSummaryInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.4, 3.8))
    AESTHETIC.apply_to_ax(ax)

    if contract.theme_order is None:
        themes: list[str] = []
        for layer in contract.layers:
            if layer.theme not in themes:
                themes.append(layer.theme)
    else:
        themes = list(contract.theme_order)
    if contract.tier_order is None:
        tiers: list[str] = []
        for layer in contract.layers:
            if layer.match_tier not in tiers:
                tiers.append(layer.match_tier)
    else:
        tiers = list(contract.tier_order)

    n_themes = len(themes)
    n_tiers = len(tiers)
    n_cols = n_tiers + 1   # + aggregate column

    Z = np.zeros((n_themes, n_tiers))
    for layer in contract.layers:
        if layer.theme in themes and layer.match_tier in tiers:
            i = themes.index(layer.theme)
            j = tiers.index(layer.match_tier)
            Z[i, j] = float(layer.support_level)

    aggregate = Z.mean(axis=1).reshape(-1, 1)
    Z_full = np.hstack([Z, aggregate])

    im = ax.imshow(Z_full, cmap="viridis",
                   vmin=0.0, vmax=1.0,
                   aspect="auto", interpolation="nearest", zorder=2)

    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.04, pad=0.03)
    cbar.set_label("support level", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.0)

    # Cell annotations.
    for i in range(n_themes):
        for j in range(n_cols):
            v = Z_full[i, j]
            txt_color = "white" if v < 0.55 else "#222222"
            ax.text(j, i, f"{smart_fmt(v)}",
                    ha="center", va="center", fontsize=6.4,
                    color=txt_color,
                    fontweight="bold" if j == n_cols - 1 else "normal",
                    zorder=4)

    # Vertical separator before the aggregate column.
    ax.axvline(n_tiers - 0.5, color="white", lw=2.2, zorder=5)

    ax.set_xticks(range(n_cols))
    ax.set_xticklabels(list(tiers) + ["aggregate"], fontsize=7.0)
    ax.set_yticks(range(n_themes))
    ax.set_yticklabels(
        [t.replace("_", " ") for t in themes], fontsize=6.8,
    )
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    # Strongest theme by aggregate.
    strongest_idx = int(np.argmax(aggregate.ravel()))
    ax.set_title(
        f"{contract.title}  ·  strongest theme: "
        f"{themes[strongest_idx].replace('_', ' ')}  ·  "
        f"aggregate = {smart_fmt(float(aggregate[strongest_idx, 0]))}",
        fontsize=8.2, pad=4,
    )
    return ax
