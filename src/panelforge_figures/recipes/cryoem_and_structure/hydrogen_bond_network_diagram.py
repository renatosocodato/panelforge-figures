"""Hydrogen-bond network diagram — central residue node with H-bond
partners radially arranged. Line thickness ∝ occupancy fraction.

Conceptual family: ≥3 text labels + ≥2 Circle patches.
"""

from __future__ import annotations

import numpy as np
import matplotlib.patches as mpatches
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class HBondPartner(RecipeContract):
    residue: str
    occupancy: float = Field(..., ge=0.0, le=1.0,
                             description="H-bond occupancy fraction across ensemble")
    distance_angstrom: float = Field(..., ge=0.0,
                                     description="mean H-bond distance in Å")


class HBondNetworkInput(RecipeContract):
    central_residue: str = Field(..., description="central residue name / label")
    partners: list[HBondPartner] = Field(..., min_length=3)
    title: str = "H-bond network"


def _demo() -> HBondNetworkInput:
    return HBondNetworkInput(
        central_residue="Asp 124",
        partners=[
            HBondPartner(residue="Lys 88",  occupancy=0.96,
                         distance_angstrom=2.7),
            HBondPartner(residue="Tyr 156", occupancy=0.83,
                         distance_angstrom=2.9),
            HBondPartner(residue="Thr 160", occupancy=0.65,
                         distance_angstrom=3.1),
            HBondPartner(residue="Arg 92",  occupancy=0.48,
                         distance_angstrom=3.3),
            HBondPartner(residue="Ser 162", occupancy=0.35,
                         distance_angstrom=3.4),
            HBondPartner(residue="Wat 203", occupancy=0.58,
                         distance_angstrom=2.8),
            HBondPartner(residue="Glu 96",  occupancy=0.24,
                         distance_angstrom=3.5),
        ],
    )


_META = RecipeMetadata(
    name="hydrogen_bond_network_diagram",
    modality="cryoem_and_structure",
    family=RecipeFamily.conceptual,
    answers_question=(
        "Around a key residue, what is the hydrogen-bond network and "
        "how often is each bond occupied across the ensemble?"
    ),
    required_fields=("central_residue", "partners"),
    optional_fields=("title",),
    file_format_hints=("yaml", "json"),
    alternatives_in_modality=("bfactor_vs_residue",),
)


@register_recipe(
    metadata=_META,
    contract=HBondNetworkInput,
    demo_contract=_demo,
)
def render(contract: HBondNetworkInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 4.2))
    AESTHETIC.apply_to_ax(ax)

    partners = list(contract.partners)
    n = len(partners)
    theta = np.linspace(0, 2 * np.pi, n, endpoint=False) + np.pi / 2

    # Partner radius varies slightly with distance for visual effect.
    r_min = 0.78
    r_max = 1.02
    distances = np.asarray([p.distance_angstrom for p in partners], float)
    d_norm = (distances - distances.min()) / max(
        distances.max() - distances.min(), 1e-9
    )
    radii = r_min + (r_max - r_min) * d_norm

    # Central residue node.
    ax.add_patch(mpatches.Circle(
        (0, 0), 0.16, facecolor="#0D47A1", edgecolor="white",
        linewidth=1.2, zorder=5,
    ))
    ax.text(0, 0, contract.central_residue,
            ha="center", va="center", fontsize=7.2,
            color="white", fontweight="bold", zorder=6)

    # Partner nodes + edges.
    for th, r, p in zip(theta, radii, partners):
        x = r * np.cos(th)
        y = r * np.sin(th)
        # Edge: dashed when occupancy < 0.5, solid otherwise.
        lw = 0.5 + 2.0 * p.occupancy
        alpha = 0.35 + 0.55 * p.occupancy
        ls = "-" if p.occupancy >= 0.5 else "--"
        ax.plot([0, x], [0, y], color="#555555", lw=lw, ls=ls,
                alpha=alpha, zorder=2)

        # Partner node.
        if "Wat" in p.residue or "HOH" in p.residue:
            color = "#1E88E5"
        else:
            color = "#2E7D32"
        ax.add_patch(mpatches.Circle(
            (x, y), 0.10, facecolor=color, edgecolor="white",
            linewidth=0.8, alpha=0.92, zorder=4,
        ))
        # Partner label outside the marker.
        label_r = r + 0.18
        ax.text(label_r * np.cos(th), label_r * np.sin(th),
                f"{p.residue}\nocc {smart_fmt(p.occupancy)}  "
                f"d = {smart_fmt(p.distance_angstrom)} Å",
                ha="center", va="center", fontsize=6.2,
                color=color, zorder=6)

    # Legend.
    proxies = [
        mpatches.Patch(facecolor="#2E7D32", label="residue"),
        mpatches.Patch(facecolor="#1E88E5", label="water"),
    ]
    ax.legend(handles=proxies, fontsize=6.8, frameon=False,
              loc="lower center", bbox_to_anchor=(0.5, -0.08),
              ncols=2, handlelength=1.0)

    ax.set_xlim(-1.5, 1.5)
    ax.set_ylim(-1.5, 1.5)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)

    occ_mean = float(np.mean([p.occupancy for p in partners]))
    ax.set_title(
        f"{contract.title}  ·  {contract.central_residue}  ·  "
        f"{n} partners, mean occ = {smart_fmt(occ_mean)}",
        fontsize=8.4, pad=4,
    )
    return ax
