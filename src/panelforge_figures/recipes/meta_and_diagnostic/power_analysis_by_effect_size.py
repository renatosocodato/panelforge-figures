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
        ax.plot(ns, pw, color=color, lw=1.6, label=f"d = {smart_fmt(d)}")
        # N@80%: first crossing.
        above = pw >= 0.80
        if above.any():
            n80 = int(ns[np.argmax(above)])
            y80_n_by_d[d] = n80
            ax.scatter([n80], [0.80], color=color, s=30, edgecolor="white",
                       linewidth=1.0, zorder=5)
            add_halo_label(ax, n80, 0.80, f"n={n80}",
                           color=color, fontsize=6.8, fontweight="bold",
                           halo_width=2.4, va="bottom", ha="left")
        else:
            y80_n_by_d[d] = None

    ax.axhline(0.80, color="#D32F2F", lw=0.9, ls="--", zorder=2)
    ax.axhline(0.05, color="#888888", lw=0.6, ls=":", zorder=1)
    add_halo_label(ax, n_lo + 2, 0.82, "80% power target",
                   color="#D32F2F", fontsize=7.0, ha="left", va="bottom",
                   halo_width=2.6, fontweight="bold")

    if contract.n_planned is not None:
        ax.axvline(contract.n_planned, color="#333333", lw=0.8, ls="--")
        add_halo_label(ax, contract.n_planned, 0.05,
                       f"planned n={contract.n_planned}",
                       color="#333333", fontsize=6.8, ha="left", va="bottom",
                       halo_width=2.4, fontweight="bold")

    # Callout: critical d given n_planned.
    if contract.n_planned is not None:
        ds_grid = np.linspace(0.1, 2.0, 120)
        pws = np.array([_power_t_two_sample(d, contract.n_planned, contract.alpha) for d in ds_grid])
        ok = pws >= 0.80
        if ok.any():
            crit_d = float(ds_grid[np.argmax(ok)])
            callout_box(
                ax,
                0.03,
                0.96,
                f"At n={contract.n_planned}, we detect d ≥ {smart_fmt(crit_d)} at 80% power.",
                accent="#333333",
                transform=ax.transAxes,
            )

    ax.set_xlim(n_lo, n_hi)
    ax.set_ylim(-0.02, 1.02)
    ax.set_xlabel("Sample size per group")
    ax.set_ylabel(r"Power (1 − $\beta$)")
    ax.set_title(contract.title, fontsize=9.0, fontweight="bold")
    ax.legend(loc="lower right", fontsize=6.8, frameon=False, ncol=2)
    return ax
