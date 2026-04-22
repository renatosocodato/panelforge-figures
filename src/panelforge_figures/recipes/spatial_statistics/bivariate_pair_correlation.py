"""Bivariate pair correlation g_12(r) — pair correlation **between** two
point types with CSR envelope. Distinct from univariate g(r).
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


class BivariatePCFInput(RecipeContract):
    r_um: list[float] = Field(..., min_length=5)
    g12_observed: list[float] = Field(..., description="observed g_12(r)")
    csr_envelope_lo: list[float] = Field(...)
    csr_envelope_hi: list[float] = Field(...)
    type_a: str = "type A"
    type_b: str = "type B"
    title: str = "Bivariate pair correlation"


def _demo() -> BivariatePCFInput:
    rng = np.random.default_rng(1413)
    r = np.linspace(0.5, 35, 55)
    # Co-clustering at short range, segregation at medium.
    g12 = 1 + 1.8 * np.exp(-(r - 6) ** 2 / 14.0) \
            - 0.4 * np.exp(-(r - 18) ** 2 / 40.0)
    g12 += rng.normal(0, 0.04, r.size)
    lo = 0.85 + 0.02 * np.sqrt(r)
    hi = 1.15 - 0.01 * np.sqrt(r)
    hi = np.maximum(hi, 1.02)
    return BivariatePCFInput(
        r_um=r.tolist(),
        g12_observed=g12.tolist(),
        csr_envelope_lo=lo.tolist(),
        csr_envelope_hi=hi.tolist(),
        type_a="microglia",
        type_b="astrocytes",
    )


_META = RecipeMetadata(
    name="bivariate_pair_correlation",
    modality="spatial_statistics",
    family=RecipeFamily.diagnostic_curve,
    answers_question=(
        "At what radii are two cell types co-clustered (g_12 > 1) vs "
        "segregated (g_12 < 1)?"
    ),
    required_fields=(
        "r_um", "g12_observed", "csr_envelope_lo", "csr_envelope_hi",
    ),
    optional_fields=("type_a", "type_b", "title"),
    file_format_hints=("csv",),
    alternatives_in_modality=("pair_correlation_function",),
)


@register_recipe(
    metadata=_META,
    contract=BivariatePCFInput,
    demo_contract=_demo,
)
def render(contract: BivariatePCFInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.6))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    r = np.asarray(contract.r_um, float)
    g = np.asarray(contract.g12_observed, float)
    lo = np.asarray(contract.csr_envelope_lo, float)
    hi = np.asarray(contract.csr_envelope_hi, float)

    ax.fill_between(r, lo, hi, color="#BBBBBB", alpha=0.35, linewidth=0,
                    zorder=1, label="CSR envelope")
    ax.axhline(1.0, color="#888888", lw=0.8, ls="--", zorder=2)

    # Colour above-1 green, below-1 red.
    ax.fill_between(r, 1.0, g, where=(g >= 1.0),
                    color="#2E7D32", alpha=0.18, linewidth=0, zorder=2)
    ax.fill_between(r, 1.0, g, where=(g < 1.0),
                    color="#C62828", alpha=0.18, linewidth=0, zorder=2)
    ax.plot(r, g, color=palette[1], lw=1.3, zorder=4,
            label=f"{contract.type_a} x {contract.type_b}")

    # Peaks.
    peak_idx = int(np.argmax(g))
    trough_idx = int(np.argmin(g))
    ax.scatter([r[peak_idx]], [g[peak_idx]],
               s=34, color="#2E7D32", edgecolor="white", linewidth=0.7,
               zorder=6, label=f"peak @ {smart_fmt(float(r[peak_idx]))} μm")
    if g[trough_idx] < 0.9:
        ax.scatter([r[trough_idx]], [g[trough_idx]],
                   s=34, color="#C62828", edgecolor="white", linewidth=0.7,
                   zorder=6,
                   label=f"trough @ {smart_fmt(float(r[trough_idx]))} μm")

    ax.set_xlabel(r"r (μm)")
    ax.set_ylabel(r"$g_{12}(r)$")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="upper right",
              handlelength=1.6)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
