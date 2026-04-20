"""Ensemble mean-squared displacement MSD(τ) per morphological state.

Log-log MSD vs τ per state with a power-law slope (α) fit per state
and a reference α = 1 (diffusive) guide. α ≈ 2 → ballistic,
α > 1 → super-diffusive, α < 1 → sub-diffusive.

Distinct from `cell_track_trajectory_field` (raw tracks, no ensemble
statistic) and `time_to_homing_survival` (survival, not MSD).
"""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class MSDByStateInput(RecipeContract):
    tau_s: list[float] = Field(..., min_length=3)
    msd_by_state: dict[str, list[float]] = Field(
        ..., description="state name → MSD(τ) in μm²"
    )
    msd_ci_by_state: dict[str, list[float]] | None = None
    alpha_fit_by_state: dict[str, float] | None = Field(
        None, description="per-state fitted slope on log-log axes"
    )
    title: str = "Ensemble MSD by state"


def _demo() -> MSDByStateInput:
    rng = np.random.default_rng(1123)
    tau = np.linspace(2.0, 120.0, 30)
    # Target α per state.
    alphas = {"homeostatic": 0.85, "surveillant": 1.20, "activated": 1.55}
    msd = {
        s: (2.0 * a * tau ** a + rng.normal(0, 0.10, tau.size))
        for s, a in alphas.items()
    }
    ci = {s: 0.18 * np.sqrt(msd[s]) for s in msd}
    return MSDByStateInput(
        tau_s=tau.tolist(),
        msd_by_state={s: np.clip(v, 0.1, None).tolist() for s, v in msd.items()},
        msd_ci_by_state={s: v.tolist() for s, v in ci.items()},
        alpha_fit_by_state=alphas,
    )


_META = RecipeMetadata(
    name="msd_curve_by_state",
    modality="intravital_imaging",
    family=RecipeFamily.timecourse_hierarchical_ci,
    answers_question=(
        "As a function of lag time, what is the MSD per morphological "
        "state, and is motion sub-, super-, or purely diffusive (α)?"
    ),
    required_fields=("tau_s", "msd_by_state"),
    optional_fields=("msd_ci_by_state", "alpha_fit_by_state", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=(
        "cell_track_trajectory_field", "time_to_homing_survival",
    ),
)


@register_recipe(
    metadata=_META,
    contract=MSDByStateInput,
    demo_contract=_demo,
)
def render(contract: MSDByStateInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 3.6))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    tau = np.asarray(contract.tau_s, float)
    ci_dict = contract.msd_ci_by_state or {}
    alphas = contract.alpha_fit_by_state or {}

    for name, vals in contract.msd_by_state.items():
        v = np.asarray(vals, float)
        color = (palette.pick(name) if name in palette.semantic
                 else palette[0])
        ci = np.asarray(ci_dict.get(name, []), float) if ci_dict else None
        if ci is not None and ci.size == v.size:
            ax.fill_between(tau, np.clip(v - ci / 2, 1e-2, None),
                            np.clip(v + ci / 2, 1e-2, None),
                            color=color, alpha=0.18, linewidth=0, zorder=2)
        a = alphas.get(name)
        label = (rf"{name}  $\alpha$={smart_fmt(float(a))}"
                 if a is not None else name)
        ax.plot(tau, v, color=color, lw=1.3, zorder=3, label=label)

    # α=1 reference line (pure diffusion).
    # Anchor through the median MSD at mid-τ to be visually useful.
    all_vals = np.concatenate([np.asarray(v, float)
                               for v in contract.msd_by_state.values()])
    mid_idx = len(tau) // 2
    # Use the anchor at tau[mid_idx] with median msd.
    ref_anchor = float(np.median(all_vals[mid_idx::len(tau)]))
    ref_anchor = max(ref_anchor, 1e-2)
    ref_curve = ref_anchor * (tau / tau[mid_idx]) ** 1.0
    ax.plot(tau, ref_curve, color="#888888", lw=0.8, ls="--", zorder=1,
            label=r"$\alpha$ = 1 (diffusive)")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(r"lag $\tau$ (s)")
    ax.set_ylabel(r"MSD ($\mu m^2$)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.6, frameon=False, loc="lower right",
              handlelength=1.6)
    ax.grid(which="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
