"""Ensemble mean-variance tube — mean ± std with N independent SSA runs."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class EnsembleTubeInput(RecipeContract):
    t: list[float] = Field(...)
    mean: list[float] = Field(...)
    std: list[float] = Field(...)
    n_runs: int = 100
    deterministic_solution: list[float] | None = None
    title: str = "Ensemble mean ± std"


def _demo() -> EnsembleTubeInput:
    t = np.linspace(0, 40, 200)
    # Deterministic ODE solution + noise that grows with state.
    mean = 10 * (1 - np.exp(-t / 8))
    std = 1.5 * np.sqrt(mean + 0.1)
    return EnsembleTubeInput(
        t=t.tolist(),
        mean=mean.tolist(),
        std=std.tolist(),
        n_runs=250,
        deterministic_solution=mean.tolist(),
        title="SSA vs ODE (N=250)",
    )


_META = RecipeMetadata(
    name="ensemble_mean_variance_tube",
    modality="gillespie_stochastic",
    family=RecipeFamily.timecourse_hierarchical_ci,
    answers_question="What is the ensemble mean trajectory and how does its variance grow over time?",
    required_fields=("t", "mean", "std"),
    optional_fields=("n_runs", "deterministic_solution", "title"),
    file_format_hints=("parquet", "npz"),
    alternatives_in_modality=("trajectory_fan_with_fpt",),
)


@register_recipe(metadata=_META, contract=EnsembleTubeInput, demo_contract=_demo)
def render(contract: EnsembleTubeInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)
    accent = palette.pick("HOME")

    t = np.array(contract.t, dtype=float)
    m = np.array(contract.mean, dtype=float)
    s = np.array(contract.std, dtype=float)

    # Mean ± 2 std tube, then mean ± 1 std inner tube.
    ax.fill_between(t, m - 2 * s, m + 2 * s, color=accent, alpha=0.10,
                    linewidth=0, zorder=2, label=r"$\mu \pm 2\sigma$")
    ax.fill_between(t, m - s, m + s, color=accent, alpha=0.22,
                    linewidth=0, zorder=3, label=r"$\mu \pm \sigma$")
    ax.plot(t, m, color=accent, lw=1.3, zorder=5,
            label="ensemble mean")

    if contract.deterministic_solution is not None:
        det = np.array(contract.deterministic_solution, dtype=float)
        ax.plot(t, det, color="#111111", lw=0.9, ls="--", zorder=6,
                label="ODE (deterministic)")

    ax.set_xlabel("time")
    ax.set_ylabel("state")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="lower right",
              handlelength=1.8)

    # Fano-factor peek (var/mean ratio late time).
    if m[-1] > 0:
        fano = (s[-1] ** 2) / m[-1]
        ax.text(0.01, 0.99,
                f"N = {contract.n_runs}   Fano(t_end) = {smart_fmt(fano)}",
                transform=ax.transAxes, ha="left", va="top",
                fontsize=6.6, color="#333333",
                bbox=dict(boxstyle="round,pad=0.20", fc="white",
                          ec="#BBBBBB", lw=0.5, alpha=0.92),
                zorder=7)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
