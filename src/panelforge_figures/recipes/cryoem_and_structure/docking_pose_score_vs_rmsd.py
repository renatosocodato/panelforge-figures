"""Docking pose score vs RMSD-to-native — funnel-shaped landscape
diagnostic. Near-native cluster is highlighted.
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


class DockingFunnelInput(RecipeContract):
    rmsd: list[float] = Field(..., min_length=10,
                              description="RMSD-to-native per pose (Å)")
    score: list[float] = Field(..., min_length=10,
                               description="docking score per pose "
                                           "(lower = better)")
    near_native_threshold: float = Field(
        2.0, description="RMSD below this = near-native"
    )
    title: str = "Docking funnel (score vs RMSD)"


def _demo() -> DockingFunnelInput:
    rng = np.random.default_rng(2911)
    n = 400
    # Generate a funnel: near-RMSD poses have lower scores.
    rmsd = rng.uniform(0, 12, n)
    score = -40 + 3.5 * rmsd + rng.normal(0, 5, n)
    # Inject a cluster of low-RMSD, low-score near-native decoys.
    n_nat = 60
    r_nat = rng.uniform(0.2, 2.0, n_nat)
    s_nat = -65 + 2.0 * r_nat + rng.normal(0, 3, n_nat)
    rmsd = np.concatenate([rmsd, r_nat])
    score = np.concatenate([score, s_nat])
    return DockingFunnelInput(
        rmsd=rmsd.tolist(),
        score=score.tolist(),
    )


_META = RecipeMetadata(
    name="docking_pose_score_vs_rmsd",
    modality="cryoem_and_structure",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "Does the docking score decrease as RMSD-to-native decreases "
        "(funnel-shaped energy landscape)?"
    ),
    required_fields=("rmsd", "score"),
    optional_fields=("near_native_threshold", "title"),
    file_format_hints=("csv",),
    alternatives_in_modality=("interface_area_vs_affinity",),
)


@register_recipe(
    metadata=_META,
    contract=DockingFunnelInput,
    demo_contract=_demo,
)
def render(contract: DockingFunnelInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.8))
    AESTHETIC.apply_to_ax(ax)

    r = np.asarray(contract.rmsd, float)
    s = np.asarray(contract.score, float)
    thr = float(contract.near_native_threshold)

    near = r <= thr
    # Shade near-native zone.
    ax.axvspan(0, thr, color="#2E7D32", alpha=0.10, linewidth=0,
               zorder=1)

    ax.scatter(r[~near], s[~near], s=16, color="#BDBDBD", alpha=0.5,
               edgecolor="none", zorder=3,
               label=f"decoys (n = {int((~near).sum())})")
    ax.scatter(r[near], s[near], s=28, color="#C62828", alpha=0.85,
               edgecolor="white", linewidth=0.4, zorder=5,
               label=f"near-native (RMSD ≤ {thr} Å; "
                     f"n = {int(near.sum())})".replace("≤", "<="))

    # Funnel-envelope fit: lower envelope = binned min score.
    bins = np.linspace(0, float(r.max()), 24)
    centres = 0.5 * (bins[:-1] + bins[1:])
    mins = []
    for lo, hi in zip(bins[:-1], bins[1:]):
        mask = (r >= lo) & (r < hi)
        if mask.any():
            mins.append(float(s[mask].min()))
        else:
            mins.append(np.nan)
    mins_arr = np.asarray(mins)
    valid = ~np.isnan(mins_arr)
    ax.plot(centres[valid], mins_arr[valid],
            color="#1565C0", lw=1.2, zorder=6,
            label="lower envelope")

    # Best-score pose marker.
    best = int(np.argmin(s))
    ax.scatter([r[best]], [s[best]], s=66, marker="*",
               color="#FFB300", edgecolor="#222222", linewidth=0.8,
               zorder=7,
               label=(f"best pose (RMSD {smart_fmt(float(r[best]))} Å, "
                      f"score {smart_fmt(float(s[best]))})"))

    # Spearman correlation as a funnel-ness metric.
    from scipy.stats import spearmanr
    rho, p = spearmanr(r, s)
    ax.set_xlabel("RMSD-to-native (Å)")
    ax.set_ylabel("docking score (lower = better)")
    ax.legend(fontsize=6.4, frameon=False, loc="lower right",
              handlelength=1.2)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    if rho > 0.3:
        verdict = "funnel-shaped"
        color = "#2E7D32"
    elif rho > 0:
        verdict = "weak funnel"
        color = "#F57C00"
    else:
        verdict = "no funnel"
        color = "#C62828"
    ax.set_title(
        f"{contract.title}  ·  Spearman ρ = {smart_fmt(float(rho))} "
        f"({verdict})",
        fontsize=8.4, pad=4, color=color,
    )
    return ax
