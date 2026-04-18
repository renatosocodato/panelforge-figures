"""Sobol convergence diagnostic — index estimates vs. increasing sample size."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    add_halo_label,
    callout_box,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class SobolConvergenceInput(RecipeContract):
    n_samples: list[int] = Field(..., description="increasing sample sizes used")
    parameter_names: list[str] = Field(..., min_length=2)
    index_trajectories: list[list[float]] = Field(
        ..., description="parameter × n_samples; the evolving ST estimate"
    )
    ci_width: list[list[float]] | None = Field(
        None, description="optional per-parameter × per-step CI width"
    )
    tolerance: float = 0.02


def _demo() -> SobolConvergenceInput:
    rng = np.random.default_rng(31)
    ns = [512, 1024, 2048, 4096, 8192, 16384, 32768]
    names = ["k_on", "k_off", "V_max", "Km", "D"]
    true_vals = np.array([0.52, 0.12, 0.31, 0.46, 0.02])
    trajectories = []
    ci_widths = []
    for i, v in enumerate(true_vals):
        # Estimator noise shrinks like 1/sqrt(N).
        est = v + rng.normal(0, 0.25, size=len(ns)) / np.sqrt(np.array(ns) / 1024)
        est = np.clip(est, 0, 1)
        w = 0.6 / np.sqrt(np.array(ns) / 1024)
        trajectories.append(est.tolist())
        ci_widths.append(w.tolist())
    return SobolConvergenceInput(
        n_samples=ns,
        parameter_names=names,
        index_trajectories=trajectories,
        ci_width=ci_widths,
        tolerance=0.03,
    )


_META = RecipeMetadata(
    name="convergence_diagnostic_sobol",
    modality="sensitivity_analysis",
    family=RecipeFamily.diagnostic_curve,
    answers_question="Have the Sobol index estimates converged — i.e., do they stop changing as we add more samples?",
    required_fields=("n_samples", "parameter_names", "index_trajectories"),
    optional_fields=("ci_width", "tolerance"),
    file_format_hints=("parquet", "csv"),
    alternatives_in_modality=("sobol_first_total_pair",),
)


@register_recipe(metadata=_META, contract=SobolConvergenceInput, demo_contract=_demo)
def render(contract: SobolConvergenceInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.4))
    AESTHETIC.apply_to_ax(ax)
    ns = np.array(contract.n_samples)
    palette = get_palette(AESTHETIC.primary_palette)
    trajs = np.array(contract.index_trajectories)
    widths = np.array(contract.ci_width) if contract.ci_width else None

    for i, name in enumerate(contract.parameter_names):
        color = palette[i]
        ax.plot(ns, trajs[i], color=color, lw=1.3, marker="o", ms=3.5,
                markerfacecolor="white", markeredgecolor=color,
                markeredgewidth=1.0, label=name, zorder=4)
        if widths is not None:
            ax.fill_between(
                ns,
                trajs[i] - widths[i] / 2,
                trajs[i] + widths[i] / 2,
                color=color,
                alpha=0.15,
                zorder=2,
            )
        # Converged indicator.
        if len(ns) >= 3:
            last_range = trajs[i, -3:].max() - trajs[i, -3:].min()
            if last_range < contract.tolerance:
                add_halo_label(
                    ax, ns[-1] * 1.03, trajs[i, -1],
                    "✓", color="#2E7D32", fontsize=8.6, fontweight="bold",
                    halo_width=2.8, ha="left", va="center",
                )

    ax.set_xscale("log")
    ax.set_xlabel("samples used (N)")
    ax.set_ylabel("Sₜ estimate")
    ax.set_title("Sobol-index convergence", fontsize=9.0, fontweight="bold")
    ax.legend(fontsize=7.0, loc="upper right", frameon=False, ncol=2)
    ax.grid(axis="y", color="#DDDDDD", lw=0.4)
    ax.set_axisbelow(True)

    converged = sum(
        1
        for i in range(trajs.shape[0])
        if trajs[i, -3:].max() - trajs[i, -3:].min() < contract.tolerance
    )
    callout_box(
        ax,
        0.02,
        0.97,
        f"{converged}/{trajs.shape[0]} parameters converged (|range| < {smart_fmt(contract.tolerance)})",
        accent="#2E7D32" if converged == trajs.shape[0] else "#D32F2F",
        transform=ax.transAxes,
    )
    return ax
