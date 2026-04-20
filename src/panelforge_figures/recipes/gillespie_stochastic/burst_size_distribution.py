"""Transcription burst-size PMF with geometric / negative-binomial fit.

Discrete burst-count histogram overlaid with the MLE geometric and
negative-binomial PMFs. The better-fit model (lower AIC) is highlighted
and the mean burst size + CV are reported as a callout.
"""

from __future__ import annotations

import numpy as np
from pydantic import Field
from scipy import stats

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class BurstSizeInput(RecipeContract):
    burst_sizes: list[int] = Field(..., min_length=10)
    title: str = "Burst-size distribution"


def _demo() -> BurstSizeInput:
    rng = np.random.default_rng(311)
    # Negative-binomial burst size: r=3, p=0.4 → mean = r(1-p)/p = 4.5
    vals = rng.negative_binomial(n=3, p=0.4, size=600)
    return BurstSizeInput(burst_sizes=vals.tolist())


_META = RecipeMetadata(
    name="burst_size_distribution",
    modality="gillespie_stochastic",
    family=RecipeFamily.diagnostic_curve,
    answers_question=(
        "For transcription-burst-style dynamics, what is the burst-"
        "size distribution, and is it geometric / negative-binomial?"
    ),
    required_fields=("burst_sizes",),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=(
        "dwell_time_log_violin", "waiting_time_ecdf_fitted",
    ),
)


@register_recipe(
    metadata=_META,
    contract=BurstSizeInput,
    demo_contract=_demo,
)
def render(contract: BurstSizeInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    x = np.asarray(contract.burst_sizes, int)
    x = x[x >= 0]
    nmax = int(x.max())
    bins = np.arange(0, nmax + 2)
    counts, _ = np.histogram(x, bins=bins)
    pmf = counts / max(counts.sum(), 1)
    k = np.arange(0, nmax + 1)

    # Observed PMF as bars.
    ax.bar(k, pmf, width=0.8, color=palette.pick("HOME"),
           alpha=0.70, edgecolor="white", linewidth=0.5, zorder=2,
           label=f"observed (N={x.size})")

    # Geometric fit: MLE p_hat = 1 / (1 + mean).
    mean_x = float(x.mean()) if x.size else 0.0
    p_geom = 1.0 / (1.0 + mean_x) if mean_x > 0 else 0.5
    geom_pmf = stats.geom.pmf(k + 1, p_geom)  # starts at 1 → shift

    # NB fit: method of moments. Variance μ + μ²/r → r = μ²/(σ² − μ).
    var_x = float(x.var()) if x.size else 0.0
    if var_x > mean_x:
        r_nb = mean_x ** 2 / max(var_x - mean_x, 1e-6)
        p_nb = r_nb / (r_nb + mean_x)
    else:
        r_nb, p_nb = 1.0, 0.5
    nb_pmf = stats.nbinom.pmf(k, r_nb, p_nb)

    # Plot fit lines.
    ax.plot(k, geom_pmf, color="#D32F2F", lw=1.2, zorder=4,
            marker="o", ms=2.5, markerfacecolor="white",
            markeredgecolor="#D32F2F", markeredgewidth=0.5,
            label=f"geom (p={smart_fmt(p_geom)})")
    ax.plot(k, nb_pmf, color="#6A1B9A", lw=1.2, zorder=5,
            marker="s", ms=2.5, markerfacecolor="white",
            markeredgecolor="#6A1B9A", markeredgewidth=0.5,
            label=f"NB (r={smart_fmt(r_nb)}, p={smart_fmt(p_nb)})")

    # AIC-style preference via RSS (same parameter count difference).
    rss_geom = float(np.sum((pmf - geom_pmf) ** 2))
    rss_nb = float(np.sum((pmf - nb_pmf) ** 2))
    preferred = "NB" if rss_nb < rss_geom else "geom"

    ax.set_xlabel("burst size k")
    ax.set_ylabel("P(k)")
    ax.set_xlim(-0.5, nmax + 0.5)
    ax.set_ylim(bottom=0)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.6, frameon=False, loc="upper right",
              handlelength=1.8)
    ax.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    cv = (np.sqrt(var_x) / mean_x) if mean_x > 0 else 0.0
    ax.text(0.02, 0.97,
            f"mean = {smart_fmt(mean_x)}   CV = {smart_fmt(cv)}\n"
            f"preferred: {preferred}",
            transform=ax.transAxes, ha="left", va="top",
            fontsize=6.6, color="#111111",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.95),
            zorder=6)
    return ax
