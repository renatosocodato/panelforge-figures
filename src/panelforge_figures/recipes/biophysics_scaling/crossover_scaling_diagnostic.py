"""Crossover scaling diagnostic — two-slope piecewise power law with
crossover scale ξ, plus a local-slope d log y / d log x inset that
reveals the transition between regimes.
"""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class CrossoverInput(RecipeContract):
    x: list[float] = Field(..., min_length=8)
    y: list[float] = Field(..., min_length=8)
    xi_guess: float | None = Field(
        None, description="initial crossover scale; None = median(x)"
    )
    x_label: str = "x"
    y_label: str = "y"
    title: str = "Crossover scaling diagnostic"


def _demo() -> CrossoverInput:
    rng = np.random.default_rng(913)
    x = np.logspace(-0.5, 2.8, 90)
    alpha_lo, alpha_hi, xi = 0.6, 2.1, 25.0
    y = np.where(
        x < xi,
        x ** alpha_lo,
        xi ** alpha_lo * (x / xi) ** alpha_hi,
    )
    y *= np.exp(rng.normal(0, 0.08, x.size))
    return CrossoverInput(
        x=x.tolist(), y=y.tolist(),
        xi_guess=20.0,
        x_label="L (μm)",
        y_label="variance",
        title="Crossover in process-length variance",
    )


_META = RecipeMetadata(
    name="crossover_scaling_diagnostic",
    modality="biophysics_scaling",
    family=RecipeFamily.diagnostic_curve,
    answers_question=(
        "Does the data cross over from one power-law regime to another "
        "at a characteristic scale ξ?"
    ),
    required_fields=("x", "y"),
    optional_fields=("xi_guess", "x_label", "y_label", "title"),
    file_format_hints=("csv",),
    alternatives_in_modality=("log_log_scaling_with_slope_box",),
)


@register_recipe(
    metadata=_META,
    contract=CrossoverInput,
    demo_contract=_demo,
)
def render(contract: CrossoverInput, ax=None, **_):
    from mpl_toolkits.axes_grid1.inset_locator import inset_axes

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.6))
    AESTHETIC.apply_to_ax(ax)

    x = np.asarray(contract.x, float)
    y = np.asarray(contract.y, float)
    lx, ly = np.log10(x), np.log10(y)

    # Local slope by 5-point window.
    win = max(5, len(x) // 12)
    centers, local_slopes = [], []
    for i in range(len(x) - win + 1):
        s, _ = np.polyfit(lx[i:i + win], ly[i:i + win], 1)
        centers.append(10 ** np.mean(lx[i:i + win]))
        local_slopes.append(s)
    centers = np.asarray(centers)
    local_slopes = np.asarray(local_slopes)

    # Find crossover as scale where local slope changes fastest.
    if contract.xi_guess is None:
        # Split point maximising slope difference.
        mid = int(np.argmax(np.abs(np.diff(local_slopes))))
        xi = float(centers[mid])
    else:
        xi = float(contract.xi_guess)

    # Fit lo-regime (x < xi) and hi-regime (x > xi).
    lo_mask = x < xi
    hi_mask = x >= xi
    if lo_mask.sum() >= 3 and hi_mask.sum() >= 3:
        a_lo, b_lo = np.polyfit(lx[lo_mask], ly[lo_mask], 1)
        a_hi, b_hi = np.polyfit(lx[hi_mask], ly[hi_mask], 1)
    else:
        a_lo = a_hi = 1.0
        b_lo = b_hi = 0.0

    # Data + piecewise fit on parent axes.
    ax.scatter(x, y, s=22, color="#1565C0", alpha=0.7,
               edgecolor="white", linewidth=0.5, zorder=3,
               label="data")
    xfit_lo = np.logspace(lx.min(), np.log10(xi), 40)
    xfit_hi = np.logspace(np.log10(xi), lx.max(), 40)
    ax.plot(xfit_lo, 10 ** (a_lo * np.log10(xfit_lo) + b_lo),
            color="#2E7D32", lw=1.1, zorder=5,
            label=f"low α = {smart_fmt(float(a_lo))}")
    ax.plot(xfit_hi, 10 ** (a_hi * np.log10(xfit_hi) + b_hi),
            color="#C62828", lw=1.1, zorder=5,
            label=f"high α = {smart_fmt(float(a_hi))}")
    ax.axvline(xi, color="#444444", lw=0.8, ls="--", zorder=4,
               label=f"ξ = {smart_fmt(xi)}")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(contract.x_label)
    ax.set_ylabel(contract.y_label)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="lower right",
              handlelength=1.6)
    ax.grid(axis="both", which="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    # Local-slope inset.
    inset = inset_axes(ax, width="34%", height="30%",
                       loc="upper left", borderpad=0.8)
    AESTHETIC.apply_to_ax(inset)
    inset.plot(centers, local_slopes, color="#1565C0", lw=0.8, zorder=3)
    inset.scatter(centers, local_slopes, s=10, color="#1565C0",
                  alpha=0.8, edgecolor="white", linewidth=0.4, zorder=4)
    inset.axvline(xi, color="#444444", lw=0.6, ls="--", zorder=2)
    inset.axhline(a_lo, color="#2E7D32", lw=0.5, ls=":", zorder=2)
    inset.axhline(a_hi, color="#C62828", lw=0.5, ls=":", zorder=2)
    inset.set_xscale("log")
    inset.set_xlabel("x", fontsize=6.2)
    inset.set_ylabel("local α", fontsize=6.2)
    inset.tick_params(labelsize=6.2)
    inset.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
    inset.set_axisbelow(True)
    return ax
