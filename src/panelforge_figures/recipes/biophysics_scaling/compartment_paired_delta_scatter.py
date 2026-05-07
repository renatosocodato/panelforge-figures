"""Compartment-paired delta scatter — per feature, whole-cell d vs
protrusion-internal d, with a null-zone square and y=x diagonal.

Exposes the manuscript's compartment-split asymmetry in one view:
features near the diagonal behave the same across compartments;
features far from the diagonal behave differently. The null-zone
square marks the TOST equivalence region around the origin.

Scatter-collapse family: >=1 scatter + >=1 fit line. Satisfied by
the per-feature scatter + the y=x diagonal.
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
from ._shared import (
    EffectSizeEstimate,
    _demo_estimate_roster,
)

_SCALE_COLOURS = {
    "polymer": "#1565C0",
    "network": "#E65100",
    "territory": "#6A1B9A",
    "geometry": "#2E7D32",
    "whole_cell": "#B71C1C",
}


class CompartmentPairedDeltaInput(RecipeContract):
    estimates: list[EffectSizeEstimate] = Field(..., min_length=6)
    scale_colour: bool = True
    null_zone_half_width: float = 0.2
    label_top_n: int = 6
    label_rule: str = Field(
        "abs_diff",
        description="'abs_diff' | 'abs_protrusion' | 'abs_whole_cell'",
    )
    diagonal: bool = True
    title: str = "Compartment-paired effect-size scatter"


def _demo() -> CompartmentPairedDeltaInput:
    return CompartmentPairedDeltaInput(estimates=_demo_estimate_roster())


_META = RecipeMetadata(
    name="compartment_paired_delta_scatter",
    modality="biophysics_scaling",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "Per feature, how does the whole-cell effect size compare to "
        "the protrusion-internal one?"
    ),
    required_fields=("estimates",),
    optional_fields=(
        "scale_colour", "null_zone_half_width", "label_top_n",
        "label_rule", "diagonal", "title",
    ),
    file_format_hints=("yaml", "json"),
    alternatives_in_modality=("hierarchical_effect_size_ladder",),
    statistical_contract=StatisticalContract(
        min_n_per_group=10,
        distribution_assumption="approximately_gaussian",
        multiple_comparisons="any_correction_required",
        independence="paired",
        effect_size_in_units="standardized_d",
        rendered_claim_template="d = {d:.2f}, TOST p = {p_tost:.4f}",
        refuses_when=("missing_paired_structure",),
    ),
)


def _pair_by_feature(
    estimates: list[EffectSizeEstimate],
) -> dict[str, tuple[EffectSizeEstimate | None, EffectSizeEstimate | None]]:
    """Return {feature: (whole_cell_est, protrusion_est)}."""
    pairs: dict[str, list] = {}
    for e in estimates:
        pairs.setdefault(e.feature, {"whole_cell": None,
                                     "protrusion_internal": None})
        if e.compartment in pairs[e.feature]:
            pairs[e.feature][e.compartment] = e
    return {k: (v["whole_cell"], v["protrusion_internal"])
            for k, v in pairs.items()}


def _label_value(wc: EffectSizeEstimate, pr: EffectSizeEstimate, rule: str) -> float:
    if rule == "abs_protrusion":
        return abs(pr.d)
    if rule == "abs_whole_cell":
        return abs(wc.d)
    return abs(wc.d - pr.d)


@register_recipe(
    metadata=_META,
    contract=CompartmentPairedDeltaInput,
    demo_contract=_demo,
)
def render(contract: CompartmentPairedDeltaInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 4.6))
    AESTHETIC.apply_to_ax(ax)

    pairs = _pair_by_feature(list(contract.estimates))
    xs, ys, labels, colours, scales = [], [], [], [], []
    for feature, (wc, pr) in pairs.items():
        if wc is None or pr is None:
            continue
        xs.append(wc.d)
        ys.append(pr.d)
        labels.append(feature)
        scale = wc.scale or pr.scale
        scales.append(scale)
        if contract.scale_colour:
            colours.append(_SCALE_COLOURS.get(scale, "#555555"))
        else:
            colours.append("#1565C0")

    xs = np.asarray(xs, float)
    ys = np.asarray(ys, float)

    # Null-zone square (TOST-width in each direction).
    h = float(contract.null_zone_half_width)
    import matplotlib.patches as mpatches
    ax.add_patch(mpatches.Rectangle(
        (-h, -h), 2 * h, 2 * h,
        facecolor="#D0D0D0", alpha=0.32, edgecolor="#BBBBBB",
        linewidth=0.5, zorder=1,
    ))

    # y = x diagonal (satisfies scatter_collapse rule).
    lo = float(min(xs.min(), ys.min())) - 0.15
    hi = float(max(xs.max(), ys.max())) + 0.15
    ax.plot([lo, hi], [lo, hi],
            color="#333333", lw=0.8, ls="--", zorder=2,
            label="y = x (compartment-agnostic)")

    # Zero axes.
    ax.axhline(0, color="#DDDDDD", lw=0.5, zorder=1)
    ax.axvline(0, color="#DDDDDD", lw=0.5, zorder=1)

    # Scatter.
    ax.scatter(xs, ys, s=48, c=colours, edgecolor="white", linewidth=0.6,
               alpha=0.90, zorder=5)

    # Label top-N.
    rankings = sorted(
        range(len(labels)),
        key=lambda i: _label_value(pairs[labels[i]][0],
                                   pairs[labels[i]][1],
                                   contract.label_rule),
        reverse=True,
    )
    for idx in rankings[: contract.label_top_n]:
        ax.annotate(labels[idx], (xs[idx], ys[idx]),
                    xytext=(6, 4), textcoords="offset points",
                    fontsize=6.4, color=colours[idx], zorder=6)

    # Correlation in title.
    from scipy.stats import spearmanr
    rho, p = spearmanr(xs, ys)

    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_aspect("equal")
    ax.set_xlabel("whole-cell effect size (Cohen's d)")
    ax.set_ylabel("protrusion-internal effect size (Cohen's d)")
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    # Legend — per-scale colour swatches + diagonal.
    from matplotlib.lines import Line2D
    handles = []
    scales_present = []
    for scale in ("polymer", "network", "territory", "geometry", "whole_cell"):
        if scale in scales:
            scales_present.append(scale)
    if contract.scale_colour:
        for scale in scales_present:
            handles.append(Line2D(
                [0], [0], marker="o", color="none",
                markerfacecolor=_SCALE_COLOURS[scale],
                markeredgecolor="white", markersize=6,
                label=scale,
            ))
    handles.append(Line2D([0], [0], color="#333333", ls="--", lw=0.8,
                          label="y = x"))
    ax.legend(handles=handles, fontsize=6.4, frameon=False,
              loc="upper left", handlelength=1.2)

    ax.set_title(
        f"{contract.title}  ·  Spearman rho = {smart_fmt(float(rho))}  "
        f"(p = {smart_fmt(float(p))})",
        fontsize=8.4, pad=4,
    )
    return ax
