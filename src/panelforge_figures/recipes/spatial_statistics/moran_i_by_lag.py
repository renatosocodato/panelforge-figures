"""Moran's I by spatial lag — autocorrelation of a scalar field vs neighborhood radius."""

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


class MoranInput(RecipeContract):
    lag_um: list[float] = Field(...)
    morans_i: list[float] = Field(...)
    ci_lo: list[float] = Field(...)
    ci_hi: list[float] = Field(...)
    expected_value: float = 0.0
    title: str = "Moran's $I$ vs spatial lag"


def _demo() -> MoranInput:
    rng = np.random.default_rng(413)
    lags = np.linspace(2, 60, 30)
    # Positive autocorr at short lags, decays to ~0.
    mi = 0.6 * np.exp(-lags / 18.0) + rng.normal(0, 0.02, lags.size)
    ci = 0.06 * np.ones_like(lags)
    return MoranInput(
        lag_um=lags.tolist(),
        morans_i=mi.tolist(),
        ci_lo=(mi - ci).tolist(),
        ci_hi=(mi + ci).tolist(),
        expected_value=-1.0 / 500,
    )


_META = RecipeMetadata(
    name="moran_i_by_lag",
    modality="spatial_statistics",
    family=RecipeFamily.diagnostic_curve,
    answers_question="At what neighborhood radius does a spatial signal stop being autocorrelated?",
    required_fields=("lag_um", "morans_i", "ci_lo", "ci_hi"),
    optional_fields=("expected_value", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("ripley_l_function",),
)


@register_recipe(metadata=_META, contract=MoranInput, demo_contract=_demo)
def render(contract: MoranInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    lags = np.array(contract.lag_um, dtype=float)
    mi = np.array(contract.morans_i, dtype=float)
    lo = np.array(contract.ci_lo, dtype=float)
    hi = np.array(contract.ci_hi, dtype=float)

    ax.fill_between(lags, lo, hi, color=palette[3], alpha=0.18,
                    linewidth=0, zorder=1, label="95% CI")
    ax.plot(lags, mi, color=palette[3], lw=1.3, zorder=3, label="Moran's $I$")
    ax.axhline(contract.expected_value, color="#888888",
               lw=0.6, ls="--", zorder=1,
               label=rf"E[I] = {smart_fmt(contract.expected_value)}")

    # Find first lag where CI crosses zero.
    crossings = np.where(np.diff(np.sign(lo)))[0]
    if crossings.size > 0:
        r_star = float(lags[crossings[0]])
        ax.axvline(r_star, color="#D32F2F", lw=0.7, ls="-.", zorder=2)
        ax.annotate(
            f"decorrelation ~ {smart_fmt(r_star)} $\\mu$m",
            xy=(r_star, max(mi.max() * 0.7, 0.2)),
            xytext=(6, 0), textcoords="offset points",
            fontsize=6.4, color="#D32F2F",
            bbox=dict(boxstyle="round,pad=0.16", fc="white",
                      ec="none", alpha=0.9),
        )

    ax.set_xlabel(r"spatial lag ($\mu$m)")
    ax.set_ylabel("Moran's $I$")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.6, frameon=False, loc="upper right",
              handlelength=1.6)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
