"""Power-law tail diagnostic — rank-frequency plot + fitted α exponent for the tail."""

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


class PowerLawTailInput(RecipeContract):
    values: list[float] = Field(..., description="strictly positive observations")
    tail_fraction: float = 0.25
    x_label: str = "value"
    title: str = "Power-law tail"


def _demo() -> PowerLawTailInput:
    rng = np.random.default_rng(89)
    # Mixture: body is lognormal, tail is power-law-like.
    body = rng.lognormal(0, 0.4, 400)
    alpha = 2.3
    tail = (rng.pareto(alpha - 1, 200) + 1) * 3
    return PowerLawTailInput(
        values=(np.concatenate([body, tail])).tolist(),
        tail_fraction=0.25,
        x_label="event magnitude",
        title="Magnitude rank-frequency",
    )


_META = RecipeMetadata(
    name="power_law_tail_diagnostic",
    modality="biophysics_scaling",
    family=RecipeFamily.diagnostic_curve,
    answers_question="Does the tail of a distribution follow a power law, and if so with what exponent?",
    required_fields=("values",),
    optional_fields=("tail_fraction", "x_label", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("log_log_scaling_with_slope_box",),
)


@register_recipe(metadata=_META, contract=PowerLawTailInput, demo_contract=_demo)
def render(contract: PowerLawTailInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)
    accent = palette[5]

    v = np.array(contract.values, dtype=float)
    v = v[v > 0]
    v.sort()
    v = v[::-1]                       # descending
    ranks = np.arange(1, v.size + 1)
    # Rank-frequency (empirical survival): P(X >= v) ≈ rank / N.
    P = ranks / v.size

    # Scatter.
    ax.scatter(v, P, s=12, color=accent, alpha=0.5,
               edgecolor="none", zorder=3)

    # Fit power law on top tail_fraction.
    n_tail = max(12, int(contract.tail_fraction * v.size))
    tail_v = v[:n_tail]
    tail_P = P[:n_tail]
    lx, ly = np.log(tail_v), np.log(tail_P)
    slope, intercept = np.polyfit(lx, ly, 1)
    alpha_est = -slope + 1          # P ~ v^(-(alpha-1)) → alpha = 1 - slope

    # Fit line (over tail range).
    xfit = np.linspace(lx.min(), lx.max(), 60)
    ax.plot(np.exp(xfit), np.exp(slope * xfit + intercept),
            color="#D32F2F", lw=1.2, zorder=5,
            label=rf"tail: $\alpha$ = {smart_fmt(alpha_est)}")

    # Tail-start marker — label anchored in axes fraction, clear of x-ticks.
    ax.axvline(tail_v[-1], color="#888888", lw=0.7, ls="--", zorder=1)
    ax.annotate(
        f"tail $\\geq$ {smart_fmt(float(tail_v[-1]))}",
        xy=(tail_v[-1], 0.55),
        xycoords=("data", "axes fraction"),
        xytext=(3, 0), textcoords="offset points",
        ha="left", va="center", fontsize=6.4, color="#555555",
        bbox=dict(boxstyle="round,pad=0.14", fc="white",
                  ec="none", alpha=0.9),
    )

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(contract.x_label)
    ax.set_ylabel(r"P(X $\geq$ x)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="lower left",
              handlelength=2.0)
    ax.grid(axis="both", which="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
