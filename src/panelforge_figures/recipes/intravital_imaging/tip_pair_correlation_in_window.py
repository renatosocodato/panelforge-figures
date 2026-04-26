"""Tip pair correlation g(r) in window — per-condition g(r) +/- CI.
g > 1 = clustering, g < 1 = repulsion.

Window-conditional intravital recast (distinct from
spatial_statistics/pair_correlation_function).

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
from ._shared import TipCentroidSnapshot

_CONDITION_PALETTE = {
    "control": "#37474F", "DISC1": "#EF5350",
    "WT": "#37474F", "LI": "#EF5350",
}


class TipPairCorrelationInWindowInput(RecipeContract):
    snapshots: list[TipCentroidSnapshot] = Field(..., min_length=2)
    condition_by_snapshot: dict[int, str] = Field(...)
    r_grid_um: list[float] = Field(...)
    bandwidth_um: float = 1.5
    title: str = "Tip pair correlation g(r) (window-conditional)"


def _polygon_area(poly: np.ndarray) -> float:
    x, y = poly[:, 0], poly[:, 1]
    return 0.5 * abs(float(np.sum(x[:-1] * y[1:] - x[1:] * y[:-1])))


def _g_of_r(xy: np.ndarray, polygon: np.ndarray,
            r_grid: np.ndarray, bw: float) -> np.ndarray:
    n = xy.shape[0]
    if n < 2:
        return np.ones_like(r_grid)
    area = _polygon_area(polygon)
    diff = xy[:, None, :] - xy[None, :, :]
    dist = np.sqrt((diff ** 2).sum(axis=2))
    iu = np.triu_indices(n, k=1)
    dists = dist[iu]
    lam = n / max(area, 1e-9)
    g = np.zeros_like(r_grid)
    for ri, r in enumerate(r_grid):
        # Kernel-density count of pairs near r.
        contributions = np.exp(-((dists - r) / bw) ** 2 / 2.0)
        density = contributions.sum() / (n * 2 * np.pi * r * bw
                                         * np.sqrt(2 * np.pi))
        g[ri] = float(density / max(lam, 1e-9))
    return g


def _demo() -> TipPairCorrelationInWindowInput:
    rng = np.random.default_rng(3111)
    snapshots = []
    cond_by: dict[int, str] = {}
    window = np.array([
        [0.0, 0.0], [80.0, 0.0], [80.0, 60.0], [0.0, 60.0], [0.0, 0.0],
    ])
    for snap_idx, cond in enumerate(["control"] * 4 + ["DISC1"] * 4):
        n_tips = 40
        if cond == "control":
            xy = rng.uniform([0, 0], [80, 60], (n_tips, 2))
        else:
            mix = rng.choice([0, 1], size=n_tips)
            xy = np.where(
                mix[:, None] == 0,
                rng.normal([20, 15], 6, (n_tips, 2)),
                rng.normal([60, 45], 6, (n_tips, 2)),
            )
            xy = np.clip(xy, [0, 0], [80, 60])
        snapshots.append(TipCentroidSnapshot(
            t_s=float(snap_idx),
            xy_um=xy.tolist(),
            window_polygon_um=window.tolist(),
        ))
        cond_by[snap_idx] = cond
    r_grid = np.linspace(2.0, 20.0, 25).tolist()
    return TipPairCorrelationInWindowInput(
        snapshots=snapshots,
        condition_by_snapshot=cond_by,
        r_grid_um=r_grid,
    )


_META = RecipeMetadata(
    name="tip_pair_correlation_in_window",
    modality="intravital_imaging",
    family=RecipeFamily.timecourse_hierarchical_ci,
    answers_question=(
        "Per condition, what is the pair correlation g(r) of tips "
        "within the cell-ROI window?"
    ),
    required_fields=("snapshots", "condition_by_snapshot", "r_grid_um"),
    optional_fields=("bandwidth_um", "title"),
    file_format_hints=("yaml",),
    alternatives_in_modality=("tip_ripleys_k_in_window",),
)


@register_recipe(
    metadata=_META,
    contract=TipPairCorrelationInWindowInput,
    demo_contract=_demo,
)
def render(contract: TipPairCorrelationInWindowInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 3.8))
    AESTHETIC.apply_to_ax(ax)

    r = np.asarray(contract.r_grid_um, float)
    by_cond: dict[str, list[np.ndarray]] = {}
    for snap_idx, snap in enumerate(contract.snapshots):
        cond = contract.condition_by_snapshot.get(snap_idx, "?")
        xy = np.asarray(snap.xy_um, float)
        polygon = np.asarray(snap.window_polygon_um, float)
        g = _g_of_r(xy, polygon, r, contract.bandwidth_um)
        by_cond.setdefault(cond, []).append(g)

    bits = []
    for cond, curves in by_cond.items():
        arr = np.asarray(curves)
        mean_g = arr.mean(axis=0)
        rng = np.random.default_rng(29)
        boot = []
        for _ in range(60):
            idx = rng.integers(0, arr.shape[0], size=arr.shape[0])
            boot.append(arr[idx].mean(axis=0))
        boot_arr = np.asarray(boot)
        lo = np.quantile(boot_arr, 0.025, axis=0)
        hi = np.quantile(boot_arr, 0.975, axis=0)
        colour = _CONDITION_PALETTE.get(cond, "#37474F")
        ax.plot(r, mean_g, color=colour, lw=1.4, zorder=4, label=cond)
        ax.fill_between(r, lo, hi, color=colour, alpha=0.18,
                        linewidth=0, zorder=2)
        # Peak g(r) verdict.
        peak_idx = int(np.argmax(mean_g))
        bits.append(
            f"{cond}: peak g = {smart_fmt(float(mean_g[peak_idx]))} "
            f"at r = {smart_fmt(float(r[peak_idx]))} um"
        )

    ax.axhline(1.0, color="#888888", lw=0.7, ls="--", zorder=3,
               label="g = 1 (CSR)")
    ax.set_xlabel("r (um)")
    ax.set_ylabel("g(r)")
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(fontsize=6.8, frameon=False, loc="upper right",
              handlelength=1.4)
    ax.set_title(
        f"{contract.title}  ·  " + "   ".join(bits),
        fontsize=7.6, pad=4,
    )
    return ax
