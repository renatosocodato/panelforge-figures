"""Knudsen-Reynolds regime diagram — Kn × Re log-log regime map with
continuum / slip / transition / free-molecular bands shaded, sample
points overlaid, and a regime-membership callout.
"""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
)
from ._aesthetic import AESTHETIC


class KnReInput(RecipeContract):
    knudsen: list[float] = Field(..., min_length=3, description="Kn per sample")
    reynolds: list[float] = Field(..., min_length=3, description="Re per sample")
    sample_labels: list[str] | None = None
    title: str = "Knudsen-Reynolds regime diagram"


def _demo() -> KnReInput:
    rng = np.random.default_rng(503)
    # Three sample clusters in different regimes.
    kn_a = 10 ** rng.normal(-3.5, 0.3, 10)   # continuum
    re_a = 10 ** rng.normal(2.0, 0.3, 10)
    kn_b = 10 ** rng.normal(-1.2, 0.3, 10)   # slip
    re_b = 10 ** rng.normal(0.8, 0.3, 10)
    kn_c = 10 ** rng.normal(0.5, 0.3, 10)    # transition
    re_c = 10 ** rng.normal(-0.5, 0.3, 10)
    kn = np.concatenate([kn_a, kn_b, kn_c])
    re = np.concatenate([re_a, re_b, re_c])
    labels = (["continuum"] * 10 + ["slip"] * 10 + ["transition"] * 10)
    return KnReInput(
        knudsen=kn.tolist(),
        reynolds=re.tolist(),
        sample_labels=labels,
        title="Microfluidic operating points",
    )


_META = RecipeMetadata(
    name="knudsen_reynolds_regime_diagram",
    modality="biophysics_scaling",
    family=RecipeFamily.matrix,
    answers_question=(
        "Given the sample's Knudsen and Reynolds numbers, which flow / "
        "transport regime (continuum, slip, transition, free-molecular) "
        "does it occupy?"
    ),
    required_fields=("knudsen", "reynolds"),
    optional_fields=("sample_labels", "title"),
    file_format_hints=("csv",),
    alternatives_in_modality=("stress_strain_regime_map",),
)


@register_recipe(metadata=_META, contract=KnReInput, demo_contract=_demo)
def render(contract: KnReInput, ax=None, **_):
    import matplotlib.patches as mpatches

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.8))
    AESTHETIC.apply_to_ax(ax)

    kn = np.asarray(contract.knudsen, float)
    re = np.asarray(contract.reynolds, float)

    # Log plot span.
    kn_lo, kn_hi = 1e-4, 1e2
    re_lo, re_hi = 1e-2, 1e4
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(kn_lo, kn_hi)
    ax.set_ylim(re_lo, re_hi)

    # Regime bands (Kn cutoffs: 0.01, 0.1, 10).
    regime_colors = {
        "continuum":     ("#DDE9F6", 1e-4, 1e-2),
        "slip":          ("#E6F2D9", 1e-2, 1e-1),
        "transition":    ("#F7E6C4", 1e-1, 1e1),
        "free-mol.":     ("#F6D6D0", 1e1, 1e2),
    }
    for name, (color, lo, hi) in regime_colors.items():
        ax.add_patch(mpatches.Rectangle(
            (lo, re_lo), hi - lo, re_hi - re_lo,
            facecolor=color, edgecolor="none", alpha=0.6, zorder=1,
        ))
        # Regime label at bottom of each strip (horizontal, no legend
        # collision).
        mid = np.sqrt(lo * hi)
        ax.text(mid, re_lo * 2.5, name,
                ha="center", va="bottom", fontsize=6.8,
                color="#444444", zorder=2, rotation=0,
                fontweight="bold")

    # Kn threshold vertical lines.
    for cut in [1e-2, 1e-1, 1e1]:
        ax.axvline(cut, color="#AAAAAA", lw=0.5, ls=":", zorder=2)

    # Sample scatter.
    labels = (contract.sample_labels
              if contract.sample_labels is not None
              else ["sample"] * len(kn))
    unique = list(dict.fromkeys(labels))
    marker_colors = ["#1565C0", "#2E7D32", "#C62828", "#6A1B9A", "#E65100"]
    gmap = {g: marker_colors[i % len(marker_colors)] for i, g in enumerate(unique)}
    for g in unique:
        idx = [i for i, lb in enumerate(labels) if lb == g]
        ax.scatter(kn[idx], re[idx], s=32,
                   color=gmap[g], edgecolor="white", linewidth=0.6,
                   alpha=0.85, zorder=5, label=g)

    # Count points per regime.
    def _which(k):
        if k < 1e-2:
            return "continuum"
        if k < 1e-1:
            return "slip"
        if k < 1e1:
            return "transition"
        return "free-mol."
    counts: dict[str, int] = {}
    for k in kn:
        w = _which(float(k))
        counts[w] = counts.get(w, 0) + 1
    summary = "  ".join(f"{k}: {v}" for k, v in counts.items())
    ax.text(0.98, 0.97, summary,
            transform=ax.transAxes, ha="right", va="top",
            fontsize=6.4, color="#333333",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=6)

    ax.set_xlabel("Knudsen number Kn")
    ax.set_ylabel("Reynolds number Re")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    # Legend below axes to avoid the regime labels.
    ax.legend(fontsize=6.8, frameon=False, loc="upper center",
              bbox_to_anchor=(0.5, -0.14),
              handlelength=1.0, ncols=len(unique), columnspacing=1.2)
    return ax
