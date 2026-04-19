"""Mixed-model residual diagnostic — QQ + fitted-vs-residual in a 1×2 panel."""

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


class ResidualDiagInput(RecipeContract):
    fitted: list[float] = Field(...)
    residuals: list[float] = Field(...)
    title: str = "Residual diagnostics"


def _demo() -> ResidualDiagInput:
    rng = np.random.default_rng(59)
    n = 280
    fitted = rng.uniform(-1.5, 2.5, n)
    residuals = rng.normal(0, 0.7, n) + 0.12 * fitted ** 2 * rng.normal(0, 0.18, n)
    return ResidualDiagInput(fitted=fitted.tolist(), residuals=residuals.tolist())


_META = RecipeMetadata(
    name="mixed_model_residual_diagnostic",
    modality="mixed_effects_models",
    family=RecipeFamily.diagnostic_curve,
    answers_question="Do the model residuals look normal (QQ) and free of fitted-value patterns?",
    required_fields=("fitted", "residuals"),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("posterior_predictive_check",),
)


@register_recipe(metadata=_META, contract=ResidualDiagInput, demo_contract=_demo)
def render(contract: ResidualDiagInput, ax=None, **_):
    """Split the axis into two side-by-side diagnostics (QQ, fitted-vs-resid)."""
    import matplotlib.pyplot as plt
    if ax is None:
        fig = plt.figure(figsize=(5.8, 3.0))
        gs = fig.add_gridspec(1, 2, wspace=0.32)
        ax_qq = fig.add_subplot(gs[0, 0])
        ax_fr = fig.add_subplot(gs[0, 1])
    else:
        fig = ax.figure
        pos = ax.get_subplotspec()
        ax.remove()
        sub = pos.subgridspec(1, 2, wspace=0.32)
        ax_qq = fig.add_subplot(sub[0, 0])
        ax_fr = fig.add_subplot(sub[0, 1])

    AESTHETIC.apply_to_ax(ax_qq)
    AESTHETIC.apply_to_ax(ax_fr)
    palette = get_palette(AESTHETIC.primary_palette)
    accent = palette[0]

    resid = np.array(contract.residuals, dtype=float)
    fitted = np.array(contract.fitted, dtype=float)

    # ── Left: QQ ────────────────────────────────────────────────────
    osm, osr = stats.probplot(resid, dist="norm", fit=False)
    ax_qq.scatter(osm, osr, s=10, color=accent, alpha=0.6,
                  edgecolor="none", zorder=3)
    # Reference line.
    slope, intercept = np.polyfit(osm, osr, 1)
    x_lim = np.array([osm.min(), osm.max()])
    ax_qq.plot(x_lim, slope * x_lim + intercept,
               color="#333333", lw=0.8, ls="--", zorder=2,
               label="reference")
    # Horizontal y=0 line for extra visual line (diagnostic context).
    ax_qq.axhline(0, color="#BBBBBB", lw=0.4, ls=":", zorder=1,
                  label="zero")
    ax_qq.legend(fontsize=6.2, frameon=False, loc="lower right",
                 handlelength=1.6)
    ax_qq.set_xlabel("theoretical quantile")
    ax_qq.set_ylabel("residual quantile")
    ax_qq.set_title("QQ plot", fontsize=8.4, pad=3)
    ax_qq.grid(axis="both", color="#EEEEEE", lw=0.4)
    ax_qq.set_axisbelow(True)
    # Shapiro-Wilk tag.
    _, pval = stats.shapiro(resid) if resid.size <= 5000 else (None, np.nan)
    ax_qq.text(0.03, 0.97,
               f"Shapiro p={smart_fmt(float(pval))}",
               transform=ax_qq.transAxes, ha="left", va="top",
               fontsize=6.4, color="#444444",
               bbox=dict(boxstyle="round,pad=0.20", fc="white",
                         ec="#BBBBBB", lw=0.5, alpha=0.92),
               zorder=5)

    # ── Right: fitted-vs-residual + lowess-lite ─────────────────────
    ax_fr.scatter(fitted, resid, s=10, color=accent, alpha=0.45,
                  edgecolor="none", zorder=3)
    # Zero line.
    ax_fr.axhline(0, color="#888888", lw=0.7, ls="--", zorder=2)
    # Rolling mean (binned).
    bins = np.linspace(fitted.min(), fitted.max(), 14)
    centers = 0.5 * (bins[:-1] + bins[1:])
    roll_mean = []
    for b_lo, b_hi in zip(bins[:-1], bins[1:]):
        mask = (fitted >= b_lo) & (fitted < b_hi)
        roll_mean.append(np.nanmean(resid[mask]) if mask.any() else np.nan)
    ax_fr.plot(centers, roll_mean, color="#D32F2F", lw=1.0, zorder=4)
    ax_fr.set_xlabel("fitted value")
    ax_fr.set_ylabel("residual")
    ax_fr.set_title("fitted vs residual", fontsize=8.4, pad=3)
    ax_fr.grid(axis="both", color="#EEEEEE", lw=0.4)
    ax_fr.set_axisbelow(True)

    fig.suptitle(contract.title, fontsize=9.6, y=1.04)
    return ax_qq
