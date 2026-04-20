"""Sobol S1 bootstrap-CI convergence — per-parameter CI-width shrinkage over N.

Different statistic from `convergence_diagnostic_sobol` (which shows
point-value stability over N): this recipe plots each parameter's S1
estimate as a line with a bootstrap 95 % CI ribbon, so the *width*
of the ribbon — not just the line value — is the convergence signal.
A rank-flip annotation marks the smallest N at which the top-k
ranking stabilises.
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


class BootstrapConvergenceInput(RecipeContract):
    n_samples: list[int] = Field(..., min_length=3)
    parameter_names: list[str] = Field(..., min_length=2)
    s1_estimate: list[list[float]] = Field(
        ..., description="n_params × n_samples mean estimate"
    )
    ci_lo: list[list[float]] = Field(..., description="n_params × n_samples CI lo")
    ci_hi: list[list[float]] = Field(..., description="n_params × n_samples CI hi")
    top_k: int = 3
    title: str = "Sobol S₁ bootstrap-CI convergence"


def _demo() -> BootstrapConvergenceInput:
    rng = np.random.default_rng(71)
    ns = [512, 1024, 2048, 4096, 8192, 16384, 32768]
    names = ["k_on", "V_max", "Km", "k_off", "D", "alpha"]
    true_vals = np.array([0.42, 0.22, 0.12, 0.08, 0.04, 0.02])
    est = np.zeros((len(names), len(ns)))
    lo = np.zeros_like(est)
    hi = np.zeros_like(est)
    for i, v in enumerate(true_vals):
        noise = rng.normal(0, 0.04, size=len(ns)) / np.sqrt(np.array(ns) / 512)
        est[i] = np.clip(v + noise, 0, 1)
        w = 0.22 / np.sqrt(np.array(ns) / 512)
        lo[i] = np.clip(est[i] - w / 2, 0, 1)
        hi[i] = np.clip(est[i] + w / 2, 0, 1)
    return BootstrapConvergenceInput(
        n_samples=ns,
        parameter_names=names,
        s1_estimate=est.tolist(),
        ci_lo=lo.tolist(),
        ci_hi=hi.tolist(),
    )


_META = RecipeMetadata(
    name="sobol_bootstrap_convergence",
    modality="sensitivity_analysis",
    family=RecipeFamily.diagnostic_curve,
    answers_question=(
        "As sample size grows, how does the bootstrap 95% CI on each "
        "Sobol S1 shrink, and have the top-k rankings stabilised?"
    ),
    required_fields=(
        "n_samples", "parameter_names", "s1_estimate", "ci_lo", "ci_hi",
    ),
    optional_fields=("top_k", "title"),
    file_format_hints=("parquet", "npz"),
    alternatives_in_modality=("convergence_diagnostic_sobol",),
)


@register_recipe(
    metadata=_META,
    contract=BootstrapConvergenceInput,
    demo_contract=_demo,
)
def render(contract: BootstrapConvergenceInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 3.6))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    ns = np.asarray(contract.n_samples, float)
    est = np.asarray(contract.s1_estimate, float)
    lo = np.asarray(contract.ci_lo, float)
    hi = np.asarray(contract.ci_hi, float)
    names = contract.parameter_names

    for i, name in enumerate(names):
        color = palette[i % len(palette.colors)]
        ax.fill_between(ns, lo[i], hi[i], color=color, alpha=0.20,
                        linewidth=0, zorder=2)
        ax.plot(ns, est[i], color=color, lw=1.2, marker="o", ms=3.2,
                markerfacecolor="white", markeredgecolor=color,
                markeredgewidth=0.9, label=name, zorder=4)

    ax.set_xscale("log")
    ax.set_xlabel("samples used (N)")
    ax.set_ylabel(r"$S_1$")
    ax.set_title(contract.title, fontsize=9.0, pad=4)

    # Rank-flip annotation: first N at which the top-k ranking matches final.
    top_k = min(contract.top_k, est.shape[0])
    final_rank = np.argsort(-est[:, -1])[:top_k].tolist()
    flip_n = int(ns[0])
    for k in range(est.shape[1]):
        if np.argsort(-est[:, k])[:top_k].tolist() == final_rank:
            flip_n = int(ns[k])
            break
    avg_ci_final = float(np.mean(hi[:, -1] - lo[:, -1]))
    ax.axvline(flip_n, color="#333333", lw=0.7, ls="--", zorder=3)
    ax.text(flip_n, ax.get_ylim()[1], f"  top-{top_k} stable @ N={flip_n}",
            ha="left", va="top", fontsize=6.6, color="#333333",
            bbox=dict(boxstyle="round,pad=0.16", fc="white",
                      ec="none", alpha=0.92),
            zorder=6)

    ax.legend(fontsize=6.6, frameon=False, loc="center left",
              bbox_to_anchor=(1.02, 0.5), handlelength=1.6)
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    fig = ax.figure
    fig.text(
        0.5, -0.16,
        f"mean 95% CI width at N={int(ns[-1])}: {smart_fmt(avg_ci_final)}",
        ha="center", va="top", fontsize=7.0,
        bbox=dict(boxstyle="round,pad=0.26", fc="white",
                  ec=AESTHETIC.annotation_style.callout_accent, lw=0.6),
        transform=ax.transAxes,
    )
    return ax
