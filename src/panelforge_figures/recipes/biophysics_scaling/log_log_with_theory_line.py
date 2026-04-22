"""Log-log scaling vs a **theory-predicted** reference line.

Distinct from `log_log_scaling_with_slope_box` (which fits its own
slope): here the theoretical exponent is specified a priori and the
panel asks whether data is consistent with it, with a residuals-from-
theory inset to quantify deviations.
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


class LogLogTheoryInput(RecipeContract):
    x: list[float] = Field(..., min_length=5)
    y: list[float] = Field(..., min_length=5)
    theory_exponent: float = Field(..., description="predicted slope")
    theory_prefactor: float | None = Field(
        None, description="predicted y = a * x^alpha; if None, fit a only"
    )
    theory_label: str = r"theory: $y = a\, x^{\alpha}$"
    x_label: str = "x"
    y_label: str = "y"
    title: str = "Log-log vs theory"


def _demo() -> LogLogTheoryInput:
    rng = np.random.default_rng(141)
    x = np.logspace(0, 3, 55)
    y = 1.7 * x ** 1.5 * np.exp(rng.normal(0, 0.14, x.size))
    return LogLogTheoryInput(
        x=x.tolist(), y=y.tolist(),
        theory_exponent=1.5,
        theory_prefactor=None,
        x_label=r"length (μm)",
        y_label=r"stiffness (pN μm$^{-1}$)",
        title="Stiffness vs length — theory alpha = 3/2",
    )


_META = RecipeMetadata(
    name="log_log_with_theory_line",
    modality="biophysics_scaling",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "Is the data consistent with a theoretically predicted scaling "
        "exponent, and how large are the residuals from theory?"
    ),
    required_fields=("x", "y", "theory_exponent"),
    optional_fields=(
        "theory_prefactor", "theory_label", "x_label", "y_label", "title",
    ),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("log_log_scaling_with_slope_box",),
)


@register_recipe(metadata=_META, contract=LogLogTheoryInput, demo_contract=_demo)
def render(contract: LogLogTheoryInput, ax=None, **_):
    from mpl_toolkits.axes_grid1.inset_locator import inset_axes

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.6))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)
    accent = palette[5]

    x = np.asarray(contract.x, float)
    y = np.asarray(contract.y, float)
    alpha_th = float(contract.theory_exponent)
    lx = np.log10(x)
    ly = np.log10(y)

    # Fit theory prefactor `a` with slope fixed at alpha_th (if not given).
    if contract.theory_prefactor is None:
        log_a = float(np.mean(ly - alpha_th * lx))
        a_th = 10 ** log_a
    else:
        a_th = float(contract.theory_prefactor)
        log_a = np.log10(a_th)

    # Fit free slope for comparison.
    slope_free, intercept_free = np.polyfit(lx, ly, 1)

    # Data scatter.
    ax.scatter(x, y, s=22, color=accent, alpha=0.7,
               edgecolor="white", linewidth=0.5, zorder=3,
               label="data")
    # Theory line.
    xfit = np.logspace(lx.min(), lx.max(), 100)
    y_th = a_th * xfit ** alpha_th
    ax.plot(xfit, y_th, color="#222222", lw=1.1, zorder=4,
            label=rf"theory (α = {smart_fmt(alpha_th)})")
    # Free-fit line (dashed).
    y_free = 10 ** (slope_free * np.log10(xfit) + intercept_free)
    ax.plot(xfit, y_free, color="#888888", lw=0.8, ls="--", zorder=3,
            label=f"fit (α = {smart_fmt(float(slope_free))})")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(contract.x_label)
    ax.set_ylabel(contract.y_label)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="lower right",
              handlelength=1.6)
    ax.grid(axis="both", which="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    # Residuals-from-theory inset (bottom-right corner of parent axes).
    resid = ly - (alpha_th * lx + log_a)
    rms = float(np.sqrt(np.mean(resid ** 2)))
    inset = inset_axes(ax, width="34%", height="30%",
                       loc="upper left", borderpad=0.8)
    AESTHETIC.apply_to_ax(inset)
    inset.axhline(0, color="#222222", lw=0.8, zorder=2)
    inset.scatter(x, resid, s=12, color=accent, alpha=0.7,
                  edgecolor="white", linewidth=0.4, zorder=3)
    inset.set_xscale("log")
    inset.set_xlabel("x", fontsize=6.2)
    inset.set_ylabel(r"log$_{10}$ resid", fontsize=6.2)
    inset.tick_params(labelsize=6.2)
    inset.text(0.97, 0.05, f"RMS = {smart_fmt(rms)}",
               transform=inset.transAxes, ha="right", va="bottom",
               fontsize=6.2, color="#333333")
    inset.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
    inset.set_axisbelow(True)
    return ax
