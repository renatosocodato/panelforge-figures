"""Speed-commitment coupling — cross-correlation between velocity
and length-rate per condition with bootstrap CI ribbons; peak-lag
callout shows whether speed leads or lags length-rate.

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


class SpeedCommitmentCouplingInput(RecipeContract):
    bundles: list[KinematicFeatureBundle] = Field(..., min_length=4)
    condition_by_cell: dict[str, str] = Field(...)
    lag_range_s: tuple[float, float] = (-30.0, 30.0)
    title: str = "Speed - length-rate cross-correlation"


def _demo() -> SpeedCommitmentCouplingInput:
    rng = np.random.default_rng(3061)
    bundles: list[KinematicFeatureBundle] = []
    cond_by: dict[str, str] = {}
    # Length-rate leads velocity by 6 s in control; no clear lag in DISC1.
    for cond, lag in (("control", 6), ("DISC1", 0)):
        for k in range(15):
            n_t = 200
            length_rate = rng.normal(0, 1.0, n_t)
            velocity = np.r_[
                rng.normal(0, 0.4, lag),
                length_rate[:-lag] * 0.7 + rng.normal(0, 0.4, n_t - lag),
            ] if lag > 0 else length_rate * 0.5 + rng.normal(0, 0.6, n_t)
            cell_id = f"{cond}_C{k:02d}"
            bundles.append(KinematicFeatureBundle(
                cell_id=cell_id,
                t_s=list(range(n_t)),
                velocity_um_per_min=velocity.tolist(),
                length_rate_um_per_min=length_rate.tolist(),
            ))
            cond_by[cell_id] = cond
    return SpeedCommitmentCouplingInput(
        bundles=bundles, condition_by_cell=cond_by,
    )


_META = RecipeMetadata(
    name="speed_commitment_coupling",
    modality="intravital_imaging",
    family=RecipeFamily.timecourse_hierarchical_ci,
    answers_question=(
        "Does protrusion length-rate lead or lag tip velocity, and "
        "does the relationship differ between conditions?"
    ),
    required_fields=("bundles", "condition_by_cell"),
    optional_fields=("lag_range_s", "title"),
    file_format_hints=("yaml", "json"),
    alternatives_in_modality=("chemotaxis_index_trajectory",),
)


@register_recipe(
    metadata=_META,
    contract=SpeedCommitmentCouplingInput,
    demo_contract=_demo,
)
def render(contract: SpeedCommitmentCouplingInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 3.8))
    AESTHETIC.apply_to_ax(ax)

    lag_lo, lag_hi = contract.lag_range_s
    lag_grid = np.arange(int(lag_lo), int(lag_hi) + 1)
    by_cond: dict[str, list[np.ndarray]] = {}
    for b in contract.bundles:
        cond = contract.condition_by_cell.get(b.cell_id, "?")
        if b.velocity_um_per_min is None or b.length_rate_um_per_min is None:
            continue
        v = np.asarray(b.velocity_um_per_min, float)
        lr = np.asarray(b.length_rate_um_per_min, float)
        v = (v - v.mean()) / max(v.std(), 1e-9)
        lr = (lr - lr.mean()) / max(lr.std(), 1e-9)
        per_lag = []
        for lag in lag_grid:
            if lag == 0:
                per_lag.append(float(np.mean(v * lr)))
            elif lag > 0:
                per_lag.append(float(np.mean(v[lag:] * lr[:-lag])))
            else:
                per_lag.append(float(np.mean(v[:lag] * lr[-lag:])))
        by_cond.setdefault(cond, []).append(np.asarray(per_lag))

    bits = []
    for cond, curves in by_cond.items():
        arr = np.asarray(curves)
        mean_c = arr.mean(axis=0)
        rng = np.random.default_rng(13)
        boot = []
        for _ in range(100):
            idx = rng.integers(0, arr.shape[0], size=arr.shape[0])
            boot.append(arr[idx].mean(axis=0))
        boot_arr = np.asarray(boot)
        lo = np.quantile(boot_arr, 0.025, axis=0)
        hi = np.quantile(boot_arr, 0.975, axis=0)
        colour = _CONDITION_PALETTE.get(cond, "#37474F")
        ax.plot(lag_grid, mean_c, color=colour, lw=1.4,
                zorder=4, label=cond)
        ax.fill_between(lag_grid, lo, hi, color=colour, alpha=0.18,
                        linewidth=0, zorder=2)
        peak_lag = lag_grid[int(np.argmax(mean_c))]
        bits.append(f"{cond}: peak lag = {smart_fmt(float(peak_lag))} s")

    ax.axvline(0, color="#888888", lw=0.7, ls="--", zorder=3)
    ax.axhline(0, color="#DDDDDD", lw=0.4, zorder=1)
    ax.set_xlabel("lag (s)  -->  positive = velocity follows length-rate")
    ax.set_ylabel("xcorr (z-scored)")
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(fontsize=6.8, frameon=False, loc="upper right",
              handlelength=1.4)
    ax.set_title(
        f"{contract.title}  ·  " + "   ".join(bits),
        fontsize=8.2, pad=4,
    )
    return ax
