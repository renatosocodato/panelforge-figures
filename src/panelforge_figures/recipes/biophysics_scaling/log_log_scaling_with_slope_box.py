"""Log-log scaling — scatter + fitted slope with a compact slope-box annotation."""

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


class LogLogScalingInput(RecipeContract):
    x: list[float] = Field(...)
    y: list[float] = Field(...)
    x_label: str = "x"
    y_label: str = "y"
    reference_slope: float | None = None
    title: str = "Log-log scaling"


def _demo() -> LogLogScalingInput:
    rng = np.random.default_rng(77)
    x = np.logspace(0, 3, 60)
    y = 2.1 * x ** 1.5 * np.exp(rng.normal(0, 0.12, x.size))
    return LogLogScalingInput(
        x=x.tolist(), y=y.tolist(),
        x_label=r"length (μm)", y_label=r"stiffness (pN μm$^{-1}$)",
        reference_slope=1.5,
    )


_META = RecipeMetadata(
    name="log_log_scaling_with_slope_box",
    modality="biophysics_scaling",
    family=RecipeFamily.scatter_collapse,
    answers_question="Does the observed y scale with x as a clean power law, and what is the exponent?",
    required_fields=("x", "y"),
    optional_fields=("x_label", "y_label", "reference_slope", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("master_curve_collapse", "power_law_tail_diagnostic"),
)


@register_recipe(metadata=_META, contract=LogLogScalingInput, demo_contract=_demo)
def render(contract: LogLogScalingInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)
    accent = palette[5]   # blue from okabe_ito

    x = np.array(contract.x, dtype=float)
    y = np.array(contract.y, dtype=float)
    # Fit slope in log space.
    lx, ly = np.log10(x), np.log10(y)
    slope, intercept = np.polyfit(lx, ly, 1)
    # R^2.
    yhat = slope * lx + intercept
    ss_res = np.nansum((ly - yhat) ** 2)
    ss_tot = np.nansum((ly - np.nanmean(ly)) ** 2)
    r2 = 1 - ss_res / max(ss_tot, 1e-12)

    # Data.
    ax.scatter(x, y, s=22, color=accent, alpha=0.65,
               edgecolor="white", linewidth=0.5, zorder=3)
    # Fit line.
    xfit = np.logspace(lx.min(), lx.max(), 80)
    yfit = 10 ** (slope * np.log10(xfit) + intercept)
    ax.plot(xfit, yfit, color="#222222", lw=1.1, zorder=4)
    # Reference slope line anchored at median log x.
    if contract.reference_slope is not None:
        x0 = 10 ** np.median(lx)
        y0 = 10 ** (slope * np.log10(x0) + intercept)
        yref = y0 * (xfit / x0) ** contract.reference_slope
        ax.plot(xfit, yref, color="#888888", lw=0.8, ls="--", zorder=2,
                label=f"ref slope {smart_fmt(contract.reference_slope)}")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(contract.x_label)
    ax.set_ylabel(contract.y_label)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    if contract.reference_slope is not None:
        ax.legend(fontsize=6.8, frameon=False, loc="lower right",
                  handlelength=1.6)

    # Slope-box annotation (upper-left).
    box_text = (
        f"slope = {smart_fmt(float(slope))}\n"
        f"R² = {smart_fmt(r2)}"
    )
    ax.text(0.02, 0.97, box_text,
            transform=ax.transAxes, ha="left", va="top",
            fontsize=7.0, color="#333333",
            bbox=dict(boxstyle="round,pad=0.24", fc="white",
                      ec="#BBBBBB", lw=0.6, alpha=0.92),
            zorder=5)
    ax.grid(axis="both", which="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
