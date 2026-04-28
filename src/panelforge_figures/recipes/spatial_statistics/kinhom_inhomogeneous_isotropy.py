"""Inhomogeneous K-function (Kinhom) — edge-corrected K(r) accounting
for spatially varying intensity λ(x); per-condition curves overlaid
with CSR Monte Carlo envelopes; Kpois(r) = π·r² reference.

Diagnostic-curve family: >=2 curves + >=1 legend.
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

_CONDITION_PALETTE = {
    "WT": "#37474F", "LI": "#EF5350",
    "control": "#37474F", "DISC1": "#EF5350",
}


class KinhomIsotropyInput(RecipeContract):
    r_grid_um: list[float] = Field(...)
    kinhom_curves: dict[str, list[float]] = Field(
        ...,
        description="condition → Kinhom(r) curve",
    )
    csr_envelope: dict[str, list[list[float]]] = Field(
        ...,
        description="condition → [(lo_at_r, hi_at_r) pairs] (n_r × 2)",
    )
    title: str = "Inhomogeneous Ripley K (edge-corrected)"


def _demo() -> KinhomIsotropyInput:
    rng = np.random.default_rng(641)
    r_grid = np.linspace(0, 8.0, 60).tolist()
    r_arr = np.asarray(r_grid)
    # Theoretical CSR baseline: Kpois(r) = π r².
    kpois = np.pi * r_arr ** 2

    kinhom: dict[str, list[float]] = {}
    envelope: dict[str, list[list[float]]] = {}
    # WT: lies inside CSR envelope (no spatial structure beyond
    # inhomogeneity).  LI: clustering — Kinhom > Kpois.
    for cond, scale in (("WT", 0.06), ("LI", 0.40)):
        # Draw 50 Monte Carlo CSR repeats with similar intensity field.
        repeats = []
        for _ in range(50):
            repeats.append(kpois * (1.0 + rng.normal(0, 0.05, kpois.size))
                           + rng.normal(0, 0.5, kpois.size))
        repeats_arr = np.asarray(repeats)
        lo = np.quantile(repeats_arr, 0.025, axis=0)
        hi = np.quantile(repeats_arr, 0.975, axis=0)
        envelope[cond] = [[float(a), float(b)]
                          for a, b in zip(lo, hi)]
        # Observed Kinhom: scaled excess clustering for LI.
        observed = kpois * (1.0 + scale) + rng.normal(0, 0.4, kpois.size)
        kinhom[cond] = observed.tolist()

    return KinhomIsotropyInput(
        r_grid_um=r_grid,
        kinhom_curves=kinhom,
        csr_envelope=envelope,
    )


_META = RecipeMetadata(
    name="kinhom_inhomogeneous_isotropy",
    modality="spatial_statistics",
    family=RecipeFamily.diagnostic_curve,
    answers_question=(
        "Per condition, does the inhomogeneous Ripley Kinhom(r) "
        "curve exceed CSR's Kpois(r) = π·r² (clustering) or sit "
        "inside the Monte-Carlo envelope (consistent with random)?"
    ),
    required_fields=("r_grid_um", "kinhom_curves", "csr_envelope"),
    optional_fields=("title",),
    file_format_hints=("csv", "yaml"),
    alternatives_in_modality=("ripley_l_function", "pair_correlation_function"),
)


@register_recipe(
    metadata=_META,
    contract=KinhomIsotropyInput,
    demo_contract=_demo,
)
def render(contract: KinhomIsotropyInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.8, 3.8))
    AESTHETIC.apply_to_ax(ax)

    r_arr = np.asarray(contract.r_grid_um, float)
    kpois = np.pi * r_arr ** 2

    # Plot Kpois reference first.
    ax.plot(r_arr, kpois, color="#888888", lw=0.9, ls="--",
            zorder=2, label="K_pois = pi r^2 (CSR)")

    bits = []
    for cond, curve in contract.kinhom_curves.items():
        colour = _CONDITION_PALETTE.get(cond, "#37474F")
        env = np.asarray(contract.csr_envelope.get(cond, []),
                         float)
        if env.size > 0:
            ax.fill_between(r_arr, env[:, 0], env[:, 1],
                            color=colour, alpha=0.18,
                            linewidth=0, zorder=2,
                            label=f"{cond} CSR envelope")
        ax.plot(r_arr, np.asarray(curve, float),
                color=colour, lw=1.4, zorder=4, label=cond)
        # Verdict: how often does the curve exceed the upper envelope?
        if env.size > 0:
            exceeds = (np.asarray(curve, float) > env[:, 1]).mean()
            bits.append(f"{cond}: {smart_fmt(exceeds * 100)}% above CSR")

    ax.set_xlabel("radius r (um)")
    ax.set_ylabel("K_inhom(r) (um^2)")
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(fontsize=6.4, frameon=False, loc="upper left",
              handlelength=1.4)
    ax.set_title(
        f"{contract.title}  ·  " + "   ".join(bits),
        fontsize=8.2, pad=4,
    )
    return ax
