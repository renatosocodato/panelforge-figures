"""Residence-time Kaplan-Meier with KS overlay — per-state KM survival
curves of residence times, overlaid with paired KS test p-values
against a reference stratum.

Each state gets one KM step curve showing the cumulative fraction
remaining in that state vs time elapsed. A vertical median-residence
reference line marks the 50% crossing per state, and a right-margin
KS p-value annotation surfaces statistically significant departures
from the reference state's residence-time distribution.

Diagnostic-curve family: >=1 curve + >=1 reference.  Satisfied by
per-state KM step curves + the per-state median reference lines.
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
from ._shared import ResidenceStratum, _demo_state_palette


class ResidenceTimeKMInput(RecipeContract):
    strata: list[ResidenceStratum] = Field(..., min_length=2)
    reference_state: str | None = None
    title: str = "Residence-time Kaplan-Meier with KS overlay"


def _demo() -> ResidenceTimeKMInput:
    rng = np.random.default_rng(835)
    # Manuscript F2E values: 3 states with distinct residence-time
    # distributions; reference = homeostatic.
    spec = [
        ("homeostatic", 12.0, 0.92),
        ("surveillant",  6.0, 0.88),
        ("activated",    9.0, 0.78),
    ]
    strata: list[ResidenceStratum] = []
    for state, scale, frac in spec:
        n = 80
        # Exponential residence times truncated at 60 min.
        rt = rng.exponential(scale, n)
        rt = np.minimum(rt, 60.0)
        cens = rng.uniform(0, 1, n) >= frac   # right-censored if uniform >= frac
        # KS p-value vs reference (homeostatic): hand-anchored.
        ks_p = 1.0 if state == "homeostatic" else (
            5.4e-7 if state == "surveillant" else 1.2e-2
        )
        median = float(np.median(rt))
        strata.append(ResidenceStratum(
            state=state,
            residence_time_min=rt.tolist(),
            censored=cens.tolist(),
            ks_p_value_vs_reference=ks_p,
            median_residence_min=median,
            n_subjects=n,
        ))
    return ResidenceTimeKMInput(strata=strata,
                                reference_state="homeostatic")


_META = RecipeMetadata(
    name="residence_time_kaplan_meier_with_ks_overlay",
    modality="intravital_imaging",
    family=RecipeFamily.diagnostic_curve,
    answers_question=(
        "Per decoded state, what does the Kaplan-Meier residence-time "
        "survival curve look like, and which states differ "
        "significantly from the reference state's residence-time "
        "distribution by KS test?"
    ),
    required_fields=("strata",),
    optional_fields=("reference_state", "title"),
    file_format_hints=("csv", "yaml"),
    alternatives_in_modality=(
        "time_to_homing_survival",
        "sojourn_survival_per_state",
    ),
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


def _km_curve(times: np.ndarray, censored: np.ndarray):
    """Compute Kaplan-Meier survival curve from times + censoring flags.

    Returns (curve_t, curve_s) for step plotting.
    """
    order = np.argsort(times)
    t = times[order]
    c = censored[order]
    n_at_risk = t.size
    s = 1.0
    curve_t = [0.0]
    curve_s = [1.0]
    for ti, ci in zip(t, c):
        if not ci:
            # Event observed; update survival.
            s *= (n_at_risk - 1) / max(n_at_risk, 1)
            curve_t.append(float(ti))
            curve_s.append(s)
        n_at_risk -= 1
    return curve_t, curve_s


@register_recipe(
    metadata=_META,
    contract=ResidenceTimeKMInput,
    demo_contract=_demo,
)
def render(contract: ResidenceTimeKMInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 3.8))
    AESTHETIC.apply_to_ax(ax)

    state_names = [s.state for s in contract.strata]
    palette = _demo_state_palette(state_names)

    summary_bits: list[str] = []
    for stratum in contract.strata:
        t = np.asarray(stratum.residence_time_min, float)
        c = np.asarray(
            stratum.censored if stratum.censored is not None
            else [False] * t.size,
            bool,
        )
        colour = palette.get(stratum.state, "#888888")
        curve_t, curve_s = _km_curve(t, c)
        ax.step(curve_t, curve_s, where="post",
                color=colour, lw=1.4, alpha=0.92, zorder=3,
                label=f"{stratum.state}  (n={stratum.n_subjects})")
        # Median residence reference (the >=1 reference for the
        # diagnostic_curve family rule).
        if stratum.median_residence_min is not None:
            ax.plot(
                [stratum.median_residence_min, stratum.median_residence_min],
                [0.0, 0.5],
                color=colour, lw=0.7, ls=":", zorder=2,
            )
            ax.scatter(
                [stratum.median_residence_min], [0.5],
                s=22, marker="v", color=colour,
                edgecolor="white", linewidth=0.5, zorder=4,
            )
        # Per-state KS p-value annotation.
        sig_marker = ""
        if (stratum.ks_p_value_vs_reference is not None
                and stratum.ks_p_value_vs_reference < 0.05
                and stratum.state != contract.reference_state):
            sig_marker = " *"
        if stratum.ks_p_value_vs_reference is not None:
            summary_bits.append(
                f"{stratum.state}: KS p="
                f"{smart_fmt(stratum.ks_p_value_vs_reference)}{sig_marker}"
            )

    # Horizontal 50%-survival reference (a second family-rule reference).
    ax.axhline(0.5, color="#888888", lw=0.6, ls="--", zorder=1)

    ax.set_xlabel("residence time (min)")
    ax.set_ylabel("fraction remaining in state")
    ax.set_xlim(left=0)
    ax.set_ylim(0.0, 1.02)
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    ax.legend(fontsize=6.4, frameon=False,
              loc="upper right", handlelength=1.6)

    ref_label = contract.reference_state or "—"
    ax.set_title(
        f"{contract.title}  ·  ref: {ref_label}  ·  "
        + "  ·  ".join(summary_bits),
        fontsize=7.4, pad=4,
    )
    return ax
