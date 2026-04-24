"""PERMANOVA R2 stratified by organizational scale — shows where
genotype variance lives across the hierarchy.

Per-scale forest of R^2 +/- CI with p-values annotated and a typical-
threshold reference line.

Coef-forest family: >=3 markers + >=1 reference line. Satisfied by
>=3 scale rows + the R^2 threshold reference.
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

_SCALE_COLOURS = {
    "polymer": "#1565C0",
    "network": "#E65100",
    "territory": "#6A1B9A",
    "geometry": "#2E7D32",
    "whole_cell": "#B71C1C",
}


class PERMANOVAR2Input(RecipeContract):
    r2_by_scale: dict[str, float] = Field(..., min_length=3)
    ci_by_scale: dict[str, tuple[float, float]] = Field(..., min_length=3)
    p_by_scale: dict[str, float] = Field(..., min_length=3)
    permutations: int = 9999
    typical_threshold: float = Field(
        0.05,
        description="reference R^2 line for 'nontrivial' stratum",
    )
    scale_order: list[str] = Field(
        default_factory=lambda: [
            "polymer", "network", "territory", "geometry", "whole_cell",
        ],
    )
    title: str = "PERMANOVA R^2 by scale"


def _demo() -> PERMANOVAR2Input:
    r2 = {
        "polymer": 0.021,
        "network": 0.084,
        "territory": 0.128,
        "geometry": 0.185,
        "whole_cell": 0.147,
    }
    ci_half = {
        "polymer": 0.012,
        "network": 0.022,
        "territory": 0.030,
        "geometry": 0.038,
        "whole_cell": 0.034,
    }
    ci = {k: (v - ci_half[k], v + ci_half[k]) for k, v in r2.items()}
    p = {
        "polymer": 0.21,
        "network": 0.004,
        "territory": 0.0002,
        "geometry": 0.0001,
        "whole_cell": 0.0003,
    }
    return PERMANOVAR2Input(
        r2_by_scale=r2,
        ci_by_scale=ci,
        p_by_scale=p,
    )


_META = RecipeMetadata(
    name="scale_stratified_permanova_r2",
    modality="biophysics_scaling",
    family=RecipeFamily.coef_forest,
    answers_question=(
        "Where across the organizational hierarchy does the genotype "
        "signal account for the most variance (PERMANOVA R^2)?"
    ),
    required_fields=("r2_by_scale", "ci_by_scale", "p_by_scale"),
    optional_fields=(
        "permutations", "typical_threshold", "scale_order", "title",
    ),
    file_format_hints=("yaml", "json"),
    alternatives_in_modality=("random_forest_importance_by_scale",),
)


@register_recipe(
    metadata=_META,
    contract=PERMANOVAR2Input,
    demo_contract=_demo,
)
def render(contract: PERMANOVAR2Input, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 3.2))
    AESTHETIC.apply_to_ax(ax)

    scales = [s for s in contract.scale_order
              if s in contract.r2_by_scale]
    r2 = np.array([contract.r2_by_scale[s] for s in scales])
    lo = np.array([contract.ci_by_scale[s][0] for s in scales])
    hi = np.array([contract.ci_by_scale[s][1] for s in scales])
    pvals = np.array([contract.p_by_scale[s] for s in scales])
    colours = [_SCALE_COLOURS.get(s, "#555555") for s in scales]

    y = np.arange(len(scales))

    # Typical-threshold reference line (≥1-line requirement).
    ax.axvline(contract.typical_threshold, color="#888888", lw=0.6,
               ls="--", zorder=2,
               label=f"typical = {smart_fmt(contract.typical_threshold)}")
    ax.axvline(0.0, color="#DDDDDD", lw=0.5, zorder=1)

    # CI segments + markers.
    for yi, lo_i, hi_i, colour in zip(y, lo, hi, colours):
        ax.plot([lo_i, hi_i], [yi, yi],
                color=colour, lw=1.2, alpha=0.85, zorder=3)
    ax.scatter(r2, y, s=54, c=colours,
               edgecolor="white", linewidth=0.6, zorder=5)

    # Annotate p-values immediately to the right of the upper CI edge
    # (one per row; stays inside the axis and never collides with a
    # corner legend).
    x_max = float(max(hi.max(), contract.typical_threshold) * 1.28)
    for yi, p, hi_i in zip(y, pvals, hi):
        ax.text(hi_i + x_max * 0.015, yi,
                f"p = {smart_fmt(float(p))}",
                ha="left", va="center", fontsize=6.4,
                color="#555555", zorder=6)

    ax.set_yticks(y)
    ax.set_yticklabels(scales, fontsize=7.0)
    ax.invert_yaxis()
    ax.set_xlim(-0.01, x_max)
    ax.set_xlabel("PERMANOVA R^2 (genotype)")
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    total_r2 = float(r2.sum())
    ax.set_title(
        f"{contract.title}  ·  "
        f"perm = {contract.permutations}  ·  "
        f"summed R^2 across scales = {smart_fmt(total_r2)}",
        fontsize=8.4, pad=4,
    )
    # Legend at top-right-above-axes (bbox_to_anchor outside axes),
    # keeps it clear of the p-value annotations and the data rows.
    ax.legend(fontsize=6.4, frameon=False, loc="lower right",
              bbox_to_anchor=(1.0, 1.02), handlelength=1.2)
    return ax
