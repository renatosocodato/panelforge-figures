"""Random-forest feature importance, horizontally ranked, bars coloured
by organizational scale.

Which features drive genotype discrimination, and from which scale
stratum do they come? The per-bar scale colour answers that at a
glance; the CI whiskers anchor the ranking.

Coef-forest family: >=3 markers + >=1 reference line. Satisfied by
>=3 feature rows + the null-importance reference line.
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
from ._shared import ScaleTaggedFeature

_SCALE_COLOURS = {
    "polymer": "#1565C0",
    "network": "#E65100",
    "territory": "#6A1B9A",
    "geometry": "#2E7D32",
    "whole_cell": "#B71C1C",
}


class RFImportanceByScaleInput(RecipeContract):
    importance_mean: list[float] = Field(..., min_length=3)
    importance_ci: list[tuple[float, float]] = Field(
        ..., min_length=3,
        description="per-feature (lo, hi) 95 % CI",
    )
    features: list[ScaleTaggedFeature] = Field(..., min_length=3)
    top_n: int = 20
    importance_metric: str = "permutation_importance"
    oob_score: float | None = None
    null_threshold: float = Field(
        0.01,
        description="importance below this is treated as noise (reference line)",
    )
    title: str = "Random-forest feature importance by scale"


def _demo() -> RFImportanceByScaleInput:
    rng = np.random.default_rng(5521)
    names = [
        ("standoff_distance", "geometry"),
        ("protrusion_width", "geometry"),
        ("orientation_alpha", "network"),
        ("territory_radius", "territory"),
        ("cell_area", "whole_cell"),
        ("curvature_ccf_peak", "network"),
        ("soma_circularity", "whole_cell"),
        ("filament_mesh_size", "network"),
        ("protrusion_count", "geometry"),
        ("persistence_length_actin", "polymer"),
        ("psd_motor_band", "polymer"),
        ("tapered_tip_fraction", "geometry"),
        ("actin_frontier_depth", "geometry"),
        ("mt_filament_fraction", "polymer"),
        ("spreading_index", "whole_cell"),
    ]
    importance = [
        0.185, 0.158, 0.122, 0.095, 0.082, 0.068, 0.051, 0.043,
        0.038, 0.032, 0.028, 0.024, 0.019, 0.015, 0.011,
    ]
    ci_half = [0.02 + rng.uniform(0, 0.015) for _ in names]
    features = [ScaleTaggedFeature(feature=n, scale=s,
                                   compartment="whole_cell")
                for n, s in names]
    return RFImportanceByScaleInput(
        importance_mean=importance,
        importance_ci=[(i - h, i + h) for i, h in zip(importance, ci_half)],
        features=features,
        oob_score=0.83,
    )


_META = RecipeMetadata(
    name="random_forest_importance_by_scale",
    modality="biophysics_scaling",
    family=RecipeFamily.coef_forest,
    answers_question=(
        "Which features drive genotype classification, ranked by "
        "random-forest importance, and from which organizational "
        "scale do they come?"
    ),
    required_fields=("importance_mean", "importance_ci", "features"),
    optional_fields=(
        "top_n", "importance_metric", "oob_score",
        "null_threshold", "title",
    ),
    file_format_hints=("csv",),
    alternatives_in_modality=("hierarchical_effect_size_ladder",),
)


@register_recipe(
    metadata=_META,
    contract=RFImportanceByScaleInput,
    demo_contract=_demo,
)
def render(contract: RFImportanceByScaleInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.8, 4.8))
    AESTHETIC.apply_to_ax(ax)

    imp = np.asarray(contract.importance_mean, float)
    ci = np.asarray(contract.importance_ci, float)
    features = list(contract.features)

    # Sort by importance descending and take top-N.
    order = np.argsort(-imp)[: contract.top_n]
    imp_s = imp[order]
    ci_s = ci[order]
    feats_s = [features[i] for i in order]
    colours = [_SCALE_COLOURS.get(f.scale, "#555555") for f in feats_s]

    y = np.arange(len(imp_s))

    # Bars.
    ax.barh(y, imp_s, color=colours, edgecolor="white",
            linewidth=0.6, alpha=0.92, zorder=3)
    # CI whiskers.
    for yi, (lo, hi) in zip(y, ci_s):
        ax.plot([lo, hi], [yi, yi],
                color="#333333", lw=0.8, zorder=4)
    # Point-estimate markers at the bar tips (satisfies coef_forest
    # ≥3-marker rule).
    ax.scatter(imp_s, y, s=32, c=colours, marker="o",
               edgecolor="white", linewidth=0.5, zorder=5)

    # Null-importance reference (satisfies coef_forest ≥1-line rule).
    ax.axvline(contract.null_threshold, color="#888888", lw=0.6,
               ls="--", zorder=2,
               label=f"null threshold = {smart_fmt(contract.null_threshold)}")

    ax.set_yticks(y)
    ax.set_yticklabels([f.feature for f in feats_s], fontsize=6.8)
    ax.invert_yaxis()
    ax.set_xlabel(contract.importance_metric.replace("_", " "))
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    # Scale-colour legend.
    from matplotlib.patches import Patch
    scales_present: list[str] = []
    for f in feats_s:
        if f.scale not in scales_present:
            scales_present.append(f.scale)
    handles = [Patch(facecolor=_SCALE_COLOURS.get(s, "#555555"),
                     label=s, alpha=0.92) for s in scales_present]
    # Include the null-threshold reference in the legend.
    from matplotlib.lines import Line2D
    handles.append(Line2D([0], [0], color="#888888", ls="--", lw=0.6,
                          label="null threshold"))
    ax.legend(handles=handles, fontsize=6.4, frameon=False,
              loc="upper left", bbox_to_anchor=(1.02, 1.0),
              borderaxespad=0.0, handlelength=1.2)

    oob_bit = (f"  ·  OOB = {smart_fmt(contract.oob_score)}"
               if contract.oob_score is not None else "")
    ax.set_title(
        f"{contract.title}  ·  top-{len(imp_s)} features{oob_bit}",
        fontsize=8.4, pad=4,
    )
    return ax
