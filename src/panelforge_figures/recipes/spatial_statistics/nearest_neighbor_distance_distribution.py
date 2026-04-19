"""Nearest-neighbor distance distribution — histogram + CDF overlay."""

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


class NNInput(RecipeContract):
    distances_um: list[float] = Field(..., description="nearest-neighbor distance per point")
    expected_mean_csr: float | None = Field(
        None, description="expected NN mean under CSR for the density"
    )
    title: str = "Nearest-neighbor distances"


def _demo() -> NNInput:
    rng = np.random.default_rng(407)
    # Clustered NN distribution: rayleigh-ish shifted toward short distances.
    d = rng.gamma(2.0, 2.3, 500)
    return NNInput(
        distances_um=d.tolist(),
        expected_mean_csr=6.5,
    )


_META = RecipeMetadata(
    name="nearest_neighbor_distance_distribution",
    modality="spatial_statistics",
    family=RecipeFamily.diagnostic_curve,
    answers_question="How are nearest-neighbor distances distributed, and does the distribution differ from the CSR expectation?",
    required_fields=("distances_um",),
    optional_fields=("expected_mean_csr", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("pair_correlation_function",),
)


@register_recipe(metadata=_META, contract=NNInput, demo_contract=_demo)
def render(contract: NNInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    d = np.array(contract.distances_um, dtype=float)
    d = d[np.isfinite(d) & (d > 0)]

    # Histogram.
    counts, bins = np.histogram(d, bins=40, density=True)
    centers = 0.5 * (bins[:-1] + bins[1:])
    ax.bar(centers, counts, width=np.diff(bins), color=palette[2],
           alpha=0.75, edgecolor="white", linewidth=0.4, zorder=2)

    # CDF on right axis.
    ax_r = ax.twinx()
    xs = np.sort(d)
    cdf = np.arange(1, xs.size + 1) / xs.size
    ax_r.plot(xs, cdf, color=palette[1], lw=1.3, zorder=5, label="CDF")
    ax_r.set_ylim(0, 1.02)
    ax_r.set_ylabel("CDF", fontsize=8.4, color=palette[1])
    ax_r.tick_params(axis="y", labelsize=6.6, colors=palette[1])

    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    handles = [
        Patch(facecolor=palette[2], edgecolor="white", label="histogram"),
        Line2D([0], [0], color=palette[1], lw=1.3, label="CDF"),
    ]
    ax.legend(handles=handles, fontsize=6.6, frameon=False,
              loc="center right", handlelength=1.4)

    # CSR expected mean line.
    med = float(np.median(d))
    ax.axvline(med, color="#333333", lw=0.7, ls="--", zorder=3)
    ax.annotate(
        f"median = {smart_fmt(med)} $\\mu$m",
        xy=(med, ax.get_ylim()[1] * 0.92),
        xytext=(4, 0), textcoords="offset points",
        fontsize=6.4, color="#333333",
        bbox=dict(boxstyle="round,pad=0.16", fc="white", ec="none", alpha=0.9),
    )
    if contract.expected_mean_csr is not None:
        ax.axvline(contract.expected_mean_csr, color="#D32F2F",
                   lw=0.7, ls="-.", zorder=3)
        ax.annotate(
            f"CSR mean = {smart_fmt(contract.expected_mean_csr)} $\\mu$m",
            xy=(contract.expected_mean_csr, ax.get_ylim()[1] * 0.72),
            xytext=(4, 0), textcoords="offset points",
            fontsize=6.4, color="#D32F2F",
            bbox=dict(boxstyle="round,pad=0.16", fc="white", ec="none", alpha=0.9),
        )

    ax.set_xlabel(r"NN distance ($\mu$m)")
    ax.set_ylabel("density")
    ax.set_title(
        f"{contract.title}  ·  N = {d.size}",
        fontsize=9.0, pad=4,
    )
    ax.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
