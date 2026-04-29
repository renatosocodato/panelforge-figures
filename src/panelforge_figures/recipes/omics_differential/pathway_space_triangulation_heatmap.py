"""Pathway-space triangulation heatmap — theme × match-tier
support-level grid showing how strongly each internal imaging-
derived theme is corroborated by external pathway-space layers
(matched / analog / internal).

Matrix family: >=1 imshow OR >=4 cell patches.
"""

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
from ._shared import PathwaySupportLayer


class PathwaySpaceTriangulationInput(RecipeContract):
    layers: list[PathwaySupportLayer] = Field(..., min_length=4)
    theme_order: list[str] | None = None
    tier_order: list[str] | None = None
    title: str = "Pathway-space triangulation heatmap"


def _demo() -> PathwaySpaceTriangulationInput:
    rng = np.random.default_rng(813)
    themes = [
        "energy_mitochondrial",
        "cytoskeletal_Rho",
        "vesicle_trafficking",
        "actin_polymerisation",
        "redox_homeostasis",
    ]
    tiers = ["matched", "analog", "internal"]
    layers: list[PathwaySupportLayer] = []
    # cytoskeletal_Rho strongest joint support; others weaker.
    base = {
        "energy_mitochondrial": [0.55, 0.20, 0.10],
        "cytoskeletal_Rho": [0.85, 0.78, 0.72],
        "vesicle_trafficking": [0.45, 0.62, 0.30],
        "actin_polymerisation": [0.58, 0.40, 0.55],
        "redox_homeostasis": [0.30, 0.18, 0.22],
    }
    for theme in themes:
        for ti, tier in enumerate(tiers):
            level = float(np.clip(
                base[theme][ti] + rng.normal(0, 0.04), 0.0, 1.0,
            ))
            layers.append(PathwaySupportLayer(
                theme=theme, match_tier=tier, support_level=level,
            ))
    return PathwaySpaceTriangulationInput(
        layers=layers,
        theme_order=themes, tier_order=tiers,
    )


_META = RecipeMetadata(
    name="pathway_space_triangulation_heatmap",
    modality="omics_differential",
    family=RecipeFamily.matrix,
    answers_question=(
        "Across themes (energy / cytoskeletal / vesicle / actin / "
        "redox) and match-tiers (matched / analog / internal), "
        "where does external pathway-space support converge with "
        "internal imaging-derived modules?"
    ),
    required_fields=("layers",),
    optional_fields=("theme_order", "tier_order", "title"),
    file_format_hints=("yaml", "csv"),
    alternatives_in_modality=("pathway_space_bridge_summary_heatmap",),
)


@register_recipe(
    metadata=_META,
    contract=PathwaySpaceTriangulationInput,
    demo_contract=_demo,
)
def render(contract: PathwaySpaceTriangulationInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.8, 4.0))
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

    Z = np.zeros((n_themes, n_tiers))
    for layer in contract.layers:
        if layer.theme in themes and layer.match_tier in tiers:
            i = themes.index(layer.theme)
            j = tiers.index(layer.match_tier)
            Z[i, j] = float(layer.support_level)

    im = ax.imshow(Z, cmap="viridis", vmin=0.0, vmax=1.0,
                   aspect="auto", interpolation="nearest", zorder=2)

    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.04, pad=0.03)
    cbar.set_label("support level", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.0)

    # Cell annotations.
    for i in range(n_themes):
        for j in range(n_tiers):
            v = Z[i, j]
            txt_color = "white" if v < 0.55 else "#222222"
            ax.text(j, i, f"{smart_fmt(v)}",
                    ha="center", va="center", fontsize=6.4,
                    color=txt_color, zorder=4)

    ax.set_xticks(range(n_tiers))
    ax.set_xticklabels(tiers, fontsize=7.0)
    ax.set_yticks(range(n_themes))
    ax.set_yticklabels(
        [t.replace("_", " ") for t in themes], fontsize=6.8,
    )
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    # Strongest theme.
    theme_means = Z.mean(axis=1)
    strongest_idx = int(np.argmax(theme_means))
    ax.set_title(
        f"{contract.title}  ·  strongest joint support: "
        f"{themes[strongest_idx].replace('_', ' ')} "
        f"(mean = {smart_fmt(float(theme_means[strongest_idx]))})",
        fontsize=8.2, pad=4,
    )
    return ax
