"""Per-residue B-factor profile — chain-colored strip with secondary-structure bands."""

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
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class BFactorInput(RecipeContract):
    residue_index: list[int] = Field(...)
    b_factor: list[float] = Field(...)
    secondary_structure: list[str] | None = Field(
        None, description="per-residue 'H' (helix), 'E' (sheet), 'C' (coil), or None"
    )
    title: str = "Per-residue B-factor"


def _demo() -> BFactorInput:
    rng = np.random.default_rng(453)
    n = 320
    idx = np.arange(1, n + 1)
    b = 30 + 25 * np.sin(idx * 0.08) + rng.normal(0, 8, n)
    b = np.clip(b, 5, None)
    ss = []
    for i in idx:
        if 30 <= i < 70 or 140 <= i < 180 or 240 <= i < 290:
            ss.append("H")
        elif 90 <= i < 120 or 200 <= i < 225:
            ss.append("E")
        else:
            ss.append("C")
    return BFactorInput(
        residue_index=idx.tolist(),
        b_factor=b.tolist(),
        secondary_structure=ss,
    )


_META = RecipeMetadata(
    name="bfactor_vs_residue",
    modality="cryoem_and_structure",
    family=RecipeFamily.diagnostic_curve,
    answers_question="Which residues have the highest thermal / conformational flexibility, and how does that align with secondary structure?",
    required_fields=("residue_index", "b_factor"),
    optional_fields=("secondary_structure", "title"),
    file_format_hints=("pdb", "csv"),
    alternatives_in_modality=("local_resolution_surface",),
)


@register_recipe(metadata=_META, contract=BFactorInput, demo_contract=_demo)
def render(contract: BFactorInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 3.0))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    idx = np.array(contract.residue_index, dtype=int)
    b = np.array(contract.b_factor, dtype=float)

    ax.plot(idx, b, color=palette[5], lw=1.1, zorder=3, label="B-factor")
    ax.fill_between(idx, 0, b, color=palette[5], alpha=0.18,
                    linewidth=0, zorder=2)
    ax.axhline(float(np.median(b)), color="#888888", lw=0.7, ls="--",
               zorder=1, label=f"median = {smart_fmt(float(np.median(b)))} $\\AA^2$")

    # Flexibility hotspots (top 5%).
    threshold = float(np.percentile(b, 95))
    hot = b >= threshold
    ax.scatter(idx[hot], b[hot], s=14, color="#D32F2F",
               edgecolor="white", linewidth=0.5, zorder=5,
               label=f"top 5% (≥{smart_fmt(threshold)})")

    # Secondary-structure strip along the bottom.
    if contract.secondary_structure is not None:
        ss_colors = {"H": "#1565C0", "E": "#D32F2F", "C": "#BDBDBD"}
        y_strip = -max(0.05, b.max() * 0.08)
        current_ss = contract.secondary_structure[0]
        start = idx[0]
        h = abs(y_strip) * 1.6
        for i in range(1, len(contract.secondary_structure) + 1):
            ss_i = (contract.secondary_structure[i]
                    if i < len(contract.secondary_structure) else None)
            if ss_i != current_ss or ss_i is None:
                end = idx[i - 1]
                ax.add_patch(mpatches.Rectangle(
                    (start - 0.5, y_strip - h / 2),
                    (end - start + 1), h,
                    facecolor=ss_colors.get(current_ss, "#BDBDBD"),
                    edgecolor="none", alpha=0.85, zorder=2,
                ))
                if ss_i is not None:
                    start = idx[i]
                    current_ss = ss_i

    ax.set_xlim(int(idx.min()), int(idx.max()))
    ax.set_ylim(y_strip * 2 if contract.secondary_structure is not None else 0,
                b.max() * 1.12)
    ax.set_xlabel("residue index")
    ax.set_ylabel(r"B-factor ($\AA^2$)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.6, frameon=False, loc="upper right",
              handlelength=1.2)
    ax.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
