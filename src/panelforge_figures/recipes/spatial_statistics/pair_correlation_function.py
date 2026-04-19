"""Pair correlation function g(r) — radial density relative to CSR baseline."""

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


class PCFInput(RecipeContract):
    r_um: list[float] = Field(...)
    g_r: list[float] = Field(...)
    ci_lo: list[float] | None = None
    ci_hi: list[float] | None = None
    title: str = "Pair correlation $g(r)$"


def _demo() -> PCFInput:
    rng = np.random.default_rng(403)
    r = np.linspace(0.5, 50, 80)
    g = 1 + 2.4 * np.exp(-((r - 10) ** 2) / 80.0) + rng.normal(0, 0.04, r.size)
    se = 0.12 * np.ones_like(r)
    return PCFInput(
        r_um=r.tolist(),
        g_r=g.tolist(),
        ci_lo=(g - 1.96 * se).tolist(),
        ci_hi=(g + 1.96 * se).tolist(),
    )


_META = RecipeMetadata(
    name="pair_correlation_function",
    modality="spatial_statistics",
    family=RecipeFamily.diagnostic_curve,
    answers_question="At what inter-point radius is the local density higher or lower than the mean density?",
    required_fields=("r_um", "g_r"),
    optional_fields=("ci_lo", "ci_hi", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("ripley_l_function",),
)


@register_recipe(metadata=_META, contract=PCFInput, demo_contract=_demo)
def render(contract: PCFInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    r = np.array(contract.r_um, dtype=float)
    g = np.array(contract.g_r, dtype=float)

    if contract.ci_lo is not None and contract.ci_hi is not None:
        lo = np.array(contract.ci_lo, dtype=float)
        hi = np.array(contract.ci_hi, dtype=float)
        ax.fill_between(r, lo, hi, color=palette[5], alpha=0.18,
                        linewidth=0, zorder=1, label="95% CI")

    ax.axhline(1.0, color="#888888", lw=0.6, ls="--", zorder=1,
               label="CSR (g=1)")
    ax.plot(r, g, color=palette[5], lw=1.3, zorder=3, label="observed")

    peak_idx = int(np.argmax(g))
    ax.annotate(
        f"peak g={smart_fmt(float(g[peak_idx]))} at r={smart_fmt(float(r[peak_idx]))} $\\mu$m",
        xy=(r[peak_idx], g[peak_idx]),
        xytext=(6, 6), textcoords="offset points",
        fontsize=6.4, color="#333333",
        bbox=dict(boxstyle="round,pad=0.16", fc="white", ec="none", alpha=0.9),
    )

    ax.set_xlabel(r"radius $r$ ($\mu$m)")
    ax.set_ylabel(r"$g(r)$")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.6, frameon=False, loc="upper right",
              handlelength=1.6)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
