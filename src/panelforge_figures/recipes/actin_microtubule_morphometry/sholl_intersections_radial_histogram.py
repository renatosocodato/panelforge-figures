"""Sholl intersections radial histogram — per-condition mean
intersection-count curve vs distance from soma, with bootstrap
95% CI ribbons + faint per-cell traces.

Encodes the canonical Sholl analysis output: count intersections
of skeleton branches with concentric circles centred on the soma,
plotted vs radial distance. The recipe aggregates per-cell curves
to per-condition means and overlays a bootstrap CI ribbon as the
hierarchical-CI atom.

Timecourse-hierarchical-CI family: >=1 CI band + >=1 mean line.
Satisfied by per-condition CI ribbon + per-condition mean curve
(2 conditions × 2 atoms = 4 family-rule satisfying primitives).
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
from ._shared import ShollProfile


class ShollHistogramInput(RecipeContract):
    profiles: list[ShollProfile] = Field(..., min_length=4)
    n_bootstrap: int = 200
    title: str = "Sholl intersections by sex"


def _demo() -> ShollHistogramInput:
    rng = np.random.default_rng(824)
    radii = np.linspace(2.0, 50.0, 25)   # µm
    profiles = []
    # Manuscript Fig 4A values: female peak ~25.97 vs male peak ~22.67.
    for sex, peak, n_cells in (("female", 25.97, 30), ("male", 22.67, 30)):
        for k in range(n_cells):
            # Gaussian-ish radial profile peaking at ~15 µm with
            # condition-specific peak amplitude.
            mu, sd = 15.0, 9.0
            curve = peak * np.exp(-0.5 * ((radii - mu) / sd) ** 2)
            curve = curve + rng.normal(0.0, 1.6, radii.size)
            curve = np.clip(curve, 0.0, None)
            profiles.append(ShollProfile(
                cell_id=f"{sex[0].upper()}{k:02d}",
                condition=sex,
                radii_um=radii.tolist(),
                intersections=curve.tolist(),
            ))
    return ShollHistogramInput(profiles=profiles)


_META = RecipeMetadata(
    name="sholl_intersections_radial_histogram",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.timecourse_hierarchical_ci,
    answers_question=(
        "How does the per-condition Sholl intersection density vary "
        "with distance from the soma, and how do the per-condition "
        "peak amplitudes compare?"
    ),
    required_fields=("profiles",),
    optional_fields=("n_bootstrap", "title"),
    file_format_hints=("csv", "yaml"),
    alternatives_in_modality=("intensity_radial_profile",),
    statistical_contract=StatisticalContract(
        min_n_per_group=10,
        distribution_assumption="non_negative_integer",
        refuses_when=("non_integer_in_count", "negative_in_non_negative"),
    ),
)


def _bootstrap_ci(curves: np.ndarray, n_bootstrap: int, rng):
    """Per-radius bootstrap mean + 95% percentile CI."""
    n_cells = curves.shape[0]
    boot_means = np.empty((n_bootstrap, curves.shape[1]))
    for b in range(n_bootstrap):
        idx = rng.integers(0, n_cells, n_cells)
        boot_means[b] = curves[idx].mean(axis=0)
    return (
        np.percentile(boot_means, 2.5, axis=0),
        np.percentile(boot_means, 97.5, axis=0),
    )


@register_recipe(
    metadata=_META,
    contract=ShollHistogramInput,
    demo_contract=_demo,
)
def render(contract: ShollHistogramInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 3.4))
    AESTHETIC.apply_to_ax(ax)

    palette = {"female": "#E91E63", "male": "#1976D2"}
    fallback = ["#37474F", "#FFB300", "#26A69A"]
    rng = np.random.default_rng(8240)

    # Group by condition.
    conditions = sorted({p.condition for p in contract.profiles})
    peak_summary: list[str] = []

    for ci, cond in enumerate(conditions):
        colour = palette.get(cond.lower(), fallback[ci % len(fallback)])
        sub = [p for p in contract.profiles if p.condition == cond]
        # All profiles must share the same radii grid.
        radii = np.asarray(sub[0].radii_um, float)
        curves = np.array([p.intersections for p in sub], float)

        # Per-cell faint traces.
        for c in curves:
            ax.plot(radii, c, color=colour, lw=0.4, alpha=0.15,
                    zorder=2)

        # Per-condition mean (the >=1 mean line).
        mean = curves.mean(axis=0)
        lo, hi = _bootstrap_ci(curves, contract.n_bootstrap, rng)

        # CI ribbon (the >=1 CI band).
        ax.fill_between(radii, lo, hi, color=colour, alpha=0.22,
                        linewidth=0, zorder=3,
                        label=f"{cond} 95% CI")
        ax.plot(radii, mean, color=colour, lw=1.4, alpha=0.95,
                zorder=4, label=f"{cond} mean (n={len(sub)})")

        # Peak callout.
        peak = float(mean.max())
        peak_r = float(radii[int(np.argmax(mean))])
        ax.scatter([peak_r], [peak], s=28, marker="v",
                   color=colour, edgecolor="white", linewidth=0.6,
                   zorder=5)
        peak_summary.append(
            f"{cond} peak {smart_fmt(peak)} at {smart_fmt(peak_r)} µm"
        )

    ax.set_xlabel("distance from soma (µm)")
    ax.set_ylabel("intersection count")
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    ax.legend(fontsize=6.4, frameon=True, framealpha=0.92,
              edgecolor="#BBBBBB", loc="upper right",
              handlelength=1.2, ncols=2, columnspacing=0.8)

    ax.set_title(
        f"{contract.title}  ·  " + "  ·  ".join(peak_summary),
        fontsize=8.2, pad=4,
    )
    return ax
