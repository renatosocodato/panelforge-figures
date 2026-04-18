"""Drift-diffusion decomposition — estimate D(x) (drift) and σ²(x) (diffusion) from trajectory."""

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


class DriftDiffusionInput(RecipeContract):
    x_bins: list[float] = Field(..., description="state-space bin centers")
    drift: list[float] = Field(..., description="estimated mean instantaneous change per bin")
    diffusion: list[float] = Field(..., description="estimated variance / time per bin")
    title: str = "Drift-diffusion decomposition"


def _demo() -> DriftDiffusionInput:
    x = np.linspace(0.3, 1.8, 40)
    # Drift: bistable potential U(x) = 0.25*(x-0.6)^2*(x-1.4)^2; drift = -dU/dx.
    U = 0.25 * (x - 0.6) ** 2 * (x - 1.4) ** 2
    dU = np.gradient(U, x)
    drift = -dU
    # Diffusion: multiplicative, D(x) ~ 0.05 + 0.12*x.
    diff = 0.05 + 0.12 * x
    return DriftDiffusionInput(
        x_bins=x.tolist(),
        drift=drift.tolist(),
        diffusion=diff.tolist(),
    )


_META = RecipeMetadata(
    name="drift_diffusion_decomposition",
    modality="redox_imaging",
    family=RecipeFamily.diagnostic_curve,
    answers_question="What are the state-dependent drift and diffusion coefficients of the redox process?",
    required_fields=("x_bins", "drift", "diffusion"),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("multiplicative_noise_diagnostic",),
)


@register_recipe(metadata=_META, contract=DriftDiffusionInput, demo_contract=_demo)
def render(contract: DriftDiffusionInput, ax=None, **_):
    """Split host axis into 2 rows (drift top, diffusion bottom) sharing x."""
    import matplotlib.pyplot as plt
    if ax is None:
        fig = plt.figure(figsize=(5.0, 3.4))
        gs = fig.add_gridspec(2, 1, hspace=0.08, height_ratios=[1, 1])
        ax_d = fig.add_subplot(gs[0, 0])
        ax_v = fig.add_subplot(gs[1, 0], sharex=ax_d)
    else:
        fig = ax.figure
        pos = ax.get_subplotspec()
        ax.remove()
        sub = pos.subgridspec(2, 1, hspace=0.08, height_ratios=[1, 1])
        ax_d = fig.add_subplot(sub[0, 0])
        ax_v = fig.add_subplot(sub[1, 0], sharex=ax_d)

    AESTHETIC.apply_to_ax(ax_d)
    AESTHETIC.apply_to_ax(ax_v)
    palette = get_palette(AESTHETIC.primary_palette)

    x = np.array(contract.x_bins, dtype=float)
    drift = np.array(contract.drift, dtype=float)
    diff = np.array(contract.diffusion, dtype=float)

    # Drift: fill above/below zero with reduced/oxidized palette colors.
    ax_d.fill_between(x, 0, np.where(drift > 0, drift, 0),
                      color=palette.pick("reduced"), alpha=0.35,
                      linewidth=0, zorder=2, label="drift > 0")
    ax_d.fill_between(x, 0, np.where(drift < 0, drift, 0),
                      color=palette.pick("oxidized"), alpha=0.35,
                      linewidth=0, zorder=2, label="drift < 0")
    ax_d.plot(x, drift, color="#222222", lw=1.2, zorder=4, label="drift A(x)")
    ax_d.axhline(0, color="#888888", lw=0.5, ls="--", zorder=1)
    # Fixed points: where drift = 0.
    fps = []
    for i in range(len(drift) - 1):
        if drift[i] * drift[i + 1] < 0:
            fps.append(0.5 * (x[i] + x[i + 1]))
    for fp in fps:
        ax_d.axvline(fp, color="#6A1B9A", lw=0.6, ls=":", zorder=3)

    ax_d.set_ylabel("drift A(x)")
    ax_d.set_title(contract.title, fontsize=9.0, pad=4)
    ax_d.legend(fontsize=6.4, frameon=False, loc="upper right",
                ncol=3, handlelength=1.4, columnspacing=0.8)
    ax_d.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax_d.set_axisbelow(True)
    ax_d.tick_params(labelbottom=False)

    # Diffusion (always positive).
    ax_v.fill_between(x, 0, diff, color=palette.pick("intermediate"),
                      alpha=0.30, linewidth=0, zorder=2)
    ax_v.plot(x, diff, color="#222222", lw=1.2, zorder=4, label="diffusion D(x)")
    ax_v.set_xlabel("redox ratio x")
    ax_v.set_ylabel("D(x)")
    ax_v.legend(fontsize=6.4, frameon=False, loc="upper left",
                handlelength=1.4)
    ax_v.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax_v.set_axisbelow(True)

    # Fixed-point callout.
    if fps:
        fps_txt = ", ".join(smart_fmt(float(f)) for f in fps)
        ax_d.text(0.01, 0.99,
                  f"fixed points: x* = {fps_txt}",
                  transform=ax_d.transAxes, ha="left", va="top",
                  fontsize=6.4, color="#333333",
                  bbox=dict(boxstyle="round,pad=0.18", fc="white",
                            ec="#BBBBBB", lw=0.5, alpha=0.92),
                  zorder=6)
    return ax_d
