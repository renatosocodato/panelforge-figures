"""Power curves by effect size — canonical pre-registration figure.

For each effect size d, draw the power(N) curve. Overlay the 80% line, mark
the N that hits 80% power for each d, and annotate the critical d given the
planned N.
"""

from __future__ import annotations

import numpy as np
from pydantic import Field
from scipy import stats

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


class PowerAnalysisInput(RecipeContract):
    effect_sizes: list[float] = Field(..., description="Cohen's d values to sweep")
    n_range: tuple[int, int] = Field((4, 200))
    alpha: float = 0.05
    n_planned: int | None = None
    title: str = "Power curves by effect size"


def _demo() -> PowerAnalysisInput:
    return PowerAnalysisInput(
        effect_sizes=[0.2, 0.5, 0.8, 1.2],
        n_range=(4, 200),
        alpha=0.05,
        n_planned=60,
    )


def _power_t_two_sample(d: float, n_per_group: int, alpha: float) -> float:
    """Analytical two-sample t-test power (equal variance, equal n)."""
    df = 2 * n_per_group - 2
    nc = d * np.sqrt(n_per_group / 2.0)
    crit = stats.t.ppf(1 - alpha / 2, df)
    return float(
        1 - stats.nct.cdf(crit, df=df, nc=nc) + stats.nct.cdf(-crit, df=df, nc=nc)
    )


_META = RecipeMetadata(
    name="power_analysis_by_effect_size",
    modality="meta_and_diagnostic",
    family=RecipeFamily.diagnostic_curve,
    answers_question="How much statistical power does each planned sample size buy for a range of effect sizes?",
    required_fields=("effect_sizes", "n_range"),
    optional_fields=("alpha", "n_planned", "title"),
    file_format_hints=("yaml", "csv"),
    alternatives_in_modality=("sample_size_decision_ladder",),
)


@register_recipe(metadata=_META, contract=PowerAnalysisInput, demo_contract=_demo)
def render(contract: PowerAnalysisInput, ax=None, **_):
    """Power curves + 80% reference line + per-d N@80% annotations."""
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)
    n_lo, n_hi = contract.n_range
    ns = np.arange(n_lo, n_hi + 1)
    y80_n_by_d: dict[float, int | None] = {}

    for i, d in enumerate(contract.effect_sizes):
        pw = np.array([_power_t_two_sample(d, int(n), contract.alpha) for n in ns])
        color = palette[i]
        ax.plot(ns, pw, color=color, lw=1.0, label=f"d = {smart_fmt(d)}")
        # N@80%: first crossing. Alternate label y offsets so they don't
        # collide when multiple effect sizes cross 80% near the same N.
        above = pw >= 0.80
        if above.any():
            n80 = int(ns[np.argmax(above)])
            y80_n_by_d[d] = n80
            ax.scatter([n80], [0.80], color=color, s=30, edgecolor="white",
                       linewidth=1.0, zorder=5)
            y_off = 0.84 + 0.04 * i        # stagger per-d
            add_halo_label(ax, n80, y_off, f"n={n80}",
                           color=color, fontsize=6.4,
                           halo_width=2.2, va="bottom", ha="center")
        else:
            y80_n_by_d[d] = None

    ax.axhline(0.80, color="#D32F2F", lw=0.9, ls="--", zorder=2)
    ax.axhline(0.05, color="#888888", lw=0.6, ls=":", zorder=1)
    # Target label placed to the RIGHT of the axis at y=0.80 so it never
    # competes with the N@80% dots/labels on the left half.
    ax.text(n_hi * 0.995, 0.80, "80% power",
            color="#D32F2F", fontsize=6.8, ha="right", va="bottom")

    if contract.n_planned is not None:
        ax.axvline(contract.n_planned, color="#333333", lw=0.8, ls="--")
        add_halo_label(ax, contract.n_planned, 0.50,
                       f"planned n={contract.n_planned}",
                       color="#333333", fontsize=6.8, ha="left", va="center",
                       halo_width=2.4)

    # Callout: critical d given n_planned — placed bottom-right (below the
    # convex part of the power curves, so it does not overlap any trace).
    if contract.n_planned is not None:
        ds_grid = np.linspace(0.1, 2.0, 120)
        pws = np.array([_power_t_two_sample(d, contract.n_planned, contract.alpha) for d in ds_grid])
        ok = pws >= 0.80
        if ok.any():
            crit_d = float(ds_grid[np.argmax(ok)])
            fig = ax.figure
            fig.text(
                0.5, -0.16,
                f"At n={contract.n_planned}: detect d ≥ {smart_fmt(crit_d)} at 80% power",
                ha="center", va="top", fontsize=7.0,
                bbox=dict(boxstyle="round,pad=0.28", fc="white",
                          ec="#333333", lw=0.6),
                transform=ax.transAxes,
            )
            _ = callout_box

    ax.set_xlim(n_lo, n_hi)
    ax.set_ylim(-0.02, 1.06)
    ax.set_xlabel("Sample size per group")
    ax.set_ylabel(r"Power (1 − $\beta$)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    # Legend lower-right: the large-N region is where d=0.20 is still
    # climbing (power < 0.5) AND all higher-d curves are already saturated
    # at 1 — there is genuine empty space to anchor in.
    ax.legend(loc="lower right", bbox_to_anchor=(0.99, 0.03),
              fontsize=6.8, frameon=True, framealpha=0.92,
              edgecolor="#BBBBBB", ncol=2, handlelength=1.6,
              columnspacing=0.8, borderpad=0.4)
    return ax
