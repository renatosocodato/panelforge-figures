"""Schild regression — log(DR-1) vs log[antagonist] with pA2 readout."""

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


class SchildInput(RecipeContract):
    log_antagonist: list[float] = Field(..., description="log10[antagonist] (M)")
    log_dr_minus_1: list[float] = Field(..., description="log10(DR - 1)")
    replicate_id: list[str] | None = None
    antagonist_name: str = "antagonist"
    title: str = "Schild regression"


def _demo() -> SchildInput:
    rng = np.random.default_rng(73)
    # True pA2 ~ 8 (so antagonist concentration at DR-1=1 is 1e-8 M).
    # Slope unity implies competitive antagonism.
    log_ant = np.tile(np.linspace(-9, -5, 9), 3)
    true = -(log_ant + 8.0)                        # slope +1, x-intercept at -8
    noisy = true + rng.normal(0, 0.12, log_ant.size)
    reps = [f"rep{k}" for k in np.repeat([1, 2, 3], 9)]
    return SchildInput(
        log_antagonist=log_ant.tolist(),
        log_dr_minus_1=noisy.tolist(),
        replicate_id=reps,
        antagonist_name="AntagonistX",
    )


_META = RecipeMetadata(
    name="schild_regression",
    modality="dose_response_pharmacology",
    family=RecipeFamily.scatter_collapse,
    answers_question="Is the antagonist competitive (Schild slope ≈ 1), and what is pA2?",
    required_fields=("log_antagonist", "log_dr_minus_1"),
    optional_fields=("replicate_id", "antagonist_name", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("hill_fit_with_ci",),
)


@register_recipe(metadata=_META, contract=SchildInput, demo_contract=_demo)
def render(contract: SchildInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.6, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)
    accent = palette.pick("signaling") if "signaling" in palette.semantic else palette[0]

    x = np.array(contract.log_antagonist, dtype=float)
    y = np.array(contract.log_dr_minus_1, dtype=float)

    ax.scatter(x, y, s=24, color=accent, alpha=0.75,
               edgecolor="white", linewidth=0.5, zorder=3)

    # Linear fit.
    slope, intercept = np.polyfit(x, y, 1)
    xfit = np.linspace(x.min(), x.max(), 60)
    yfit = slope * xfit + intercept
    ax.plot(xfit, yfit, color="#333333", lw=1.1, zorder=4)

    # Reference slope-1 line anchored at the fit's x-intercept.
    x0 = -intercept / max(slope, 1e-9)
    ax.plot(xfit, -(xfit - x0),
            color="#888888", lw=0.7, ls="--", zorder=2)

    # pA2 = -log[A] where log(DR-1) = 0. Solve 0 = slope*x + intercept.
    pa2 = -(-intercept / max(slope, 1e-9))       # = x0

    ax.scatter([x0], [0], s=48, color="#D32F2F",
               edgecolor="white", linewidth=1.0, zorder=5, marker="*")
    ax.axhline(0, color="#888888", lw=0.5, ls=":", zorder=1)

    ax.set_xlabel(r"$\log_{10}$[" + contract.antagonist_name + r"] (M)")
    ax.set_ylabel(r"$\log_{10}(DR - 1)$")
    ax.set_title(contract.title, fontsize=9.0, pad=4)

    ax.text(0.02, 0.97,
            f"slope = {smart_fmt(float(slope))}\n"
            r"$\mathrm{pA}_2$ = " + smart_fmt(float(pa2)),
            transform=ax.transAxes, ha="left", va="top",
            fontsize=6.8, color="#333333",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=6)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
