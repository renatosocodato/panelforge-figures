"""Master-equation steady-state overlap — analytic P(n) vs sampled histogram.

Overlays the analytical master-equation stationary distribution P(n) on
top of a histogram of samples drawn from long SSA trajectories.
Annotates KL(sample || analytic) and total-variation distance to
quantify the match.
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


class MasterEqSSInput(RecipeContract):
    n_values: list[int] = Field(..., min_length=3)
    analytic_p: list[float] = Field(..., description="P(n) from master-equation")
    sampled_counts: list[int] = Field(
        ..., description="histogram counts of SSA samples at each n"
    )
    species_label: str = "molecule count n"
    title: str = "Master-equation steady state"


def _demo() -> MasterEqSSInput:
    rng = np.random.default_rng(29)
    # Birth-death process at steady state → Poisson with mean μ.
    mu = 12.0
    n = np.arange(0, 40)
    # Analytical Poisson PMF.
    from math import lgamma
    log_p = n * np.log(mu) - mu - np.array([lgamma(int(k) + 1) for k in n])
    p_analytic = np.exp(log_p)
    # Sample.
    samples = rng.poisson(mu, 8000)
    counts, _ = np.histogram(samples, bins=np.arange(0, 41))
    return MasterEqSSInput(
        n_values=n.tolist(),
        analytic_p=p_analytic.tolist(),
        sampled_counts=counts.tolist(),
    )


_META = RecipeMetadata(
    name="master_equation_steady_state",
    modality="gillespie_stochastic",
    family=RecipeFamily.diagnostic_curve,
    answers_question=(
        "Does the Gillespie steady-state sampled distribution P(n) "
        "match the analytical master-equation solution?"
    ),
    required_fields=("n_values", "analytic_p", "sampled_counts"),
    optional_fields=("species_label", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("waiting_time_ecdf_fitted",),
)


@register_recipe(
    metadata=_META,
    contract=MasterEqSSInput,
    demo_contract=_demo,
)
def render(contract: MasterEqSSInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    n = np.asarray(contract.n_values, float)
    pa = np.asarray(contract.analytic_p, float)
    counts = np.asarray(contract.sampled_counts, float)
    total = counts.sum()
    p_sample = counts / max(total, 1.0)

    # Sample histogram as step outline (counts as PDF).
    ax.step(n, p_sample, where="mid", color=palette.pick("HOME"),
            lw=1.1, zorder=3, label=f"sampled (N={int(total)})")
    ax.fill_between(n, 0, p_sample, step="mid", color=palette.pick("HOME"),
                    alpha=0.22, zorder=2)

    # Analytic P(n).
    ax.plot(n, pa, color="#D32F2F", lw=1.4, zorder=4,
            label="analytic master-eq.", marker="o", ms=2.5,
            markerfacecolor="white", markeredgecolor="#D32F2F",
            markeredgewidth=0.6)

    # KL(sample || analytic) and TV distance.
    eps = 1e-12
    kl = float(np.sum(np.where(p_sample > 0,
                               p_sample * np.log((p_sample + eps) / (pa + eps)),
                               0.0)))
    tv = 0.5 * float(np.sum(np.abs(p_sample - pa)))

    ax.set_xlabel(contract.species_label)
    ax.set_ylabel("P(n)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.set_xlim(n.min(), n.max())
    ax.set_ylim(bottom=0)
    ax.legend(fontsize=6.6, frameon=False, loc="upper right",
              handlelength=1.6)
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    ax.text(0.02, 0.97,
            f"KL(sample || analytic) = {smart_fmt(kl)}\n"
            f"TV distance = {smart_fmt(tv)}",
            transform=ax.transAxes, ha="left", va="top",
            fontsize=6.6, color="#111111",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.95),
            zorder=6)
    return ax
