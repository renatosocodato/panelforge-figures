"""Per-track anomalous-diffusion α fit — scatter of per-track α values
vs per-track D, one representative MSD fit overlaid + α histogram inset.

Distinct from `msd_by_condition` (pooled per-condition mean MSD): this
panel shifts the axis grammar to **per-track** single-particle α fits
and asks about the distribution of α across individual tracks.
"""

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


class MSDAnomalousInput(RecipeContract):
    alpha_per_track: list[float] = Field(..., min_length=5)
    D_per_track: list[float] = Field(..., min_length=5,
                                     description="apparent D (μm²/s^α)")
    representative_lag_s: list[float] = Field(..., min_length=3)
    representative_msd: list[float] = Field(..., min_length=3)
    representative_alpha: float = Field(..., description="fitted α for the overlaid track")
    title: str = "Per-track anomalous diffusion"


def _demo() -> MSDAnomalousInput:
    rng = np.random.default_rng(1511)
    n = 160
    # Two latent populations: confined (α ≈ 0.5) + free (α ≈ 1.0).
    alpha = np.concatenate([
        rng.normal(0.55, 0.08, n // 2),
        rng.normal(1.05, 0.10, n - n // 2),
    ])
    D = np.concatenate([
        rng.lognormal(-1.8, 0.4, n // 2),
        rng.lognormal(-0.9, 0.4, n - n // 2),
    ])
    # One representative track's MSD.
    lags = np.logspace(-1, 1.3, 14)
    a_rep = 0.95
    msd = 0.08 * lags ** a_rep * np.exp(rng.normal(0, 0.08, lags.size))
    return MSDAnomalousInput(
        alpha_per_track=alpha.tolist(),
        D_per_track=D.tolist(),
        representative_lag_s=lags.tolist(),
        representative_msd=msd.tolist(),
        representative_alpha=a_rep,
    )


_META = RecipeMetadata(
    name="msd_anomalous_exponent_fit",
    modality="diffusion_and_tracking",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "What is the per-track anomalous-diffusion exponent α, and how "
        "is α distributed across tracks?"
    ),
    required_fields=(
        "alpha_per_track", "D_per_track",
        "representative_lag_s", "representative_msd",
        "representative_alpha",
    ),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("msd_by_condition",),
)


@register_recipe(
    metadata=_META,
    contract=MSDAnomalousInput,
    demo_contract=_demo,
)
def render(contract: MSDAnomalousInput, ax=None, **_):
    from mpl_toolkits.axes_grid1.inset_locator import inset_axes

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.8))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    alpha = np.asarray(contract.alpha_per_track, float)
    D = np.asarray(contract.D_per_track, float)
    lags = np.asarray(contract.representative_lag_s, float)
    msd = np.asarray(contract.representative_msd, float)
    a_rep = float(contract.representative_alpha)

    # Per-track α vs D scatter (colour by α — blue (confined) to orange (directed)).
    # Map α into palette ranks.
    ax.scatter(D, alpha, s=26, c=alpha, cmap="RdYlBu_r",
               vmin=0.3, vmax=1.8, alpha=0.8,
               edgecolor="white", linewidth=0.4, zorder=3)
    # Per-track mean/median lines.
    alpha_med = float(np.median(alpha))
    ax.axhline(alpha_med, color="#222222", lw=0.8, zorder=4,
               label=f"median α = {smart_fmt(alpha_med)}")
    ax.axhline(1.0, color="#888888", lw=0.6, ls="--", zorder=2,
               label="α = 1 (Brownian)")

    ax.set_xscale("log")
    ax.set_xlabel(r"per-track D (μm$^2$/s$^{\alpha}$)")
    ax.set_ylabel(r"per-track α")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.set_ylim(max(0.1, alpha.min() - 0.1), alpha.max() + 0.1)
    ax.legend(fontsize=6.8, frameon=False, loc="upper left",
              handlelength=1.6)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    # Representative track MSD inset at lower-right (log-log).
    inset = inset_axes(ax, width="34%", height="34%",
                       loc="lower right", borderpad=0.8)
    AESTHETIC.apply_to_ax(inset)
    inset.scatter(lags, msd, s=14, color=palette[5], alpha=0.8,
                  edgecolor="white", linewidth=0.4, zorder=3)
    # Fit line.
    lo, hi = lags.min(), lags.max()
    lfit = np.logspace(np.log10(lo), np.log10(hi), 40)
    # fit prefactor
    intercept = float(np.mean(np.log(msd) - a_rep * np.log(lags)))
    inset.plot(lfit, np.exp(intercept) * lfit ** a_rep,
               color="#222222", lw=0.8, zorder=4,
               label=f"α = {smart_fmt(a_rep)}")
    inset.set_xscale("log")
    inset.set_yscale("log")
    inset.set_xlabel("τ (s)", fontsize=6.2, labelpad=1)
    inset.set_ylabel("MSD", fontsize=6.2, labelpad=2)
    inset.tick_params(labelsize=6.2)
    inset.legend(fontsize=6.2, frameon=False, loc="upper left",
                 handlelength=1.2)

    # Callout: fraction confined (α < 0.7) vs free (α ≥ 0.7).
    frac_conf = float((alpha < 0.7).mean())
    ax.text(0.02, 0.04,
            f"N tracks = {len(alpha)}\n"
            f"frac α < 0.7 = {smart_fmt(frac_conf)}",
            transform=ax.transAxes, ha="left", va="bottom",
            fontsize=6.4, color="#333333",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=6)
    return ax
