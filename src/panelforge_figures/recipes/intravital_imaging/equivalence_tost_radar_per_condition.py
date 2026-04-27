"""Equivalence TOST radar per condition — multi-feature polar plot
of |observed effect| vs equivalence margin per feature; condition
polygon is filled, reference circle = equivalence margin (TOST
classification: 'equivalent' inside, 'inequivalent' outside).

Radar family: >=1 polar axis + >=1 filled polygon.
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
)
from ._aesthetic import AESTHETIC


class EquivalenceFeatureRow(RecipeContract):
    feature: str
    condition: str
    observed_effect: float                # signed
    se: float
    margin: float                         # equivalence margin (>0)


class EquivalenceTOSTRadarInput(RecipeContract):
    rows: list[EquivalenceFeatureRow] = Field(..., min_length=6)
    title: str = "Equivalence TOST radar per condition"


def _demo() -> EquivalenceTOSTRadarInput:
    rng = np.random.default_rng(3271)
    features = ["velocity", "length_rate", "curvature", "turning_angle",
                "directionality"]
    margin = 0.20
    rows: list[EquivalenceFeatureRow] = []
    # control vs reference: all features within margin (equivalent).
    for f in features:
        rows.append(EquivalenceFeatureRow(
            feature=f, condition="control",
            observed_effect=float(rng.normal(0, 0.06)),
            se=0.05, margin=margin,
        ))
    # DISC1 vs reference: 2/5 features escape margin.
    disc_effects = {
        "velocity": 0.32, "length_rate": -0.28,
        "curvature": 0.08, "turning_angle": -0.05,
        "directionality": 0.10,
    }
    for f, e in disc_effects.items():
        rows.append(EquivalenceFeatureRow(
            feature=f, condition="DISC1",
            observed_effect=float(e + rng.normal(0, 0.02)),
            se=0.06, margin=margin,
        ))
    return EquivalenceTOSTRadarInput(rows=rows)


_META = RecipeMetadata(
    name="equivalence_tost_radar_per_condition",
    modality="intravital_imaging",
    family=RecipeFamily.radar,
    answers_question=(
        "Per feature, does the condition pass the equivalence test "
        "(observed |effect| < margin), and on which axes does the "
        "condition escape equivalence?"
    ),
    required_fields=("rows",),
    optional_fields=("title",),
    file_format_hints=("yaml", "csv"),
    alternatives_in_modality=("commitment_vs_chemotaxis_contingency",),
)


_CONDITION_PALETTE = {
    "control": "#37474F", "DISC1": "#EF5350",
    "WT": "#37474F", "LI": "#EF5350",
}


@register_recipe(
    metadata=_META,
    contract=EquivalenceTOSTRadarInput,
    demo_contract=_demo,
)
def render(contract: EquivalenceTOSTRadarInput, ax=None, **_):
    import matplotlib.pyplot as plt
    if ax is None:
        fig = plt.figure(figsize=(4.8, 4.4))
        ax = fig.add_subplot(111, polar=True)
    elif not hasattr(ax, "set_theta_offset"):
        # Caller gave a cartesian axis — replace with polar.
        fig = ax.figure
        pos = ax.get_subplotspec()
        ax.remove()
        ax = fig.add_subplot(pos, polar=True)

    AESTHETIC.apply_to_fig(ax.figure)

    features = list(dict.fromkeys(r.feature for r in contract.rows))
    n_f = len(features)
    theta = np.linspace(0, 2 * np.pi, n_f, endpoint=False)
    theta_closed = np.concatenate([theta, theta[:1]])

    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(theta)
    ax.set_xticklabels(features, fontsize=6.8)

    # Find a sensible radial scale.
    all_eff = [abs(r.observed_effect) for r in contract.rows]
    all_margin = [r.margin for r in contract.rows]
    r_max = max(max(all_eff), max(all_margin)) * 1.25
    ax.set_ylim(0, r_max)
    ax.set_yticks(np.linspace(0, r_max, 5)[1:])
    ax.set_yticklabels(
        [f"{smart_fmt(t)}" for t in np.linspace(0, r_max, 5)[1:]],
        fontsize=6.0, color="#666666",
    )
    ax.spines["polar"].set_color("#BBBBBB")
    ax.grid(color="#DDDDDD", lw=0.5)

    # Equivalence margin reference circle (uses the median margin —
    # demos pin one margin; production data may vary per feature).
    margin_med = float(np.median(all_margin))
    margin_closed = np.full(n_f + 1, margin_med)
    ax.fill(theta_closed, margin_closed, color="#26A69A", alpha=0.10,
            zorder=1, label="equivalence margin")
    ax.plot(theta_closed, margin_closed, color="#26A69A", lw=1.0,
            ls="--", zorder=2)

    # Per-condition polygons.
    conditions = list(dict.fromkeys(r.condition for r in contract.rows))
    bits = []
    for cond in conditions:
        rows_cond = {r.feature: r for r in contract.rows
                     if r.condition == cond}
        vals = [abs(rows_cond[f].observed_effect)
                if f in rows_cond else 0.0 for f in features]
        v_closed = np.concatenate([vals, vals[:1]])
        colour = _CONDITION_PALETTE.get(cond, "#888888")
        ax.plot(theta_closed, v_closed, color=colour, lw=1.2,
                zorder=4, label=cond)
        ax.fill(theta_closed, v_closed, color=colour, alpha=0.18,
                zorder=3)
        # Per-feature TOST classification (null_accepting = within
        # equivalence margin under the standard TOST decision rule).
        n_equiv = 0
        n_total = 0
        for f in features:
            if f not in rows_cond:
                continue
            r = rows_cond[f]
            ci_lo = r.observed_effect - 1.96 * r.se
            ci_hi = r.observed_effect + 1.96 * r.se
            outcome = classify_outcome(ci_lo, ci_hi,
                                       lower=-r.margin, upper=r.margin)
            if outcome == "null_accepting":
                n_equiv += 1
            n_total += 1
        bits.append(f"{cond}: {n_equiv}/{n_total} equiv")

    ax.set_title(
        f"{contract.title}  ·  margin = {smart_fmt(margin_med)}  ·  "
        + "   ".join(bits),
        fontsize=8.4, pad=14,
    )

    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles, labels,
              loc="upper center", bbox_to_anchor=(0.5, -0.08),
              fontsize=6.4, ncol=min(len(conditions) + 1, 3),
              frameon=False, handlelength=1.6)
    return ax
