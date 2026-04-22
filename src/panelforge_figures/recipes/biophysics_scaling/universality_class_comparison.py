"""Universality-class comparison — data overlaid on 2-3 theoretical
universality curves (e.g. mean-field, Ising-2D, KPZ) with per-class
residual bars choosing the best fit.

Distinct from `master_curve_collapse` (rescales to one unknown master)
and `log_log_with_theory_line` (single theory curve): here multiple
candidate classes are compared side-by-side.
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


class UniversalityClassInput(RecipeContract):
    x: list[float] = Field(..., min_length=5)
    y: list[float] = Field(..., min_length=5)
    class_names: list[str] = Field(..., min_length=2)
    class_exponents: list[float] = Field(
        ..., description="predicted exponent per class, same length as class_names"
    )
    x_label: str = "x"
    y_label: str = "y"
    title: str = "Universality-class comparison"


def _demo() -> UniversalityClassInput:
    rng = np.random.default_rng(209)
    # Data actually follows KPZ-like alpha ≈ 0.33.
    x = np.logspace(0, 2.8, 45)
    y = 0.7 * x ** 0.33 * np.exp(rng.normal(0, 0.08, x.size))
    return UniversalityClassInput(
        x=x.tolist(), y=y.tolist(),
        class_names=["mean-field (1/2)", "Ising-2D (1/8)", "KPZ (1/3)"],
        class_exponents=[0.5, 0.125, 1 / 3],
        x_label="system size L",
        y_label="roughness W(L)",
        title="Surface-roughness universality",
    )


_META = RecipeMetadata(
    name="universality_class_comparison",
    modality="biophysics_scaling",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "Which universality class (e.g. mean-field, Ising-2D, KPZ) best "
        "matches the data?"
    ),
    required_fields=("x", "y", "class_names", "class_exponents"),
    optional_fields=("x_label", "y_label", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=(
        "master_curve_collapse",
        "log_log_with_theory_line",
    ),
)


@register_recipe(
    metadata=_META,
    contract=UniversalityClassInput,
    demo_contract=_demo,
)
def render(contract: UniversalityClassInput, ax=None, **_):
    from mpl_toolkits.axes_grid1.inset_locator import inset_axes

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 3.8))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    x = np.asarray(contract.x, float)
    y = np.asarray(contract.y, float)
    lx = np.log10(x)
    ly = np.log10(y)

    names = contract.class_names
    alphas = np.asarray(contract.class_exponents, float)

    # For each class, fit its prefactor (intercept) and RMS residual.
    rms_list: list[float] = []
    log_as: list[float] = []
    for a in alphas:
        log_a = float(np.mean(ly - a * lx))
        resid = ly - (a * lx + log_a)
        rms_list.append(float(np.sqrt(np.mean(resid ** 2))))
        log_as.append(log_a)
    rms_arr = np.asarray(rms_list)
    best_idx = int(np.argmin(rms_arr))

    # Data scatter.
    ax.scatter(x, y, s=26, color="#333333", alpha=0.75,
               edgecolor="white", linewidth=0.5, zorder=4,
               label="data")

    # Each theory class as a coloured line.
    xfit = np.logspace(lx.min(), lx.max(), 100)
    for k, (nm, a, la) in enumerate(zip(names, alphas, log_as)):
        color = palette[k % len(palette.colors)]
        y_fit = 10 ** (a * np.log10(xfit) + la)
        lw = 1.3 if k == best_idx else 0.8
        ls = "-" if k == best_idx else "--"
        ax.plot(xfit, y_fit, color=color, lw=lw, ls=ls, zorder=3,
                label=f"{nm}  (RMS {smart_fmt(rms_arr[k])})")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(contract.x_label)
    ax.set_ylabel(contract.y_label)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="lower right",
              handlelength=1.6)
    ax.grid(axis="both", which="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    # Per-class RMS residual bar inset (horizontal bars, sorted).
    inset = inset_axes(ax, width="32%", height="28%",
                       loc="upper left", borderpad=0.8)
    AESTHETIC.apply_to_ax(inset)
    order = np.argsort(rms_arr)
    bar_colors = [palette[i % len(palette.colors)] for i in order]
    inset.barh(range(len(names)), rms_arr[order],
               color=bar_colors, edgecolor="white", linewidth=0.5,
               alpha=0.85)
    inset.set_yticks(range(len(names)))
    inset.set_yticklabels([names[i].split(" ")[0] for i in order],
                          fontsize=6.2)
    inset.invert_yaxis()
    inset.set_xlabel("RMS resid", fontsize=6.2)
    inset.tick_params(labelsize=6.2)

    # Callout for best class.
    ax.text(0.02, 0.04,
            f"best class: {names[best_idx]}\n"
            f"RMS = {smart_fmt(float(rms_arr[best_idx]))}",
            transform=ax.transAxes, ha="left", va="bottom",
            fontsize=6.8, color="#333333",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=5)
    return ax
