"""FRET vs orthogonal scalar-activity regression — cross-method validation."""

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


class FRETVsScalarInput(RecipeContract):
    fret_ratio: list[float] = Field(...)
    scalar_activity: list[float] = Field(
        ..., description="independent scalar activity readout (same n as fret_ratio)"
    )
    scalar_label: str = Field(..., description="y-axis label for the independent measure")
    condition: list[str] | None = Field(
        None, description="optional per-observation condition (drives point color)"
    )
    title: str = "FRET vs orthogonal activity"


def _demo() -> FRETVsScalarInput:
    rng = np.random.default_rng(617)
    n_per = 80
    # Two conditions: baseline (weak correlation) and stimulated (strong).
    fret_a = rng.normal(1.05, 0.08, n_per)
    scalar_a = 0.6 * fret_a + rng.normal(0.02, 0.06, n_per)
    fret_b = rng.normal(1.45, 0.14, n_per)
    scalar_b = 1.4 * fret_b + rng.normal(0.08, 0.10, n_per) - 0.8
    fret = np.concatenate([fret_a, fret_b])
    scalar = np.concatenate([scalar_a, scalar_b])
    conds = ["baseline"] * n_per + ["stimulated"] * n_per
    return FRETVsScalarInput(
        fret_ratio=fret.tolist(),
        scalar_activity=scalar.tolist(),
        scalar_label="phospho-ERK intensity (a.u.)",
        condition=conds,
    )


_META = RecipeMetadata(
    name="fret_vs_scalar_activity_regression",
    modality="fret_biosensors",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "Does the FRET ratio correlate with an independent scalar activity "
        "measure, and with what slope and Pearson r?"
    ),
    required_fields=("fret_ratio", "scalar_activity", "scalar_label"),
    optional_fields=("condition", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("sensor_calibration_curve",),
)


@register_recipe(
    metadata=_META,
    contract=FRETVsScalarInput,
    demo_contract=_demo,
)
def render(contract: FRETVsScalarInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.6, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    x = np.asarray(contract.fret_ratio, dtype=float)
    y = np.asarray(contract.scalar_activity, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]

    # Scatter coloured by condition when provided.
    if contract.condition is not None:
        conds = np.asarray(contract.condition)[mask]
        unique = list(dict.fromkeys(conds.tolist()))
        for i, name in enumerate(unique):
            m = conds == name
            color = (palette.pick(name) if name in palette.semantic
                     else palette[i % len(palette.colors)])
            ax.scatter(x[m], y[m], s=14, color=color, alpha=0.75,
                       edgecolor="white", linewidth=0.35,
                       zorder=3, label=f"{name} (n={int(m.sum())})")
    else:
        ax.scatter(x, y, s=14, color=palette[0], alpha=0.75,
                   edgecolor="white", linewidth=0.35, zorder=3)

    # Pooled OLS fit + 95% prediction band.
    slope, intercept = np.polyfit(x, y, 1)
    xfit = np.linspace(float(x.min()), float(x.max()), 200)
    yfit = slope * xfit + intercept
    resid = y - (slope * x + intercept)
    sigma = float(np.sqrt(np.mean(resid ** 2)))
    ax.fill_between(xfit, yfit - 1.96 * sigma, yfit + 1.96 * sigma,
                    color="#111111", alpha=0.08, linewidth=0, zorder=2)
    ax.plot(xfit, yfit, color="#111111", lw=1.1, zorder=4,
            label=f"fit (slope = {smart_fmt(float(slope))})")

    # Pearson r + p.
    try:
        r_val, p_val = stats.pearsonr(x, y)
    except Exception:
        r_val, p_val = float("nan"), float("nan")
    ax.text(
        0.04, 0.96,
        f"r = {smart_fmt(float(r_val))}\n"
        f"p = {smart_fmt(float(p_val))}\n"
        f"n = {x.size}",
        transform=ax.transAxes, ha="left", va="top",
        fontsize=6.6, color="#333333",
        bbox=dict(boxstyle="round,pad=0.22", fc="white",
                  ec="#BBBBBB", lw=0.5, alpha=0.92),
        zorder=7,
    )

    ax.set_xlabel(r"FRET ratio  F$_A$/F$_D$")
    ax.set_ylabel(contract.scalar_label)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.4, frameon=False, loc="lower right",
              handlelength=1.6)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
