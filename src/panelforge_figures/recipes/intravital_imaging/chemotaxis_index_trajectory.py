"""Chemotaxis index trajectory — CI(t) = <cos(theta - cue_hat)>
+/- 95 % CI per condition, time-aligned to cue onset.

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


class ChemotaxisIndexTrajectoryInput(RecipeContract):
    bundles: list[KinematicFeatureBundle] = Field(..., min_length=4)
    cue_onset_s_by_cell: dict[str, float] = Field(...)
    condition_by_cell: dict[str, str] = Field(...)
    align_to_cue: bool = True
    title: str = "Chemotaxis index trajectory"


def _demo() -> ChemotaxisIndexTrajectoryInput:
    rng = np.random.default_rng(3031)
    bundles: list[KinematicFeatureBundle] = []
    onset: dict[str, float] = {}
    cond_by: dict[str, str] = {}
    for cond, ramp in (("control", 0.6), ("DISC1", 0.3)):
        for k in range(30):
            cell_id = f"{cond}_C{k:02d}"
            n_t = 90
            t = np.arange(n_t).astype(float)
            cue_dir = 0.0  # cue points right (theta=0)
            # Pre-cue: random heading. Post-cue: drift toward cue with
            # cohort-distinct ramp speed.
            cue_t = 30.0
            heading = np.where(
                t < cue_t,
                rng.uniform(-180, 180, n_t),
                cue_dir + rng.normal(0, (1 - ramp) * 90, n_t)
                * np.exp(-(t - cue_t) / 30),
            )
            bundles.append(KinematicFeatureBundle(
                cell_id=cell_id,
                t_s=t.tolist(),
                heading_deg=heading.tolist(),
                cue_vector_deg=[cue_dir] * n_t,
            ))
            onset[cell_id] = cue_t
            cond_by[cell_id] = cond
    return ChemotaxisIndexTrajectoryInput(
        bundles=bundles,
        cue_onset_s_by_cell=onset,
        condition_by_cell=cond_by,
    )


_META = RecipeMetadata(
    name="chemotaxis_index_trajectory",
    modality="intravital_imaging",
    family=RecipeFamily.timecourse_hierarchical_ci,
    answers_question=(
        "After cue onset, how does the chemotaxis index "
        "CI(t) = <cos(theta - cue)> evolve per condition?"
    ),
    required_fields=("bundles", "cue_onset_s_by_cell", "condition_by_cell"),
    optional_fields=("align_to_cue", "title"),
    file_format_hints=("yaml", "json"),
    alternatives_in_modality=("directional_persistence_autocorr",),
)


@register_recipe(
    metadata=_META,
    contract=ChemotaxisIndexTrajectoryInput,
    demo_contract=_demo,
)
def render(contract: ChemotaxisIndexTrajectoryInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 3.8))
    AESTHETIC.apply_to_ax(ax)

    # Per-cell CI(t) on a common aligned grid.
    by_cond: dict[str, list[np.ndarray]] = {}
    aligned_grid: np.ndarray | None = None
    t_min = -30.0
    t_max = 60.0
    aligned_grid = np.linspace(t_min, t_max, 60)
    for b in contract.bundles:
        cond = contract.condition_by_cell.get(b.cell_id, "?")
        if b.heading_deg is None or b.cue_vector_deg is None:
            continue
        head = np.asarray(b.heading_deg, float)
        cue = np.asarray(b.cue_vector_deg, float)
        ci = np.cos(np.deg2rad(head - cue))
        t_local = np.asarray(b.t_s, float)
        if contract.align_to_cue:
            t_local = t_local - contract.cue_onset_s_by_cell.get(b.cell_id, 0.0)
        # Resample to aligned grid via interp (linear, NaN outside range).
        valid = (aligned_grid >= t_local.min()) & (aligned_grid <= t_local.max())
        ci_resampled = np.full_like(aligned_grid, np.nan)
        ci_resampled[valid] = np.interp(aligned_grid[valid], t_local, ci)
        by_cond.setdefault(cond, []).append(ci_resampled)

    bits = []
    import warnings
    for cond, curves in by_cond.items():
        arr = np.asarray(curves)
        # Mean and bootstrap CI per timepoint. Suppress 'Mean of
        # empty slice' RuntimeWarning at edges where every cell's
        # window excludes the timepoint (intentional under cue-onset
        # alignment).
        rng = np.random.default_rng(7)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            mean_ci = np.nanmean(arr, axis=0)
            boot = []
            for _ in range(100):
                idx = rng.integers(0, arr.shape[0], size=arr.shape[0])
                boot.append(np.nanmean(arr[idx], axis=0))
            boot_arr = np.asarray(boot)
            lo = np.nanquantile(boot_arr, 0.025, axis=0)
            hi = np.nanquantile(boot_arr, 0.975, axis=0)
        colour = _CONDITION_PALETTE.get(cond, "#37474F")
        ax.plot(aligned_grid, mean_ci, color=colour, lw=1.4,
                zorder=4, label=cond)
        ax.fill_between(aligned_grid, lo, hi, color=colour, alpha=0.18,
                        linewidth=0, zorder=2)
        # Plateau CI value (last 20 frames).
        plateau = float(np.nanmean(mean_ci[-20:]))
        bits.append(f"{cond}: plateau {smart_fmt(plateau)}")

    ax.axvline(0, color="#888888", lw=0.7, ls="--", zorder=3,
               label="cue onset")
    ax.axhline(0, color="#DDDDDD", lw=0.4, zorder=1)
    ax.set_xlabel("time relative to cue onset (s)")
    ax.set_ylabel("CI(t) = <cos(theta - cue)>")
    ax.set_ylim(-1, 1)
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(fontsize=6.8, frameon=False, loc="lower right",
              handlelength=1.4)
    ax.set_title(
        f"{contract.title}  ·  " + "   ".join(bits),
        fontsize=8.2, pad=4,
    )
    return ax
