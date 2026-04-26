"""Directional persistence autocorrelation — C(tau) = <cos(d_theta)>
per condition with bootstrap CI ribbons and fitted exponential
persistence time tau_p.

Timecourse-hierarchical-CI family: >=1 CI band + >=1 mean line.
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
from ._shared import KinematicFeatureBundle

_CONDITION_PALETTE = {
    "control": "#37474F", "DISC1": "#EF5350",
    "WT": "#37474F", "LI": "#EF5350",
}


class DirectionalPersistenceAutocorrInput(RecipeContract):
    bundles: list[KinematicFeatureBundle] = Field(..., min_length=4)
    condition_by_cell: dict[str, str] = Field(...)
    tau_max_s: float = 60.0
    fit_exponential: bool = True
    title: str = "Directional persistence autocorrelation"


def _demo() -> DirectionalPersistenceAutocorrInput:
    rng = np.random.default_rng(3041)
    bundles: list[KinematicFeatureBundle] = []
    cond_by: dict[str, str] = {}
    # Persistence times: control ~12 s (less memory), DISC1 ~25 s
    # (more memory).
    for cond, tau_p in (("control", 12.0), ("DISC1", 25.0)):
        for k in range(40):
            n_t = 200
            # Generate heading via OU on the angle: dθ = -θ/τ_p dt + σ dW.
            heading = np.zeros(n_t)
            heading[0] = rng.uniform(-180, 180)
            for t in range(1, n_t):
                heading[t] = (heading[t-1] * np.exp(-1.0 / tau_p)
                              + rng.normal(0, 30 * np.sqrt(1 - np.exp(-2.0 / tau_p))))
            cell_id = f"{cond}_C{k:02d}"
            bundles.append(KinematicFeatureBundle(
                cell_id=cell_id,
                t_s=list(range(n_t)),
                heading_deg=heading.tolist(),
            ))
            cond_by[cell_id] = cond
    return DirectionalPersistenceAutocorrInput(
        bundles=bundles, condition_by_cell=cond_by,
    )


_META = RecipeMetadata(
    name="directional_persistence_autocorr",
    modality="intravital_imaging",
    family=RecipeFamily.timecourse_hierarchical_ci,
    answers_question=(
        "Per condition, what is the directional autocorrelation "
        "C(tau) and the fitted persistence time tau_p?"
    ),
    required_fields=("bundles", "condition_by_cell"),
    optional_fields=("tau_max_s", "fit_exponential", "title"),
    file_format_hints=("yaml", "json"),
    alternatives_in_modality=("chemotaxis_index_trajectory",),
)


@register_recipe(
    metadata=_META,
    contract=DirectionalPersistenceAutocorrInput,
    demo_contract=_demo,
)
def render(contract: DirectionalPersistenceAutocorrInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 3.8))
    AESTHETIC.apply_to_ax(ax)

    tau_grid = np.arange(1, int(contract.tau_max_s) + 1)
    by_cond: dict[str, list[np.ndarray]] = {}
    for b in contract.bundles:
        cond = contract.condition_by_cell.get(b.cell_id, "?")
        if b.heading_deg is None:
            continue
        head = np.asarray(b.heading_deg, float)
        per_tau = []
        for tau in tau_grid:
            if tau >= head.size:
                per_tau.append(np.nan)
                continue
            d_theta = head[tau:] - head[:-tau]
            per_tau.append(float(np.mean(np.cos(np.deg2rad(d_theta)))))
        by_cond.setdefault(cond, []).append(np.asarray(per_tau))

    bits = []
    for cond, curves in by_cond.items():
        arr = np.asarray(curves)
        mean_c = np.nanmean(arr, axis=0)
        rng = np.random.default_rng(11)
        boot = []
        for _ in range(100):
            idx = rng.integers(0, arr.shape[0], size=arr.shape[0])
            boot.append(np.nanmean(arr[idx], axis=0))
        boot_arr = np.asarray(boot)
        lo = np.nanquantile(boot_arr, 0.025, axis=0)
        hi = np.nanquantile(boot_arr, 0.975, axis=0)
        colour = _CONDITION_PALETTE.get(cond, "#37474F")
        ax.plot(tau_grid, mean_c, color=colour, lw=1.4,
                zorder=4, label=cond)
        ax.fill_between(tau_grid, lo, hi, color=colour, alpha=0.18,
                        linewidth=0, zorder=2)
        # Fit exponential C(tau) = exp(-tau / tau_p) on positive part.
        if contract.fit_exponential:
            valid = (mean_c > 0.05) & np.isfinite(mean_c)
            if valid.sum() >= 3:
                tau_p = -1.0 / np.polyfit(tau_grid[valid],
                                          np.log(mean_c[valid]), 1)[0]
                bits.append(f"{cond}: tau_p = {smart_fmt(float(tau_p))} s")

    ax.axhline(0, color="#DDDDDD", lw=0.4, zorder=1)
    ax.set_xlabel("lag tau (s)")
    ax.set_ylabel("C(tau) = <cos(d_theta)>")
    ax.set_ylim(-0.2, 1.05)
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(fontsize=6.8, frameon=False, loc="upper right",
              handlelength=1.4)
    ax.set_title(
        f"{contract.title}  ·  " + "   ".join(bits),
        fontsize=8.2, pad=4,
    )
    return ax
