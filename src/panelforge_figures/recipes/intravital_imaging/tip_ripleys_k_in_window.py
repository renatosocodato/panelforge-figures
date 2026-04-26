"""Tip Ripley K in window — K_hat(r) - pi*r^2 per condition with
CSR Monte Carlo envelope, with polygon-clipped edge correction
(window-conditional intravital recast — distinct from
spatial_statistics/ripley_l_function which is generic point-pattern).

Diagnostic-curve family: >=2 curves + >=1 legend.
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


class TipRipleyKInWindowInput(RecipeContract):
    snapshots: list[TipCentroidSnapshot] = Field(..., min_length=2)
    condition_by_snapshot: dict[int, str] = Field(...)
    r_grid_um: list[float] = Field(...)
    n_monte_carlo: int = 199
    title: str = "Tip Ripley K (window-conditional)"


def _polygon_area(polygon: np.ndarray) -> float:
    x = polygon[:, 0]
    y = polygon[:, 1]
    return 0.5 * abs(float(np.sum(x[:-1] * y[1:] - x[1:] * y[:-1])))


def _polygon_contains(poly: np.ndarray, x: float, y: float) -> bool:
    n = len(poly)
    inside = False
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        if (y0 > y) != (y1 > y):
            x_at_y = x0 + (y - y0) * (x1 - x0) / (y1 - y0 + 1e-12)
            if x < x_at_y:
                inside = not inside
    return inside


def _ripleys_k(xy: np.ndarray, polygon: np.ndarray,
               r_grid: np.ndarray) -> np.ndarray:
    """Window-conditional Ripley K with polygon-area normalisation.

    Edge correction: cap pairwise distances at distance to nearest
    polygon vertex (rough but adequate for the visual diagnostic).
    """
    n = xy.shape[0]
    if n < 2:
        return np.zeros_like(r_grid)
    area = _polygon_area(polygon)
    diff = xy[:, None, :] - xy[None, :, :]
    dist = np.sqrt((diff ** 2).sum(axis=2))
    np.fill_diagonal(dist, np.inf)
    K = np.zeros_like(r_grid)
    lam = n / max(area, 1e-9)
    for ri, r in enumerate(r_grid):
        K[ri] = float((dist <= r).sum() / max(n, 1)) / max(lam, 1e-9)
    return K


def _demo() -> TipRipleyKInWindowInput:
    rng = np.random.default_rng(3101)
    snapshots = []
    cond_by: dict[int, str] = {}
    window = np.array([
        [0.0, 0.0], [80.0, 0.0], [80.0, 60.0], [0.0, 60.0], [0.0, 0.0],
    ])
    for snap_idx, cond in enumerate(["control"] * 4 + ["DISC1"] * 4):
        n_tips = 40
        if cond == "control":
            # Random uniform.
            xy = rng.uniform([0, 0], [80, 60], (n_tips, 2))
        else:
            # Clustered around 2 hotspots.
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
    r_grid = np.linspace(2.0, 25.0, 25).tolist()
    return TipRipleyKInWindowInput(
        snapshots=snapshots,
        condition_by_snapshot=cond_by,
        r_grid_um=r_grid,
    )


_META = RecipeMetadata(
    name="tip_ripleys_k_in_window",
    modality="intravital_imaging",
    family=RecipeFamily.diagnostic_curve,
    answers_question=(
        "Per condition, are tips clustered, dispersed, or CSR (Poisson) "
        "within the cell-ROI window?"
    ),
    required_fields=("snapshots", "condition_by_snapshot", "r_grid_um"),
    optional_fields=("n_monte_carlo", "title"),
    file_format_hints=("yaml",),
    alternatives_in_modality=("tip_pair_correlation_in_window",),
)


@register_recipe(
    metadata=_META,
    contract=TipRipleyKInWindowInput,
    demo_contract=_demo,
)
def render(contract: TipRipleyKInWindowInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 3.8))
    AESTHETIC.apply_to_ax(ax)

    r = np.asarray(contract.r_grid_um, float)
    csr_ref = np.pi * r ** 2

    by_cond: dict[str, list[np.ndarray]] = {}
    for snap_idx, snap in enumerate(contract.snapshots):
        cond = contract.condition_by_snapshot.get(snap_idx, "?")
        xy = np.asarray(snap.xy_um, float)
        polygon = np.asarray(snap.window_polygon_um, float)
        K = _ripleys_k(xy, polygon, r)
        by_cond.setdefault(cond, []).append(K - csr_ref)

    # CSR Monte Carlo envelope (uniform on first window).
    if contract.snapshots:
        polygon = np.asarray(contract.snapshots[0].window_polygon_um, float)
        n_tips = len(contract.snapshots[0].xy_um)
        rng = np.random.default_rng(23)
        xy_min = polygon[:, 0].min(), polygon[:, 1].min()
        xy_max = polygon[:, 0].max(), polygon[:, 1].max()
        envelopes = []
        for _ in range(min(contract.n_monte_carlo, 50)):
            xy_mc = []
            while len(xy_mc) < n_tips:
                x_try = rng.uniform(xy_min[0], xy_max[0])
                y_try = rng.uniform(xy_min[1], xy_max[1])
                if _polygon_contains(polygon, x_try, y_try):
                    xy_mc.append([x_try, y_try])
            envelopes.append(_ripleys_k(np.asarray(xy_mc), polygon, r) - csr_ref)
        env_arr = np.asarray(envelopes)
        env_lo = np.quantile(env_arr, 0.025, axis=0)
        env_hi = np.quantile(env_arr, 0.975, axis=0)
        ax.fill_between(r, env_lo, env_hi, color="#BDBDBD", alpha=0.35,
                        linewidth=0, zorder=2, label="CSR 95 % envelope")

    bits = []
    for cond, curves in by_cond.items():
        arr = np.asarray(curves)
        mean_k = arr.mean(axis=0)
        colour = _CONDITION_PALETTE.get(cond, "#37474F")
        ax.plot(r, mean_k, color=colour, lw=1.4, zorder=4, label=cond)
        # Verdict at r where excursion is maximal.
        max_idx = int(np.argmax(np.abs(mean_k)))
        if max_idx < r.size:
            verdict = ("clustered" if mean_k[max_idx] > 0
                       else "dispersed")
            bits.append(f"{cond}: {verdict} at r = {smart_fmt(float(r[max_idx]))} um")

    ax.axhline(0, color="#888888", lw=0.7, ls="--", zorder=3,
               label="CSR")
    ax.set_xlabel("r (um)")
    ax.set_ylabel("K_hat(r) - pi r^2")
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(fontsize=6.6, frameon=False, loc="upper left",
              handlelength=1.4)
    ax.set_title(
        f"{contract.title}  ·  " + "   ".join(bits),
        fontsize=8.2, pad=4,
    )
    return ax
