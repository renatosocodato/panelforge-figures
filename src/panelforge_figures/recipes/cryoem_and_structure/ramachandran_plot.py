"""Ramachandran φ/ψ plot — backbone dihedrals with favored / allowed regions."""

from __future__ import annotations

import matplotlib.patches as mpatches
import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
)
from ._aesthetic import AESTHETIC


class RamachandranInput(RecipeContract):
    phi_deg: list[float] = Field(...)
    psi_deg: list[float] = Field(...)
    residue_type: list[str] | None = Field(
        None, description="optional category (e.g. 'glycine', 'proline', 'generic')"
    )
    title: str = "Ramachandran plot"


def _demo() -> RamachandranInput:
    rng = np.random.default_rng(451)
    # Three clusters: α-helix, β-sheet, left-handed.
    alpha = np.column_stack([rng.normal(-63, 10, 180), rng.normal(-43, 10, 180)])
    beta = np.column_stack([rng.normal(-120, 14, 120), rng.normal(130, 14, 120)])
    left = np.column_stack([rng.normal(60, 12, 30), rng.normal(40, 14, 30)])
    # Sparse outliers.
    out = np.column_stack([rng.uniform(-180, 180, 18), rng.uniform(-180, 180, 18)])
    pts = np.vstack([alpha, beta, left, out])
    return RamachandranInput(
        phi_deg=pts[:, 0].tolist(),
        psi_deg=pts[:, 1].tolist(),
    )


_META = RecipeMetadata(
    name="ramachandran_plot",
    modality="cryoem_and_structure",
    family=RecipeFamily.scatter_collapse,
    answers_question="Do backbone φ/ψ dihedrals cluster in favored Ramachandran regions, and how many outliers are there?",
    required_fields=("phi_deg", "psi_deg"),
    optional_fields=("residue_type", "title"),
    file_format_hints=("pdb", "mmcif", "csv"),
    alternatives_in_modality=("fsc_resolution_curve",),
)


@register_recipe(metadata=_META, contract=RamachandranInput, demo_contract=_demo)
def render(contract: RamachandranInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.2, 4.0))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    # Favored ellipses (simplified).
    favored = [
        (-63, -43, 22, 20, "α"),       # α helix
        (-120, 130, 25, 20, "β"),      # β sheet
        (60, 40, 15, 15, "L"),         # left-handed
    ]
    for cx, cy, rx, ry, label in favored:
        ax.add_patch(mpatches.Ellipse(
            (cx, cy), 2 * rx, 2 * ry,
            facecolor=palette[3], edgecolor="none", alpha=0.18, zorder=1,
        ))
        # Wider allowed region.
        ax.add_patch(mpatches.Ellipse(
            (cx, cy), 3.2 * rx, 3.2 * ry,
            facecolor=palette[3], edgecolor="none", alpha=0.08, zorder=1,
        ))
        ax.text(cx, cy, label, ha="center", va="center",
                fontsize=7.0, color="#444444", fontweight="bold")

    phi = np.array(contract.phi_deg, dtype=float)
    psi = np.array(contract.psi_deg, dtype=float)
    # Classify each point: inside any favored ellipse?
    inside = np.zeros(phi.size, dtype=bool)
    for cx, cy, rx, ry, _ in favored:
        inside |= (((phi - cx) / (1.6 * rx)) ** 2
                   + ((psi - cy) / (1.6 * ry)) ** 2) < 1.0
    ax.scatter(phi[inside], psi[inside], s=10, color=palette[5],
               alpha=0.7, edgecolor="none", zorder=3, label="favored")
    ax.scatter(phi[~inside], psi[~inside], s=14, color="#D32F2F",
               alpha=0.85, edgecolor="white", linewidth=0.4,
               zorder=4, label=f"outlier ({int((~inside).sum())})")

    ax.axhline(0, color="#BBBBBB", lw=0.4, zorder=1)
    ax.axvline(0, color="#BBBBBB", lw=0.4, zorder=1)
    ax.set_xlim(-180, 180)
    ax.set_ylim(-180, 180)
    ax.set_xticks([-180, -90, 0, 90, 180])
    ax.set_yticks([-180, -90, 0, 90, 180])
    ax.set_xlabel(r"$\varphi$ (deg)")
    ax.set_ylabel(r"$\psi$ (deg)")
    ax.set_aspect("equal")

    frac_favored = 100 * inside.sum() / max(inside.size, 1)
    ax.set_title(
        f"{contract.title}  ·  favored {frac_favored:.1f}%",
        fontsize=8.6, pad=4,
    )
    ax.legend(fontsize=6.6, frameon=False, loc="lower left",
              handlelength=1.2)
    return ax
