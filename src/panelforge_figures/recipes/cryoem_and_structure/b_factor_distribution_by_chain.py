"""Per-chain B-factor ridge — one ridge per chain with median markers.

Distinct from `bfactor_vs_residue` (single trace across all residues):
this shows per-chain distributions so differences in flexibility
between chains are visible.
"""

from __future__ import annotations

import numpy as np
from pydantic import Field
from scipy.stats import gaussian_kde

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class BFactorByChainInput(RecipeContract):
    b_factors_by_chain: dict[str, list[float]] = Field(
        ..., description="chain ID -> list of per-atom / per-residue B-factors"
    )
    title: str = "B-factor distribution by chain"


def _demo() -> BFactorByChainInput:
    rng = np.random.default_rng(2707)
    return BFactorByChainInput(
        b_factors_by_chain={
            "chain A": rng.gamma(2.8, 6.0, 350).tolist(),
            "chain B": rng.gamma(2.2, 9.0, 280).tolist(),
            "chain C": rng.gamma(3.0, 5.5, 220).tolist(),
            "chain D": rng.gamma(1.8, 12.0, 160).tolist(),
        },
    )


_META = RecipeMetadata(
    name="b_factor_distribution_by_chain",
    modality="cryoem_and_structure",
    family=RecipeFamily.ridge_by_group,
    answers_question=(
        "Across chains, how do B-factor distributions differ (which "
        "chains are more flexible)?"
    ),
    required_fields=("b_factors_by_chain",),
    optional_fields=("title",),
    file_format_hints=("csv",),
    alternatives_in_modality=("bfactor_vs_residue",),
)


@register_recipe(
    metadata=_META, contract=BFactorByChainInput, demo_contract=_demo,
)
def render(contract: BFactorByChainInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.4))
    AESTHETIC.apply_to_ax(ax)

    chains = list(contract.b_factors_by_chain.keys())
    palette_colors = ["#1565C0", "#E65100", "#2E7D32", "#6A1B9A", "#C2185B"]
    all_vals = np.concatenate([
        np.asarray(contract.b_factors_by_chain[c], float) for c in chains
    ])
    xg = np.linspace(0, float(np.percentile(all_vals, 99)), 240)

    kdes = {c: gaussian_kde(np.asarray(contract.b_factors_by_chain[c], float))
            for c in chains}
    max_d = max(k(xg).max() for k in kdes.values())

    y_step = 1.0
    for i, c in enumerate(chains[::-1]):
        color = palette_colors[(len(chains) - 1 - i) % len(palette_colors)]
        vals = np.asarray(contract.b_factors_by_chain[c], float)
        dens = kdes[c](xg)
        dens_s = (dens / max_d) * 0.85 * y_step
        y_base = i * y_step
        ax.fill_between(xg, y_base, y_base + dens_s,
                        color=color, alpha=0.55, linewidth=0, zorder=3)
        ax.plot(xg, y_base + dens_s, color=color, lw=0.8, zorder=4)

        med = float(np.median(vals))
        mean = float(np.mean(vals))
        ax.scatter([med], [y_base + 0.08], s=22, marker="v",
                   color=color, edgecolor="white", linewidth=0.4,
                   zorder=6)
        ax.text(xg[0], y_base + 0.45 * y_step, c,
                ha="left", va="center", fontsize=7.0, color="#222222")
        ax.text(xg[-1] * 0.98, y_base + 0.82 * y_step,
                f"med {smart_fmt(med)}   mean {smart_fmt(mean)}",
                ha="right", va="top", fontsize=6.4, color=color)

    ax.set_xlim(0, xg.max())
    ax.set_ylim(-0.3, len(chains) - 0.1)
    ax.set_yticks([])
    ax.set_xlabel("B-factor (Å²)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)

    for side in ("left",):
        ax.spines[side].set_visible(False)
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
