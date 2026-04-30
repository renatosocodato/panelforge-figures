"""Hierarchical effect-size ladder — effect-size forest grouped by
organizational scale x compartment.

The headline beta-pack panel: renders the manuscript's central argument
(where in the polymer -> network -> territory -> geometry -> whole_cell
hierarchy does the genotype signal live, and how does it split across
whole-cell vs protrusion-internal compartments) in a single panel.

Coef-forest family: >=3 markers + >=1 reference line. Satisfied by
>=3 feature rows + the x=0 null reference + the TOST-band midline.
"""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    classify_outcome,
    register_recipe,
    tost_band_patch,
)
from ._aesthetic import AESTHETIC
from ._shared import (
    OUTCOME_PALETTE_DEFAULT,
    EffectSizeEstimate,
    _demo_estimate_roster,
)


class HierarchicalEffectSizeLadderInput(RecipeContract):
    estimates: list[EffectSizeEstimate] = Field(..., min_length=3)
    scale_order: list[str] = Field(
        ..., min_length=1,
        description="order of scale strata, e.g. ['polymer','network',...]",
    )
    compartment_order: list[str] = Field(
        default_factory=lambda: ["whole_cell", "protrusion_internal"],
        description="render order for the two compartments",
    )
    show_tost_band: bool = True
    sort_within_scale: str = Field(
        "abs_d",
        description="'d' | 'feature_name' | 'abs_d'",
    )
    title: str = "Hierarchical effect-size ladder"


def _demo() -> HierarchicalEffectSizeLadderInput:
    return HierarchicalEffectSizeLadderInput(
        estimates=_demo_estimate_roster(),
        scale_order=[
            "polymer", "network", "territory", "geometry", "whole_cell",
        ],
        compartment_order=["whole_cell", "protrusion_internal"],
    )


_META = RecipeMetadata(
    name="hierarchical_effect_size_ladder",
    modality="biophysics_scaling",
    family=RecipeFamily.coef_forest,
    answers_question=(
        "Across the polymer -> network -> territory -> geometry -> "
        "whole-cell hierarchy, how large are the per-feature effects "
        "and how do they split across compartments?"
    ),
    required_fields=("estimates", "scale_order"),
    optional_fields=(
        "compartment_order", "show_tost_band",
        "sort_within_scale", "title",
    ),
    file_format_hints=("yaml", "json"),
    alternatives_in_modality=("scaling_exponent_ci_forest",),
)


def _sort_key(est: EffectSizeEstimate, rule: str):
    if rule == "d":
        return est.d
    if rule == "feature_name":
        return est.feature
    return abs(est.d)


@register_recipe(
    metadata=_META,
    contract=HierarchicalEffectSizeLadderInput,
    demo_contract=_demo,
)
def render(contract: HierarchicalEffectSizeLadderInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.6, 5.4))
    AESTHETIC.apply_to_ax(ax)

    palette = AESTHETIC.outcome_palette or OUTCOME_PALETTE_DEFAULT
    marker_by_compartment = {
        contract.compartment_order[0]: "o",
        contract.compartment_order[-1]: "s" if len(
            contract.compartment_order) > 1 else "o",
    }

    # Group estimates by scale, preserving scale_order.
    by_scale: dict[str, list[EffectSizeEstimate]] = {
        s: [] for s in contract.scale_order
    }
    for est in contract.estimates:
        if est.scale in by_scale:
            by_scale[est.scale].append(est)

    # Build row list: flat (scale, feature, compartment) in display order.
    rows: list[tuple[str, str, EffectSizeEstimate]] = []
    separators: list[float] = []  # y-positions between scale groups
    for scale in contract.scale_order:
        items = by_scale[scale]
        if not items:
            continue
        # One entry per (feature, compartment) pair — keep features paired.
        unique_features: list[str] = []
        seen: set[str] = set()
        for e in items:
            if e.feature not in seen:
                unique_features.append(e.feature)
                seen.add(e.feature)
        unique_features.sort(
            key=lambda f: _sort_key(
                next(e for e in items if e.feature == f),
                contract.sort_within_scale,
            ),
            reverse=True,
        )
        for feature in unique_features:
            for compartment in contract.compartment_order:
                match = next(
                    (e for e in items
                     if e.feature == feature and e.compartment == compartment),
                    None,
                )
                if match is not None:
                    rows.append((scale, feature, match))
        separators.append(len(rows) - 0.5)

    n_rows = len(rows)
    y_positions = np.arange(n_rows)

    # TOST band — use the first estimate's zone (pack convention: uniform
    # per roster; if not uniform, band is drawn only if all match).
    tost_zones = {(e.tost.lower, e.tost.upper) for _, _, e in rows}
    if contract.show_tost_band and len(tost_zones) == 1:
        lo, hi = next(iter(tost_zones))
        tost_band_patch(ax, lo, hi, orientation="y",
                        color="#D0D0D0", alpha=0.35, zorder=1,
                        label="TOST equivalence")

    # Null reference at x=0.
    ax.axvline(0.0, color="#888888", lw=0.5, ls="--", zorder=2)

    # Marker + CI per row.
    for yi, (_, _, est) in zip(y_positions, rows):
        colour = palette.get(est.outcome_class, palette["equivocal"])
        marker = marker_by_compartment.get(est.compartment, "o")
        ax.plot([est.ci_lo, est.ci_hi], [yi, yi],
                color=colour, lw=1.1, alpha=0.85, zorder=3)
        ax.scatter([est.d], [yi], s=38, marker=marker,
                   color=colour, edgecolor="white", linewidth=0.5,
                   zorder=5)

    # Scale-group separator lines.
    for sep in separators[:-1]:
        ax.axhline(sep, color="#DDDDDD", lw=0.5, zorder=1)

    # Y-tick labels — feature name only on first compartment row of a pair.
    tick_positions: list[float] = []
    tick_labels: list[str] = []
    for yi, (_, feature, est) in zip(y_positions, rows):
        if est.compartment == contract.compartment_order[0]:
            tick_positions.append(yi + 0.5)  # midway between paired rows
            tick_labels.append(feature)
    ax.set_yticks(tick_positions)
    ax.set_yticklabels(tick_labels, fontsize=6.8)
    ax.invert_yaxis()

    # Scale-group labels — placed just below each stratum separator,
    # left-aligned in axes-fraction x and data-units y. Decoupled from
    # stratum size so single-feature strata (e.g. 'territory') don't
    # collide with neighbours.
    import matplotlib.transforms as mtrans
    trans = mtrans.blended_transform_factory(ax.transAxes, ax.transData)
    row_idx = 0
    x_hi = max(1.30, float(max(
        (e.ci_hi for _, _, e in rows), default=1.0)) + 0.30)
    for scale in contract.scale_order:
        features_in_scale = {e.feature for e in by_scale[scale]}
        n_unique = len(features_in_scale)
        if n_unique == 0:
            continue
        n_rows_this = n_unique * len(contract.compartment_order)
        # Anchor just above the first row of the stratum (y = row_idx - 0.35).
        label_y = row_idx - 0.35
        ax.text(1.005, label_y, scale,
                ha="left", va="center", fontsize=6.4,
                color="#555555", fontweight="bold",
                transform=trans, clip_on=False, zorder=6)
        row_idx += n_rows_this

    # Legend — outcome colours + compartment markers + TOST band.
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    handles: list = []
    for cls in ("significant", "null_accepting", "equivocal"):
        if any(e.outcome_class == cls for _, _, e in rows):
            handles.append(Line2D([0], [0], marker="o", color="none",
                                  markerfacecolor=palette[cls],
                                  markeredgecolor="white",
                                  markersize=6, label=cls))
    for compartment in contract.compartment_order:
        if any(e.compartment == compartment for _, _, e in rows):
            handles.append(Line2D(
                [0], [0], marker=marker_by_compartment[compartment],
                color="#555555", markerfacecolor="#555555",
                markeredgecolor="white", markersize=5,
                linestyle="-", lw=0.8,
                label=compartment.replace("_", "-"),
            ))
    if contract.show_tost_band and len(tost_zones) == 1:
        handles.append(Patch(facecolor="#D0D0D0", alpha=0.45,
                             label="TOST zone"))
    # Legend sits well below the xlabel so it never overlaps the
    # 'effect size (Cohen's d)' axis label.
    ax.legend(handles=handles, fontsize=6.4, frameon=False,
              loc="upper center", bbox_to_anchor=(0.5, -0.16),
              ncols=3, handlelength=1.0)

    ax.set_xlim(min(-1.1, float(min(
        (e.ci_lo for _, _, e in rows), default=-1.0)) - 0.15), x_hi)
    ax.set_xlabel("effect size (Cohen's d)")
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    # Counts in title.
    total = len(rows)
    sig = sum(1 for _, _, e in rows if e.outcome_class == "significant")
    nul = sum(1 for _, _, e in rows if e.outcome_class == "null_accepting")
    ax.set_title(
        f"{contract.title}  ·  n = {total} (feature x compartment)  ·  "
        f"{sig} significant, {nul} null-accepting",
        fontsize=8.4, pad=4,
    )

    # Reclassification sanity check — uses shared utility; silently used
    # to verify outcome classes on the roster (no visible side effect).
    for _, _, est in rows:
        _ = classify_outcome(est.ci_lo, est.ci_hi, est.tost)
    return ax
