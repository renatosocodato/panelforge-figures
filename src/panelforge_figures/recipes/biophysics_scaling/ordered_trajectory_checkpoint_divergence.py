"""Ordered-trajectory checkpoint divergence — per-group LOESS curve
along an ordered axis (e.g. Actin Drive Index t in [0, 1]) with CI
ribbons and a checkpoint vertical reference at t ≈ 0.6.

Footer caveat banner explicit: this is an *ordered fixed-cell
reconstruction*, not a live measurement. Crucial governance for the
manuscript's §5c claim.

Timecourse-hierarchical-CI family: >=1 filled CI band + >=1 mean
line. Satisfied by per-group fits + bootstrap CI ribbons.
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
from ._shared import OrderedTrajectoryPoint

_GROUP_COLOURS = {"WT": "#1565C0", "LI": "#C62828",
                  "control": "#1565C0", "treated": "#C62828"}


class OrderedTrajectoryInput(RecipeContract):
    points: list[OrderedTrajectoryPoint] = Field(..., min_length=10)
    t_index_label: str = "Actin Drive Index"
    y_label: str
    breakpoint_t: float | None = None
    smoother: str = Field("loess", description="'loess' | 'linear'")
    ci: float = 0.95
    title: str = "Ordered-trajectory checkpoint divergence"


def _demo() -> OrderedTrajectoryInput:
    rng = np.random.default_rng(5757)
    n = 60
    points: list[OrderedTrajectoryPoint] = []
    for i in range(n):
        t = i / (n - 1)
        for group in ("WT", "LI"):
            base = 0.4 + 0.5 / (1 + np.exp(-12 * (t - 0.5)))
            if group == "LI" and t > 0.6:
                base += 0.4 * (t - 0.6)
            value = float(base + rng.normal(0, 0.07))
            points.append(OrderedTrajectoryPoint(
                cell_id=f"C{i:03d}_{group}",
                group=group,
                t_index=t,
                value=value,
            ))
    return OrderedTrajectoryInput(
        points=points,
        y_label="standoff (um)",
        breakpoint_t=0.60,
    )


_META = RecipeMetadata(
    name="ordered_trajectory_checkpoint_divergence",
    modality="biophysics_scaling",
    family=RecipeFamily.timecourse_hierarchical_ci,
    answers_question=(
        "Along the ordered fixed-cell trajectory, where do the per-"
        "group curves diverge (checkpoint location)?"
    ),
    required_fields=("points", "y_label"),
    optional_fields=(
        "t_index_label", "breakpoint_t", "smoother", "ci", "title",
    ),
    file_format_hints=("csv", "yaml"),
    alternatives_in_modality=("shared_manifold_scatter_with_residuals",),
)


def _loess(x: np.ndarray, y: np.ndarray, xg: np.ndarray, frac: float = 0.55) -> np.ndarray:
    n = len(x)
    k = max(3, int(np.ceil(frac * n)))
    out = np.zeros_like(xg)
    for i, x0 in enumerate(xg):
        d = np.abs(x - x0)
        idx = np.argsort(d)[:k]
        dw = d[idx] / max(d[idx].max(), 1e-9)
        w = (1 - dw ** 3) ** 3
        xi = x[idx]
        yi = y[idx]
        wx = np.sum(w * xi)
        wy = np.sum(w * yi)
        wxx = np.sum(w * xi * xi)
        wxy = np.sum(w * xi * yi)
        sw = np.sum(w)
        denom = sw * wxx - wx * wx
        if abs(denom) < 1e-12:
            out[i] = wy / max(sw, 1e-9)
        else:
            b = (sw * wxy - wx * wy) / denom
            a = (wy - b * wx) / sw
            out[i] = a + b * x0
    return out


@register_recipe(
    metadata=_META,
    contract=OrderedTrajectoryInput,
    demo_contract=_demo,
)
def render(contract: OrderedTrajectoryInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.0, 3.8))
    AESTHETIC.apply_to_ax(ax)

    points = list(contract.points)
    by_group: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for group in dict.fromkeys(p.group for p in points):
        ts = np.array([p.t_index for p in points if p.group == group])
        ys = np.array([p.value for p in points if p.group == group])
        order = np.argsort(ts)
        by_group[group] = (ts[order], ys[order])

    xg = np.linspace(0.0, 1.0, 80)
    rng = np.random.default_rng(13)
    fits_at_xg: dict[str, np.ndarray] = {}
    for group, (t, y) in by_group.items():
        colour = _GROUP_COLOURS.get(group, "#333333")
        ax.scatter(t, y, s=14, color=colour, edgecolor="white",
                   linewidth=0.4, alpha=0.45, zorder=3)
        yg = _loess(t, y, xg)
        fits_at_xg[group] = yg
        boot = []
        for _ in range(150):
            idx = rng.integers(0, t.size, size=t.size)
            boot.append(_loess(t[idx], y[idx], xg))
        boot = np.asarray(boot)
        a = (1 - contract.ci) / 2
        lo = np.quantile(boot, a, axis=0)
        hi = np.quantile(boot, 1 - a, axis=0)
        ax.plot(xg, yg, color=colour, lw=1.4, zorder=5, label=group)
        ax.fill_between(xg, lo, hi, color=colour, alpha=0.18,
                        linewidth=0, zorder=2)

    # Breakpoint detection (CUSUM-flavoured): if not specified, find
    # the t where |Δ_fits| is largest in the second half.
    breakpoint = contract.breakpoint_t
    if breakpoint is None and len(fits_at_xg) == 2:
        g0, g1 = list(fits_at_xg.keys())
        diff = np.abs(fits_at_xg[g1] - fits_at_xg[g0])
        idx = int(np.argmax(diff[len(diff) // 2:])) + len(diff) // 2
        breakpoint = float(xg[idx])

    if breakpoint is not None:
        ax.axvline(breakpoint, color="#444444", lw=0.8, ls=":",
                   zorder=4,
                   label=f"checkpoint t = {smart_fmt(breakpoint)}")

    # Divergence magnitude (max |Δmedian| post-checkpoint).
    div_mag = None
    if breakpoint is not None and len(fits_at_xg) == 2:
        g0, g1 = list(fits_at_xg.keys())
        post_mask = xg >= breakpoint
        div_mag = float(
            np.max(np.abs(fits_at_xg[g1][post_mask]
                          - fits_at_xg[g0][post_mask]))
        )

    ax.set_xlabel(contract.t_index_label)
    ax.set_ylabel(contract.y_label)
    ax.set_xlim(0, 1)
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(fontsize=6.8, frameon=False, loc="upper left",
              handlelength=1.2)

    title_bits = [contract.title]
    if div_mag is not None:
        title_bits.append(f"max post-checkpoint Δ = {smart_fmt(div_mag)}")
    ax.set_title("  ·  ".join(title_bits), fontsize=8.2, pad=4)

    # Caveat footer banner — manuscript governance.
    ax.text(0.5, -0.20,
            "Ordered fixed-cell reconstruction — not a live measurement.",
            transform=ax.transAxes,
            ha="center", va="top", fontsize=6.4,
            color="#777777", style="italic",
            bbox=dict(boxstyle="round,pad=0.22", fc="#F5F5F5",
                      ec="#BBBBBB", lw=0.4),
            zorder=7)
    return ax
