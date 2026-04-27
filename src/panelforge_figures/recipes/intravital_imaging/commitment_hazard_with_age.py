"""Commitment hazard with age — kernel-smoothed h(tau) per condition
with bootstrap CI ribbons.

Flat h(tau) = stochastic (memoryless commitment); ramp / peak =
staged commitment.

Timecourse-hierarchical-CI family: >=1 CI band + >=1 mean line.
"""

from __future__ import annotations

import warnings

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
from ._shared import ProtrusionPolyline

_CONDITION_PALETTE = {
    "control": "#37474F", "DISC1": "#EF5350",
    "WT": "#37474F", "LI": "#EF5350",
}


class CommitmentHazardInput(RecipeContract):
    protrusions: list[ProtrusionPolyline] = Field(..., min_length=4)
    condition_by_protrusion: dict[str, str] = Field(...)
    bandwidth_s: float = 12.0
    n_bootstrap: int = 100
    survival_floor: float = 0.10
    title: str = "Commitment hazard with age"


def _demo() -> CommitmentHazardInput:
    rng = np.random.default_rng(3011)
    protrusions: list[ProtrusionPolyline] = []
    cond_by: dict[str, str] = {}
    # Control: gamma-distributed (rising hazard) lifetime; DISC1:
    # exponential (flat hazard).
    for cond, draw in (("control", lambda: rng.gamma(shape=3.0, scale=25.0)),
                       ("DISC1", lambda: rng.exponential(50.0))):
        for k in range(80):
            pid = f"{cond}_p{k:03d}"
            protrusions.append(ProtrusionPolyline(
                protrusion_id=pid,
                xy_um=[[0.0, 0.0], [1.0, 1.0]],
                parent_cell_id=f"{cond}_c{k // 4:02d}",
                born_s=0.0,
                died_s=float(draw()),
            ))
            cond_by[pid] = cond
    return CommitmentHazardInput(
        protrusions=protrusions,
        condition_by_protrusion=cond_by,
    )


_META = RecipeMetadata(
    name="commitment_hazard_with_age",
    modality="intravital_imaging",
    family=RecipeFamily.timecourse_hierarchical_ci,
    answers_question=(
        "Per condition, does the commitment hazard h(tau) depend on "
        "age (ramp/peak = staged) or is it flat (memoryless)?"
    ),
    required_fields=("protrusions", "condition_by_protrusion"),
    optional_fields=(
        "bandwidth_s", "n_bootstrap", "survival_floor", "title",
    ),
    file_format_hints=("yaml", "json"),
    alternatives_in_modality=("protrusion_commitment_survival",),
)


def _kernel_hazard(durations: np.ndarray, tau_grid: np.ndarray,
                   bw: float, *, survival_floor: float) -> np.ndarray:
    f = np.zeros_like(tau_grid)
    for v in durations:
        f += np.exp(-((tau_grid - v) / bw) ** 2 / 2.0)
    f /= (durations.size * bw * np.sqrt(2 * np.pi))
    sorted_d = np.sort(durations)
    s = np.array([
        float((sorted_d > t).sum() / durations.size)
        for t in tau_grid
    ])
    h = np.full_like(tau_grid, np.nan)
    valid = s >= survival_floor
    h[valid] = f[valid] / s[valid]
    return h


@register_recipe(
    metadata=_META,
    contract=CommitmentHazardInput,
    demo_contract=_demo,
)
def render(contract: CommitmentHazardInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 3.8))
    AESTHETIC.apply_to_ax(ax)

    by_cond: dict[str, list[float]] = {}
    for proto in contract.protrusions:
        cond = contract.condition_by_protrusion.get(proto.protrusion_id, "?")
        if proto.died_s is None:
            continue
        by_cond.setdefault(cond, []).append(
            float(proto.died_s - (proto.born_s or 0.0))
        )

    all_d = np.concatenate([np.asarray(v, float) for v in by_cond.values()])
    if all_d.size == 0:
        ax.set_title(contract.title, fontsize=8.4, pad=4)
        return ax
    tau_max = float(np.quantile(all_d, 0.90)) * 1.1
    tau_grid = np.linspace(2.0, max(tau_max, 10.0), 60)
    rng = np.random.default_rng(13)

    bits = []
    for cond, durations in by_cond.items():
        d = np.asarray(durations, float)
        if d.size < 5:
            continue
        h = _kernel_hazard(d, tau_grid, contract.bandwidth_s,
                           survival_floor=contract.survival_floor)
        boot_curves = []
        for _ in range(contract.n_bootstrap):
            idx = rng.integers(0, d.size, size=d.size)
            boot_curves.append(_kernel_hazard(
                d[idx], tau_grid, contract.bandwidth_s,
                survival_floor=contract.survival_floor,
            ))
        boot = np.asarray(boot_curves)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            lo = np.nanquantile(boot, 0.025, axis=0)
            hi = np.nanquantile(boot, 0.975, axis=0)
        colour = _CONDITION_PALETTE.get(cond, "#37474F")
        ax.plot(tau_grid, h, color=colour, lw=1.2, zorder=4, label=cond)
        ax.fill_between(tau_grid, lo, hi, color=colour, alpha=0.18,
                        linewidth=0, zorder=2)
        h_finite = h[np.isfinite(h)]
        if h_finite.size:
            verdict = "rising" if h_finite[-1] > h_finite[0] * 1.4 \
                else "flat" if h_finite[-1] < h_finite[0] * 1.4 \
                                and h_finite[-1] > h_finite[0] * 0.7 \
                else "decaying"
            bits.append(f"{cond}: {verdict}")

    ax.set_xlabel("age tau (s)")
    ax.set_ylabel("hazard h(tau)")
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(fontsize=6.8, frameon=False, loc="upper right",
              handlelength=1.4)
    ax.set_title(
        f"{contract.title}  ·  " + "   ".join(bits),
        fontsize=8.2, pad=4,
    )
    _ = smart_fmt
    return ax
