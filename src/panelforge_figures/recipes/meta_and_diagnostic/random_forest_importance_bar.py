"""Random-forest feature-importance horizontal bar — top-K discriminative features."""

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


class RFImportanceBarInput(RecipeContract):
    importances: dict[str, float] = Field(
        description="feature name → RF importance (Gini); will be sorted descending"
    )
    top_k: int = 15
    importance_label: str = "RF importance (Gini)"
    title: str = "Top-K features discriminating groups"


def _demo() -> RFImportanceBarInput:
    return RFImportanceBarInput(
        importances={
            "zone_actin_exclusive_mt_cv": 0.031,
            "zone_desert_mt_cv": 0.028,
            "cell_area_um2": 0.027,
            "coloc_pearson_r": 0.025,
            "coloc_manders_m2": 0.024,
            "protrusion_width_mean_um": 0.022,
            "zone_actin_exclusive_mt_mean": 0.022,
            "feret_max_um": 0.021,
            "zone_desert_area_um2": 0.021,
            "actin_n_filaments_3d": 0.020,
            "cup_competence_index": 0.019,
            "sp_g_actin_self_median": 0.017,
            "protrusion_width_std_um": 0.017,
            "crosstalk_perpendicular_frac": 0.016,
            "major_axis_um": 0.016,
        },
        top_k=15,
        title="Top-15 features (WT vs LI, n=23 cells, OOB-style RF)",
    )


_META = RecipeMetadata(
    name="random_forest_importance_bar",
    modality="meta_and_diagnostic",
    family=RecipeFamily.sobol_bar,
    answers_question="Which features most discriminate the groups according to a random forest?",
    required_fields=("importances",),
    optional_fields=("top_k", "importance_label", "title"),
    file_format_hints=("csv", "json"),
    alternatives_in_modality=("random_forest_confusion_loocv",),
)


@register_recipe(metadata=_META, contract=RFImportanceBarInput, demo_contract=_demo)
def render(contract: RFImportanceBarInput, ax=None, **_):
    import matplotlib.pyplot as plt
    import numpy as np

    if ax is None:
        _, ax = plt.subplots(figsize=(7.2, 6.0))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)
    bar_color = palette[0] if hasattr(palette, "__getitem__") else "#5b8aa4"

    items = sorted(contract.importances.items(), key=lambda x: -x[1])[:contract.top_k]
    names = [n for n, _ in items]
    vals = [v for _, v in items]

    y = np.arange(len(names))[::-1]
    ax.barh(y, vals, color=bar_color, edgecolor="#23416b", linewidth=0.5)
    for yi, v in zip(y, vals):
        ax.text(v + max(vals) * 0.005, yi, f"{v:.3f}",
                va="center", fontsize=7.0, color="#444")
    ax.set_yticks(y)
    ax.set_yticklabels([n.replace("_", " ")[:42] for n in names], fontsize=8.4)
    ax.set_xlabel(contract.importance_label, fontsize=9.6)
    ax.set_title(contract.title, fontsize=9.6, color="#2c3e50", pad=6)
    ax.spines[["top", "right"]].set_visible(False)
    return ax
