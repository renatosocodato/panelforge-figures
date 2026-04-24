"""Equivalence forest with TOST bounds — effect-size forest with a
shaded equivalence zone; rows colour-coded by TOST outcome.

Operationalizes the pre-registered equivalence grammar: features whose
CI lies entirely inside the TOST margins are *positive null-accepting*
constraints on the pathway, not failed tests. Reviewers (PNAS / eLife)
actively look for this pattern.

Coef-forest family: >=3 markers + >=1 reference line. Satisfied by
>=3 feature rows + the x=0 null reference.
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
    smart_fmt,
    tost_band_patch,
)
from ._aesthetic import AESTHETIC
from ._shared import (
    OUTCOME_PALETTE_DEFAULT,
    EffectSizeEstimate,
    _demo_estimate_roster,
)


class EquivalenceForestInput(RecipeContract):
    estimates: list[EffectSizeEstimate] = Field(..., min_length=3)
    tost_shading: bool = True
    sort_rule: str = Field(
        "tost_distance",
        description="'abs_d' | 'tost_distance' | 'feature'",
    )
    show_outcome_colour: bool = True
    annotate_n: bool = True
    compartment_filter: str | None = Field(
        None,
        description=(
            "optional compartment filter; if set, only estimates matching "
            "this compartment are plotted"
        ),
    )
    title: str = "Equivalence forest"


def _demo() -> EquivalenceForestInput:
    # Take the whole-cell compartment slice from the shared roster so the
    # forest is readable (one row per feature, no compartment duplication).
    return EquivalenceForestInput(
        estimates=_demo_estimate_roster(),
        compartment_filter="whole_cell",
    )


_META = RecipeMetadata(
    name="equivalence_forest_with_tost_bounds",
    modality="biophysics_scaling",
    family=RecipeFamily.coef_forest,
    answers_question=(
        "Which features lie inside the pre-registered TOST equivalence "
        "zone (null-accepting), which sit outside it (significant), "
        "and which straddle a bound (equivocal)?"
    ),
    required_fields=("estimates",),
    optional_fields=(
        "tost_shading", "sort_rule", "show_outcome_colour",
        "annotate_n", "compartment_filter", "title",
    ),
    file_format_hints=("yaml", "json"),
    alternatives_in_modality=("hierarchical_effect_size_ladder",),
)


def _sort_key(est: EffectSizeEstimate, rule: str) -> float | str:
    if rule == "abs_d":
        return -abs(est.d)
    if rule == "feature":
        return est.feature
    # "tost_distance": smallest |d - nearest-bound| first (i.e. most
    # ambiguous at the top).
    if est.d < est.tost.lower:
        dist = est.tost.lower - est.d
    elif est.d > est.tost.upper:
        dist = est.d - est.tost.upper
    else:
        dist = min(est.d - est.tost.lower, est.tost.upper - est.d)
    return dist


@register_recipe(
    metadata=_META,
    contract=EquivalenceForestInput,
    demo_contract=_demo,
)
def render(contract: EquivalenceForestInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.8, 4.2))
    AESTHETIC.apply_to_ax(ax)

    palette = AESTHETIC.outcome_palette or OUTCOME_PALETTE_DEFAULT

    ests = list(contract.estimates)
    if contract.compartment_filter is not None:
        ests = [e for e in ests if e.compartment == contract.compartment_filter]
    if len(ests) < 3:
        raise ValueError(
            "Equivalence forest needs >=3 estimates after filtering; "
            f"got {len(ests)}."
        )
    ests.sort(key=lambda e: _sort_key(e, contract.sort_rule))

    y = np.arange(len(ests))

    # TOST band — assumes uniform zone across rows; if not, we draw the
    # widest zone so that every row's band is visibly covered.
    zones = [(e.tost.lower, e.tost.upper) for e in ests]
    if contract.tost_shading:
        band_lo = min(z[0] for z in zones)
        band_hi = max(z[1] for z in zones)
        tost_band_patch(ax, band_lo, band_hi, orientation="y",
                        color="#D0D0D0", alpha=0.40, zorder=1,
                        label="TOST equivalence zone")

    ax.axvline(0.0, color="#888888", lw=0.5, ls="--", zorder=2)

    # Rows.
    for yi, est in zip(y, ests):
        outcome = (classify_outcome(est.ci_lo, est.ci_hi, est.tost)
                   if contract.show_outcome_colour else "equivocal")
        colour = palette.get(outcome, palette["equivocal"])
        ax.plot([est.ci_lo, est.ci_hi], [yi, yi],
                color=colour, lw=1.1, alpha=0.85, zorder=3)
        ax.scatter([est.d], [yi], s=44, marker="o",
                   color=colour, edgecolor="white", linewidth=0.6,
                   zorder=5)

    # Row labels = feature; optional N annotation to the right.
    tick_labels: list[str] = []
    for est in ests:
        label = est.feature
        if contract.annotate_n and est.n_per_group:
            n_str = " / ".join(
                f"n_{k}={v}" for k, v in est.n_per_group.items()
            )
            label = f"{est.feature}  ({n_str})"
        tick_labels.append(label)
    ax.set_yticks(y)
    ax.set_yticklabels(tick_labels, fontsize=6.8)
    ax.invert_yaxis()

    ax.set_xlabel("effect size (Cohen's d)")
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    # Legend — outcome colours + TOST band.
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    handles: list = []
    counts: dict[str, int] = {
        "significant": 0, "null_accepting": 0, "equivocal": 0,
    }
    for est in ests:
        oc = classify_outcome(est.ci_lo, est.ci_hi, est.tost)
        counts[oc] = counts.get(oc, 0) + 1
    for cls in ("significant", "null_accepting", "equivocal"):
        if counts[cls]:
            handles.append(Line2D(
                [0], [0], marker="o", color="none",
                markerfacecolor=palette[cls],
                markeredgecolor="white", markersize=6,
                label=f"{cls} (n={counts[cls]})",
            ))
    if contract.tost_shading:
        handles.append(Patch(facecolor="#D0D0D0", alpha=0.45,
                             label="TOST zone"))
    ax.legend(handles=handles, fontsize=6.4, frameon=False,
              loc="upper right", handlelength=1.2)

    ax.set_title(
        f"{contract.title}  ·  "
        f"{counts['significant']} sig  ·  "
        f"{counts['null_accepting']} null-accept  ·  "
        f"{counts['equivocal']} equivocal  "
        f"(TOST [{smart_fmt(zones[0][0])}, {smart_fmt(zones[0][1])}])",
        fontsize=8.4, pad=4,
    )
    return ax
