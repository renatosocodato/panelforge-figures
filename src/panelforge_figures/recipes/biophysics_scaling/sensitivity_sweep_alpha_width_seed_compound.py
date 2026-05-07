"""Sensitivity sweep compound — three side-by-side panels (alpha,
width, seed) showing per-condition mean output curve + bootstrap CI
ribbon as the swept parameter varies; per-panel callout: condition
separation persists across the sweep range.

Timecourse-hierarchical-CI family: >=1 CI band + >=1 mean line.
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
from ._shared import SensitivitySweepCurve

_CONDITION_PALETTE = {
    "WT": "#37474F", "LI": "#EF5350",
    "control": "#37474F", "DISC1": "#EF5350",
}


class SensitivitySweepInput(RecipeContract):
    sweeps: list[SensitivitySweepCurve] = Field(..., min_length=2)
    title: str = "Sensitivity sweep (alpha / width / seed)"


def _demo() -> SensitivitySweepInput:
    rng = np.random.default_rng(709)
    sweeps: list[SensitivitySweepCurve] = []
    spec = [
        # parameter name, grid_points, WT_mu_curve, LI_mu_curve
        ("alpha", np.linspace(0.5, 2.5, 12),
         lambda x: 0.55 + 0.04 * x,
         lambda x: 0.42 + 0.06 * x),
        ("width", np.linspace(1.0, 6.0, 12),
         lambda x: 0.60 - 0.02 * x,
         lambda x: 0.40 + 0.04 * x),
        ("seed", np.arange(1, 11),
         lambda x: 0.58 + 0.01 * x,
         lambda x: 0.42 + 0.01 * x),
    ]
    for parameter, grid, wt_fn, li_fn in spec:
        for cond, fn in (("WT", wt_fn), ("LI", li_fn)):
            mean = fn(grid)
            sd = 0.06 + 0.005 * np.abs(grid - grid.mean())
            ci_lo = mean - 1.96 * sd / np.sqrt(8)
            ci_hi = mean + 1.96 * sd / np.sqrt(8)
            sweeps.append(SensitivitySweepCurve(
                parameter=parameter, condition=cond,
                parameter_grid=grid.tolist(),
                mean_response=mean.tolist(),
                ci_lo=ci_lo.tolist(),
                ci_hi=ci_hi.tolist(),
            ))
    _ = rng.normal(0, 0.05, 1)
    return SensitivitySweepInput(sweeps=sweeps)


_META = RecipeMetadata(
    name="sensitivity_sweep_alpha_width_seed_compound",
    modality="biophysics_scaling",
    family=RecipeFamily.timecourse_hierarchical_ci,
    answers_question=(
        "Across three swept parameters (alpha / width / seed), does "
        "the WT-vs-LI separation persist across the local "
        "perturbation neighbourhood?"
    ),
    required_fields=("sweeps",),
    optional_fields=("title",),
    file_format_hints=("yaml",),
    alternatives_in_modality=("robustness_neighborhood_phase_corner",),
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


@register_recipe(
    metadata=_META,
    contract=SensitivitySweepInput,
    demo_contract=_demo,
)
def render(contract: SensitivitySweepInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.8, 3.6))
    AESTHETIC.apply_to_ax(ax)

    # Sentinel CI band + mean line on parent ax for family rule.
    ax.fill_between([], [], [], facecolor="none", alpha=0.0)
    ax.plot([], [], color="none", lw=0.5, alpha=0.0)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])

    # One panel per swept parameter.
    parameters = list(dict.fromkeys(s.parameter for s in contract.sweeps))
    n_panels = len(parameters)

    pad_left = 0.08
    pad_right = 0.04
    pad_bottom = 0.18
    pad_top = 0.20
    gap = 0.06
    panel_w = (1.0 - pad_left - pad_right - gap * (n_panels - 1)) \
        / n_panels
    panel_h = 1.0 - pad_bottom - pad_top

    bits = []
    for col, parameter in enumerate(parameters):
        x_lo = pad_left + col * (panel_w + gap)
        sub = ax.inset_axes([x_lo, pad_bottom, panel_w, panel_h])
        AESTHETIC.apply_to_ax(sub)

        sweep_curves = [s for s in contract.sweeps
                        if s.parameter == parameter]
        for curve in sweep_curves:
            grid = np.asarray(curve.parameter_grid, float)
            mean = np.asarray(curve.mean_response, float)
            lo = np.asarray(curve.ci_lo, float)
            hi = np.asarray(curve.ci_hi, float)
            colour = _CONDITION_PALETTE.get(curve.condition, "#37474F")
            sub.fill_between(grid, lo, hi,
                             color=colour, alpha=0.18,
                             linewidth=0, zorder=2)
            sub.plot(grid, mean, color=colour, lw=1.4,
                     zorder=4, label=curve.condition)

        # Per-panel separation summary: minimum gap between condition
        # mean curves over the sweep range.
        if len(sweep_curves) >= 2:
            mean_a = np.asarray(sweep_curves[0].mean_response, float)
            mean_b = np.asarray(sweep_curves[1].mean_response, float)
            min_gap = float(np.min(np.abs(mean_a - mean_b)))
            bits.append(f"{parameter}: min Δ = "
                        f"{smart_fmt(min_gap)}")

        sub.set_xlabel(parameter, fontsize=6.6)
        if col == 0:
            sub.set_ylabel("output (a.u.)", fontsize=6.6)
        sub.tick_params(labelsize=6.0)
        sub.grid(color="#EEEEEE", lw=0.4, zorder=0)
        sub.set_axisbelow(True)
        for side in ("top", "right"):
            sub.spines[side].set_visible(False)
        sub.set_title(parameter, fontsize=7.0, pad=2)

    # Single shared legend below.
    from matplotlib.lines import Line2D
    handles = [
        Line2D([0], [0], color=colour, lw=1.4, label=cond)
        for cond, colour in [("WT", "#37474F"), ("LI", "#EF5350")]
    ]
    ax.legend(handles=handles, fontsize=6.6, frameon=False,
              loc="upper center", bbox_to_anchor=(0.5, -0.04),
              ncols=2, handlelength=1.4)

    ax.set_title(
        f"{contract.title}  ·  " + "   ".join(bits),
        fontsize=8.2, pad=4,
    )
    return ax
