"""Pharmacophore-feature × compound activity heatmap (SAR grammar)."""

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


class PharmacophoreInput(RecipeContract):
    feature_names: list[str] = Field(..., min_length=3)
    compound_names: list[str] = Field(..., min_length=3)
    activity: list[list[float]] = Field(
        ..., description="n_features × n_compounds pIC50 or z-scored activity"
    )
    active_mask: list[bool] | None = Field(
        None, description="one per feature; True → known active feature"
    )
    title: str = "Pharmacophore SAR"


def _demo() -> PharmacophoreInput:
    rng = np.random.default_rng(503)
    features = [
        "H-bond acceptor", "H-bond donor", "aromatic ring A",
        "aromatic ring B", "lipophilic cap", "basic amine",
        "halogen-methyl", "carboxylate", "sulfonamide", "thioether",
    ]
    compounds = [f"C{i+1:02d}" for i in range(12)]
    A = rng.normal(5.0, 1.0, (len(features), len(compounds)))
    # Active features boost activity for some compounds.
    active = [0, 2, 5, 7]
    for fi in active:
        A[fi] += rng.uniform(1.0, 2.5, len(compounds))
    mask = [i in active for i in range(len(features))]
    return PharmacophoreInput(
        feature_names=features,
        compound_names=compounds,
        activity=A.tolist(),
        active_mask=mask,
    )


_META = RecipeMetadata(
    name="pharmacophore_activity_heatmap",
    modality="dose_response_pharmacology",
    family=RecipeFamily.heatmap,
    answers_question=(
        "For a pharmacophore × compound matrix, which structural "
        "features drive activity?"
    ),
    required_fields=("feature_names", "compound_names", "activity"),
    optional_fields=("active_mask", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("ic50_forest_across_compounds",),
)


@register_recipe(
    metadata=_META,
    contract=PharmacophoreInput,
    demo_contract=_demo,
)
def render(contract: PharmacophoreInput, ax=None, **_):
    import matplotlib as mpl
    import matplotlib.patches as mpatches

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 4.0))
    AESTHETIC.apply_to_ax(ax)

    features = contract.feature_names
    compounds = contract.compound_names
    A = np.asarray(contract.activity, float)
    n_f, n_c = A.shape

    cmap = mpl.colormaps[AESTHETIC.continuous_cmap]
    im = ax.imshow(A, cmap=cmap, aspect="auto", interpolation="nearest")

    ax.set_xticks(range(n_c))
    ax.set_xticklabels(compounds, rotation=45, ha="right", fontsize=6.4)
    ax.set_yticks(range(n_f))
    ax.set_yticklabels(features, fontsize=6.6)

    # Active-feature strip on the left.
    if contract.active_mask is not None:
        for fi, active in enumerate(contract.active_mask):
            color = "#D32F2F" if active else "#CCCCCC"
            ax.add_patch(mpatches.Rectangle(
                (-0.56, fi - 0.48), 0.12, 0.96,
                facecolor=color, edgecolor="white", linewidth=0.3,
                clip_on=False, zorder=4,
            ))

    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.040, pad=0.03)
    cbar.set_label("activity", fontsize=6.8)
    cbar.ax.tick_params(labelsize=6.4)

    top_i, top_j = np.unravel_index(int(np.argmax(A)), A.shape)
    ax.set_title(
        f"{contract.title}  ·  top: {features[top_i]} × {compounds[top_j]} "
        f"({smart_fmt(float(A[top_i, top_j]))})",
        fontsize=8.4, pad=4,
    )
    return ax
